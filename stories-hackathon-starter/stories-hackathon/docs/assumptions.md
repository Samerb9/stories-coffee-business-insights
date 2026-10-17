# Assumptions register

Rule: no clarifying questions. Every judgement call goes here. **Decision impact** is one of: `none` · `changes size` · `flips action`.

| ID | Assumption | Why it's reasonable | If wrong… | Decision impact |
|---|---|---|---|---|
| A1 | The data (which looks generated/perturbed) reflects Stories' real business patterns | Brief says it is real data with replacement IDs | All findings become illustrative only | flips action |
| A2 | Branches are comparable outlets with the same opening hours (07:00–24:00) | Identical hourly coverage in data | Branch comparisons need hour adjustment | changes size |
| A3 | Garden's cost gap is at least partly closable (closable share = scenario variable) | Same products cost 30% less at two other branches | F1 value shrinks | changes size |
| A4 | Headline annualisation = full-period average; June run-rate shown as upper case | Strong growth trend (trap T7) | Value range shifts | changes size |
| A5 | Prices are VAT-inclusive | Typical café POS | Revenue figures scale | none |
| A6 | Unit cost = COGS (ingredients + packaging), not allocated overhead | Column named "Unit Cost" at line level | F1 becomes an accounting-allocation issue; action changes from "renegotiate suppliers" to "review cost allocation" | flips action |
| A7 | The 15% lines identify the complete promotion (SKUs and windows) | 100% of promo-SKU lines at Harbour in-window carry 15% | F2 estimate may be biased | changes size |
| A8 | Customer IDs may have been scrambled in anonymisation | IDs show zero behavioural signal | F3 becomes "re-test on raw IDs" | changes size |
| A9 | Purpose of the 10% discount is unknown → treated as discretionary | No reason code in data | F6 recommendation changes if it's contractual | changes size |
| A10 | Exact duplicate rows are double scans | Real doubles are recorded as qty = 2 | ≈$741 revenue, negligible | none |
| A11 | No closures or special events beyond weekday + trend effects | No outlier days in audit | Local effects missed | none |
| A12 | Labour cost per staff-hour (F5) = external range, not from data | No labour data provided | F5 value range shifts | changes size |
