# Decision log

## Decisions
| ID | Decision | Alternatives considered | Why |
|---|---|---|---|
| D1 | Do not commit the raw CSV to the public repo; commit scripts + aggregated evidence | Commit raw data | Brief calls it real company data; graders already have it |
| D2 | Drop 132 exact duplicate rows in the main analysis | Keep them | Look like double scans (A10); sensitivity rerun keeps them |
| D3 | Basket lift on multi-item baskets only | All baskets | 54% single-item baskets bias lift below 1 (trap T4) |
| D4 | Promo evaluation via DiD with branch + date fixed effects | Raw before/after | Before/after is confounded by growth trend and weekday mix (T5, T6) |
| D5 | Interpretable models only, unless ML beats them on June holdout | Gradient boosting / deep learning | Brief: complexity alone earns no credit |

## Rejected approaches
| Approach | Why rejected | Evidence |
|---|---|---|
| Sales dashboards / top-product rankings | Brief: earns no credit; Stories' data team already has them | — |
| "Chat with your database" interface | Explicitly excluded by the brief | — |
| RFM / CLV / churn / customer segmentation | Customer IDs show no behavioural signal | F3 |
| Price elasticity from cross-branch prices | No within-branch or over-time price variation | audit check 14–18, F7 |
| Association rules on all baskets | Biased by single-item baskets | D3 |
| Causal claim about the Tuesday spike | Cause not identifiable from the data | F5 |

## Log (append as you go: date/time · who · what · why)
