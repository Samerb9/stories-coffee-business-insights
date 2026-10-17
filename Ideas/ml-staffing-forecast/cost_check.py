"""Second finding: Garden's recorded unit costs are 1.43x Harbour's on every product.

Run:  python cost_check.py
Writes outputs/cost_check.csv (per product) and outputs/cost_check.json (key numbers).
"""
import argparse
import json
from pathlib import Path

import pandas as pd

from forecast import find_data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=None)
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "outputs"))
    args = ap.parse_args()
    args.data = find_data(args.data)
    out = Path(args.out)

    d = pd.read_csv(args.data).drop_duplicates()
    d["Date"] = pd.to_datetime(d["Date"])
    d["cogs"] = d["Unit Cost (USD)"] * d["Quantity"]

    # unit cost and price never change within a branch x product, so one value each
    cost = d.groupby(["Product", "Category", "Branch"])["Unit Cost (USD)"].agg(["min", "max"])
    price = d.groupby(["Product", "Branch"])["Unit Price (USD)"].agg(["min", "max"])
    assert (cost["min"] == cost["max"]).all() and (price["min"] == price["max"]).all()
    c = cost["min"].unstack("Branch")
    pr = price["min"].unstack("Branch")
    per_product = c.reset_index().rename(columns={b: f"unit_cost_{b}" for b in ["Garden", "Harbour", "Uptown"]})
    per_product["garden_over_harbour_cost"] = (c.Garden / c.Harbour).values
    per_product["uptown_over_harbour_cost"] = (c.Uptown / c.Harbour).values
    per_product["garden_over_harbour_price"] = (pr.Garden / pr.Harbour).reindex(per_product.Product).values
    per_product.to_csv(out / "cost_check.csv", index=False, float_format="%.4f")

    c = c.droplevel("Category")   # one row per product from here on
    s = d.groupby("Branch").agg(revenue=("Line Revenue (USD)", "sum"), gross_profit=("Line Gross Profit (USD)", "sum"),
                                cogs=("cogs", "sum"), units=("Quantity", "sum"))
    s["margin"] = s.gross_profit / s.revenue
    g = d[d.Branch == "Garden"]
    ratio = c.Garden / c.Harbour
    garden_cogs_at_harbour_costs = (g["Unit Cost (USD)"] / ratio.reindex(g.Product).values * g.Quantity).sum()
    gap = s.loc["Garden", "cogs"] - garden_cogs_at_harbour_costs
    # margin Garden would have if it ran Harbour's product mix at its own prices and costs
    h = d[d.Branch == "Harbour"].groupby("Product").Quantity.sum()
    mix_margin = 1 - (h * c.Garden.reindex(h.index)).sum() / (h * pr.Garden.reindex(h.index)).sum()
    monthly = d.groupby([d.Date.dt.month, "Branch"]).cogs.sum().unstack()
    water = [p for p in c.index if "water" in p.lower()]

    nums = {
        "garden_over_harbour_unit_cost": {"min": round(float(ratio.min()), 4), "max": round(float(ratio.max()), 4),
                                          "products": int(len(ratio))},
        "uptown_over_harbour_unit_cost": {"min": round(float((c.Uptown / c.Harbour).min()), 4),
                                          "max": round(float((c.Uptown / c.Harbour).max()), 4)},
        "garden_over_harbour_price": {"min": round(float((pr.Garden / pr.Harbour).min()), 4),
                                      "max": round(float((pr.Garden / pr.Harbour).max()), 4)},
        "water_products_cost_ratio": {p: round(float(ratio.loc[p]), 4) for p in water},
        "by_branch": {b: {k: round(float(v), 4) for k, v in r.items()} for b, r in s.iterrows()},
        "garden_units_vs_harbour": round(float(s.loc["Garden", "units"] / s.loc["Harbour", "units"] - 1), 4),
        "garden_cogs_vs_harbour": round(float(s.loc["Garden", "cogs"] / s.loc["Harbour", "cogs"] - 1), 4),
        "monthly_cogs_garden_over_harbour": {int(m): round(float(v), 3) for m, v in (monthly.Garden / monthly.Harbour).items()},
        "garden_margin_with_harbour_mix": round(float(mix_margin), 4),
        "garden_margin_at_harbour_costs": round(float(1 - garden_cogs_at_harbour_costs / s.loc["Garden", "revenue"]), 4),
        "excess_cost_jan_jun_usd": round(float(gap), 0),
        "excess_cost_per_year_usd": round(float(gap * 365 / 181), 0),
    }
    (out / "cost_check.json").write_text(json.dumps(nums, indent=2))
    print(f"[costs] Garden/Harbour unit cost {ratio.min():.3f}-{ratio.max():.3f} on {len(ratio)} products; "
          f"margin {s.loc['Garden', 'margin']:.1%} vs {s.loc['Harbour', 'margin']:.1%}; "
          f"excess cost ${gap:,.0f} Jan-Jun (~${gap * 365 / 181:,.0f}/year)")


if __name__ == "__main__":
    main()
