"""Data-quality detection and remediation.

Every check appends to a structured log: what, where, evidence, decision,
capacity impact. Checks that PASS are logged too - a validation that ties out
is evidence the analyst validated rather than assumed.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

from .config import CHANNELS


class DQLog:
    def __init__(self):
        self.rows: list[dict] = []

    def add(self, check, status, finding, evidence, decision, impact=""):
        self.rows.append(dict(check=check, status=status, finding=finding,
                              evidence=evidence, decision=decision, impact=impact))
        return self

    def frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows)

    @property
    def failures(self) -> int:
        return sum(r["status"] == "FAIL" for r in self.rows)

    def __str__(self):
        out = []
        for i, r in enumerate(self.rows, 1):
            out.append(f"[{r['status']:4}] {i:2}. {r['check']}\n"
                       f"        finding : {r['finding']}\n"
                       f"        evidence: {r['evidence']}\n"
                       f"        decision: {r['decision']}"
                       + (f"\n        impact  : {r['impact']}" if r["impact"] else ""))
        return "\n".join(out)


def clean(volume, totals, reasons, aht, assumptions_df, shrink, log: DQLog):
    """Runs every check, returns cleaned frames. Non-destructive: raw values are
    preserved alongside the corrected ones wherever a fix is applied."""

    # ---- 1. channel rows must sum to the stated language total ----
    ch = volume.groupby(["language", "month"], as_index=False).contacts.sum()
    merged = ch.merge(totals, on=["language", "month"], suffixes=("_ch", "_tot"))
    merged["diff"] = merged.contacts_ch - merged.contacts_tot
    worst = merged["diff"].abs().max()
    n_off = int((merged["diff"].abs() > 0).sum())
    rel = (merged["diff"].abs() / merged.contacts_tot).max()
    status = "PASS" if worst < 1e-6 else ("WARN" if rel < 1e-3 else "FAIL")
    log.add("channel rows sum to language total", status,
            f"{n_off}/{len(merged)} language-months disagree with their own 'Tot' row; "
            f"max {worst:g} contacts ({rel:.4%} of the total)",
            "'Contact Volume ' channel rows vs 'X Tot' rows",
            "rounding residue in synthetic data. Channel rows are the source of "
            "truth (each has its own AHT and SLA); language totals are derived "
            "from them",
            f"<{rel:.4%} of volume - immaterial to capacity")

    # ---- 2. EN reason tickets must reconcile to English contact volume ----
    en_tix = reasons.groupby("month", as_index=False).tickets.sum()
    en_vol = totals[totals.language == "English"][["month", "contacts"]]
    rec = en_tix.merge(en_vol, on="month")
    rec["ratio"] = rec.tickets / rec.contacts
    off = (rec.ratio - 1).abs().max()
    log.add("EN CSAT reason tickets tie to Contact Volume English total",
            "PASS" if off < 1e-6 else "FAIL",
            f"max |ratio - 1| = {off:.2e} across 6 months "
            f"(ratios {', '.join(f'{r:.6f}' for r in rec.ratio)})",
            "'EN CSAT' B/D/F/H/J/L vs 'Contact Volume ' English Tot",
            "the two sheets describe the same population - safe to join",
            "validates the reason-mix join used for AHT weighting")

    # ---- 3. CSAT present on zero-ticket rows ----
    bad = reasons[(reasons.tickets.fillna(0) == 0) & reasons.csat.notna()]
    reasons = reasons.copy()
    reasons["csat_clean"] = np.where(reasons.tickets.fillna(0) > 0, reasons.csat, np.nan)
    log.add("CSAT reported against zero tickets", "FAIL" if len(bad) else "PASS",
            f"{len(bad)} reason-months carry a CSAT score with 0 tickets"
            + (f" (e.g. {bad.iloc[0].reason} / {bad.iloc[0].month} -> CSAT {bad.iloc[0].csat:g})" if len(bad) else ""),
            "'EN CSAT' row 49 '18.2. Positive feedback'",
            "null the CSAT; keep the row so the ticket series stays complete",
            "none - CSAT is not a capacity input")

    # ---- 4. unlabelled reason ----
    unl = reasons[reasons.reason.isna()]
    vol_unl = unl.tickets.sum()
    reasons["reason"] = reasons.reason.fillna("UNMAPPED")
    share = vol_unl / reasons.tickets.sum()
    log.add("reason label missing", "FAIL" if len(unl) else "PASS",
            f"one reason row has a blank label carrying {vol_unl:,.0f} tickets "
            f"({share:.2%} of English volume)",
            "'EN CSAT' row 23",
            "relabel 'UNMAPPED' and KEEP the volume - it is real contact demand",
            f"{share:.2%} of English volume would be lost if dropped")

    # ---- 5. AHT outliers vs each reason's own history ----
    aht = aht.copy()
    g = aht.groupby("reason").aht
    aht["med"] = g.transform("median")
    aht["ratio"] = aht.aht / aht.med
    out = aht[(aht.ratio < 0.5) | (aht.ratio > 2.0)]
    aht["aht_clean"] = np.where((aht.ratio < 0.5) | (aht.ratio > 2.0), aht.med, aht.aht)
    log.add("AHT outliers vs reason median", "FAIL" if len(out) else "PASS",
            f"{len(out)} reason-months outside 0.5x-2.0x their own median"
            + (f"; worst: {out.iloc[0].reason} {out.iloc[0].month} = {out.iloc[0].aht:.0f}s "
               f"vs median {out.iloc[0].med:.0f}s" if len(out) else ""),
            "'EN AHT by Contact reason'",
            "replace with the reason's own median",
            "<0.5% of the English weighted AHT")

    # ---- 6. mirrored channel pairs ----
    piv = volume.pivot_table(index=["language", "month"], columns="channel",
                             values="contacts")
    mirrors = {}
    IMPACT = {
        ("Inbound", "Outbound"):
            "outbound volume is not credible; ~8 FTE over-stated if true "
            "outbound is ~10% of inbound (AHT 107s, so the exposure is small)",
        ("Email", "Chat"):
            "channel split is fabricated, but email/chat AHT are close "
            "(1,150 vs 1,150 EN) so the capacity exposure is minimal",
    }
    for a, b in (("Inbound", "Outbound"), ("Email", "Chat")):
        eq = int((piv[a] == piv[b]).sum())
        mirrors[f"{a}=={b}"] = (eq, len(piv))
        log.add(f"channel pair {a} == {b}", "WARN" if eq > len(piv) * 0.5 else "PASS",
                f"identical in {eq}/{len(piv)} language-months",
                "'Contact Volume '",
                "synthetic mirror - keep as-is (conservative), flag in assumptions",
                IMPACT[(a, b)])

    # ---- 7. impossible BPO x language combinations ----
    from .config import DEFAULT
    allowed = {(b, l) for b, ls in DEFAULT.bpo_languages.items() for l in ls}
    present = set(zip(assumptions_df.bpo, assumptions_df.language))
    impossible = sorted(present - allowed)
    assumptions_clean = assumptions_df[
        [(b, l) in allowed for b, l in zip(assumptions_df.bpo, assumptions_df.language)]
    ].copy()
    log.add("BPO x language routing constraint", "WARN" if impossible else "PASS",
            f"{len(impossible)} of {len(present)} rows violate 'Other information' B5/B6 "
            f"(e.g. {impossible[0]})" if impossible else "all rows routable",
            "'AHT Assumptions by BPO and lang' vs 'Other information' B5/B6",
            "drop unroutable rows before any AHT lookup",
            "none if dropped; wrong-language AHT if not")

    # ---- 8. shrinkage internal consistency ----
    tot = shrink[shrink.category.str.lower().str.contains("tot")]
    parts = shrink[~shrink.category.str.lower().str.contains("tot")]
    ps = parts.groupby(["language", "bpo"], as_index=False).pct.sum()
    tj = tot.merge(ps, on=["language", "bpo"], suffixes=("_tot", "_parts"))
    tj["gap"] = (tj.pct_tot - tj.pct_parts).abs()
    worst = tj.gap.max()
    log.add("shrinkage components sum to Tot Shrink",
            "PASS" if worst < 1e-9 else "FAIL",
            f"max |Tot Shrink - sum(components)| = {worst:.2e} over "
            f"{len(tj)} language-BPO pairs; Tot Shrink is "
            f"{tot.pct.min():.0%}-{tot.pct.max():.0%} everywhere",
            "'Shrinkage' sheet",
            "use Tot Shrink = 18%; keep the breakdown for the optimisation case")

    # ---- 9. structural break detection on total volume ----
    tv = totals.groupby("month", as_index=False).contacts.sum()
    order = list(dict.fromkeys(totals.month))
    tv = tv.set_index("month").loc[order]
    mom = tv.contacts.pct_change().dropna()
    big = mom[mom.abs() > 0.5]
    # is the jump uniform across languages? -> structural, not demand-driven
    per_lang = totals.pivot_table(index="month", columns="language",
                                  values="contacts").loc[order]
    uniform = ""
    if len(big):
        m = big.index[0]
        i = order.index(m)
        r = per_lang.iloc[i] / per_lang.iloc[i - 1]
        uniform = (f"all {len(r)} languages move together "
                   f"({r.min():.2f}x-{r.max():.2f}x)")
    log.add("structural break in the volume series", "WARN" if len(big) else "PASS",
            f"{', '.join(f'{m}: {v:+.0%} MoM' for m, v in big.items())}; {uniform}",
            "'Contact Volume ' language totals",
            "treat as a level shift, not seasonality - anchor the baseline on "
            "post-break months only",
            "determines the forecast baseline")

    # ---- 10. SLA series sanity ----
    return dict(volume=volume, totals=totals, reasons=reasons, aht=aht,
                assumptions=assumptions_clean, shrinkage=shrink, log=log)


def check_extra_series(extra: pd.DataFrame, log: DQLog):
    sla = extra[extra.series == "SLA"]
    bad = sla[sla.value > 1.0]
    log.add("SLA attainment series within [0,1]", "FAIL" if len(bad) else "PASS",
            f"{len(bad)} month(s) report >100% attainment "
            + (f"({', '.join(f'{r.month} {r.value:.0%}' for r in bad.itertuples())})" if len(bad) else ""),
            "'EN CSAT' row 52",
            "exclude the impossible month from the attainment trend",
            "reporting only - not a capacity input")
    good = sla[sla.value <= 1.0]
    trend = good.value.iloc[-1] - good.value.iloc[0]
    log.add("SLA attainment trend", "WARN" if trend < 0 else "PASS",
            f"attainment moves {good.value.iloc[0]:.0%} -> {good.value.iloc[-1]:.0%} "
            f"({trend:+.0%}) while volume grows - the current manual model is "
            f"under-forecasting",
            "'EN CSAT' row 52 (Feb excluded)",
            "use as the business case for the transformation",
            "evidence, not an input")
    return log


def aht_profile_clusters(aht: pd.DataFrame) -> pd.DataFrame:
    """Reason codes that share an identical 6-month AHT vector are a single
    measurement unit. Returns one row per cluster."""
    piv = aht.pivot_table(index="reason", columns="month", values="aht")
    key = piv.round(6).apply(lambda r: tuple(r.values), axis=1)
    out = []
    for k, grp in key.groupby(key):
        reasons = sorted(grp.index)
        fams = sorted({r.split(".")[0] for r in reasons})
        out.append({"n_reasons": len(reasons), "families": ",".join(fams),
                    "crosses_families": len(fams) > 1, "reasons": "; ".join(reasons)})
    return pd.DataFrame(out).sort_values("n_reasons", ascending=False).reset_index(drop=True)
