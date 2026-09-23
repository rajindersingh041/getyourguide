"""Task 1b - optimisation levers, each quantified end-to-end in FTE.

Every lever is re-solved through the same Erlang engine as the base plan, so a
saving here is directly comparable to the plan's own number. No lever is
asserted; if the arithmetic says it costs FTE, it is reported as a cost.
"""
from __future__ import annotations
import pandas as pd

from .config import Assumptions
from .erlang import solve_queue


def _fte_from_seats(seats: float, a: Assumptions) -> float:
    return seats * a.ops_hours_per_month / a.shrink_divisor / a.hours_per_fte_month


def pool_queues(queues: pd.DataFrame, a: Assumptions, languages: list[str],
                channel: str, scenario="BASE", month=None) -> dict:
    """Merge several single-language queues into one multilingual queue.

    Small queues staffed 24/7 pay the 80/20 minimum-seat floor independently;
    pooling them shares that floor. Only valid where the languages already sit
    in the same BPO."""
    q = queues.query("scenario==@scenario and channel==@channel and language in @languages")
    if month:
        q = q.query("month==@month")
    q = q[q.month == q.month.iloc[0]]
    target, secs = a.sla_for(channel)
    conc = float(q.concurrency.iloc[0])

    siloed_seats = q.seats.sum()
    # pooled: aggregate erlangs, AHT = contact-weighted blend
    contacts = q.contacts.sum()
    aht = (q.contacts * q.aht).sum() / contacts
    pooled = solve_queue(contacts, aht, a.ops_hours_per_month, target, secs, conc)

    return {
        "channel": channel, "languages": "+".join(languages),
        "siloed_seats_raw": int(q.seats_raw.sum()), "siloed_seats": siloed_seats,
        "siloed_occupancy_min": q.occupancy.min(), "siloed_occupancy_max": q.occupancy.max(),
        "pooled_seats_raw": pooled["seats_raw"], "pooled_seats": pooled["seats"],
        "pooled_occupancy": pooled["occupancy"],
        "pooled_service_level": pooled["service_level"],
        "blended_aht": aht, "contacts": contacts,
        "fte_siloed": _fte_from_seats(siloed_seats, a),
        "fte_pooled": _fte_from_seats(pooled["seats"], a),
        "fte_saved": _fte_from_seats(siloed_seats - pooled["seats"], a),
    }


def concurrency_sensitivity(queues: pd.DataFrame, a: Assumptions,
                            values=(1.2, 1.5, 2.0, 2.5, 3.0),
                            scenario="BASE", month=None) -> pd.DataFrame:
    q = queues.query("scenario==@scenario and channel=='Chat'")
    q = q[q.month == (month or q.month.iloc[0])]
    rows = []
    for c in values:
        fte = sum(_fte_from_seats(r.seats_raw / c, a) for r in q.itertuples())
        rows.append({"concurrency": c, "chat_fte": fte})
    base = rows[0]["chat_fte"]
    for r in rows:
        r["delta_vs_1.2"] = r["chat_fte"] - base
    return pd.DataFrame(rows)


def deflection(queues: pd.DataFrame, a: Assumptions, language="English",
               frm="Inbound", to="Chat", shares=(0.0, 0.1, 0.2, 0.3),
               scenario="BASE", month=None) -> pd.DataFrame:
    """Move a share of one channel's contacts into another and re-solve BOTH
    queues. Tests the direction of a deflection claim rather than assuming it."""
    q = queues.query("scenario==@scenario and language==@language")
    q = q[q.month == (month or q.month.iloc[0])]
    src = q[q.channel == frm].iloc[0]
    dst = q[q.channel == to].iloc[0]
    t_s, s_s = a.sla_for(frm)
    t_d, s_d = a.sla_for(to)
    rows = []
    for sh in shares:
        moved = src.contacts * sh
        a1 = solve_queue(src.contacts - moved, src.aht, a.ops_hours_per_month,
                         t_s, s_s, concurrency=(src.concurrency if frm == "Chat" else 1.0))
        a2 = solve_queue(dst.contacts + moved, dst.aht, a.ops_hours_per_month,
                         t_d, s_d, concurrency=(dst.concurrency if to == "Chat" else 1.0))
        fte = _fte_from_seats(a1["seats"] + a2["seats"], a)
        rows.append({"share_moved": sh, "moved_contacts": moved,
                     f"{frm}_seats": a1["seats_raw"], f"{to}_seats": a2["seats_raw"],
                     "combined_fte": fte})
    base = rows[0]["combined_fte"]
    for r in rows:
        r["delta_fte"] = r["combined_fte"] - base
    df = pd.DataFrame(rows)
    df.attrs["agent_seconds_per_contact"] = {
        frm: src.aht / (src.concurrency if frm == "Chat" else 1.0),
        to: dst.aht / (dst.concurrency if to == "Chat" else 1.0)}
    return df


def shrinkage_sensitivity(queues: pd.DataFrame, a: Assumptions,
                          points=(0.16, 0.17, 0.18, 0.19, 0.20),
                          scenario="BASE", month=None) -> pd.DataFrame:
    q = queues.query("scenario==@scenario")
    q = q[q.month == (month or q.month.iloc[0])]
    seat_hours = q.seat_hours.sum()
    rows = []
    for s in points:
        rows.append({"shrinkage": s,
                     "fte": seat_hours / (1 - s) / a.hours_per_fte_month})
    base = next(r["fte"] for r in rows if abs(r["shrinkage"] - a.shrinkage) < 1e-9)
    for r in rows:
        r["delta_fte"] = r["fte"] - base
    return pd.DataFrame(rows)


def reason_opportunity(reasons: pd.DataFrame, aht: pd.DataFrame,
                       month: str, top: int = 12) -> pd.DataFrame:
    """Effort x satisfaction: where volume, handling time and CSAT all point the
    same way. Drives the 'deflect out of the centre' case."""
    r = reasons[reasons.month == month][["reason", "tickets", "csat_clean"]]
    aa = aht[aht.month == month][["reason", "aht_clean"]]
    df = r.merge(aa, on="reason", how="left")
    df["handling_hours"] = df.tickets * df.aht_clean / 3600
    df["share_of_hours"] = df.handling_hours / df.handling_hours.sum()
    med = df.csat_clean.median()
    df["low_csat"] = df.csat_clean < med
    return (df.sort_values("handling_hours", ascending=False)
            .head(top).reset_index(drop=True))
