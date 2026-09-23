# GetYourGuide — Manager, Workforce Management — Take-Home Task Plan

Role: Manager, WFM (Care Experience & Strategy). Replace manual Google-Sheets forecasting with an AI-driven, scalable capacity model.

Hard constraint: **ignore the hidden `CSAT` sheet** — use only the 6 visible sheets.

---

## 0. What we are solving

| Section | Deliverable |
|---|---|
| 1a | Capacity forecast (FTE + productive hours) for next 3 months, +10% contacts, shrinkage + SLA |
| 1b | 2 data-grounded optimisation strategies |
| 1c | Honest AI-usage reflection |
| 2a | 30/60/90 transformation plan |
| 2b | Bringing the 3-person team along |
| 2c | Metrics to measure the transformation |

Everything hangs off one formula chain:

```
contacts (lang x channel x month)
   -> x AHT (sec)  =  workload (hours)
   -> / (1 - shrinkage)  =  productive hours required
   -> / hours-per-FTE   =  FTE required
   -> + Erlang-C agents for phone/chat SLA (80% in 20s / 60s)
```

---

## 1. Data inventory (6 visible sheets)

| Sheet | What it holds | Used for |
|---|---|---|
| `Contact Volume ` | contacts per language (EN/DE/IT/ES/FR) x channel (Email/Inbound/Outbound/Chat), Jan–Jun | volume forecast |
| `EN CSAT` | English: per-reason ticket counts + CSAT% | reason mix, AHT weighting, 1b |
| `EN AHT by Contact reason` | English: per-reason AHT (seconds) | English AHT |
| `AHT Assumptions by BPO and lang` | channel AHT per BPO x language + chat concurrency | non-English AHT |
| `Shrinkage` | language x time-category x BPO shrink % | productive hours |
| `Other information` | FTE=40h/wk, learning curve, BPO constraints, SLA, attrition, training | constants + buffers |

(There is a 7th sheet, `CSAT`, which is **hidden** — excluded per constraint.)

---

## 2. Data cleaning & validation (~20 min)

Python pipeline (`uv` venv ready; `openpyxl`/`pandas`). Loads **only the 6 visible sheets**.

**Flags & fixes:**
- `EN CSAT`: rows with 0 tickets but a CSAT value → null the CSAT. Blank reason label → "UNMAPPED" (keep the volume — it feeds capacity).
- Decimal ticket counts → round for reporting (keep raw for math).
- `Contact Volume`: **Outbound == Inbound** for DE/IT/ES/FR (EN differs only in Apr). Copied data. Default = keep-as-is (no capacity lost, conservative) but flag that true outbound is normally ~5–15% of inbound → quantify in §sensitivity.
- `AHT Assumptions`: drop impossible combos — **BPO3-English** and **BPO1/2-non-English**.
- `EN AHT`: replace placeholder/outlier AHT (e.g. `1.4 Pricing` Jun = 271s) with the reason's trailing median.
- **AHT is measured coarser than the reason codes** — several "different" reasons share identical AHT (see §3 taxonomy). Drives our aggregation choice.
- **Chat concurrency column is labelled "English" but repeated on every row** — ambiguity to flag (see §3).

Emit a **data quality log** (a scoring criterion). Every fix: what, why, impact.

---

## 3. Contact volume forecast (next 3 months) — seasonality-aware

A naive average is wrong here. The data is **seasonal travel demand**, and a 6-month window is too short to see a full cycle. What the data actually shows:

### 3.1 The hidden pattern in Jan–Jun

1. **A market-wide step-up in March** — total contacts jump **+87% MoM** (113.6k→212.7k), and it's *uniform across all 5 languages, all 4 channels, and all contact reasons* (English +106%, German +81%, Italian +82%, Spanish +71%, French +60%). A data glitch would be reason- or channel-specific; this is a genuine demand shift (spring/summer travel ramp).
2. **Language-specific seasonality.** English (international tourists) swings ~3x winter→summer (Jan = 32% of June). Domestic languages are far flatter (German 66–119% of June). → **don't forecast all languages with one shape.**
3. **Event-driven bumps.** April = Easter (Easter 2026 is Apr 5) → Apr elevated, **May dips back** (−7% MoM English), June = summer start (on the upswing).
4. **A few genuinely volatile reasons** (worth a watch-list, possibly temporary): `3.1 Voucher/Ticket not received` doubles May→Jun (5.3k→10.1k), `7.1 Bank/Conversion fees` ~3x in June, `3.7 Supplier related questions` triples Feb→Jun. `5.4 cancellation self-serve` spiked only in April (feature/promo event). These can create ±volume pockets a monthly total hides.

### 3.2 The honest limitation

We only have **6 months** → we cannot estimate annual seasonality statistically (need 24+ months). We also don't know the demand geography (Europe assumed — GYG is Berlin-based) or the events calendar (promos, outages, Easter dates, new markets). So the forecast **must** be scenario-based, anchored on the closest "summer" data point.

### 3.3 Refined method

1. **Baseline = June run-rate** (latest month, on the summer upswing), *not* the trailing-3mo average — trailing-3mo drags the peak down with May's post-Easter dip and under-forecasts summer.
2. **Apply the mandated +10% seasonal uplift** to the June run-rate.
3. **Language-specific summer index** (documented assumption): English peaks in Aug (+~8% over July) and tapers in Sep (−~5%); domestic languages stay ~flat through summer.
4. **Channel split** = June mix (uniform 24.6/25.4/25.4/24.6 — flag as synthetic).
5. **Report LOW / BASE / HIGH scenarios** to bracket the demand risk.

| Scenario | July volume | July FTE | When to use |
|---|---|---|---|
| **LOW** = June × 1.00 | 267,151 | **389** | June peak was partly a one-off (voucher/FX spikes) |
| **BASE** = June × 1.10 | 293,866 | **428** | mandated +10% seasonal uplift on current run-rate |
| **HIGH** = June × 1.20 | 320,581 | **467** | full summer peak with carry-over of June growth |

**Baseline choice matters:** trailing-3mo+10% gives 265.7k/376 FTE vs June×1.10 gives 293.9k/**428 FTE** — a **+52 FTE (~14%)** swing. That is exactly the high/low-capacity risk: under-forecasting summer peak = missed SLA + burnout; over-forecasting = idle cost.

**Real fix to state in the submission:** request 24+ months of history, the events calendar, and market/geo mix, then fit a proper seasonal model (e.g. Holt-Winters multiplicative or a travel-seasonality index) instead of a 6-month average.

### 3.4 Probabilistic forecast — confidence intervals (instead of a point)

A single point hides the real risk (hiring too few/many). We model July volume as a **random variable** and report confidence intervals, which is the right way to communicate demand risk to an operational audience.

**Model:** July volume ~ LogNormal with **median = base** (June×1.1) and scale σ. FTE scales *identically*, because `FTE = volume × (AHT/3600 ÷ 0.82 ÷ 173.33)` is **linear in volume** → relative uncertainty carries through 1:1.

**σ (relative volatility), estimated from the data:** standard deviation of month-over-month log-returns `ln(V_t / V_t-1)`, *excluding the March seasonal step* (+87% is a known seasonal ramp, not forecast error). Result: **total ≈ 14%**, English ≈ 20%, Italian ≈ 27%, German/Spanish/French ≈ 6–8%.

**Caveat:** 6 months can't capture the *unknown* Jul–Sep summer peak, so true σ is likely higher → also show a conservative **σ = 25%** band.

**Output (total, base = 293,866 vol / 428 FTE):**

| Percentile | σ=15% volume | σ=15% FTE | σ=25% FTE |
|---|---|---|---|
| P10 | 242,457 | 353 | 311 |
| P50 (median) | 293,866 | 428 | 428 |
| P90 | 356,176 | 519 | 590 |

**Planning implication:** don't hire to a single number. Staff a ~430 FTE **core** and hold a **flexible bench / cross-trained pool** for the P90 upside (~520 FTE), with monthly triggers (actuals vs forecast) to scale up/down.

---

## 4. AHT & workload model

`workload (hours) = Σ contacts × AHT(sec) / 3600`

**English** — reason-level weighted AHT (most granular, use actuals):
`weighted AHT = SUMPRODUCT(tickets, AHT) / SUM(tickets)` over `EN CSAT` × `EN AHT`.

**Non-English** — channel AHT from `AHT Assumptions`, **BPO3 only** (BPO3 = the non-English BPO).

### Taxonomy insight — why the same issue appears in many buckets

Reason codes form a 2-level tree (`family.sub-reason`). The same real issue is re-coded by journey stage — "Meeting point" as `1.2`/`3.3`/`6.3`, "Refund" as `7.2`/`12.4`, "Cancellation" split `5.1–5.4`. The data proves the granularity is cosmetic: those codes share **identical AHT**. So AHT is really family-level.

Consequence: **aggregate English to family level (first digit)** — June share 1=37%, 3=26%, 5=10%, 4=10% (~83% in 4 families). Forecasting 14 families beats 49 sub-reasons and matches how AHT is actually measured.

### New vs old agent (blended AHT)

36% annual attrition ≈ 3%/mo, 3-month ramp (120/110/105%). Steady-state mix ≈ 3%/3%/3%/91% → **blended AHT ≈ +1.05%**. The bigger cost is **4-week training**: ~3% of headcount produces 0 volume while paid. Both are explicit FTE buffers (§6).

### Chat concurrency (flagged gap)

`AHT Assumptions` has one column `Chat concurrency English = 1.2` on every row (all BPOs x langs). Ambiguous (English-only or universal?) and **very conservative** (industry 2–3). Concurrency is a ±40% lever on chat staffing → run as a sensitivity, don't take 1.2 as given.

---

## 5. Shrinkage → productive hours → FTE

```
productive hours = workload / (1 - shrinkage)
FTE              = productive hours / hours_per_FTE
```
- Shrinkage = **18%** (`Tot Shrink`, consistent across all languages/BPOs).
- Hours per FTE = **40 × 52 / 12 = 173.33 h/month**.

### Shrinkage composition — why the breakdown is given

Every BPO sums to the same 18%, but with a *different mix* (from `Shrinkage`):

| Bucket | BPO1 | BPO2 | BPO3 |
|---|---|---|---|
| Break + Lunch | 6% | 6% | 6% |
| Meetings | 1% | 1% | 1% |
| Coaching | 1% | 1% | 1% |
| Vacation | 5% | 5% | **7%** |
| Sick | 5% | 5% | **3%** |
| Projects | — | — | **0%** |
| **Tot Shrink** | **18%** | **18%** | **18%** |

Why this matters:

1. **It's the Task 1b shrinkage lever.** *Controllable* (Break+Lunch 6% + Meetings 1% + Coaching 1% = 8%) vs *fixed/entitlement* (Vacation + Sick = 10%). "Cut shrinkage" is generic; "reclaim 1–2 pts from Break+Lunch via staggered/off-peak breaks and move coaching to low-demand hours" is data-grounded.
2. **Seasonal adjustment (critical for Jul–Sep).** Vacation is 7% at BPO3 and *rises* in summer. A flat 18% under-states summer shrinkage → under-staffs. Adjust shrinkage up ~+1–2 pts for the summer months.
3. **Vendor profiling.** BPO3 has a `Projects` line (0%) and a different Vacation/Sick mix than BPO1/2 — a different vendor model / labour regime (useful when comparing or renegotiating).
4. **Paid-hours conversion.** Contracts are *per productive hour* (`Other information` B11), so `paid hours = productive ÷ (1 − shrinkage)`; the breakdown justifies the 18% and lets each bucket be sensitised separately.

---

## 6. Service level (Erlang C) + hiring buffer

- **Phone:** 80% ≤ 20s → Erlang C → min agents (monthly-aggregate approximation; real WFM runs 15-min intervals).
- **Chat:** 80% ≤ 60s, concurrency 1.2 → chat agents = Erlang agents / concurrency.
- **Email:** 80% ≤ 120 min → backlog/turnaround model, not Erlang.
- **Hiring buffer:** 36% attrition ≈ 3%/mo ≈ **11.6 FTE/mo** churn → recruit ahead (4-week training + 3-month ramp).

---

## 7. WORKED EXAMPLE — July, fully Excel-reproducible

Every number below can be recomputed in Excel. Constants first:

| Name | Value | Excel |
|---|---|---|
| Hours per FTE / month | 173.33 | `=40*52/12` |
| Shrinkage | 18% | `0.18` |
| Shrinkage divisor | 0.82 | `=1-0.18` |
| Seasonal uplift | 10% | `1.10` |

**Source map — where every raw input lives in the workbook** (so you can trace any number back to its cell):

| Input | Value used | Source (sheet → cell) |
|---|---|---|
| June volume: English / German / Italian / Spanish / French | 158,297 / 32,849 / 21,878 / 29,888 / 24,239 | `Contact Volume ` → **G2 / G7 / G12 / G17 / G22** |
| June channels (English) Email / Inbound / Outbound / Chat | 38,984 / 40,165 / 40,165 / 38,984 | `Contact Volume ` → **G3 / G4 / G5 / G6** |
| Non-English channel AHT (BPO3) German | Email 700, In 360, Out 115, Chat 900 | `AHT Assumptions by BPO and lang` → **C4:F4** |
| Non-English channel AHT (BPO3) Italian | 800 / 360 / 115 / 900 | → **C16:F16** |
| Non-English channel AHT (BPO3) Spanish | 600 / 360 / 115 / 900 | → **C10:F10** |
| Non-English channel AHT (BPO3) French | 600 / 360 / 115 / 900 | → **C13:F13** |
| English phone AHT (450 s) | 450 | `AHT Assumptions` → **D5** (BPO1 English Inbound) |
| English chat AHT (1,200 s) | 1,200 | `AHT Assumptions` → **F5** (BPO1 English Chat) |
| Chat concurrency | 1.2 | `AHT Assumptions` → **G5** (and every row) |
| English reason tickets (per month) | — | `EN CSAT` → cols **B/D/F/H/J/L** |
| English reason AHT (per month) | — | `EN AHT by Contact reason` → cols **B–G** |
| Shrinkage | 18% | `Shrinkage` → 'Tot Shrink' rows (e.g. **A2**) |
| FTE = 40 h/week | 40 | `Other information` → **B2** |
| Phone SLA 80% / 20 s | 80%, 20 s | `Other information` → **B8** |
| Chat SLA 80% / 60 s | 80%, 60 s | `Other information` → **B9** |
| Email SLA 80% / 120 min | 80%, 120 min | `Other information` → **B10** |
| Learning curve 120/110/105% | — | `Other information` → **B4** |
| Attrition 36% | 36% | `Other information` → **B12** |
| Training 4 weeks | 4 wks | `Other information` → **B13** |

### 7.1 Volume forecast (July) — June run-rate × uplift

Baseline = **June** (latest month, on the summer upswing). LOW = ×1.00, BASE = ×1.10 (mandated), HIGH = ×1.20 (full peak).

| Language | Jun | LOW `=B*1.0` | BASE `=B*1.1` | HIGH `=B*1.2` |
|---|---|---|---|---|
| English | 158,297 | 158,297 | **174,126.70** | 189,956.40 |
| German | 32,849 | 32,849 | **36,133.90** | 39,418.80 |
| Italian | 21,878 | 21,878 | **24,065.80** | 26,253.60 |
| Spanish | 29,888 | 29,888 | **32,876.80** | 35,865.60 |
| French | 24,239 | 24,239 | **26,662.90** | 29,086.80 |
| **Total** | 267,151 | 267,151 | **293,866.10** | 320,581.20 |

Example arithmetic (English): `158,297 × 1.10 = 174,126.70`.
*(Sources: June totals from `Contact Volume ` G2/G7/G12/G17/G22.)*

> Why June and not trailing-3mo: trailing-3mo (Apr–Jun) = 130,227 for English — it averages out the Easter spike and the May dip, and *under-forecasts* the summer peak. June is the closest "summer" data point. (See §3 for the full seasonality reasoning.)

### 7.2 AHT

**English — weighted AHT (trailing 3 months).** From `EN CSAT` (tickets) × `EN AHT` (seconds):

`weighted AHT = SUMPRODUCT(tickets_Apr:Jun, AHT_Apr:Jun) / SUM(tickets_Apr:Jun)`
`= 353,103,004 / 388,547 = 908.78 s`

Monthly weighted AHT (for verification): Jan 1121.1 · Feb 1073.1 · Mar 955.5 · Apr 938.0 · May 962.5 · Jun 848.6 → Apr–Jun combined = **908.78 s**. (We use the 3-month value for stability; June alone = 848.60 s, which would lower English FTE by ~20 — keep as a sensitivity.)
*(Sources: tickets from `EN CSAT` cols B–L; AHT from `EN AHT by Contact reason` cols B–G.)*

**Non-English — blended channel AHT (BPO3).** Channel mix 24.6/25.4/25.4/24.6:

| Language | Formula | Result |
|---|---|---|
| German | 0.246×700 + 0.254×360 + 0.254×115 + 0.246×900 | **514.25 s** |
| Italian | 0.246×800 + 0.254×360 + 0.254×115 + 0.246×900 | **538.85 s** |
| Spanish | 0.246×600 + 0.254×360 + 0.254×115 + 0.246×900 | **489.65 s** |
| French | 0.246×600 + 0.254×360 + 0.254×115 + 0.246×900 | **489.65 s** |

*(Sources: BPO3 channel AHT from `AHT Assumptions by BPO and lang` C4:F4 (German), C16:F16 (Italian), C10:F10 (Spanish), C13:F13 (French).)*

Example (German): `172.20 + 91.44 + 29.21 + 221.40 = 514.25`.

### 7.3 Workload → productive hours → FTE (BASE scenario)

`workload = volume × AHT / 3600` · `prod = workload / 0.82` · `FTE = prod / 173.33`

| Language | Volume | AHT s | Workload h `=B*C/3600` | Prod h `=D/0.82` | FTE `=E/173.33` |
|---|---|---|---|---|---|
| English | 174,126.70 | 908.78 | 43,956.4 | 53,605.3 | **309.26** |
| German | 36,133.90 | 514.25 | 5,161.6 | 6,294.7 | **36.32** |
| Italian | 24,065.80 | 538.85 | 3,602.2 | 4,392.9 | **25.34** |
| Spanish | 32,876.80 | 489.65 | 4,471.7 | 5,453.3 | **31.46** |
| French | 26,662.90 | 489.65 | 3,626.5 | 4,422.6 | **25.51** |
| **Total** | **293,866.10** | | **60,818.4** | **74,168.8** | **427.90** |

Example (English): `174,126.70 × 908.78 / 3600 = 43,956.4 h` → `43,956.4 / 0.82 = 53,605.3 h` → `53,605.3 / 173.33 = 309.26 FTE`.

> **BASE result: ~428 FTE / ~74k productive hours for July.** Scenario spread:
> LOW (June×1.0) = **389 FTE** · BASE (June×1.1) = **428 FTE** · HIGH (June×1.2) = **467 FTE**.

### 7.4 Channel split (English BASE) — for SLA / Erlang

`channel = 174,126.70 × mix`

| Channel | Mix | Contacts |
|---|---|---|
| Email | 24.6% | 42,835.2 |
| Inbound | 25.4% | 44,228.2 |
| Outbound | 25.4% | 44,228.2 |
| Chat | 24.6% | 42,835.2 |

*(Source: mix = channel ÷ total from `Contact Volume ` G3:G6 ÷ G2.)*

### 7.5 Erlang C (English phone, BASE)

`inbound = 44,228.2 calls/mo` → `calls/hr = 44,228.2 / 30 / 24 = 61.43` → traffic `A = 61.43 × 450 / 3600 = 7.679 erlangs` (AHT 450s — from `AHT Assumptions` **D5**).

`SL = 1 − P(wait>0) × exp(−(N−A) × 20 / 450)` for target 20s. Scan N:

| N (agents) | Service level |
|---|---|
| 11 | 82.84% ✅ (≥80%) |
| 12 | 90.90% |
| 13 | 95.42% |

→ **11 phone agents** for English. Chat uses concurrency 1.2 → agents/1.2.

### 7.6 Sensitivities (why the "high variance" matters)

| Driver | Base | Alt | FTE impact |
|---|---|---|---|
| Forecast baseline | June×1.1 = 293.9k | trailing-3mo×1.1 = 265.7k | **−52 FTE (under-staff)** |
| Summer peak index | Aug ≈ July | Aug +8% (English) | **+~25 FTE in Aug** |
| Chat concurrency | 1.2 → 68.9 FTE | 2.0 → 41.3 FTE | **±40% of chat** |
| Outbound==Inbound | keep (44.2k) | true outbound ~10% | **~8 FTE over-staff** |
| Learning curve | competent 100% | blended +1.05% | ~+1% AHT |
| Attrition | — | 3%/mo | **~11.6 FTE/mo** to backfill |

### 7.7 Probabilistic forecast — confidence intervals (Excel)

Log-normal percentile formula (median = base):

`p-th percentile = base × EXP(z_p × σ)` where `z_p = NORM.S.INV(p)` (Excel `=NORM.S.INV(0.1)` → −1.282, etc.).

| p | z `=NORM.S.INV(p)` |
|---|---|
| 5% | −1.645 |
| 10% | −1.282 |
| 25% | −0.674 |
| 50% | 0 |
| 75% | +0.674 |
| 90% | +1.282 |
| 95% | +1.645 |

Worked (total, base = 293,866 vol, σ = 0.15):
- P10 = `293,866 × EXP(−1.282 × 0.15)` = `293,866 × 0.825` = **242,457**
- P90 = `293,866 × EXP(+1.282 × 0.15)` = `293,866 × 1.212` = **356,176**
- FTE (linear, base 428): P10 = `428 × 0.825` = **353**, P90 = `428 × 1.212` = **519**

→ **"80% confident July needs 353–519 FTE"** (90%: 334–548 FTE; σ=25% conservative: 311–590 FTE).

To compute σ yourself in Excel: `σ = STDEV.S(LN(Feb/Jan), LN(Apr/Mar), LN(May/Apr), LN(Jun/May))` = **0.138 ≈ 14%** (drop the Mar/Feb return — it's the seasonal step).

### 7.8 BPO-level FTE & productive hours (BASE scenario)

The BPO↔language map is fixed (`Other information` B5/B6): **BPO1 & BPO2 = English only; BPO3 = German/Italian/Spanish/French only.** So BPO3 falls out cleanly; English must be split across BPO1/BPO2 (the one assumption).

| BPO | Languages | Productive hours | FTE |
|---|---|---|---|
| **BPO3** | German + Italian + Spanish + French | 6,294.7 + 4,392.9 + 5,453.3 + 4,422.6 = **20,563** | **118.6** |
| **BPO1 + BPO2** | English | **53,605** | **309.3** |

- **BPO3 ≈ 119 FTE / 20.6k productive hours** — firm, no assumption needed.
- **English = 309.3 FTE** split across BPO1/BPO2. Default rule: **50/50 ≈ 154.6 FTE each** (or "primary + overflow"). Note BPO1 vs BPO2 channel AHT differs slightly (inbound 450 vs 465, chat 1,200 vs 1,100 — `AHT Assumptions` D5/F5 vs D6/F6), so the split nudges capacity a little; it's small vs the volume uncertainty.

Why BPO-level matters: contracts are *cost per productive hour* (`Other information` B11), shrinkage is BPO-level, and a WFM manager briefs **each vendor** with their own FTE + productive hours — this is the number that becomes the vendor bill.

---

## 8. Task 1b — 2 optimisation strategies (data-grounded)

### Why CSAT is in the dataset (and how to use it)

CSAT is **not** a capacity input — it never touches the FTE formula. Its purpose:

1. **It drives 1b.** CSAT × volume × AHT = effort × satisfaction matrix → which reasons to fix. Prime targets (high volume + high AHT + low CSAT):
   - `3.1 Voucher/Ticket not received` — 10,127 tix (Jun), AHT 1,366s (Jun), **CSAT 65%** *(`EN CSAT` L11 / M11, `EN AHT` G20)*
   - `3.3 Meeting point/Pick-up/Drop off` — 22,807 tix (Jun, #1), **CSAT 76%** *(`EN CSAT` L6 / M6)*
   - `7.2 I have not received my refund yet` — **CSAT 65%** *(`EN CSAT` L22 / M22)*
   Fixing these removes workload *and* raises CSAT together. Contrast `8.1 purchase gift certificate` (low volume, CSAT 70–94%) — leave it.
2. **Experience side of the staffing trade-off.** SLA targets exist to protect CSAT — CSAT justifies staffing above the minimum.
3. **Leading indicator of volume.** Falling CSAT → repeat contacts → future volume.

Bonus: the hidden `CSAT` sheet adds an extra integer column per month (e.g. `5680` vs `7194.04`) — the CSAT survey **response count**, exposing the ~50–64% survey response rate.

### Strategy 1 — Channel deflection (phone → chat)

Phone is the most expensive channel (real-time SLA, 1:1 agents). Chat has concurrency 1.2 and lower AHT. Data: English chat AHT 1,200s but concurrency 1.2 → effective 1,000s/agent vs phone 450s×1 (but 20s SLA forces idle capacity). Quantify: shifting X% of inbound phone → chat saves Y FTE.

### Strategy 2 — Language routing / BPO3 consolidation

BPO3 has the *lowest* channel AHT (e.g. Spanish email 600 vs BPO1/2 800) and is the only non-English BPO. Show consolidating non-English into BPO3 (already the constraint) and renegotiating BPO1/2 toward BPO3 AHT levels.
- Alt: **shrinkage reduction** — 18% total, biggest buckets Break+Lunch (6%) and Vacation (5–7%); target scheduling patterns to reclaim 1–2 pts.

Each strategy stated as: "if X, we save Y productive hours ≈ Z FTE/month".

---

## 9. Task 1c — AI usage (write honestly)

Document exactly where AI was used (data cleaning/anomaly detection, formula/model structuring, drafting 30/60/90 + metrics). Accept/reject/change table. What we'd do differently. Specific, not marketing.

---

## 10. Section 2 — Transformation roadmap

**2a — 30/60/90:**
- **0–30:** audit current Sheets model; freeze single source of truth; set accuracy target (MAPE ≤10% weekly/language); pilot = English (highest volume). Decisions first: data ownership, granularity, tooling, who signs off assumptions.
- **31–60:** build AI-assisted forecast in parallel (shadow mode); weekly reconciliation; train team.
- **61–90:** cut over English; start DE/IT/ES/FR; escalation/override rules; "done" = new model produces the weekly plan, beats manual accuracy, team runs it solo.

**2b — Team of 3:** assess each person (forecasting × AI skill, a 2×2); set expectations (AI is the tool, they own judgement); build capability via paired shadowing + a repeatable prompt/playbook, without disrupting BAU (run parallel, not instead).

**2c — Metrics:** leading (data completeness %, model coverage %, time-to-forecast, % plans with documented assumptions, AI adoption) + lagging (forecast MAPE/BIAS per language, SLA attainment, shrinkage actual-vs-plan, FTE variance).

---

## 11. Automation & production

1. Reproducible `uv` Python project: `load → clean → forecast → capacity → output`. All assumptions (10% uplift, 18% shrink, 173.33 h/FTE, BPO-lang map, SLA, concurrency) as config.
2. Output: formatted Excel (assumptions, cleaned data, forecast, workload/FTE, charts) + 5-slide/3-page deck.
3. Any-dataset-in-similar-format: schema contract + validation that auto-detects languages/channels; skips unknown sheets, ignores hidden sheets.
4. Website (rajindersingh.tech): upload-and-forecast app (FastAPI/Streamlit) → capacity table + charts.

---

## 12. Execution order (~2h)

1. Data cleaning + quality log (~20 min)
2. Volume forecast (~15 min)
3. AHT + workload + shrinkage + FTE (~20 min)
4. Erlang C + hiring buffer (~15 min)
5. 1b strategies (~15 min)
6. Outputs (Excel + charts) (~15 min)
7. Section 2 + 1c write-up (~20 min)

---

## 13. Open decisions (need user's call)

1. English BPO1/BPO2 split — default pooled average (OK?).
2. Outbound==Inbound anomaly — default keep-as-is + flag (OK, or re-estimate outbound?).
3. Forecast baseline — default **June run-rate × 1.10** (base), with LOW (×1.0) and HIGH (×1.2) scenarios (OK?).
4. Summer curve for Jul/Aug/Sep — default Aug = English peak (+8%), Sep shoulder (−5%), domestic flat (OK?).
5. Chat concurrency — default 1.2 but run 1.2/2.0/3.0 sensitivity (OK?).
6. Output — Excel + 5-slide deck; website app as stretch.
