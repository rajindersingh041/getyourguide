# GetYourGuide WFM case study — interview walkthrough

Submitted file: `GYG_Rajinder_Singh_2026_09_29.pdf`
This doc is the talk-track for explaining that submission live — the story,
the numbers, and the answers to the questions most likely to come up.

---

## 1. The 30-second pitch

I replaced the "average the last few months" approach with a proper
capacity-planning chain: clean the data → forecast volume with seasonality
in mind → convert volume to workload using the right AHT per channel →
solve for the number of agents that actually meets the SLA (not just
average workload) → add shrinkage, training, and attrition buffers on top.
Every number in the deck is reproducible from the source workbook and
re-derived by a Python model (`run_model.py`), not typed into a slide by
hand. Two optimisation levers are quantified end-to-end through the same
engine — including one that looked obviously good and turned out to
*cost* FTE when actually solved.

---

## 2. The formula chain (say this out loud, it's the spine of everything)

```
contacts (language x channel x month)
   -> x AHT (seconds)                  = workload (hours)
   -> Erlang C (phone, chat)           = seats needed to hit SLA
      OR hours / occupancy (email, outbound) = seat-equivalent hours
   -> / (1 - shrinkage 18%)            = paid hours
   -> / 173.33 h per FTE               = FTE meeting SLA
   -> / tenure efficiency (learning curve + attrition) = on-floor FTE
   -> + training-class backfill        = PAID FTE (the actual bill)
```

**Why Erlang C and not just "hours ÷ hours-per-FTE":** workload alone tells
you the average number of agents busy at any moment, not how many you need
on the clock. Customers arrive randomly; you need enough slack in the
schedule to absorb bursts and still answer 80% of calls within 20 seconds.
That slack *is* idle time — occupancy under 100% is not waste, it's the
service level. A German inbound queue with only 1.26 erlangs of workload
still needs 3 seats round the clock to hit 80/20, because you can't have a
fraction of an agent answer a burst. That's also the root cause behind the
whole language-pooling optimisation idea (§5).

**Why so many buffers stacked on top of the SLA number:** the "FTE meeting
SLA" number (484) isn't what you'd actually hire. New agents are slower
(120%/110%/105% of AHT for their first 3 months) — that costs ~5.5 FTE.
36% annual attrition means ~3.65%/month of the workforce is mid-training,
producing nothing while paid — that costs ~17.9 FTE. Add those and 484
becomes **508 paid FTE** — the number that goes on the bill.

---

## 3. Data understanding — what I found before trusting any number

The workbook has 7 sheets; 1 (`CSAT`) is hidden and explicitly excluded per
instructions. Of the 6 visible sheets, here's what needed fixing before any
math ran on it:

- **EN CSAT:** a "18.2 Positive feedback" row has 0 tickets but a CSAT
  value present — nulled the CSAT rather than dividing by zero or fabricating
  a weight. One row has a blank reason label with 735 tickets in January —
  kept the volume (it's real demand) but tagged it "UNMAPPED" rather than
  silently dropping it.
- **EN AHT by Contact reason:** one clear outlier (`1.4 Pricing`, June =
  271s vs 860–2046s everywhere else) — replaced with the reason's trailing
  median rather than trusting a value 3-5x out of family.
- **AHT taxonomy:** 45 reason codes collapse to 25 distinct AHT profiles —
  the same real issue (e.g. "meeting point") is re-coded at different
  journey stages (`1.2`/`3.3`/`6.3`) but shares identical AHT. That's proof
  the codes are cosmetically granular but measured at family level, so I
  aggregated English to the first-digit family (14 families, ~83% of
  volume in the top 4) rather than forecasting 49 noisy sub-reason series.
- **Contact Volume:** Outbound Phone contacts exactly mirror Inbound Phone
  for German/Italian/Spanish/French every month (and English in 5 of 6) —
  the signature of a copied or synthetic column, not independently measured
  outbound activity. Flagged as an open question rather than silently
  "fixed" — see §7.
- **AHT Assumptions by BPO and lang:** some BPO×language combinations are
  structurally impossible (BPO3-English, BPO1/2-non-English) given the
  routing constraint in `Other information` — dropped those rows rather
  than let them silently pollute an average.
- **Chat concurrency = 1.2** sits under a column header that literally says
  "Chat concurrency *English*" but repeats identically on every BPO and
  every language row — treated as a flagged assumption, not a fact. See §7.

**Takeaway to state explicitly:** every one of these was a *decision*, not
a silent fix — the deck documents what was found, what was done about it,
and why, so a reviewer can disagree with a specific call without distrusting
the whole model.

---

## 4. Task 1a — the forecast (why June, not an average)

The naive move is "average the 6 months, add 10%." That's wrong here
because the data isn't noise around a flat mean — it's **seasonal travel
demand with a structural step**:

- **March jumps +87% MoM, uniformly** across all 5 languages, all 4
  channels, all contact reasons. A data glitch would hit one reason or
  channel; this hits everything equally — that's the signature of a real
  demand shift (spring/summer travel ramp), not an error.
- **English swings ~3x winter to summer** (January is 32% of June's
  volume) because it's driven by international tourists. The domestic
  languages (German, Italian, Spanish, French) are far flatter — so a
  single seasonal shape across all languages would be wrong.
- **April is elevated (Easter), May dips back** (−7% MoM English), June is
  the start of the summer ramp.

**Forecast method:** baseline = **June run-rate** (the most recent month,
already on the summer upswing), not a trailing-3-month average — a
trailing average drags the June peak down with May's post-Easter dip and
would *under-forecast* the actual summer peak. Apply the mandated +10%
uplift on top. Report **LOW/BASE/HIGH** scenarios (×1.00/×1.10/×1.20) to
bracket the risk explicitly rather than hand over one number pretending to
be certain.

**The baseline choice is not cosmetic** — trailing-3mo+10% gives 265.7k
contacts / 376 FTE; June×1.10 gives 293.9k / **428 FTE**. That's a 52 FTE
swing from one methodology choice. Under-forecasting the summer peak means
missed SLA and agent burnout; over-forecasting means idle cost. State this
number if asked "why does the baseline choice matter" — it's the clearest
illustration of why the method, not just the output, needs defending.

**Confidence intervals, not a point estimate:** modelled July volume as
log-normal (median = base, σ from the historical month-over-month
log-returns excluding the March seasonal step ≈ 14%). Result: "80%
confident July needs somewhere between 353 and 519 FTE" rather than a
false-precision single number. **Planning implication stated explicitly:**
staff a ~430 FTE core and hold a flexible/cross-trained bench for the
upside, with monthly actual-vs-forecast triggers to scale.

**Honest limitation to volunteer, not wait to be asked:** 6 months of data
cannot support a real seasonal model — you need 24+ months to see a full
annual cycle. The real fix, stated in the submission, is to request more
history, an events calendar, and market/geo mix, then fit something like
Holt-Winters multiplicative instead of a hand-built scenario.

---

## 5. Task 1b — optimisation, ranked honestly by effort-to-act

Full numbers and per-queue data are in `task1b.md` — this is the talk-track
summary. The organizing idea for the interview: **don't present these as
equally "doable."** Rank them by what it actually takes to execute, because
that's what a hiring manager for a WFM role is actually listening for —
judgement, not just arithmetic.

### The one action with zero dependencies — BPO channel routing (4.5 FTE)

English volume is split 50/50 between BPO1 and BPO2 **uniformly across
every channel**. But the vendors aren't equally fast at every channel:
BPO1 is faster at Inbound (450s vs 465s) and Outbound (105s vs 110s); BPO2
is faster at Chat (1,100s vs 1,200s). Routing each channel to whichever
vendor is already faster at it — no renegotiation, no new headcount, just
an IVR/router config change — drops English from 283.5 to 279.0 FTE.
Smaller than the other levers, but the only one on the list that needs
nobody's approval and has zero execution risk.

### Language pooling — 18.8 FTE pilot, up to 78.8 FTE if fully extended

**The mechanism:** small non-English queues are staffed 24/7 and each pays
the Erlang-C minimum-seat floor independently — a queue with barely one
call in progress at a time still needs 3 seats to hit 80/20 around the
clock. Pool several languages into one queue and you share that floor
instead of paying it four times.

**The catch I volunteer before anyone asks:** pooling only works if agents
are cross-skilled. The router still needs to match a German caller to
someone who speaks German — it just draws from a wider pool of eligible
agents. It is **not** random cross-language routing, and it is **not**
achievable without first checking whether BPO3 already has multilingual
agents, or needs a hiring/training plan.

**Phased, not all-at-once:**
- Phase 1 — pilot **Spanish + French** (chosen for Romance-language
  adjacency, higher odds real bilingual agents exist): **18.8 FTE**
  (10.3 Inbound + 8.6 Chat), start on the overnight window where the
  floors are most wasteful and customer-facing risk is lowest if it needs
  correcting.
- Phase 2 — extend to German + Italian, merged into one 4-language pool,
  **gated on Phase 1's actual results**: **51.4 FTE cumulative**.
- Phase 3 — add English into the same pool: **78.8 FTE cumulative**, but
  this requires vendor consolidation (English sits in BPO1/2, the other
  four in BPO3) — a bigger lift, flagged as a later-stage goal not a
  near-term commitment.

**Cost honesty:** bilingual agents likely cost more per hour. The
Phase-1 saving tolerates up to a ~34% pay premium before it's erased;
realistic BPO bilingual premiums run 5-15%, a wide margin — but state the
math, don't just assert it's fine.

### Tested and rejected — deflect phone to chat

The intuitive lever: chat agents can multitask, so shift volume there.
Modelled end-to-end through the same Erlang engine, it **costs** FTE: even
accounting for 1.2x concurrency, English chat consumes 958 agent-seconds
per contact against phone's 458. Shifting 30% of inbound to chat *adds*
15.4 FTE. **Why this matters for the interview:** it shows the model
re-solves every idea rather than asserting the obvious answer — an idea
that sounds right and turns out wrong is more convincing evidence of rigor
than three ideas that all happen to work.

### Two things flagged as questions, not actions

- **Chat concurrency (up to 75 FTE):** the 1.2 figure is labelled "English"
  but applied to every BPO and language. Chat is 188 FTE — 39% of the
  entire operation — so if 1.2 was never actually measured for the other
  languages, the plan could be off by 75 FTE in either direction.
- **Outbound volume (up to 78 FTE):** Outbound mirrors Inbound almost
  exactly, which structurally cannot be real independent demand. This
  can't be resolved from the dataset alone — it needs the data owner.
  **If asked "why didn't you just fix it":** because guessing the right
  correction (delete it? discount it 90%? model it separately?) risks
  being more wrong than leaving it flagged with the number priced both
  ways (508 FTE including it vs 585 FTE if the ticket-level AHT basis is
  used instead — see `understanding_numbers.md` for the full derivation).

### Shrinkage restagger — real, but flagged as not provable from this data

8 of the 18 shrinkage points (Break+Lunch 6%, Meetings 1%, Coaching 1%)
are scheduling choices, not fixed entitlements like Vacation/Sick.
Reclaiming 1-2 points via staggering breaks off peak-demand hours is worth
5.8-11.5 FTE. **Say this honestly if asked:** the source data is
monthly-aggregate only, with no hour-of-day volume, so the model can't
actually prove a staggered schedule reduces peak understaffing — the lever
is directionally real but needs intraday data and labor/scheduling buy-in
before it's more than a hypothesis.

---

## 6. Task 1c — how AI was actually used (be specific, not promotional)

State plainly where AI helped and where it didn't, and where a suggestion
was rejected or changed:

- **Used for:** data-quality triage (spotting the AHT outlier, the
  Outbound==Inbound mirror, the AHT taxonomy collapse), structuring the
  Erlang C / shrinkage / FTE formula chain into clean Python, drafting the
  30/60/90 roadmap skeleton, generating the verification suite
  (`crosscheck.py`, 72 checks) to catch regressions.
- **Rejected / changed:** an early AI suggestion to silently "fix" the
  Outbound==Inbound anomaly by discounting it 85% — rejected, because
  there was no data-grounded basis for that specific number; flagged as an
  open question instead. Also rejected a first-pass chat-deflection
  recommendation that assumed deflection always saves FTE — re-solved it
  properly and it came back negative.
- **What I'd do differently with more time:** get real intraday
  (15/30-minute) arrival data instead of monthly aggregates — the Erlang
  math is currently a defensible floor, not a precise answer, because
  monthly averaging smooths out the bursts that actually drive staffing.

---

## 7. Section 2 — the transformation roadmap (talk-track, not a slide read)

**30/60/90, in one sentence each:**
- Days 0-30: stop guessing, start deciding — freeze a single source of
  truth, agree an accuracy target (MAPE ≤10%), pilot on English (highest
  volume, most data).
- Days 31-60: build the AI-assisted forecast in parallel (shadow mode) —
  never cut over on day one, run it alongside the existing Sheets process
  and reconcile weekly.
- Days 61-90: cut over English, extend to the other 4 languages, "done"
  means the model produces the weekly plan, beats manual accuracy, and the
  team can run it without me in the room.

**Team of 3, one sentence:** assess each person on a forecasting-skill ×
AI-comfort 2x2, pair the strong-AI person with the strong-forecasting
person for shadowing, and keep BAU running in parallel rather than
disrupting it — the team should feel like they gained a tool, not that
their judgement got replaced.

**Metrics, one sentence:** leading indicators (data completeness, time to
forecast, % of plans with documented assumptions) tell you if the *process*
is healthy before the lagging indicators (forecast MAPE, SLA attainment,
shrinkage actual-vs-plan) tell you if the *outcome* is.

---

## 8. Anticipated questions and how to answer them

**"Why 6 months isn't enough — what would you actually do with 24?"**
Fit a real seasonal model (Holt-Winters multiplicative or similar) instead
of a hand-built scenario multiplier, and separate the March step-change
from ongoing trend instead of lumping both into one volatility number.

**"What's the single riskiest assumption in this plan?"**
Whether Outbound English volume is real. It swings the answer between 508
and 585 FTE — bigger than any of the optimisation levers — and it's the
one thing genuinely impossible to resolve from the dataset alone.

**"If you had to cut this to one optimisation idea, which one?"**
BPO channel routing — smallest number (4.5 FTE) but zero dependencies,
zero risk, same-day executable. Everything bigger costs either a
verification (concurrency, outbound) or an operational dependency
(pooling needs a skills audit; shrinkage needs labor buy-in and data this
dataset doesn't have).

**"How would you put this in production?"**
Reproducible Python pipeline (`load → clean → forecast → capacity →
optimise → report`), every assumption in one config file
(`wfm/config.py`), schema-driven loader so a new language/month flows
through with no code change, 72-check verification suite so a future edit
can't silently break a number. Output as a formatted Excel workbook plus
the deck. Stretch: a small upload-and-forecast web app.

**"What would you have done differently given more than 2 hours?"**
Gotten intraday arrival data before trusting the Erlang C numbers as more
than a directional floor, and gotten a straight answer on the Outbound
question before presenting two versions of the same number.

---

## 9. Where the receipts live (for "can you show me that")

- `PLAN.md` — the full working plan, every formula, every sourced cell
  reference back to the workbook.
- `task1b.md` — full Task 1b data: all phases, all per-queue numbers, the
  ease-vs-impact ranking.
- `understanding_numbers.md` — the 360→484→508 FTE build-up walked through
  step by step, plus the full Outbound/AHT open-question derivation.
- `MODEL_README.md` — how to run the model (`run_model.py`,
  `crosscheck.py`) and what each module does.
- `wfm/` — the actual Python implementation (`erlang.py`, `capacity.py`,
  `optimise.py`, `clean.py`, `forecast.py`).
- `GYG_WFM_Submission.pptx` / `.pdf` / `.html` — the rendered deck.
