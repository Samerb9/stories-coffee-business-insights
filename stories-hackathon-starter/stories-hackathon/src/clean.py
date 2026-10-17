"""Phase 1b: build the clean datasets every finding uses.

Decisions applied here (see docs/decision_log.md):
  D2 - exact duplicate rows are dropped (treated as double scans, assumption A10).
Outputs:
  data/processed/lines.csv         one row per product line
  data/processed/transactions.csv  one row per receipt
"""
import numpy as np

from .config import DRINK_CATEGORIES, LINES_CSV, TX_CSV
from .load import raw
from .numbers import Recorder


def build(drop_duplicates: bool = True):
    df = raw()
    n_raw = len(df)
    if drop_duplicates:
        df = df.drop_duplicates(subset=[c for c in df.columns if c not in ("d", "dt")])
    df["is_drink"] = df["cat"].isin(DRINK_CATEGORIES)
    df["list_rev"] = (df["qty"] * df["price"]).round(2)
    df["discount_usd"] = (df["list_rev"] - df["rev"]).round(2)
    df["known_cust"] = df["cust"].notna()

    first_drink = df[df.is_drink].groupby("tid")["cat"].first()
    tx = df.groupby("tid").agg(
        d=("d", "first"), dt=("dt", "first"), dow=("dow", "first"), hour=("hour", "first"),
        month=("month", "first"), week=("week", "first"), branch=("branch", "first"),
        cust=("cust", "first"), otype=("otype", "first"),
        lines=("product", "size"), items=("qty", "sum"),
        rev=("rev", "sum"), gp=("gp", "sum"), list_rev=("list_rev", "sum"),
        discount_usd=("discount_usd", "sum"), max_disc=("disc", "max"),
        n_drink=("is_drink", "sum"),
    ).reset_index()
    tx["n_food"] = tx["lines"] - tx["n_drink"]
    tx["has_drink"] = tx["n_drink"] > 0
    tx["has_food"] = tx["n_food"] > 0
    tx["drink_cat"] = tx["tid"].map(first_drink)
    tx["known_cust"] = tx["cust"].notna()
    return df, tx, n_raw


def main():
    df, tx, n_raw = build()
    out = df.drop(columns=["d", "dt"])
    out.to_csv(LINES_CSV, index=False)
    tx.to_csv(TX_CSV, index=False)

    rec = Recorder("clean")
    rec.record("rows_raw", n_raw, "MEASURED", f"{n_raw:,}")
    rec.record("rows_clean", len(df), "MEASURED", f"{len(df):,}")
    rec.record("duplicates_dropped", n_raw - len(df), "MEASURED", f"{n_raw - len(df):,}")
    rec.record("transactions", len(tx), "MEASURED", f"{len(tx):,}")
    rec.record("customers", int(df["cust"].nunique()), "MEASURED", f"{df['cust'].nunique():,}")
    rec.record("date_min", str(df["d"].min().date()), "MEASURED")
    rec.record("date_max", str(df["d"].max().date()), "MEASURED")
    share_single = float(np.mean(tx["lines"] == 1))
    rec.record("share_single_item_baskets", share_single, "MEASURED", f"{share_single:.0%}")
    rec.save()
    print(f"clean: {len(df):,} lines, {len(tx):,} transactions -> {LINES_CSV.parent}")


if __name__ == "__main__":
    main()
