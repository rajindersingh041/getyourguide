# PLAN (Claude revision) — GetYourGuide, Manager WFM Take-Home

Companion to `PLAN.md` (left untouched). Two parts:

- **Part A — Evaluation** of the existing plan: what holds up, what breaks, ranked by impact.
- **Part B — Improved plan**, with the corrected model and every number recomputed from the workbook.

Everything below was recomputed from `WFM_Manager_-_Case_Study_Data.xlsx` (6 visible sheets only; the hidden `CSAT` sheet was not opened).

---

# PART A — EVALUATION

## A.0 Verdict

The plan is **strong on framing and weak on the two things the brief actually grades hardest**: a forecast that meets SLA, and optimisation strategies that survive arithmetic.

| Rubric (from the PDF) | Score | Comment |
|---|---|---|
| Forecasting rigour | 5/10 | Formula chain is right, but **SLA is never priced into the FTE number** — and the brief explicitly requires it. Only 1 of the 3 required months is produced. |
| Analytical thinking | 7/10 | Good anomaly hunting and a genuinely sharp taxonomy observation. Two conclusions drawn from it are wrong. |
| AI fluency | 4/10 | §9 is a placeholder ("write honestly"). Nothing concrete yet. |
| Strategic clarity | 7/10 | 30/60/90 is sensibly sequenced; needs the decisions named, not just the phases. |
| Communication | 6/10 | 25k words of plan for a **max 5 slides / 3 pages** deliverable. No slide skeleton exists. |

**Headline correction:** the plan's answer is **428 FTE for July**. Rebuilt with service levels enforced, it is **484 FTE to meet SLA, 508 paid FTE** once ramp and training are included. The plan is **~19% light**, and the gap is exactly the thing the brief asked for.

> Every number in Part B is produced by `run_model.py` and independently verified by `crosscheck.py` (**72/72 checks pass**) — including Erlang C against a discrete-event M/M/c simulation, and the whole capacity chain re-derived from raw worksheet cells through a separate code path.

---

## A.1 What is genuinely good — keep it

1. **The formula chain** (`contacts → ×AHT → workload → ÷(1−shrink) → ÷hours-per-FTE`) is correct and correctly applied.
2. **The "identical AHT across different reason codes" observation** is a real, non-obvious finding. **Confirmed: 45 reason codes collapse to 25 distinct AHT profiles.** Very strong material.
3. **The shrinkage decomposition** (controllable 8% vs entitlement 10%) is the right way to turn a flat 18% into an actionable lever.
4. **The Erlang C arithmetic itself is correct.** Verified independently: A = 7.679 erlangs, N = 11 → SL = 82.85%. The formula and the answer are right. What is missing is what that 11 *costs*.
5. **Summer vacation inflating shrinkage** in Jul–Sep — correct instinct, and BPO3's 7% vacation line supports it.
6. **Refusing a single point estimate** in favour of a band is the right posture for an ops audience.

---

## A.2 Findings, ranked by impact

### F1 — SLA is computed but never costed. The FTE number does not meet service level. `CRITICAL`

The brief says: *"Account for shrinkage rates **and ensure service level targets are met**."*

§7.3 produces 428 FTE from workload ÷ shrinkage. That math implicitly assumes **100% occupancy** — every agent busy every second. §7.5 then computes 11 phone agents and **stops there**. The two sections never meet.

Erlang C's answer is a **concurrent seat count**, not an FTE. Converting it:

```
11 concurrent seats × 730 h/month = 8,030 seat-hours
8,030 ÷ 0.82 (shrinkage) = 9,793 paid hours
9,793 ÷ 173.33 = 56.5 FTE      ← to meet 80/20 on English inbound
```
versus the plan's workload-only figure for the same queue:
```
44,228 calls × 450 s ÷ 3600 = 5,523 h → ÷0.82 ÷173.33 = 38.9 FTE
```

**Occupancy at 80/20 on this queue is 72%, not 100%.** The 28% idle time *is* the service level. Across every real-time queue (all phone + all chat, 5 languages) this is **+34% on total FTE**.

| Build-up (BASE, July) | FTE |
|---|---|
| Workload ÷ shrinkage only (the plan's method, channel AHT) | 360 |
| **+ Erlang C occupancy to hold 80/20 and 80/60** | **484** |
| + learning-curve blend (tenure mix at 36% attrition) | 490 |
| + in-training class (4 weeks, non-producing) | **508 paid** |

This one fix moves the answer from 428 to 508 and is the single highest-value change in the document.

---

### F2 — Strategy 1 (phone → chat deflection) makes things **worse**, not better. `CRITICAL`

§8 claims: *"Phone is the most expensive channel… Chat has concurrency 1.2 and lower AHT."*

**Both halves are false in this dataset.** From `AHT Assumptions` rows 5–6 — English, BPO1/BPO2 blended 50/50:

| Channel | AHT | Concurrency | Agent-seconds per contact |
|---|---|---|---|
| Inbound phone | **457.5 s** | 1.0 | **458** |
| Chat | **1,150 s** | 1.2 | **958** |

Chat costs **2.1× more agent time per contact than phone**. Modelled end-to-end (Erlang on both queues, July BASE, English):

| Shift inbound → chat | Phone seats | Chat seats | Combined FTE |
|---|---|---|---|
| 0% (today) | 11 | 24 | **159.2** |
| 10% | 10 | 26 | 162.6 (**+3.4**) |
| 20% | 9 | 28 | 166.1 (**+6.8**) |
| 30% | 9 | 30 | 174.6 (**+15.4**) |

Presenting this strategy invites one question in the Q&A — *"did you check the AHTs?"* — and the answer is no. **Cut it and replace it** (see B.5).

---

### F3 — Two irreconcilable English AHTs; the plan picks one silently. `HIGH`

The workbook gives English AHT **twice**:

| Source | English AHT | July English workload |
|---|---|---|
| `EN AHT by Contact reason` (ticket-weighted, Apr–Jun) | **908.78 s** | 43,306 h |
| `AHT Assumptions` BPO1/2 blend × June channel mix | **709.78 s** | 34,331 h |

A **26.1% gap.** Re-running the full model on the reason-based AHT gives **585 paid FTE against 508** — the open question is worth **+78 FTE (+15.3%)** on the answer. The plan uses 908.78 for English and channel AHT for every other language — so the model is **internally inconsistent by language** and the discrepancy is never mentioned.

They cannot both be right. Outbound phone is 25.4% of English contacts at **105 s**; a genuine all-channel blend of 909 s is arithmetically impossible against email 1,150 / inbound 450 / outbound 105 / chat 1,200.

**Most likely:** the reason-level AHT is measured on ticket-type contacts (email/chat) only, or excludes outbound.

**Fix:** make **channel AHT the engine for every language** — it is channel-resolved (required for Erlang), consistent across languages, and BPO-contractible. Keep reason AHT for the *mix* analysis in Task 1b, and carry the gap as **Open Question #1** with its price tag: **508 vs 585 paid FTE**. Naming a 15% uncertainty and its owner is a stronger answer than hiding it.

---

### F4 — Only 1 of the 3 required months is delivered. `HIGH`

The brief asks for *"the next three months."* §7 produces July. §3.3 promises a "language-specific summer index" (Aug +8%, Sep −5%) that never appears in any table, and those two numbers are **not derived from anything in the workbook**. Aug and Sep must be produced as actual rows — see B.3.

---

### F5 — "Language-specific seasonality" is asserted, then not applied. `HIGH`

§3.3 correctly argues languages must not share one shape. §7.1 then multiplies **every language by the same 1.10**. The data supports the argument strongly:

| Language | Mar | Apr | May | Jun | Post-March behaviour |
|---|---|---|---|---|---|
| English | 99,401 | 120,190 | 112,196 | 158,297 | **+59% Mar→Jun — real growth** |
| German | 38,953 | 33,510 | 32,777 | 32,849 | −16%, then flat |
| Italian | 20,909 | 28,614 | 20,962 | 21,878 | flat + one Apr spike |
| Spanish | 28,446 | 29,222 | 27,715 | 29,888 | flat |
| French | 25,034 | 26,808 | 25,564 | 24,239 | flat, slightly declining |

**Only English is growing.** The other four have been flat since March. This is cleaner and more defensible than the "travel seasonality" story, and it changes the scenario design: risk is concentrated almost entirely in English.

---

### F6 — The March +87% step is over-confidently read as demand. `MEDIUM`

§3.1 argues: *"A data glitch would be reason- or channel-specific; this is a genuine demand shift."*

That reasoning is backwards. A **uniform** doubling across 5 languages × 4 channels × 49 reason codes in a single month is the signature of a **structural change** — a reporting/system cutover, a market or brand onboarded, a merged queue — far more than of consumer demand, which does not double month-over-month in lockstep across five independent markets.

The planning action is the same either way (**anchor on post-March data**), so state both readings and the decision rule. Asserting one and being wrong in the Q&A is pure downside; presenting both shows judgement.

---

### F7 — Family-level aggregation is contradicted by the plan's own evidence. `MEDIUM`

§4 concludes: *"aggregate English to family level (first digit)… AHT is really family-level."*

The AHT clusters were tested. **They cross families in 6 of 11 multi-code groups:**

| Shared AHT profile | Reason codes | Families |
|---|---|---|
| 902.1 / 956.8 / 923.6 / 872.8 / 943.2 / 980.4 | 13.1, **4.3**, 9.1, 9.2, 9.3 | 13, 4, 9 |
| 1207.8 / 1018.0 / 964.4 / 1014.7 / 990.4 / 1366.3 | 2.1, 2.3, **3.1** | 2, 3 |
| 1118.3 / 1130.0 / 1058.5 / 1003.3 / 968.8 / 738.9 | 12.4, **7.2** | 12, 7 |
| 998.8 / 912.9 / 820.7 / 799.3 / 829.1 / 793.7 | 1.2, **6.3** | 1, 6 |
| 1008.8 / 939.4 / 881.7 / 817.9 / 835.8 / 827.4 | 3.2, **9.5** | 3, 9 |
| 1001.6 / 957.3 / 893.5 / 844.4 / 876.9 / 733.6 | 10.2, **9.4** | 10, 9 |

The correct unit is the **AHT cluster (25 groups), not the family (14)**. The insight is even better restated: *"the reason taxonomy and the AHT measurement taxonomy are different taxonomies, and neither is nested in the other — which is itself a data-model defect worth fixing at source."*

---

### F8 — The channel split is synthetic in **both** pairs, not one. `MEDIUM`

§2 flags `Outbound == Inbound`. Tested across all 30 language-months, a second mirror was missed:

- `Inbound == Outbound`: true in **29/30** (English April is the only exception)
- `Email == Chat`: true in **23/30** (all five February cells, plus English and Italian in April)

So the channel dimension is essentially **two mirrored pairs**, i.e. fabricated. That is a cleaner, more complete data-quality call, and it bounds how much channel-level precision to claim. Impact is modest (outbound ~107 s, and English email/chat are both 1,150 s after blending) — **quantify it and move on**, don't over-invest.

---

### F9 — Two data series are never mentioned. `MEDIUM`

`EN CSAT` rows 52–53 carry data the plan ignores entirely:

| Row | Jan | Feb | Mar | Apr | May | Jun |
|---|---|---|---|---|---|---|
| **SLA attainment** | 95% | **110%** | 94% | 95% | 90% | **92%** |
| **Refunds** | 44,190 | 45,458 | 57,638 | 76,444 | 74,552 | 80,861 |

Two things fall out:

1. **SLA = 110% in February is impossible.** A clean, free data-quality finding.
2. **SLA attainment is trending down (95% → 92%) while volume is up 2.2×.** This is the *evidence* that the current manual model is under-forecasting — the exact business case for the transformation the whole exercise is about. It belongs on slide 1, not in a footnote.

Refunds rising 83% Jan→Jun alongside refund-reason contacts is a supporting signal for the Task 1b self-serve case.

---

### F10 — A validation that **passes** is not reported. `LOW (but free credibility)`

Checked: the `EN CSAT` per-reason ticket counts sum **exactly** to the `Contact Volume ` English totals, all six months (ratio 1.000000). The two sheets reconcile perfectly.

That is worth one line in the data-quality log. A reviewer reads "I ran the cross-sheet reconciliation and it tied out" as evidence the analyst actually validated rather than assumed.

---

### F10b — Channel rows do not sum to their own `Tot` rows. `LOW — new`

Not in the plan, found by the model's reconciliation: in **17 of 30** language-months the four channel rows disagree with the stated `X Tot` row, by 1–2 contacts (max **0.012%** of a month's volume).

Immaterial to capacity, but it forces a modelling decision worth stating: **the channel rows are the source of truth** (each carries its own AHT and its own SLA), and the language total is derived from them. Saying which row you trusted, and why, is exactly the kind of thing the "reasoned assumptions" criterion rewards.

---

### F11 — §8 cites the hidden sheet, violating the stated constraint. `LOW but fix immediately`

§8 ends: *"Bonus: the hidden `CSAT` sheet adds an extra integer column per month (e.g. 5680 vs 7194.04)…"*

The document's own hard constraint is to ignore that sheet. **Delete this paragraph.** In a submission it reads as "excluded the data, then used it anyway."

---

### F12 — Smaller items

| # | Item | Fix |
|---|---|---|
| a | Monthly attrition stated as 3%. Compounded, 36%/yr = **3.65%/mo**. | State which convention; 3.65% is the correct one. |
| b | June volume paired with **Apr–Jun** AHT — the newest volume with older, higher AHT. English AHT is falling steadily (1,121 → 849 s). | Pick one basis. Mixing is defensible only if declared as deliberate conservatism. |
| c | Erlang run on a **flat 24/7 monthly average** arrival rate. | Correct as a floor, but say so: real intraday peaks and overnight minimum-staffing floors make interval-level staffing **higher**, never lower. |
| d | Email is modelled as pure workload at 100% occupancy. | An 80%-in-120-min target is near-real-time. Apply an occupancy factor (85% used here) or an explicit deferred-queue model. |
| e | §11 (website/FastAPI/Streamlit) is scope the brief never asked for. | Keep as one line of "how this productionises." It is not a deliverable. |
| f | 25,000 words of plan for a **5-slide / 3-page** submission. | The plan is the workbook, not the deck. Build the 5-slide skeleton **first** (B.8) and let it constrain the analysis. |

---

# PART B — IMPROVED PLAN

## B.1 Model architecture (the one change that fixes most of it)

```
                 ┌─ Email    ─┐
contacts ──────► │  Outbound  ├──► workload h ──► ÷ occupancy (0.85) ──┐
(lang×channel)   └────────────┘   deferred                             │
                 ┌─ Inbound  ─┐                                        ├──► ÷ (1 − 0.18)
                 │  Chat      ├──► Erlang C ──► concurrent seats ──────┘    shrinkage
                 └────────────┘   (80/20s, 80/60s)  × 730 h/mo              │
                                  chat ÷ concurrency 1.2                    ▼
                                                              ÷ 173.33 h = FTE (SLA-met)
                                                                            │
                                            ÷ 0.9889 tenure-blend  ─────────┤
                                            + 3.65% in-training class ──────┘
                                                                            ▼
                                                                     PAID FTE (the bill)
```

**Constants** — all traceable to the workbook:

| Constant | Value | Source |
|---|---|---|
| Hours per FTE / month | 173.33 (`=40*52/12`) | `Other information` B2 |
| Shrinkage | 18% → divisor 0.82 | `Shrinkage` D2 (`Tot Shrink`, identical all BPOs) |
| Hours per month (24/7) | 730 | `Other information` B7 |
| Phone SLA | 80% ≤ 20 s | B8 |
| Chat SLA | 80% ≤ 60 s | B9 |
| Email SLA | 80% ≤ 120 min | B10 |
| Chat concurrency | 1.2 | `AHT Assumptions` G column |
| Deferred-channel occupancy | 85% | **assumption — flag it** |
| Seasonal uplift | +10% | Brief |
| Attrition | 3.65%/mo (36% p.a. compounded) | B12 |
| Learning curve | 120 / 110 / 105% AHT, months 1–3 | B4 |
| Training | 4 weeks non-producing | B13 |
| Routing | BPO1/2 = English only; BPO3 = DE/IT/ES/FR only | B5 / B6 |

---

## B.2 Data-quality log (the scoring criterion — make it a table, not prose)

| # | Status | Finding | Evidence | Decision | Capacity impact |
|---|---|---|---|---|---|
| 1 | WARN | Channel rows disagree with their own `Tot` row in **17/30** language-months, by ≤2 contacts (0.012%) | `Contact Volume ` | Channel rows are the source of truth; totals derived from them | immaterial |
| 2 | ✅ **PASS** | `EN CSAT` reason tickets tie to `Contact Volume ` English totals — **all 6 months, ratio exactly 1.000000** | both sheets | Safe to join | validates the reason-mix join |
| 3 | FIX | 3 reason-months carry a CSAT score against **0 tickets** | `EN CSAT` row 49 (`18.2 Positive feedback`) | Null the CSAT, keep the row | none (CSAT is not a capacity input) |
| 4 | FIX | Blank reason label carrying **3,729 tickets** (0.63% of English volume) | `EN CSAT` row 23 | Relabel `UNMAPPED`, **keep the volume** | 0.63% of EN volume if wrongly dropped |
| 5 | FIX | 1 AHT outside 0.5×–2.0× its own median: `1.4 Pricing` June = **271 s** vs median 1,408 s | `EN AHT` row 6 | Replace with the reason's median | <0.5% of English AHT |
| 6 | WARN | `Inbound == Outbound` in **29/30** language-months | `Contact Volume ` | Synthetic mirror — keep (conservative), flag | ~8 FTE if true outbound is ~10% of inbound |
| 7 | WARN | `Email == Chat` in **23/30** language-months | `Contact Volume ` | Same call | minimal (EN email/chat AHT both 1,150 s) |
| 8 | WARN | **9 of 15** `AHT Assumptions` rows are unroutable under `Other information` B5/B6 | that sheet vs B5/B6 | Drop before any AHT lookup → 6 routable rows | wrong-language AHT if not dropped |
| 9 | ✅ **PASS** | Shrinkage components sum to `Tot Shrink` exactly, all 15 language-BPO pairs; 18% everywhere | `Shrinkage` | Use 18%; keep the breakdown for 1b | — |
| 10 | WARN | **Structural break**: March +87% MoM, all 5 languages together (1.60×–2.06×) | `Contact Volume ` | Level shift, not seasonality → anchor post-break | determines the baseline |
| 11 | FIX | **SLA attainment = 110% in February** — impossible | `EN CSAT` row 52 | Exclude from the trend | reporting only |
| 12 | WARN | SLA attainment **95% → 92% while volume doubled** | `EN CSAT` row 52 | Use as the business case | evidence, not an input |

**Bonus structural finding:** 45 reason codes collapse to **25 distinct AHT profiles**, and **6 of those clusters cross reason families** — so AHT is measured on a *different taxonomy* than the reason codes, and neither is nested in the other.

---

## B.3 Volume forecast — three scenarios, three months

**Baseline = June, per language** (post-structural-break, latest actual). **+10% applied as mandated.**

English is the only growing series (linear trend on Mar–Jun: **+16,869 contacts/month**, R-squared strong). The other four are flat since March, so they are held flat — the "language-specific shape" the plan promised, actually applied.

| Scenario | Rule | Jul | Aug | Sep |
|---|---|---|---|---|
| **LOW** | June run-rate, no uplift (June peak was partly one-off) | 267,154 | 267,154 | 267,154 |
| **BASE** | June × 1.10, flat (the brief's mandated case) | **293,869** | **293,869** | **293,869** |
| **HIGH** | English on linear trend × 1.10; others flat × 1.10 | 300,906 | 319,463 | 338,019 |

**BASE by language (Jul–Sep, each month):**

| Language | June actual | × 1.10 | Email | Inbound | Outbound | Chat |
|---|---|---|---|---|---|---|
| English | 158,297 | **174,128** | 42,882 | 44,182 | 44,182 | 42,882 |
| German | 32,849 | **36,135** | 8,899 | 9,169 | 9,169 | 8,899 |
| Italian | 21,878 | **24,066** | 5,927 | 6,106 | 6,106 | 5,927 |
| Spanish | 29,888 | **32,879** | 8,097 | 8,342 | 8,342 | 8,097 |
| French | 24,239 | **26,662** | 6,566 | 6,765 | 6,765 | 6,566 |
| **Total** | 267,151 | **293,869** | | | | |

**Say the honest thing:** a flat Jul–Sep base is not a claim that demand is flat — it is a refusal to invent a summer curve from 6 months of data that contains a structural break. The HIGH case *is* the summer-peak scenario, and B.7 gives the trigger that switches to it.

---

## B.4 Capacity — BASE, July (Aug/Sep identical under BASE)

Erlang C per real-time queue, arrival rate = monthly volume ÷ 730 h. Every service level below is the **achieved** level at the solved seat count, and every one clears 80%.

| Lang | Email h | Inb h | Outb h | Chat h | Inb seats | Occ | Chat seats | Occ | FTE email | FTE inb | FTE outb | FTE chat | **FTE** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| English | 13,699 | 5,615 | 1,319 | 13,699 | **11** | 70% | **24** | 78% | 113.4 | 56.5 | 10.9 | 102.7 | **283.5** |
| German | 1,730 | 917 | 293 | 2,225 | **3** | 42% | **6** | 51% | 14.3 | 15.4 | 2.4 | 25.7 | **57.8** |
| Italian | 1,317 | 611 | 195 | 1,482 | **3** | 28% | **4** | 51% | 10.9 | 15.4 | 1.6 | 17.1 | **45.0** |
| Spanish | 1,350 | 834 | 266 | 2,024 | **3** | 38% | **5** | 55% | 11.2 | 15.4 | 2.2 | 21.4 | **50.2** |
| French | 1,094 | 677 | 216 | 1,641 | **3** | 31% | **5** | 45% | 9.1 | 15.4 | 1.8 | 21.4 | **47.7** |
| **Total** | **19,190** | **8,653** | **2,290** | **21,070** | | | | | **158.9** | **118.1** | **18.9** | **188.3** | **484.2** |

English AHT is the **BPO1/BPO2 50/50 blend** (inbound 457.5 s, chat 1,150 s, email 1,150 s, outbound 107.5 s), so the capacity number does not depend on how English is split between the two vendors.

**Headcount build-up:**

| Step | Jul | Aug | Sep |
|---|---|---|---|
| Workload ÷ shrinkage only *(the naive number)* | 360 | 360 | 360 |
| **+ Erlang occupancy → SLA met** | **484** | **484** | **484** |
| ÷ 0.9889 tenure-blend (learning curve at 3.65%/mo attrition) | 490 | 490 | 490 |
| + 17.9 in training (4-week class) | **508** | **508** | **508** |

**Service level costs +34% on FTE.** Productive hours (the contracted unit): **68,827/month**; paid hours 83,935.

**By BPO** — the number each vendor is briefed with and billed on:

| BPO | Languages | FTE (SLA-met) | Productive hours | Contacts |
|---|---|---|---|---|
| **BPO 3** | DE + IT + ES + FR | **200.7** | 28,529 | 119,742 |
| **BPO 1** | English (50%) | **141.8** | 20,149 | 87,064 |
| **BPO 2** | English (50%) | **141.8** | 20,149 | 87,064 |

**All three scenarios, paid FTE:**

| | Jul | Aug | Sep |
|---|---|---|---|
| LOW | 462 | 462 | 462 |
| **BASE** | **508** | **508** | **508** |
| HIGH | 518 | 551 | 579 |

**Uncertainty band** (σ = 13.8%, log-return SD with the March break excluded; FTE is linear in volume so the same multipliers apply):

| Percentile | Contacts | Paid FTE |
|---|---|---|
| P10 | 246,292 | **425** |
| P25 | 267,784 | 463 |
| **P50** | **293,869** | **508** |
| P75 | 322,496 | 557 |
| P90 | 350,638 | **606** |

**Recommendation:** contract a **~490 FTE core** and hold a **cross-trained flex pool of ~60–100** against the P90, released monthly on the B.7 trigger. Do not hire to a point estimate.

---

## B.5 Task 1b — two strategies that survive arithmetic

Both fall directly out of the occupancy column in B.4, which only becomes visible once Erlang is done properly. Neither is a generic best practice.

### Strategy 1 — Pool the four non-English phone and chat queues. **Saves 51.4 FTE (10.1%).**

The occupancy column is the finding: German inbound runs at **42%** occupancy, Italian at **28%**. Not because agents are idle by choice — because 80/20 on a queue of 0.84 erlangs, staffed 24/7, needs 3 seats no matter how few calls arrive. **Four separate small queues each pay that floor four times.**

All four sit in **BPO3 already** (`Other information` B6), so this is a routing and skilling change, not a vendor change.

| Queue | Siloed seats | Pooled seats | Achieved SL | FTE saved |
|---|---|---|---|---|
| Inbound phone (DE+IT+ES+FR) | 3+3+3+3 = **12** (occ 28–42%) | **7** (occ **59.5%**) | 86.4% ✅ | **25.7** |
| Chat (DE+IT+ES+FR) | 6+4+5+5 = **20** (occ 45–56%) | **14** (occ **72.1%**) | 85.8% ✅ | **25.7** |
| | | | | **51.4 FTE** |

≈ **8,900 productive hours/month** off the BPO3 bill, at an unchanged (in fact higher) service level — the pooled queues were re-solved through the same Erlang engine, not assumed. Cost: multilingual skilling and a routing change. Phase it — start with the overnight window where the floors bite hardest.

### Strategy 2 — Raise chat concurrency from 1.2. **1.2 → 2.0 saves 75.3 FTE (15%).**

Chat is **188.3 FTE — 39% of the entire operation**, the largest single line in B.4. Concurrency 1.2 is far below the 2–3 that is standard for this channel, and the `AHT Assumptions` sheet carries the value in a column headed *"Chat concurrency **English**"* yet repeats 1.2 on every BPO and every language — which reads like a placeholder, not a measurement.

| Concurrency | Chat FTE (all languages) | Δ vs 1.2 |
|---|---|---|
| **1.2 (as given)** | **188.3** | — |
| 1.5 | 150.7 | **−37.7** |
| 2.0 | 113.0 | **−75.3** |
| 2.5 | 90.4 | −97.9 |
| 3.0 | 75.3 | −113.0 |

Ask: validate the 1.2. If measured, the tooling or the routing rules are the constraint and there is a clear business case to fix them. If it is a placeholder, the plan has a **75 FTE** error in it. **Either answer is worth having**, and framing it as "here is the value of getting this one number right" is the strongest thing on this slide.

> **On the plan's original Strategy 1 (phone → chat):** run end-to-end it *costs* **+6.8 FTE at a 20% shift and +15.4 at 30%**, because chat consumes **958 agent-seconds** per contact against phone's **458**. Replaced above. The direction that *does* pay is **deflection out of the contact centre entirely** — reasons `3.1 Voucher/Ticket not received` (10,127 tickets in June, 65% CSAT), `3.3 Meeting point` (22,807, the #1 driver) and `7.2 Refund not received` (65% CSAT) are the high-volume, low-CSAT, automatable set, and the Refunds series rising 83% Jan→Jun corroborates the refund pressure. That is a product ask, not a scheduling change, so it belongs as a third "where the real prize is" line rather than as one of the two scheduling strategies.

---

## B.6 Task 1c — AI usage (write this from the actual session, not in the abstract)

Fill the table with what genuinely happened. The brief is explicit that honest reflection beats a polished narrative — and it names *"what did you change, and why"* as a specific question.

| Where | Tool | Output quality | Accepted / changed | Why |
|---|---|---|---|---|
| Sheet parsing, anomaly sweep, cross-sheet reconciliation | Claude Code + Python/openpyxl | High | Accepted | Deterministic, and I verified the reconciliation independently |
| Erlang C implementation | AI-generated, hand-checked | Correct | Accepted after checking N=11 → 82.85% by hand | Never ship a staffing formula you have not verified |
| **First-pass model structure** | AI | **Wrong** | **Rejected** | Produced workload ÷ shrinkage and a separate Erlang table that never met. Meets the brief only once occupancy feeds the FTE. |
| **"Deflect phone → chat"** | AI | **Wrong** | **Rejected** | Generic WFM instinct contradicted by this dataset's AHTs (chat 1,200 s vs phone 450 s). Caught by modelling it, not by reading it. |
| Reason-taxonomy clustering | AI | Good, then over-generalised | Changed | AI concluded "AHT is family-level"; testing showed clusters cross families in 6 of 11 groups |
| Narrative drafting | AI | Good | Heavily edited | Defaulted to hedging; an ops audience needs a number and a recommendation |

**What I would do differently:** state the acceptance test *before* generating — "the FTE number must satisfy the SLA constraint" — rather than reviewing after. AI is reliable for parsing, arithmetic and structure, and **unreliable at knowing which of two conflicting numbers in a workbook is the real one**; that gap (F3) is a judgement call requiring the business, and no amount of prompting resolves it. The two errors it made were both *plausible-sounding domain defaults*, which is precisely where it needs an expert reviewer.

---

## B.7 Additional data requested, and the re-forecast trigger

**Requested (in priority order):**

1. **Which English AHT is authoritative** — reason-level (908.78 s) or channel-level (709.78 s)? Re-running the model both ways gives **508 vs 585 paid FTE — worth 78 FTE (+15.3%)**. *(Open Q#1)*
2. **Is chat concurrency 1.2 measured or assumed?** Worth **75 FTE** at 2.0. *(Open Q#2)*
3. **24+ months of history**, to fit real seasonality instead of anchoring on one month.
4. **Interval-level (15/30-min) arrival data** — monthly-average Erlang is a floor; intraday peaks and overnight floors only push staffing up.
5. **What happened in March** — system change, market launch, or genuine demand?
6. **Cost per productive hour by BPO** — none of the above can be ranked by €-impact without it.
7. **True outbound volumes** — the mirrored columns cannot be real.

**Monthly re-forecast trigger (put this on the slide — it is what makes the forecast operational):**

| Signal | Threshold | Action |
|---|---|---|
| English actual vs BASE | > +8% for 2 consecutive weeks | Switch to HIGH; release flex pool |
| English actual vs BASE | < −8% for 2 consecutive weeks | Switch to LOW; freeze the hiring pipeline |
| SLA attainment | < 90% for 2 consecutive weeks | Immediate re-forecast — this already happened in **May (90%)** |
| AHT drift | ±5% vs plan | Re-baseline AHT, do not re-baseline volume |

---

## B.8 Deliverable — build these 5 slides first, then fill them

The brief caps this at **5 slides / 3 pages**. Draft the skeleton before any further analysis and let it discipline the scope.

| # | Slide | The one thing it must land |
|---|---|---|
| 1 | **The answer** | Jul–Sep: **508 paid FTE / 68,827 productive hours** (BASE). LOW 462 · HIGH 518–579. Build-up bar: 360 → **+SLA 484** → +ramp 490 → +training **508**. P10–P90 band 425–606. |
| 2 | **Method + data quality** | The chain, the 11-row DQ log condensed to 5 rows, and the two open questions with their FTE price tags. |
| 3 | **Two optimisation strategies** | Pool non-English queues → **−51.4 FTE**. Validate/raise chat concurrency → **−75.3 FTE at 2.0**. Both with the occupancy evidence. |
| 4 | **AI usage** | The accept/reject table — including the two things AI got wrong and how they were caught. |
| 5 | **Transformation 30/60/90 + metrics** | Sequenced plan, the decisions needed in the first 30 days, and the definition of "done" at 90. |

**Appendix (the workbook, not the deck):** full model, Erlang outputs, sensitivities, scenario tables.

---

## B.9 Section 2 — sharpen what is already there

The existing §10 is sound. Three upgrades:

**2a — the brief asks "what decisions before you can move forward?"** Name them explicitly, because they are real and visible in this dataset:
1. **Single source of truth for AHT** — F3 is unresolvable without an owner. Decide *who* owns the AHT definition. Week 1.
2. **Forecast granularity** — language × channel × interval. Anything coarser cannot produce an SLA-compliant number; F1 is exactly that failure.
3. **Who signs off assumptions** (concurrency, shrinkage, occupancy) and how often they are revisited.
4. **Build vs buy** for the forecasting engine, and where the model lives.

**Sequencing rationale:** English first — 59% of volume, all the growth, all the forecast risk (σ = 20% vs under 9% for German/Spanish/French). Fix the biggest, most volatile queue first.

**"Done" at 90 days:** the new model produces the weekly plan unaided; it beats the manual baseline on MAPE for ≥6 consecutive weeks; the three specialists run it without me; assumptions are versioned and dated.

**2b — assess with an artefact, not an opinion.** Give each specialist the same task on this dataset (clean it, forecast one language, document assumptions). What comes back places them on forecasting-depth × AI-fluency far better than a conversation. Then pair the strongest forecaster with the weakest AI user. **Protect BAU by running the new model in shadow for 6 weeks** — the manual plan stays the plan until the new one has beaten it on the board.

**2c — metrics.** Keep the leading/lagging split and add the ones this dataset makes concrete:

*Leading:* % of forecast inputs with a named owner and a dated assumption · time-to-produce-a-plan (baseline it in week 1) · % of plan runs that are reproducible from source · number of open data-quality items (starts at **12**, from B.2) · specialists able to run the model solo (0 → 3).

*Lagging:* **forecast MAPE and BIAS by language** (bias matters more — this plan was 20% *under*) · SLA attainment (baseline **92%**, and falling) · FTE plan-vs-actual variance · shrinkage actual-vs-plan by bucket · cost per contact.

**One metric to lead with:** *forecast bias by language*. Accuracy alone hides direction, and direction is what F1 got wrong.

---

## B.9b The model itself

Built and verified. `run_model.py` reproduces every number in Part B from the workbook in one command; `crosscheck.py` verifies it independently.

```
wfm/config.py     every assumption in one frozen dataclass - nothing hard-coded downstream
wfm/erlang.py     Erlang B/C, SLA, ASA, staffing solver, normal inverse CDF
wfm/loader.py     schema-driven reader; refuses the hidden sheet; auto-detects
                  languages/channels/months by pattern, not by cell address
wfm/clean.py      12 data-quality checks -> structured log (PASS / FIX / WARN)
wfm/forecast.py   structural-break detection, per-language growth test, 3 scenarios,
                  log-normal confidence bands
wfm/capacity.py   workload -> Erlang -> seats -> FTE -> paid headcount, by BPO
wfm/optimise.py   each 1b lever re-solved through the same engine
wfm/report.py     formatted Excel output
run_model.py      end-to-end run
crosscheck.py     72 independent verification checks
```

**What the cross-check actually verifies** (72/72 pass):

| Section | Check |
|---|---|
| A–B | Erlang B recursion vs the textbook closed form (max diff **1.1e-16**); Erlang C vs the M/M/c **stationary distribution**, derived independently (max diff **<1e-12**) |
| C | Erlang C vs a **discrete-event M/M/c simulation** — 5 replications × 300k arrivals per case, analytic value inside a 3-sigma band on both service level and ASA |
| D | The staffing solver returns the **minimal** feasible seat count, and SL is monotone in n |
| E | **Little's Law** `Lq = λWq` holds exactly |
| F | Normal inverse CDF vs published z-values (**1.9e-09**) and against its own forward CDF |
| G | The **entire July chain re-derived from raw worksheet cells** through a separate code path — matches the pipeline to 1e-6 |
| H | Every cross-sheet reconciliation, including CSAT↔volume at ratio **exactly 1.000000** |
| I | Every real-time queue **achieves ≥80%** (min 80.37%); occupancy <100%; queue FTE sums exactly to the roll-up; BPO split re-aggregates with **zero** FTE lost; LOW ≤ BASE ≤ HIGH |
| J | Attrition compounds to 36.00%/yr; tenure efficiency matches a **3,000-iteration cohort simulation** |
| K | OLS slope matches `numpy.polyfit`; BASE is June × 1.10 to 1e-9; channel forecasts sum exactly to language forecasts |
| L | Every 1b lever **re-solved, not asserted** — including the phone→chat test that comes back negative |
| M | **PLAN.md's own numbers reproduced** — 908.78 s, 427.90 FTE, 11 agents @ 82.85% — then shown to under-book the SLA queue by 45% |
| N | Pipeline runs unchanged with a language removed and with every assumption altered; hidden sheet refused |

Three real defects were found **in my own model** by this suite and fixed at source: the growth test keyed off `|slope|` so a *declining* language qualified as growing; `HIGH` could land below `BASE`; and the reported trend was a one-step projection rather than the OLS slope. A fourth failure surfaced the ±2-contact residue that became DQ finding #1, and one "failure" turned out to be a wrong reference value in the test, not a bug in the code — confirmed by four independent derivations agreeing to 1e-12.

```bash
python run_model.py                      # full run + Excel output
python run_model.py --aht-source reason  # the Open Q#1 sensitivity
python crosscheck.py                     # 72 verification checks
```

---

## B.10 Execution order (revised, ~3–4 h)

| # | Step | Time | Why this order |
|---|---|---|---|
| 1 | **Draft the 5 slide headlines** (B.8) | 15 m | Constrains everything downstream |
| 2 | Load + reconcile + DQ log (B.2) | 25 m | Reconciliation is the credibility anchor |
| 3 | Volume scenarios, 3 months × 3 cases (B.3) | 20 m | |
| 4 | **Erlang → FTE, end to end** (B.4) | 35 m | The fix that makes the answer correct |
| 5 | Headcount build-up + BPO split | 15 m | |
| 6 | Strategies 1 & 2 quantified (B.5) | 25 m | Both come free from step 4's occupancy column |
| 7 | Sensitivities + triggers (B.7) | 20 m | |
| 8 | Section 2 + AI reflection (B.6, B.9) | 30 m | |
| 9 | Build deck + working workbook | 40 m | |

---

## B.11 One-line summary to open with

> *July–September needs **508 paid FTE / 68,827 productive hours per month** to hold 80/20 phone and 80/60 chat at June run-rate +10%. **A quarter of that requirement is service level, not workload** — a pure workload model returns 360 and misses SLA. Two changes give it back: pooling the four non-English queues (**−51.4 FTE**) and validating chat concurrency (**−75.3 FTE if it moves to 2.0**). One unresolved number in the source data — which English AHT is real — is worth **78 FTE (15%)** and needs an owner before the next cycle.*
