"""Phase 1a: data-quality audit on the RAW file.

Writes:
  outputs/tables/audit_checks.csv        one row per check: result, pass/fail, rows affected, treatment
  outputs/tables/audit_price_cost_by_branch.csv
  outputs/tables/audit_discount_census.csv
  outputs/audit_report.md                auto-generated summary (interpreted in data-audit/README.md)
"""
import numpy as np
import pandas as pd

from .config import ROOT, TABLES
from .load import raw
from .numbers import Recorder

checks = []


def check(name, passed, result, rows=0, treatment=""):
    checks.append({"check": name, "pass": bool(passed), "result": result,
                   "rows_affected": int(rows), "treatment": treatment})


def main():
    df = raw()
    rec = Recorder("audit")
    value_cols = ["tid", "date", "time", "branch", "cust", "otype", "product", "cat",
                  "qty", "price", "disc", "cost", "rev", "gp"]

    # 1. Shape and coverage
    check("row count", True, f"{len(df):,} rows, {df.tid.nunique():,} transactions")
    days = df.d.nunique(); span = (df.d.max() - df.d.min()).days + 1
    check("calendar coverage", days == span, f"{df.d.min().date()} to {df.d.max().date()}, {days} of {span} days present")
    per_branch_days = df.groupby("branch").d.nunique()
    check("every branch every day", (per_branch_days == span).all(), per_branch_days.to_dict())
    check("opening hours", True, f"times {df.time.min()} to {df.time.max()}")

    # 2. Missingness
    na = df[value_cols].isna().sum()
    na_other = na.drop("cust")
    check("missing values (except customer)", na_other.sum() == 0, na_other[na_other > 0].to_dict() or "none")
    anon = df.cust.isna().mean()
    check("anonymous customer share", True, f"{anon:.1%} of lines have no Customer ID", df.cust.isna().sum(),
          "kept; customer analyses use known IDs only")
    rec.record("anon_line_share", anon, "MEASURED", f"{anon:.1%}")

    # 3. Arithmetic integrity
    rev_err = (df.rev - (df.qty * df.price * (1 - df.disc)).round(2)).abs() > 0.011
    gp_err = (df.gp - (df.rev - df.qty * df.cost)).abs() > 0.011
    check("revenue = qty*price*(1-disc)", rev_err.sum() == 0, f"{rev_err.sum()} mismatches", rev_err.sum())
    check("gross profit = revenue - qty*cost", gp_err.sum() == 0, f"{gp_err.sum()} mismatches", gp_err.sum())

    # 4. Ranges
    bad = (df.qty <= 0) | (df.price <= 0) | (df.cost <= 0) | (df.cost >= df.price)
    check("positive qty/price/cost and cost < price", bad.sum() == 0, f"{bad.sum()} rows violate", bad.sum())
    check("discount values", True, sorted(df.disc.unique().tolist()))
    check("quantity values", True, df.qty.value_counts().sort_index().to_dict())

    # 5. Transaction consistency
    g = df.groupby("tid")[["date", "time", "branch", "otype"]].nunique()
    cust_n = df.groupby("tid").cust.apply(lambda s: s.nunique(dropna=False))
    incons = int(((g > 1).any(axis=1) | (cust_n > 1)).sum())
    check("one date/time/branch/customer/order type per transaction", incons == 0, f"{incons} inconsistent transactions", incons)

    # 7. Price and cost stability per product x branch
    pc = df.groupby(["product", "branch"]).agg(price_mean=("price", "mean"), price_std=("price", "std"),
                                               cost_mean=("cost", "mean"), cost_std=("cost", "std"),
                                               lines=("price", "size")).reset_index()
    pc.to_csv(TABLES / "audit_price_cost_by_branch.csv", index=False)
    max_std = float(pc[["price_std", "cost_std"]].max().max())
    check("price & cost constant within product x branch", max_std < 1e-9, f"max std = {max_std:.4f}")
    wide_p = pc.pivot(index="product", columns="branch", values="price_mean")
    wide_c = pc.pivot(index="product", columns="branch", values="cost_mean")
    for b in ["Garden", "Uptown"]:
        pr = wide_p[b] / wide_p["Harbour"]; cr = wide_c[b] / wide_c["Harbour"]
        check(f"{b} vs Harbour price ratio", True, f"mean {pr.mean():.3f} (range {pr.min():.3f}-{pr.max():.3f})")
        check(f"{b} vs Harbour cost ratio", True, f"mean {cr.mean():.3f} (range {cr.min():.3f}-{cr.max():.3f})")

    # 8. Discount census (this is how promo windows are found)
    dc = (df[df.disc > 0].groupby(["disc", "branch", "cat"]).agg(lines=("tid", "size"),
          first=("date", "min"), last=("date", "max"), days=("date", "nunique")).reset_index())
    dc.to_csv(TABLES / "audit_discount_census.csv", index=False)
    check("discount census", True, f"{(df.disc > 0).mean():.1%} of lines discounted; see audit_discount_census.csv")

    # 9. Daily outliers after weekday + trend
    daily = df.groupby("d").tid.nunique().rename("n").to_frame()
    X = pd.get_dummies(daily.index.day_name()).astype(float).values
    X = np.column_stack([X, np.arange(len(daily))])
    beta, *_ = np.linalg.lstsq(X, np.log(daily.n.values), rcond=None)
    resid = np.log(daily.n.values) - X @ beta
    check("daily outliers (|resid| > 3 SD after weekday+trend)", (np.abs(resid) > 3 * resid.std()).sum() == 0,
          f"residual SD {resid.std():.3f}; {(np.abs(resid) > 3 * resid.std()).sum()} outlier days")

    # 10. Synthetic-data signals (neutral statement)
    synth = df.tid.str.startswith("SYN-").mean()
    check("ID format", True, f"{synth:.0%} of IDs start with 'SYN-' (replacement IDs per brief); "
          "constant multipliers suggest generated/perturbed data", 0, "noted as a weak area in each report")

    out = pd.DataFrame(checks)
    out.to_csv(TABLES / "audit_checks.csv", index=False)
    md = ["# Automated data audit (generated by src/audit.py; do not edit by hand)", "",
          "| # | Check | Pass | Result | Rows | Treatment |", "|---|---|---|---|---|---|"]
    for i, r in out.iterrows():
        md.append(f"| {i+1} | {r.check} | {'✅' if r['pass'] else '⚠️'} | {r.result} | {r.rows_affected} | {r.treatment} |")
    (ROOT / "outputs" / "audit_report.md").write_text("\n".join(md) + "\n")
    rec.save()
    print(f"audit: {len(out)} checks, {(~out['pass']).sum()} flagged -> outputs/audit_report.md")


if __name__ == "__main__":
    main()
