"""Idea 4: did Harbour's 15% promotion build a lasting habit?

Harbour ran 15% off 9 cold coffee and dessert items for a week in March and again in May.
Compare Harbour with Garden and Uptown on the same days, before (Jan 1 - Mar 11) and after
(Mar 20 - Jun 30, promotion weeks excluded): a difference-in-differences with branch and date
effects. Then check it against chance (fake start dates, random item sets), against each
control branch alone, and within each branch (promoted vs other items).

Run:  python promo_habit.py   (reads ../data/stories_transactions.csv, writes outputs/)
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
import statsmodels.formula.api as smf

SEED = 490
HERE = Path(__file__).resolve().parent
POST_START = pd.Timestamp("2026-03-20")
PRE_END = pd.Timestamp("2026-03-11")
ACCENT, GREY, BLUE = "#C0392B", "#7F7F7F", "#2E6DB4"
SOURCE = "Source: Stories POS receipts, Jan-Jun 2026 (duplicates removed); team analysis."


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


def daily_units(d, items):
    """Units per branch per day of the given items, and of everything else."""
    g = d.assign(sel=d["item"].isin(items)).groupby(["branch", "date", "sel"]).q.sum().unstack(fill_value=0)
    g = g.reindex(columns=[True, False], fill_value=0).rename(columns={True: "sel", False: "other"}).reset_index()
    return g


def did(df, col, post_start, branches=None, cluster=True):
    """Lift for Harbour after `post_start`: log units ~ branch + date + Harbour x post."""
    x = df if branches is None else df[df.branch.isin(branches)]
    y = np.log(x[col]) if col == "ratio" else np.log(x[col].clip(lower=0.5))   # floor zero-sale days
    x = x.assign(H=(x.branch == "Harbour").astype(int), post=(x.date >= post_start).astype(int), y=y)
    cov = dict(cov_type="cluster", cov_kwds={"groups": x.date.dt.isocalendar().week.values}) if cluster \
        else dict(cov_type="HC1")
    r = smf.ols("y ~ C(branch) + C(date) + H:post", data=x).fit(**cov)
    b, (lo, hi) = r.params["H:post"], r.conf_int().loc["H:post"]
    return {"lift": float(np.exp(b) - 1), "lo95": float(np.exp(lo) - 1), "hi95": float(np.exp(hi) - 1),
            "p": float(r.pvalues["H:post"])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=None)
    ap.add_argument("--out", default=str(HERE / "outputs"))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)

    raw = pd.read_csv(find_data(args.data)).drop_duplicates()
    d = pd.DataFrame({"branch": raw.Branch, "item": raw.Product, "cat": raw.Category, "q": raw.Quantity,
                      "date": pd.to_datetime(raw.Date), "disc": raw["Discount Rate"],
                      "list": raw["Unit Price (USD)"] * raw.Quantity, "gp": raw["Line Gross Profit (USD)"]})

    # ---------------- the promotion, as recorded
    promo = d[d.disc == 0.15]
    promo_items = sorted(promo["item"].unique())
    promo_days = sorted(promo.date.unique())
    windows = []
    for day in promo_days:
        if windows and (day - windows[-1][1]).days == 1:
            windows[-1][1] = day
        else:
            windows.append([day, day])
    discount_usd = float((promo.list * promo.disc).sum())
    in_window = d.date.isin(pd.date_range(*windows[0])) | d.date.isin(pd.date_range(*windows[1]))
    dd = d[~in_window & ((d.date <= PRE_END) | (d.date >= POST_START))]   # analysis sample

    g = daily_units(dd, promo_items)
    main_res = did(g, "sel", POST_START)
    other_res = did(g, "other", POST_START)
    hc1_res = did(g, "sel", POST_START, cluster=False)
    vs = {b: did(g, "sel", POST_START, ["Harbour", b]) for b in ["Garden", "Uptown"]}
    # same comparison in sales levels (Poisson): bigger branches weigh more, unlike the log version
    xp = g.assign(H=(g.branch == "Harbour").astype(int), post=(g.date >= POST_START).astype(int))
    rp = smf.glm("sel ~ C(branch) + C(date) + H:post", data=xp, family=sm.families.Poisson()).fit(
        cov_type="cluster", cov_kwds={"groups": xp.date.dt.isocalendar().week.values})
    lo_p, hi_p = rp.conf_int().loc["H:post"]
    levels_res = {"lift": float(np.exp(rp.params["H:post"]) - 1), "lo95": float(np.exp(lo_p) - 1),
                  "hi95": float(np.exp(hi_p) - 1), "p": float(rp.pvalues["H:post"])}
    g["ratio"] = (g.sel + 0.5) / (g.other + 0.5)
    within = did(g, "ratio", POST_START)                       # promoted vs other items, within branch
    growth = g.assign(post=g.date >= POST_START).groupby(["branch", "post"])[["sel", "other"]].mean().unstack()
    growth_tbl = pd.DataFrame({"promoted_items_growth": growth["sel"][True] / growth["sel"][False] - 1,
                               "other_items_growth": growth["other"][True] / growth["other"][False] - 1})
    growth_tbl.to_csv(out / "promo_growth_by_branch.csv", float_format="%.4f")

    # ---------------- week by week: Harbour vs the other two branches
    w = g.assign(week=g.date.dt.to_period("W").dt.start_time, ctrl=g.branch != "Harbour")
    wk = w.groupby(["week", "ctrl"]).sel.sum().unstack()
    wk = wk[(wk[False] > 0) & (wk[True] > 0)]
    gap = np.log(wk[False] / wk[True])
    pre_mean = gap[gap.index <= PRE_END].mean()
    wk_gap = (np.exp(gap - pre_mean) - 1).rename("harbour_vs_others").to_frame()
    wk_gap["period"] = np.where(wk_gap.index <= PRE_END, "before", "after")
    wk_gap.to_csv(out / "promo_weekly_gap.csv", float_format="%.4f")
    above = wk_gap.groupby("period").harbour_vs_others.apply(lambda s: [int((s > 0).sum()), int(len(s))])

    # ---------------- chance checks
    pre = g[g.date <= PRE_END]
    fake_dates = pd.date_range("2026-01-22", periods=28, freq="D")   # leaves >= 3 weeks each side in Jan-Mar 11
    fake = [did(pre, "sel", fd)["lift"] for fd in fake_dates]
    others = [i for i in d["item"].unique() if i not in promo_items]
    rand = []
    for _ in range(500):
        items = list(rng.choice(others, size=len(promo_items), replace=False))
        rand.append(did(daily_units(dd, items), "sel", POST_START)["lift"])
    pd.DataFrame({"test": ["fake date"] * len(fake) + ["random items"] * len(rand), "lift": fake + rand}) \
        .to_csv(out / "promo_chance_checks.csv", index=False, float_format="%.4f")

    # ---------------- value: extra gross profit at Harbour on the promoted items after the promotion
    h_post = dd[(dd.branch == "Harbour") & dd["item"].isin(promo_items) & (dd.date >= POST_START)]
    gp_post = float(h_post.gp.sum())
    extra = {k: gp_post * v["lift"] / (1 + v["lift"]) for k, v in
             [("vs both branches", main_res), ("vs both branches, sales levels", levels_res),
              ("vs Garden only", vs["Garden"]), ("vs Uptown only", vs["Uptown"]),
              ("promoted vs other items", within)]}
    extra_lo = gp_post * main_res["lo95"] / (1 + main_res["lo95"])
    extra_hi = gp_post * main_res["hi95"] / (1 + main_res["hi95"])
    june = h_post[h_post.date.dt.month == 6]
    per_week_june = float(june.gp.sum() * main_res["lift"] / (1 + main_res["lift"]) / (june.date.nunique() / 7))

    # ---------------- charts
    fig, ax = plt.subplots(figsize=(11, 4.6))
    ax.axhline(0, color="#999999", lw=0.8)
    ax.plot(wk_gap.index, wk_gap.harbour_vs_others * 100, color=BLUE, marker="o", ms=4, lw=2)
    for a, b in windows:
        ax.axvspan(a, b + pd.Timedelta(days=1), color=ACCENT, alpha=0.18, lw=0)
        ax.text(a, ax.get_ylim()[0] * 0.9 if ax.get_ylim()[0] < 0 else 0, " 15% off", color=ACCENT, fontsize=8)
    wk_after = float(wk_gap[wk_gap.period == "after"].harbour_vs_others.mean())
    ax.hlines(wk_after * 100, POST_START, wk_gap.index.max(), colors=GREY, linestyles="--",
              label=f"average week after: +{wk_after:.0%}")
    ax.set_ylabel("Harbour vs other branches,\ncold coffee + desserts (%)")
    ax.legend(frameon=False, loc="upper left")
    style(ax)
    ax.set_title(f"After the first promotion, Harbour sat above the other branches in {above['after'][0]} of "
                 f"{above['after'][1]} weeks (before: {above['before'][0]} of {above['before'][1]})",
                 loc="left", fontweight="bold", fontsize=11)
    fig.text(0.01, 0.01, SOURCE + " Weekly units, relative to the Jan-Mar 11 gap.", fontsize=7.5, color=GREY)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(out / "promo_weekly_gap.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 4.4))
    ax.hist(np.array(rand) * 100, bins=30, color=GREY, label=f"Random sets of {len(promo_items)} other items (500)")
    ax.hist(np.array(fake) * 100, bins=10, color=BLUE, alpha=0.8, label="Fake start dates, Jan-Mar (28)")
    ax.axvline(main_res["lift"] * 100, color=ACCENT, lw=3)
    ax.text(main_res["lift"] * 100 + 0.4, ax.get_ylim()[1] * 0.85, f"Real promotion\n+{main_res['lift']:.0%}",
            color=ACCENT)
    ax.set_xlabel("Lasting change in units vs other branches (%)")
    ax.set_ylabel("Number of tests")
    ax.legend(frameon=False, loc="upper left", fontsize=8)
    style(ax)
    share_rand = float(np.mean(np.array(rand) >= main_res["lift"]))
    n_fake = int(np.sum(np.array(fake) >= main_res["lift"]))
    ax.set_title(f"Chance rarely gives a lasting lift this large: {n_fake} of 28 fake dates, "
                 f"{share_rand:.1%} of random item sets", loc="left", fontweight="bold", fontsize=11)
    fig.text(0.01, 0.01, SOURCE, fontsize=7.5, color=GREY)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(out / "promo_chance_checks.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 4.6))
    labels = ["Discount\ngiven", "Extra profit:\nvs Garden only", "Extra profit:\nsales levels",
              "Extra profit:\npromoted vs\nother items", "Extra profit:\nvs both branches"]
    vals = [discount_usd, extra["vs Garden only"], extra["vs both branches, sales levels"],
            extra["promoted vs other items"], extra["vs both branches"]]
    ax.bar(range(5), vals, color=[GREY] + [BLUE] * 4, width=0.6)
    ax.errorbar([4], [vals[4]], yerr=[[vals[4] - extra_lo], [extra_hi - vals[4]]], fmt="none", ecolor="#444444",
                capsize=6)
    for i, v in enumerate(vals):
        ax.text(i, v / 2, f"\\${v:,.0f}", ha="center", color="white", fontweight="bold")
    ax.set_xticks(range(5))
    ax.set_xticklabels(labels)
    ax.set_ylabel("USD, Mar 20 - Jun 30")
    style(ax)
    ax.set_title(f"A \\${discount_usd:,.0f} discount, against \\${min(vals[1:]):,.0f}-{max(vals[1:]):,.0f} of "
                 f"estimated extra profit", loc="left", fontweight="bold", fontsize=11)
    fig.text(0.01, 0.01, SOURCE + " Bar on the main estimate: 95% range.", fontsize=7.5, color=GREY)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(out / "promo_money.png", dpi=150)
    plt.close(fig)

    # ---------------- key numbers
    rnd = lambda r: {k: round(v, 4) for k, v in r.items()}
    nums = {
        "promo_items": promo_items,
        "promo_windows": [[str(a.date()), str(b.date())] for a, b in windows],
        "discount_usd": round(discount_usd, 2),
        "lift_vs_both_week_clustered": rnd(main_res),
        "lift_vs_both_heteroskedasticity_robust": rnd(hc1_res),
        "lift_vs_both_sales_levels": rnd(levels_res),
        "weekly_gap_average_after": round(wk_after, 4),
        "lift_other_items": rnd(other_res),
        "lift_vs_garden_only": rnd(vs["Garden"]),
        "lift_vs_uptown_only": rnd(vs["Uptown"]),
        "lift_promoted_vs_other_items_within_branch": rnd(within),
        "growth_by_branch_post_vs_pre": {b: {k: round(float(v), 4) for k, v in r.items()}
                                         for b, r in growth_tbl.iterrows()},
        "weeks_harbour_above_others": {k: v for k, v in above.items()},
        "fake_dates_reaching_real_lift": n_fake,
        "random_item_sets_reaching_real_lift_share": round(share_rand, 4),
        "harbour_promo_items_gp_post": round(gp_post, 2),
        "extra_gp": {k: round(v, 0) for k, v in extra.items()},
        "extra_gp_main_95": [round(extra_lo, 0), round(extra_hi, 0)],
        "extra_gp_per_week_june": round(per_week_june, 0),
    }
    (out / "promo_numbers.json").write_text(json.dumps(nums, indent=2, default=str))
    print(json.dumps(nums, indent=1, default=str))


if __name__ == "__main__":
    main()
