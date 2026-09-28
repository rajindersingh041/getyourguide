# Task 1b — Optimisation findings

All numbers re-solved through the same Erlang engine as the base capacity plan
(`wfm/optimise.py`), Jul BASE scenario unless noted. Ranked here by
effort-to-act, not by FTE size — the biggest numbers are verification asks,
not actions.

---

## Ease-vs-impact summary

| Lever | FTE | Dependency before you can act | Action today, alone? |
|---|---|---|---|
| BPO1/BPO2 channel routing (English) | 4.5 | None | **Yes** |
| Pool Spanish + French (pilot) | 18.8 | Confirm bilingual agents exist at BPO3 | No — one check first |
| Pool all 4 non-English (phase 2) | 51.4 cumulative | Pilot validates first | No |
| Add English to the pool (phase 3) | 78.8 cumulative | Vendor consolidation (BPO1/2 → BPO3) | No |
| Shrinkage restagger (Break+Lunch off-peak) | 5.8–11.5 | Labor/scheduling buy-in; model has no intraday data to prove it | No |
| Chat concurrency verification | up to 75 | Someone confirms if 1.2 is real for all languages | Not an action — a question |
| Outbound volume verification | up to 78 | Data owner explains the Outbound==Inbound match | Not an action — a question (deferred) |

---

## 1. BPO channel routing (English) — the one action with zero dependencies

**Finding:** English volume is split 50/50 between BPO1 and BPO2 uniformly
across every channel. But the two vendors aren't equally fast at every
channel:

| Channel | BPO1 AHT | BPO2 AHT | Faster vendor |
|---|---|---|---|
| Inbound | 450s | 465s | BPO1 |
| Outbound | 105s | 110s | BPO1 |
| Chat | 1,200s | 1,100s | BPO2 |
| Email | 1,150s | 1,150s | tied |

Splitting 50/50 on every channel sends some Inbound/Outbound calls to the
slower vendor (BPO2) and some Chats to the slower vendor (BPO1), for no
reason — both are already contracted for English.

**Action:** route Inbound + Outbound fully to BPO1, Chat fully to BPO2
(Email either). Pure IVR/chat-router config change.

**Quantified:**

| Scenario | English FTE |
|---|---|
| 50/50 split, uniform per channel (current) | 283.5 |
| Channel-optimal (Inbound+Outbound→BPO1, Chat→BPO2) | 279.0 |
| **Saved** | **4.5** |

No hiring, no cross-training, no language risk, no vendor renegotiation,
no labor/union involvement. Can be implemented the same day.

---

## 2. Language pooling — 3 phases, gated on a skills check

**Core mechanism:** small non-English queues (DE/IT/ES/FR) are staffed
24/7 and each independently pays the 80/20 minimum-seat floor even when
volume is low. Pooling shares that floor across languages instead of
paying it once per language.

**Critical caveat (not optional):** pooling only works if agents are
cross-skilled — the router still matches a caller to someone who speaks
their language, it just draws from a wider pool of eligible agents. It is
**not** random cross-language routing. This requires either:
- Confirming BPO3 already has agents certified in 2+ of DE/IT/ES/FR (ask
  for their skills matrix first), or
- A hiring/training plan if they don't.

**Cost check:** bilingual agents likely cost more per hour. Pooling
Spanish+French needs ~54.8 total FTE of pooled staff to capture the 18.8
FTE saving — breakeven bilingual pay premium is **~34%** before the saving
is erased. Realistic BPO bilingual premiums run 5–15%, a wide margin.

**Rollout: start on the overnight window**, where per-language floors are
most wasteful relative to actual volume and customer-facing risk is
lowest if the pilot needs correcting. (The workbook has monthly totals
only, no hour-of-day volume, so an exact overnight-only FTE number needs
an intraday-volume data request — the qualitative case holds regardless.)

### Phase 1 — Pool Spanish + French (pilot pair)

Chosen over other pairs because both are Romance languages — higher
real-world odds of existing bilingual agents than pairing with German.
Three pairs tie for best combined saving (Spanish+French, Italian+French,
German+Italian, all ≈18.8 FTE); Spanish+French recommended for language
adjacency.

| Queue | Siloed seats | Pooled seats | Occupancy | SL | FTE saved |
|---|---|---|---|---|---|
| Inbound ES+FR | 6 | 4 | 51.7% | 82.8% | 10.3 |
| Chat ES+FR | 8.33 | 6.67 | 62.8% | 86.0% | 8.6 |
| **Total** | | | | | **18.8** |

### Phase 2 — Extend to German + Italian (merge into one 4-language pool)

Gate on Phase 1 results: SLA holds ≥80%, misroute rate is low, bilingual
pay premium confirmed under breakeven.

| Queue | Siloed seats | Pooled seats | Occupancy | SL | FTE saved (cumulative, vs fully siloed) |
|---|---|---|---|---|---|
| Inbound DE+IT+ES+FR | 12 | 7 | 59.5% | 86.4% | 25.7 |
| Chat DE+IT+ES+FR | 20 | 14 | 72.1% | 85.8% | 25.7 |
| **Total (cumulative)** | | | | | **51.4** |
| **Incremental over Phase 1** | | | | | **+32.6** |

(Running German+Italian as a *separate* second pool instead of merging
with Spanish+French only saves 18.8 on its own — merging all four into
one pool captures an extra 13.7 FTE from shared floor coverage: 51.4 vs.
18.8+18.8=37.6.)

### Phase 3 — Add English into the same pool

| Queue | Siloed seats | Pooled seats | Occupancy | SL | FTE saved (cumulative, vs fully siloed) |
|---|---|---|---|---|---|
| Inbound EN+DE+IT+ES+FR | 23 | 16 | 74.1% | 84.5% | 36.0 |
| Chat EN+DE+IT+ES+FR | 44 | 34 | 84.9% | 80.2% | 42.8 |
| **Total (cumulative)** | | | | | **78.8** |
| **Incremental over Phase 2** | | | | | **+27.4** |

Note: Phase 3's Chat SL (80.2%) sits right at the floor — much less
headroom than Phases 1–2. It also requires **vendor consolidation**
(English currently sits in BPO1/2, the other four in BPO3), which is a
bigger lift than a routing change — treat as a later-stage goal, not a
near-term commitment.

### Per-queue siloed reference data (Jul, BASE)

| Queue | Contacts | Seats (raw) | Occupancy | Service level |
|---|---|---|---|---|
| Italian inbound | 6,106.1 | 3 | 27.9% | 94.8% |
| French inbound | 6,765.0 | 3 | 30.9% | 93.3% |
| Spanish inbound | 8,342.4 | 3 | 38.1% | 88.7% |
| German inbound | 9,168.5 | 3 | 41.9% | 85.7% |
| English inbound | 44,181.5 | 11 | 69.9% | 82.6% |
| Italian chat | 5,926.8 | 4 | 50.7% | 84.1% |
| German chat | 8,899.0 | 6 | 50.8% | 91.3% |
| French chat | 6,565.9 | 5 | 45.0% | 92.5% |
| Spanish chat | 8,097.1 | 5 | 55.5% | 84.2% |
| English chat | 42,882.4 | 24 | 78.2% | 86.2% |

---

## 3. Shrinkage restagger (Break+Lunch off-peak) — real action, but not easy

Shrinkage is 18% everywhere:

| Bucket | % | Type |
|---|---|---|
| Break + Lunch | 6% | Scheduling |
| Meetings | 1% | Scheduling |
| Coaching | 1% | Scheduling |
| Vacation | 5–7% | Fixed entitlement |
| Sick | 3–5% | Fixed entitlement |

8 of the 18 points are scheduling choices rather than entitlements, in
theory movable off peak-demand hours. Quantified:

| Shrinkage | FTE required (BASE plan) | FTE saved |
|---|---|---|
| 18% (current) | 484.2 | — |
| 17% (reclaim 1 pt) | 478.4 | 5.8 |
| 16% (reclaim 2 pts) | 472.7 | 11.5 |
| 15% (reclaim 3 pts) | 467.2 | 17.1 |

**Why it's flagged as hard, not dropped:** this needs labor/scheduling
buy-in (break minutes are often contractually protected), and the source
data is monthly-aggregate only — there's no intraday volume curve in the
model to actually prove a staggered-break schedule reduces peak-hour
understaffing. The lever is directionally real but not provable or
actionable from this dataset alone, and not something a WFM manager can
execute unilaterally.

---

## 4. Two verification asks (not actions, but the biggest numbers)

### Chat concurrency — up to 75 FTE

"1.2 chats per agent concurrently" sits under a column header that says
"Chat concurrency *English*" but is applied uniformly to every BPO and
every language in the source data. Chat is 188 FTE — 39% of the entire
operation, the single largest line in the plan.

**Ask:** was 1.2 actually measured for German/Italian/Spanish/French, or
copy-pasted from the English figure? If it's a placeholder, the plan
carries a 75 FTE error.

Sensitivity:

| Concurrency | Chat FTE |
|---|---|
| 1.2 | 188 |
| 1.5 | 151 |
| 2.0 | 113 |
| 2.5 | 90 |
| 3.0 | 75 |

### Outbound volume — up to 78 FTE (deferred — cannot resolve from this data)

Outbound Phone volume exactly matches Inbound Phone volume for
German/Italian/Spanish/French in every month, and for English in 5 of 6
months — the signature of a copied or synthetic column, not independent
demand.

**Ask:** is Outbound volume real, or a data artifact? If it's not real,
the plan is carrying 78 FTE of phantom staffing. If it is real, someone
needs to explain why two independently-driven call directions match
exactly.

Status: **open, cannot be resolved with the current dataset** — needs the
data owner.

---

## Recommendation

Lead with **BPO channel routing** (4.5 FTE) as the only zero-dependency
action available today. Treat **Spanish+French pooling** as the next-tier
action, gated on a one-time BPO3 skills-matrix check. Raise **chat
concurrency** and **outbound volume** as open questions worth resolving
before trusting the plan's larger numbers, not as levers to execute.
Park **shrinkage restagger** as directionally real but not provable or
actionable from this dataset.
