"""Workload -> service level -> FTE -> paid headcount.

The chain, in one place:

    contacts x AHT                      -> workload hours
    real-time channels: Erlang C        -> concurrent seats (occupancy < 100%)
    deferred channels: / occupancy      -> seat-equivalent hours
    / (1 - shrinkage)                   -> paid hours
    / hours per FTE                     -> FTE meeting SLA
    / tenure efficiency                 -> on-floor FTE (learning curve)
    + training class                    -> paid FTE (the bill)
"""
from __future__ import annotations
import pandas as pd

from .config import Assumptions, REALTIME_CHANNELS, DEFERRED_CHANNELS
from .erlang import solve_queue


def language_bpo_map(a: Assumptions) -> dict[str, str]:
    """Each language -> its serving BPO. English has two; the AHT used is the
    split-weighted blend so the capacity number is split-agnostic."""
    out = {}
    for bpo, langs in a.bpo_languages.items():
        for l in langs:
            out.setdefault(l, []).append(bpo)
    return out


def effective_aht(assumptions_df: pd.DataFrame, a: Assumptions) -> pd.DataFrame:
    """One AHT per language x channel, weighting multi-BPO languages by the
    declared split."""
    lb = language_bpo_map(a)
    recs = []
    for lang, bpos in lb.items():
        rows = assumptions_df[(assumptions_df.language == lang) &
                              (assumptions_df.bpo.isin(bpos))]
        if rows.empty:
            raise ValueError(f"no AHT row for {lang} in {bpos}")
        w = {b: a.english_bpo_split.get(b, 1.0 / len(bpos)) for b in bpos}
        tot = sum(w[b] for b in bpos)
        for ch in ("Email", "Inbound", "Outbound", "Chat"):
            val = sum(rows[rows.bpo == b][ch].iloc[0] * w[b] for b in bpos) / tot
            recs.append({"language": lang, "channel": ch, "aht": val,
                         "concurrency": float(rows.concurrency.iloc[0]),
                         "bpos": "+".join(bpos)})
    return pd.DataFrame(recs)


def queue_capacity(volume_by_channel: pd.DataFrame, aht: pd.DataFrame,
                   a: Assumptions) -> pd.DataFrame:
    """One row per scenario x month x language x channel."""
    df = volume_by_channel.merge(aht, on=["language", "channel"])
    rows = []
    for r in df.itertuples():
        target, secs = a.sla_for(r.channel)
        rec = {"scenario": r.scenario, "month": r.month, "language": r.language,
               "channel": r.channel, "contacts": r.contacts, "aht": r.aht,
               "bpos": r.bpos}
        if r.channel in REALTIME_CHANNELS:
            conc = r.concurrency if r.channel == "Chat" else 1.0
            q = solve_queue(r.contacts, r.aht, a.ops_hours_per_month,
                            target, secs, concurrency=conc)
            rec.update(model="ErlangC", erlangs=q["erlangs"], seats_raw=q["seats_raw"],
                       seats=q["seats"], concurrency=conc, occupancy=q["occupancy"],
                       service_level=q["service_level"], asa_seconds=q["asa_seconds"],
                       workload_hours=q["workload_hours"],
                       seat_hours=q["seats"] * a.ops_hours_per_month)
        else:
            wl = r.contacts * r.aht / 3600.0
            rec.update(model="deferred", erlangs=float("nan"), seats_raw=float("nan"),
                       seats=wl / a.deferred_occupancy / a.ops_hours_per_month,
                       concurrency=1.0, occupancy=a.deferred_occupancy,
                       service_level=float("nan"), asa_seconds=float("nan"),
                       workload_hours=wl, seat_hours=wl / a.deferred_occupancy)
        rec["productive_hours"] = rec["seat_hours"]
        rec["paid_hours"] = rec["seat_hours"] / a.shrink_divisor
        rec["fte"] = rec["paid_hours"] / a.hours_per_fte_month
        rec["fte_workload_only"] = (rec["workload_hours"] / a.shrink_divisor
                                    / a.hours_per_fte_month)
        rows.append(rec)
    return pd.DataFrame(rows)


def headcount_build(queues: pd.DataFrame, a: Assumptions,
                    month_order: list[str] | None = None,
                    scenario_order=("LOW", "BASE", "HIGH")) -> pd.DataFrame:
    """Roll queues up to the number the business actually pays for."""
    g = (queues.groupby(["scenario", "month"], as_index=False)
         .agg(contacts=("contacts", "sum"),
              workload_hours=("workload_hours", "sum"),
              productive_hours=("productive_hours", "sum"),
              fte_sla=("fte", "sum"),
              fte_workload_only=("fte_workload_only", "sum")))
    g["sla_uplift_pct"] = g.fte_sla / g.fte_workload_only - 1
    g["fte_on_floor"] = g.fte_sla / a.tenure_efficiency
    g["fte_in_training"] = g.fte_on_floor * a.attrition_monthly
    g["fte_paid"] = g.fte_on_floor + g.fte_in_training
    g["monthly_backfill_hires"] = g.fte_paid * a.attrition_monthly
    if month_order:
        g["month"] = pd.Categorical(g.month, categories=month_order, ordered=True)
    g["scenario"] = pd.Categorical(g.scenario, categories=scenario_order, ordered=True)
    return g.sort_values(["scenario", "month"]).reset_index(drop=True)


def by_bpo(queues: pd.DataFrame, a: Assumptions) -> pd.DataFrame:
    """Per-vendor FTE and productive hours - the number each BPO is briefed on
    and billed for (contracts are cost-per-productive-hour)."""
    rows = []
    for r in queues.itertuples():
        bpos = r.bpos.split("+")
        for b in bpos:
            w = a.english_bpo_split.get(b, 1.0 / len(bpos)) if len(bpos) > 1 else 1.0
            tot = sum(a.english_bpo_split.get(x, 1.0 / len(bpos)) for x in bpos) if len(bpos) > 1 else 1.0
            rows.append({"scenario": r.scenario, "month": r.month, "bpo": b,
                         "language": r.language, "channel": r.channel,
                         "fte": r.fte * w / tot,
                         "productive_hours": r.productive_hours * w / tot,
                         "contacts": r.contacts * w / tot})
    return pd.DataFrame(rows)
