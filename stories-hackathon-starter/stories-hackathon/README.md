# Stories Coffee — <one-line headline with $ value>

**Team:** <Name 1>, <Name 2>  ·  EECE490 Stories Coffee Hackathon

> Status: work in progress. Every number below must come from `outputs/key_numbers.json` (run `python -m src.check_numbers`).

## 1. Conclusion (read this if nothing else)
<One paragraph, ≤120 words: the action, the $ value [ESTIMATED] and its basis, the key measured fact [MEASURED], how confident we are, and the first step Stories should take this month.>

## 2. Recommended actions
| # | Action | Owner at Stories | Value per year (low / base / high) | Confidence | First step / pilot |
|---|--------|------------------|------------------------------------|------------|--------------------|
| 1 | | | | | |

## 3. Findings
<One short section per finding: claim → evidence (link to table/figure) → value → main caveat. Full write-ups in `docs/03_findings/`.>

## 4. Data quality: what we checked and what we fixed
See [`docs/01_data_audit.md`](docs/01_data_audit.md) and the automated [`outputs/audit_report.md`](outputs/audit_report.md).

## 5. Facts vs assumptions vs estimates
Tags used throughout: **[MEASURED]** computed directly from data · **[ESTIMATED]** derived using assumptions · **[ASSUMPTION A#]** see [`docs/assumptions.md`](docs/assumptions.md).

## 6. What would change our recommendation
| Assumption | If it's wrong… | Flip point |
|---|---|---|

## 7. Tests Stories should run before wider rollout
See [`docs/pilot_designs.md`](docs/pilot_designs.md).

## 8. Limitations, uncertainty and missing information

## 9. Approaches we rejected and why
See [`docs/decision_log.md`](docs/decision_log.md).

## 10. Reproduce
```bash
pip install -r requirements.txt
# place the hackathon file at data/raw/stories_transactions.csv (not committed; see D1)
python -m src.run_all
```
