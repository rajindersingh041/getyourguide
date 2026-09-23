# WFM Capacity Model

Reproduces the GetYourGuide take-home capacity forecast from the source workbook.

## Run

```bash
python run_model.py                      # full run, writes WFM_Capacity_Model_Output.xlsx
python run_model.py --aht-source reason  # sensitivity: reason-level English AHT
python run_model.py --workbook other.xlsx --excel out.xlsx
python crosscheck.py                     # 72 independent verification checks
```

## The chain

```
contacts x AHT                    -> workload hours
real-time (phone, chat): Erlang C -> concurrent seats   (occupancy < 100% IS the service level)
deferred (email, outbound)        -> hours / planned occupancy
/ (1 - shrinkage 18%)             -> paid hours
/ 173.33 h per FTE                -> FTE meeting SLA
/ tenure efficiency               -> on-floor FTE  (learning curve at 3.65%/mo attrition)
+ training class                  -> PAID FTE      (the bill)
```

## Answer (BASE = June run-rate x 1.10)

| | Jul | Aug | Sep |
|---|---|---|---|
| Contacts | 293,869 | 293,869 | 293,869 |
| FTE meeting SLA | 484 | 484 | 484 |
| **Paid FTE** | **508** | **508** | **508** |
| Productive hours | 68,827 | 68,827 | 68,827 |

LOW 462 · HIGH 518 / 551 / 579 · P10-P90 band 425-606.

## Design notes

- **Only the 6 visible sheets are read.** The hidden `CSAT` sheet raises `DataError` if requested.
- **Schema-driven, not cell-indexed.** Languages, channels and months are discovered by
  pattern, so a new language or month flows through with no code change.
- **Every assumption lives in `wfm/config.py`.** Nothing is hard-coded downstream;
  `crosscheck.py` section N proves it by re-running with altered assumptions.
- **Channel rows are the source of truth**, not the `X Tot` rows (which carry a
  +/-2 rounding residue in 17 of 30 language-months).
- **No lever is asserted.** Each optimisation is re-solved through the same Erlang
  engine - including one that turns out to cost FTE rather than save it.

## Files

| File | Purpose |
|---|---|
| `wfm/config.py` | assumptions (frozen dataclass) |
| `wfm/erlang.py` | Erlang B/C, SLA, ASA, staffing solver, normal inverse CDF |
| `wfm/loader.py` | workbook reader + schema contract |
| `wfm/clean.py` | 12 data-quality checks -> structured log |
| `wfm/forecast.py` | break detection, growth test, scenarios, confidence bands |
| `wfm/capacity.py` | workload -> Erlang -> FTE -> paid headcount, by BPO |
| `wfm/optimise.py` | Task 1b levers, each quantified |
| `wfm/report.py` | Excel export |
| `run_model.py` | end-to-end run |
| `crosscheck.py` | 72 independent verification checks |
