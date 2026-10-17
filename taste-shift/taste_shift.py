"""Idea 3: are customers' tastes shifting, and how should each branch plan its item mix?

Within each category (e.g. Matcha & Tea), which items do customers pick, and does that change?
1. Trend test for every item's share of its category, at monthly and daily level, with the
   direction checked at each branch and a correction for testing 45 items.
2. Do month-to-month swings persist or reverse?
3. June test: plan each item's June share with 4 rules using only Jan-May data, score on June.

Run:  python taste_shift.py   (reads ../data/stories_transactions.csv, writes outputs/)
"""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests

SEED = 490
HERE = Path(__file__).resolve().parent
ACCENT, GREY, GREEN = "#C0392B", "#7F7F7F", "#1E8449"
SOURCE = "Source: Stories POS receipts, Jan-Jun 2026 (132 duplicate lines removed); team analysis."


def find_data(arg=None):
    for p in [arg, HERE.parent / "data" / "stories_transactions.csv", HERE / "data" / "stories_transactions.csv"]:
        if p and Path(p).exists():
            return Path(p)
    raise SystemExit("stories_transactions.csv not found: put it in the data/ folder at the repo root")


def style(ax):
    ax.grid(color="#E5E5E5", linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def share_trend(x, unit):
    """Binomial GLM: item units vs rest of category, branch effects + linear time trend.
    Returns slope (log-odds per period), p-value, and whether all 3 branches slope the same way."""
    y = np.column_stack([x.q, x.cat_q - x.q])
    X = pd.get_dummies(x.branch, drop_first=True).astype(float)
    X["t"] = x[unit].astype(float).values
    r = sm.GLM(y, sm.add_constant(X), family=sm.families.Binomial()).fit()
    signs = set()
    for _, xb in x.groupby("branch"):
        rb = sm.GLM(np.column_stack([xb.q, xb.cat_q - xb.q]), sm.add_constant(xb[unit].astype(float).values),
                    family=sm.families.Binomial()).fit()
        signs.add(np.sign(rb.params[1]))
    return r.params["t"], r.pvalues["t"], len(signs) == 1


def counts(d, unit):
    g = d.groupby(["branch", "cat", "item", unit]).q.sum()
    keys = g.reset_index()[["branch", "cat", "item"]].drop_duplicates()
    periods = sorted(d[unit].unique())
    idx = pd.MultiIndex.from_tuples([(b, c, i, t) for b, c, i in keys.itertuples(index=False) for t in periods],
                                    names=g.index.names)
    g = g.reindex(idx, fill_value=0).reset_index()
    g["cat_q"] = g.groupby(["branch", "cat", unit]).q.transform("sum")
    return g[g.cat_q > 0]


def trend_table(d):
    m, dd = counts(d, "month"), counts(d, "day")
    rows = []
    for (c, i), x in m.groupby(["cat", "item"]):
        sm_, pm, same3 = share_trend(x, "month")
        _, pdy, _ = share_trend(dd[(dd.cat == c) & (dd.item == i)], "day")
        rows.append({"category": c, "item": i, "slope_per_month": sm_, "p_monthly": pm, "p_daily": pdy,
                     "same_direction_all_branches": same3})
    t = pd.DataFrame(rows)
    t["p_monthly_bh"] = multipletests(t.p_monthly, method="fdr_bh")[1]
    t["p_daily_bh"] = multipletests(t.p_daily, method="fdr_bh")[1]
    return t


def chain_shares(d, unit):
    s = d.groupby(["cat", "item", unit]).q.sum().rename("q").reset_index()
    s["share"] = s.q / s.groupby(["cat", unit]).q.transform("sum")
    return s.pivot_table(index=["cat", "item"], columns=unit, values="share")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=None)
    ap.add_argument("--out", default=str(HERE / "outputs"))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)

    raw = pd.read_csv(find_data(args.data)).drop_duplicates()
    d = pd.DataFrame({"branch": raw.Branch, "cat": raw.Category, "item": raw.Product, "q": raw.Quantity,
                      "date": pd.to_datetime(raw.Date), "cost": raw["Unit Cost (USD)"],
                      "gp_unit": raw["Line Gross Profit (USD)"] / raw.Quantity})
    d["month"] = d.date.dt.month
    d["day"] = (d.date - d.date.min()).dt.days

    # ---------------- 1. trend test for every item's share of its category
    t = trend_table(d)
    sh = chain_shares(d, "month")
    t["share_jan"] = [sh.loc[(c, i), 1] for c, i in zip(t.category, t["item"])]
    t["share_jun"] = [sh.loc[(c, i), 6] for c, i in zip(t.category, t["item"])]
    t["change_pts"] = (t.share_jun - t.share_jan) * 100
    t["mover"] = (t.p_monthly < 0.05) & t.same_direction_all_branches
    t["mover_both_tests"] = t.mover & (t.p_daily < 0.05)
    t.sort_values("p_monthly").to_csv(out / "taste_item_trends.csv", index=False, float_format="%.4f")
    movers = t[t.mover].sort_values("change_pts", ascending=False)
    robust = t[t.mover_both_tests]
    borderline = t[(~t.mover) & t.same_direction_all_branches & ((t.p_monthly < 0.1) | (t.p_daily < 0.05))]

    # ---------------- 2. do swings persist or reverse? (two-month blocks, chain level)
    d["block"] = (d.month + 1) // 2
    bp = chain_shares(d, "block") * 100
    ch1, ch2 = bp[2] - bp[1], bp[3] - bp[2]
    rev = pd.DataFrame({"change_janfeb_to_marapr": ch1, "change_marapr_to_mayjun": ch2}).reset_index()
    rev["mover"] = rev.item.isin(movers["item"])
    rev.to_csv(out / "taste_reversal.csv", index=False, float_format="%.3f")
    reversal_corr = float(np.corrcoef(ch1, ch2)[0, 1])
    kept_direction = float(((ch1 * ch2) > 0).mean())

    # ---------------- 3. June test: plan each item's share of its branch category
    m = counts(d, "month")
    m["share"] = m.q / m.cat_q
    S = m.pivot_table(index=["branch", "cat", "item"], columns="month", values="share").fillna(0)
    jun = m[m.month == 6].set_index(["branch", "cat", "item"])
    months = np.arange(1, 6)
    trend_fc = S[list(months)].apply(lambda r: max(0.0, np.polyval(np.polyfit(months, r.values, 1), 6)), axis=1)
    avg5 = S[list(months)].mean(axis=1)
    # watchlist built from Jan-May only: same test, same rule (monthly p < 0.05, same direction at all branches)
    t_jm = trend_table(d[d.month <= 5])
    watch = t_jm[(t_jm.p_monthly < 0.05) & t_jm.same_direction_all_branches]["item"].tolist()
    in_watch = S.index.get_level_values("item").isin(watch)
    rules = {"Copy last month's mix": S[5], "Fit a trend for every item": trend_fc,
             "Average of the last 5 months": avg5,
             "5-month average + watchlist": avg5.where(~in_watch, trend_fc)}
    errs, cell_err = [], {}
    for name, share in rules.items():
        pred = jun.cat_q * share.reindex(jun.index).fillna(0)
        e = (pred - jun.q).abs()
        cell_err[name] = e
        errs.append({"rule": name, "june_error": e.sum() / jun.q.sum(), "units_misplanned": e.sum(),
                     "error_on_watchlist_items": e[jun.index.get_level_values("item").isin(watch)].sum() /
                     jun.q[jun.index.get_level_values("item").isin(watch)].sum() if watch else np.nan})
    # 95% bootstrap range for each rule and for (last month - 5-month average), resampling branch-item cells
    n = len(jun)
    B = rng.integers(0, n, size=(2000, n))
    qv = jun.q.values
    boot = {k: np.array([v.values[b].sum() / qv[b].sum() for b in B]) for k, v in cell_err.items()}
    for r in errs:
        r["lo95"], r["hi95"] = np.quantile(boot[r["rule"]], [0.025, 0.975])
    june = pd.DataFrame(errs)
    june.to_csv(out / "taste_june_test.csv", index=False, float_format="%.4f")
    diff_last_avg = boot["Copy last month's mix"] - boot["Average of the last 5 months"]
    diff_trend_avg = boot["Fit a trend for every item"] - boot["Average of the last 5 months"]

    # daily planning: same shares, applied to each day's actual category total in June
    dd = counts(d[d.month == 6], "day").set_index(["branch", "cat", "item"])
    daily = {}
    for name, share in rules.items():
        pred = dd.cat_q * share.reindex(dd.index).fillna(0).values
        daily[name] = float((pred - dd.q).abs().sum() / dd.q.sum())

    # ---------------- value
    avg_cost = float((d.cost * d.q).sum() / d.q.sum())
    j = june.set_index("rule")
    units_saved = float(j.loc["Copy last month's mix", "units_misplanned"] - j.loc["5-month average + watchlist",
                                                                                  "units_misplanned"])
    gp_item = d.groupby("item").apply(lambda x: (x.gp_unit * x.q).sum() / x.q.sum(), include_groups=False)
    jun_cat = d[d.month == 6].groupby("cat").q.sum()
    mix_effect = float(sum(jun_cat[c] * (sh.loc[(c, i), 6] - sh.loc[(c, i), 1]) * gp_item[i] for c, i in sh.index))

    # ---------------- charts
    fig, ax = plt.subplots(figsize=(10, 4.6))
    mv = movers.sort_values("change_pts")
    for k, r in enumerate(mv.itertuples()):
        col = GREEN if r.change_pts > 0 else ACCENT
        ax.annotate("", xy=(r.share_jun * 100, k), xytext=(r.share_jan * 100, k),
                    arrowprops=dict(arrowstyle="-|>", color=col, lw=2.5))
        ax.scatter([r.share_jan * 100], [k], color=GREY, zorder=3, s=36)
        ax.text(max(r.share_jan, r.share_jun) * 100 + 0.6, k, f"{r.change_pts:+.1f} pts", va="center", color=col)
    ax.set_yticks(range(len(mv)))
    ax.set_yticklabels([f"{r.item} ({r.category})" for r in mv.itertuples()])
    ax.set_xlabel("Share of its category's units (%): grey dot = January, arrow tip = June")
    style(ax)
    ax.set_title(f"{len(mv)} items show a steady trend in share, the same way at all 3 branches",
                 loc="left", fontweight="bold")
    fig.text(0.01, 0.01, SOURCE + " Trend: monthly binomial test, p < 0.05.", fontsize=7.5, color=GREY)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(out / "taste_movers.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5.6))
    ax.axhline(0, color="#999999", lw=0.8)
    ax.axvline(0, color="#999999", lw=0.8)
    ax.scatter(rev.change_janfeb_to_marapr[~rev.mover], rev.change_marapr_to_mayjun[~rev.mover], color=GREY, s=26)
    ax.scatter(rev.change_janfeb_to_marapr[rev.mover], rev.change_marapr_to_mayjun[rev.mover], color=ACCENT, s=34,
               label="items with a steady trend")
    k, b0 = np.polyfit(rev.change_janfeb_to_marapr, rev.change_marapr_to_mayjun, 1)
    xs = np.linspace(rev.change_janfeb_to_marapr.min(), rev.change_janfeb_to_marapr.max(), 10)
    ax.plot(xs, k * xs + b0, ls="--", color=ACCENT, lw=1.4)
    ax.set_xlabel("Change in share, Jan-Feb to Mar-Apr (percentage points)")
    ax.set_ylabel("Change in share, Mar-Apr to May-Jun (points)")
    ax.legend(frameon=False, loc="upper right")
    style(ax)
    ax.set_title(f"Most item swings reverse (correlation {reversal_corr:.2f}): last month is a poor guide",
                 loc="left", fontweight="bold", fontsize=11)
    fig.text(0.01, 0.01, SOURCE, fontsize=7.5, color=GREY)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(out / "taste_reversal.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    cols = [GREY, GREY, GREY, ACCENT]
    x = np.arange(len(june))
    ax.bar(x, june.june_error * 100, color=cols, width=0.6)
    ax.errorbar(x, june.june_error * 100, yerr=[(june.june_error - june.lo95) * 100, (june.hi95 - june.june_error) * 100],
                fmt="none", ecolor="#444444", capsize=6)
    for xi, v in zip(x, june.june_error):
        ax.text(xi, v * 100 / 2, f"{v:.1%}", ha="center", color="white", fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(["Copy last\nmonth", "Trend for\nevery item", "5-month\naverage", "5-month average\n+ watchlist"])
    ax.set_ylabel("June planning error (% of units mis-planned)")
    style(ax)
    ax.set_title("A steady 5-month mix plans June best; chasing last month or trends is worse",
                 loc="left", fontweight="bold", fontsize=11)
    fig.text(0.01, 0.01, SOURCE + " Bars: 95% bootstrap range.", fontsize=7.5, color=GREY)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(out / "taste_june_test.png", dpi=150)
    plt.close(fig)

    # ---------------- key numbers
    r4 = lambda v: round(float(v), 4)
    nums = {
        "items_tested": int(len(t)),
        "significant_monthly_p05": int((t.p_monthly < 0.05).sum()),
        "expected_by_chance": round(len(t) * 0.05, 2),
        "movers": {r.item: {"category": r.category, "share_jan": r4(r.share_jan), "share_jun": r4(r.share_jun),
                            "change_pts": round(float(r.change_pts), 2), "p_monthly": r4(r.p_monthly),
                            "p_daily": r4(r.p_daily)} for r in movers.itertuples()},
        "movers_significant_in_both_tests": robust["item"].tolist(),
        "borderline_items": {r.item: {"p_monthly": r4(r.p_monthly), "p_daily": r4(r.p_daily),
                                      "change_pts": round(float(r.change_pts), 2)} for r in borderline.itertuples()},
        "min_p_after_correction": {"monthly": r4(t.p_monthly_bh.min()), "daily": r4(t.p_daily_bh.min())},
        "share_items_same_direction_all_branches": r4(t.same_direction_all_branches.mean()),
        "same_direction_by_chance": 0.25,
        "reversal_correlation": r4(reversal_corr),
        "share_items_kept_direction": r4(kept_direction),
        "watchlist_from_jan_may": watch,
        "june_test": {r.rule: {"error": r4(r.june_error), "units_misplanned": round(float(r.units_misplanned), 1),
                               "lo95": r4(r.lo95), "hi95": r4(r.hi95),
                               "error_on_watchlist_items": r4(r.error_on_watchlist_items)} for r in june.itertuples()},
        "last_minus_avg_pts": [round(float(np.mean(diff_last_avg) * 100), 2),
                               round(float(np.quantile(diff_last_avg, 0.025) * 100), 2),
                               round(float(np.quantile(diff_last_avg, 0.975) * 100), 2)],
        "trend_minus_avg_pts": [round(float(np.mean(diff_trend_avg) * 100), 2),
                                round(float(np.quantile(diff_trend_avg, 0.025) * 100), 2),
                                round(float(np.quantile(diff_trend_avg, 0.975) * 100), 2)],
        "relative_error_reduction_vs_last_month": r4(1 - j.loc["5-month average + watchlist", "june_error"] /
                                                     j.loc["Copy last month's mix", "june_error"]),
        "daily_level_error": {k: r4(v) for k, v in daily.items()},
        "units_saved_june": round(units_saved, 1),
        "avg_unit_cost": round(avg_cost, 2),
        "yearly_value_upper_bound": round(units_saved * avg_cost * 12, 0),
        "mix_shift_profit_effect_per_month_at_june_volumes": round(mix_effect, 1),
    }
    (out / "taste_numbers.json").write_text(json.dumps(nums, indent=2))
    print(json.dumps(nums, indent=1))


if __name__ == "__main__":
    main()
