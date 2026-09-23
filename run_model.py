#!/usr/bin/env python
"""End-to-end WFM capacity model.

    python run_model.py [--workbook FILE] [--excel OUT.xlsx] [--aht-source channel|reason]

Reads the 6 visible sheets, cleans, forecasts 3 months x 3 scenarios, solves
service levels, and writes an operational workbook.
"""
from __future__ import annotations
import argparse, sys
import pandas as pd

from wfm import config, clean, forecast, capacity, optimise
from wfm.loader import Workbook

pd.set_option("display.width", 200, "display.max_columns", 50)


def banner(t):
    print(f"\n{'=' * 78}\n{t}\n{'=' * 78}")


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--workbook", default=config.WORKBOOK)
    p.add_argument("--excel", default="WFM_Capacity_Model_Output.xlsx")
    p.add_argument("--aht-source", default="channel", choices=["channel", "reason"])
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args(argv)

    a = config.Assumptions(english_aht_source=args.aht_source)

    # ---------------- load ----------------
    wb = Workbook(args.workbook)
    volume, totals = wb.contact_volume()
    assum = wb.aht_assumptions()
    shrink = wb.shrinkage()
    reasons, extra = wb.en_reasons()
    en_aht = wb.en_aht()

    banner("1. LOAD")
    print(f"workbook       : {args.workbook}")
    print(f"sheets read    : {len(config.VISIBLE_SHEETS)} visible")
    print(f"sheets excluded: {wb.excluded} (hidden - excluded by instruction)")
    print(f"languages      : {sorted(totals.language.unique())}")
    print(f"channels       : {sorted(volume.channel.unique())}")
    print(f"months         : {forecast.month_order(totals)}")

    # ---------------- clean ----------------
    log = clean.DQLog()
    cl = clean.clean(volume, totals, reasons, en_aht, assum, shrink, log)
    clean.check_extra_series(extra, log)
    banner("2. DATA QUALITY")
    if not args.quiet:
        print(log)
    dq = log.frame()
    print(f"\n-> {(dq.status=='PASS').sum()} validations passed, "
          f"{(dq.status=='FAIL').sum()} defects corrected, "
          f"{(dq.status=='WARN').sum()} flagged as immaterial or by-design")

    clusters = clean.aht_profile_clusters(cl["aht"])
    n_cross = int(clusters.crosses_families.sum())
    print(f"-> AHT taxonomy: {len(cl['aht'].reason.unique())} reason codes collapse to "
          f"{len(clusters)} distinct AHT profiles; {n_cross} clusters cross reason families")

    # ---------------- forecast ----------------
    brk = forecast.detect_break(cl["totals"])
    fc = forecast.VolumeForecast(cl["volume"], cl["totals"], config.FORECAST_MONTHS,
                                 a.seasonal_uplift, brk["month"] if brk else None)
    banner("3. VOLUME FORECAST")
    if brk:
        print(f"structural break : {brk['month']} (+{brk['total_ratio']-1:.0%} total, "
              f"uniform across languages = {brk['uniform']})")
    print(f"baseline month   : {fc.baseline_month}\n")
    gp = fc.growth_profile()
    print(gp[["baseline", "post_break_change", "trend_per_month",
              "trend_pct_of_baseline", "r2", "sigma_logret", "growing"]].to_string(
        float_format=lambda v: f"{v:,.3f}"))
    sc = fc.scenarios()
    print("\nscenario totals:")
    print(sc.pivot_table(index="month", columns="scenario", values="contacts",
                         aggfunc="sum").reindex(config.FORECAST_MONTHS)
          [["LOW", "BASE", "HIGH"]].to_string(float_format=lambda v: f"{v:,.0f}"))

    # ---------------- capacity ----------------
    aht_eff = capacity.effective_aht(cl["assumptions"], a)
    vbc = fc.by_channel()
    queues = capacity.queue_capacity(vbc, aht_eff, a)
    build = capacity.headcount_build(queues, a, list(config.FORECAST_MONTHS))

    banner("4. CAPACITY")
    print("effective AHT (seconds), split-weighted where a language has 2 BPOs:")
    print(aht_eff.pivot_table(index="language", columns="channel", values="aht")
          .to_string(float_format=lambda v: f"{v:,.1f}"))

    base_m = config.FORECAST_MONTHS[0]
    q = queues.query("scenario=='BASE' and month==@base_m")
    print(f"\nBASE / {base_m} - per queue:")
    print(q[["language", "channel", "contacts", "aht", "model", "erlangs",
             "seats_raw", "seats", "occupancy", "service_level", "workload_hours",
             "fte"]].to_string(index=False, float_format=lambda v: f"{v:,.2f}"))

    print(f"\nBASE / {base_m} - per language:")
    pl = q.groupby("language", as_index=False).agg(
        contacts=("contacts", "sum"), workload_hours=("workload_hours", "sum"),
        productive_hours=("productive_hours", "sum"), fte=("fte", "sum"),
        fte_workload_only=("fte_workload_only", "sum"))
    pl["sla_uplift"] = pl.fte / pl.fte_workload_only - 1
    print(pl.to_string(index=False, float_format=lambda v: f"{v:,.1f}"))

    print("\nheadcount build-up:")
    print(build[["scenario", "month", "contacts", "workload_hours", "productive_hours",
                 "fte_workload_only", "fte_sla", "sla_uplift_pct", "fte_on_floor",
                 "fte_in_training", "fte_paid", "monthly_backfill_hires"]]
          .to_string(index=False, float_format=lambda v: f"{v:,.1f}"))

    bpo = capacity.by_bpo(q, a).groupby("bpo", as_index=False).agg(
        fte=("fte", "sum"), productive_hours=("productive_hours", "sum"),
        contacts=("contacts", "sum"))
    print(f"\nBASE / {base_m} - per BPO (the vendor brief / the bill):")
    print(bpo.to_string(index=False, float_format=lambda v: f"{v:,.1f}"))

    # ---------------- uncertainty ----------------
    ci = fc.intervals()
    banner("5. FORECAST UNCERTAINTY")
    sig = ci.sigma.iloc[0]
    fte_base = build.query("scenario=='BASE' and month==@base_m").fte_paid.iloc[0]
    print(f"sigma (log-return sd, structural break excluded) = {sig:.1%}")
    c = ci[ci.month == base_m].copy()
    c["fte_paid"] = fte_base * c.multiplier
    print(c[["percentile", "multiplier", "contacts", "fte_paid"]].to_string(
        index=False, float_format=lambda v: f"{v:,.3f}"))

    # ---------------- optimisation ----------------
    banner("6. OPTIMISATION LEVERS (Task 1b)")
    non_en = [l for l in sorted(totals.language.unique()) if l != "English"]
    pools = [optimise.pool_queues(queues, a, non_en, ch, month=base_m)
             for ch in ("Inbound", "Chat")]
    pf = pd.DataFrame(pools)
    print("Lever 1 - pool the non-English queues (all already in BPO 3):")
    print(pf[["channel", "languages", "siloed_seats_raw", "siloed_occupancy_min",
              "siloed_occupancy_max", "pooled_seats_raw", "pooled_occupancy",
              "pooled_service_level", "fte_siloed", "fte_pooled", "fte_saved"]]
          .to_string(index=False, float_format=lambda v: f"{v:,.3f}"))
    print(f"  => total saved: {pf.fte_saved.sum():.1f} FTE "
          f"({pf.fte_saved.sum()/fte_base:.1%} of paid headcount)")

    cs = optimise.concurrency_sensitivity(queues, a, month=base_m)
    print("\nLever 2 - chat concurrency:")
    print(cs.to_string(index=False, float_format=lambda v: f"{v:,.1f}"))

    dfl = optimise.deflection(queues, a, month=base_m)
    print("\nTest - phone -> chat deflection (the intuitive lever, verified):")
    print(f"  agent-seconds per contact: {dfl.attrs['agent_seconds_per_contact']}")
    print(dfl.to_string(index=False, float_format=lambda v: f"{v:,.1f}"))

    shr = optimise.shrinkage_sensitivity(queues, a, month=base_m)
    print("\nShrinkage sensitivity:")
    print(shr.assign(shrinkage=shr.shrinkage.map(lambda v: f"{v:.0%}"))
          .to_string(index=False, float_format=lambda v: f"{v:,.1f}"))

    latest = forecast.month_order(cl["reasons"])[-1]
    opp = optimise.reason_opportunity(cl["reasons"], cl["aht"], latest)
    print(f"\nTop handling-hour drivers ({latest}, English) - deflection targets:")
    print(opp.to_string(index=False, float_format=lambda v: f"{v:,.1f}"))

    # ---------------- export ----------------
    from wfm.report import write_excel
    write_excel(args.excel, dict(
        assumptions=pd.DataFrame(sorted(
            ((k, str(v)) for k, v in a.to_dict().items()), key=lambda x: x[0]),
            columns=["assumption", "value"]),
        data_quality=dq, aht_clusters=clusters, growth=gp.reset_index(),
        forecast=sc, forecast_by_channel=vbc, queues=queues,
        headcount=build, by_bpo=capacity.by_bpo(queues, a), intervals=ci,
        lever_pooling=pf, lever_concurrency=cs, test_deflection=dfl,
        sens_shrinkage=shr, reason_opportunity=opp,
        effective_aht=aht_eff,
    ))
    banner("7. OUTPUT")
    print(f"written: {args.excel}")
    return dict(build=build, queues=queues, fc=fc, dq=dq, a=a, clusters=clusters,
                pools=pf, concurrency=cs, deflection=dfl, cleaned=cl, aht_eff=aht_eff)


if __name__ == "__main__":
    main()
