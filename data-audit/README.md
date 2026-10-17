# Data audit

**Team:** Christopher Ferzli, Samer Bannout

Before any analysis, we checked the raw file in 20 automated tests. The full table is in [outputs/audit_report.md](outputs/audit_report.md).

**What we found:**
- **The file is internally consistent.**
  - 51,177 lines and 33,887 receipts, covering 181 of 181 days for every branch.
  - No missing values except Customer ID.
  - Revenue and gross profit reconcile exactly on every line.
  - Every receipt has a single date, time, branch and order type.
  - No outlier days once weekday and growth are accounted for.
- **36.5% of lines have no Customer ID.**
- **Prices and costs never change within a product and branch.** Each branch is a constant multiple of Harbour:

  | Branch vs Harbour | Price | Unit cost |
  |---|---|---|
  | Garden | ×0.95 | **×1.43** |
  | Uptown | ×0.91 | ×0.96 |

  Garden's cost multiple is the basis of the Garden cost finding in [`ml-staffing-forecast`](../Ideas/ml-staffing-forecast) (report §10).
- **The transaction IDs are replacement IDs (`SYN-…`).** The brief says so, and the constant multipliers suggest the data may be generated or perturbed. Each report lists this as a weak area.

**What this means for our conclusions:** the numbers are clean enough to trust as recorded. The constant multipliers rule out learning price effects from this data. That's why no idea relies on price elasticity.

## Run

```bash
cd data-audit
pip install -r requirements.txt
python -m src.audit
```

It reads `data/stories_transactions.csv` at the repo root and writes `outputs/`.
