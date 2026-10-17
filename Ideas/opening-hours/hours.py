"""Idea 2: are Stories' opening hours right?

For every branch, weekday and edge hour (07-11 and 22-24), compare the gross profit the hour
brings in with what it costs to keep the branch open that hour. Uses the visit forecast from
../ml-staffing-forecast (run that first). The decision is tested on June: decide with the Jan-May
model, then score the decision on June's real profit, against a plain-average baseline.
After midnight there is no data, so no model: measured evidence, break-even and a pilot.

Run:  python hours.py
"""
import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
FORECAST_DIR = HERE.parent / "ml-staffing-forecast"
sys.path.insert(0, str(FORECAST_DIR))
from forecast import BRANCHES, DOW, HOURS, START, design, load_and_clean, build_hourly_table  # noqa: E402

# ---- assumptions (not in the data)
HOUR_COST = 8.0       # USD saved per hour the branch is closed: 1 staff-hour ($4) + power/generator (~$4)
SHIFT_SHARE = 0.0     # share of a closed hour's customers who come at another hour instead (0 = all lost)
OPEN_CHOICES = [7, 8, 9, 10, 11]
CLOSE_CHOICES = [22, 23, 24]   # closing time; 24 = midnight (today's hours: 07:00-24:00)
MONTHS = ["Jul", "Aug", "Sep", "Oct"]
ACCENT, GREY = "#C0392B", "#7F7F7F"
SOURCE = ("Source: Stories POS receipts Jan-Jun 2026; visit forecast Jul-Oct. Assumes an open hour costs $8 "
          "(1 staff-hour + power) and customers of a closed hour are lost.")


def find_data(arg):
    for p in [arg] + [a / "data" / "stories_transactions.csv" for a in (HERE, *HERE.parents)]:
        if p and Path(p).exists():
            return Path(p)
    sys.exit("stories_transactions.csv not found: put it in the data/ folder at the repo root or pass --data")


def receipts_with_gp(path, garden_cost_fix=False):
    """One row per receipt: branch, date, hour, gross profit. Optionally re-cost Garden at
    Harbour's unit costs (see ml-staffing-forecast/cost_check.py)."""
    d = pd.read_csv(path).drop_duplicates()
    if garden_cost_fix:
        ratio = (d[d.Branch == "Garden"].groupby("Product")["Unit Cost (USD)"].first() /
                 d[d.Branch == "Harbour"].groupby("Product")["Unit Cost (USD)"].first())
        g = d.Branch == "Garden"
        new_cost = d.loc[g, "Unit Cost (USD)"] / d.loc[g, "Product"].map(ratio)
        d.loc[g, "Line Gross Profit (USD)"] = d.loc[g, "Line Revenue (USD)"] - new_cost * d.loc[g, "Quantity"]
    r = d.groupby(["Transaction ID", "Branch", "Date", "Time"])["Line Gross Profit (USD)"].sum().reset_index()
    r["date"] = pd.to_datetime(r.Date)
    r["hour"] = r.Time.str[:2].astype(int)
    return r.rename(columns={"Branch": "branch", "Line Gross Profit (USD)": "gp"})


def gp_per_receipt(r, until=None):
    rr = r if until is None else r[r.date <= until]
    return rr.groupby(["branch", "hour"]).gp.mean()


def choose_hours(gp_cell, cost, shift):
    """gp_cell: expected GP per open hour, indexed by (branch, key, hour) where key is a weekday
    or 'all' (same hours every day, GP summed over the week). Returns the best open/close per
    (branch, key) and the value of cutting hours vs today's 07-24, in USD per period."""
    out = []
    for (b, k), g in gp_cell.groupby(level=[0, 1]):
        g = g.droplevel([0, 1])
        n_days = 7 if k == "all" else 1
        best = (7, 24, 0.0)
        for o in OPEN_CHOICES:
            for c in CLOSE_CHOICES:
                cut = [h for h in HOURS if h < o or h >= c]
                value = sum(n_days * cost - (1 - shift) * g[h] for h in cut)
                if value > best[2] + 1e-9:
                    best = (o, c, value)
        out.append({"branch": b, "key": k, "open": best[0], "close": best[1], "value": best[2],
                    "hours_cut_per_day": (best[0] - 7) + (24 - best[1])})
    return pd.DataFrame(out)


def realised_value(decision, actual_gp, cost, shift):
    """Score a decision on actual June profit: per cut hour, cost saved minus profit lost."""
    a = actual_gp.copy()
    a["dow"] = a.date.dt.dayofweek
    tot = 0.0
    for r in decision.itertuples():
        days = a[(a.branch == r.branch) & ((a.dow == DOW.index(r.key)) if r.key != "all" else True)]
        cut = days[(days.hour < r.open) | (days.hour >= r.close)]
        tot += len(cut) * cost - (1 - shift) * cut.gp.sum()
    return tot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=None)
    ap.add_argument("--out", default=str(HERE / "outputs"))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    data = find_data(args.data)

    r = receipts_with_gp(data)
    receipts, _ = load_and_clean(data)
    table = build_hourly_table(receipts)
    gp_r = gp_per_receipt(r)                                   # measured, Jan-Jun
    gp_r.unstack(0).to_csv(out / "hours_gp_per_receipt.csv", float_format="%.3f")

    # ---------------- Jul-Oct: expected profit per open hour (forecast x profit per receipt)
    heat = pd.read_csv(FORECAST_DIR / "outputs/forecast_heatmap.csv")
    heat["gp"] = heat.estimate_mean.values * gp_r.reindex(pd.MultiIndex.from_frame(heat[["branch", "hour"]])).values
    edge = heat[heat.hour.isin([7, 8, 9, 10, 21, 22, 23])]
    edge.pivot_table(index=["branch", "month", "weekday"], columns="hour", values="gp") \
        .to_csv(out / "hours_break_even.csv", float_format="%.2f")

    def decide(month_rows, cost=HOUR_COST, shift=SHIFT_SHARE, per_weekday=True):
        if per_weekday:
            cell = month_rows.set_index(["branch", "weekday", "hour"]).gp
        else:
            cell = month_rows.groupby(["branch", "hour"]).gp.sum()
            cell.index = pd.MultiIndex.from_tuples([(b, "all", h) for b, h in cell.index])
        return choose_hours(cell, cost, shift)

    rows = []
    for m in MONTHS:
        for per_wd, label in [(True, "by weekday"), (False, "same every day")]:
            dec = decide(heat[heat.month == m], per_weekday=per_wd).assign(month=m, policy=label)
            rows.append(dec)
    decisions = pd.concat(rows, ignore_index=True)
    decisions.to_csv(out / "hours_decision.csv", index=False, float_format="%.2f")
    weekly = decisions.groupby(["policy", "month"]).value.sum()
    yearly = {p: round(float(weekly.loc[p].mean() * 52), 0) for p in ["by weekday", "same every day"]}

    # ---------------- sensitivity: which assumptions change the decision?
    r_fix = receipts_with_gp(data, garden_cost_fix=True)
    gp_fix = gp_per_receipt(r_fix)
    heat_fix = heat.assign(gp=heat.estimate_mean.values *
                           gp_fix.reindex(pd.MultiIndex.from_frame(heat[["branch", "hour"]])).values)
    sens = []
    for variant, hh in [("recorded costs", heat), ("Garden at Harbour's costs", heat_fix)]:
        for cost in [4, 6, 8, 10, 12, 15, 20]:
            for shift in [0.0, 0.25, 0.5]:
                vals, cut_hours, lines = [], [], []
                for m in MONTHS:
                    dd = decide(hh[hh.month == m], cost, shift)
                    vals.append(dd.value.sum())
                    cut_hours.append(dd.hours_cut_per_day.sum())
                    if m == "Oct":
                        lines = sorted({f"{x.branch} {'open ' + str(x.open) + ':00' if x.open > 7 else ''}"
                                        f"{' close ' + str(x.close) + ':00' if x.close < 24 else ''}".strip()
                                        for x in dd.itertuples() if x.hours_cut_per_day > 0})
                sens.append({"gp_variant": variant, "hour_cost": cost, "shift_share": shift,
                             "yearly_value": np.mean(vals) * 52, "branch_days_x_hours_cut_oct": cut_hours[-1],
                             "changes_in_oct": "; ".join(lines) if lines else "none"})
    sens_df = pd.DataFrame(sens)
    sens_df.to_csv(out / "hours_sensitivity.csv", index=False, float_format="%.2f")

    # ---------------- June test: decide with Jan-May information only, score on actual June profit
    model_test = json.loads((FORECAST_DIR / "outputs/model_test.json").read_text())
    june = table[table.date.dt.month == 6].copy()
    june["mu"] = np.exp(design(june, model_test["spec"]).values @ np.array(model_test["params"]))
    gp_jm = gp_per_receipt(r, until=pd.Timestamp("2026-05-31"))
    gp_idx = lambda df: gp_jm.reindex(pd.MultiIndex.from_frame(df[["branch", "hour"]])).values
    june["weekday"] = june.dow.map(dict(enumerate(DOW)))
    fc_cells = june.groupby(["branch", "weekday", "hour"]).mu.mean().reset_index()
    fc_cells["gp"] = fc_cells.mu * gp_idx(fc_cells)
    jm = table[table.date <= pd.Timestamp("2026-05-31")].assign(weekday=lambda d: d.dow.map(dict(enumerate(DOW))))
    base_cells = jm.groupby(["branch", "weekday", "hour"]).y.mean().reset_index()
    base_cells["gp"] = base_cells.y * gp_idx(base_cells)
    actual = r[r.date.dt.month == 6].groupby(["branch", "date", "hour"]).gp.sum()
    full = pd.MultiIndex.from_product([BRANCHES, pd.date_range("2026-06-01", "2026-06-30"), HOURS],
                                      names=["branch", "date", "hour"])
    actual = actual.reindex(full, fill_value=0).reset_index()
    hind = actual.assign(weekday=actual.date.dt.dayofweek.map(dict(enumerate(DOW)))) \
        .groupby(["branch", "weekday", "hour"]).gp.mean().reset_index()

    june_rows = []
    for name, cells in [("Forecast model (trained Jan-May)", fc_cells),
                        ("Baseline: Jan-May average, no growth", base_cells),
                        ("Hindsight: June's actual averages (upper bound)", hind)]:
        for cost in [8, 12, 15]:
            dec = choose_hours(cells.set_index(["branch", "weekday", "hour"]).gp, cost, SHIFT_SHARE)
            june_rows.append({"decision_from": name, "hour_cost": cost,
                              "hours_cut_per_week": int(dec.hours_cut_per_day.sum()),
                              "predicted_value_june": dec.value.sum() * 30 / 7,
                              "realised_value_june": realised_value(dec, actual, cost, SHIFT_SHARE)})
    june_df = pd.DataFrame(june_rows)
    june_df.to_csv(out / "hours_june_test.csv", index=False, float_format="%.2f")

    # ---------------- after midnight: no data, so no model. Measured evidence + break-even.
    raw = pd.read_csv(data).drop_duplicates("Transaction ID")
    raw["hour"] = raw.Time.str[:2].astype(int)
    raw["block"] = raw.Time.str[3:5].astype(int) // 10
    blocks = {h: raw[raw.hour == h].groupby("block").size().reindex(range(6), fill_value=0).tolist()
              for h in [7, 22, 23]}
    chi_p = {h: float(stats.chisquare(v).pvalue) for h, v in blocks.items()}
    last_sale = str(raw.Time.max())
    late = heat[(heat.hour == 23)].pivot_table(index=["branch", "weekday"], columns="month", values="gp")
    measured_23 = r[r.hour == 23].assign(weekday=r.date.dt.dayofweek.map(dict(enumerate(DOW)))) \
        .groupby(["branch", "weekday"]).gp.sum() / table.drop_duplicates("date").assign(
            weekday=lambda d: d.dow.map(dict(enumerate(DOW)))).groupby("weekday").size()
    ln = late[["Oct"]].rename(columns={"Oct": "gp_23h_oct_forecast"})
    ln["gp_23h_jan_jun_measured"] = measured_23.reindex(ln.index).values
    ln["break_even_share_of_23h"] = HOUR_COST / ln.gp_23h_oct_forecast
    for s in (0.25, 0.5, 0.75):
        ln[f"value_if_midnight_hour_is_{int(s * 100)}pct"] = s * ln.gp_23h_oct_forecast - HOUR_COST
    ln.to_csv(out / "hours_late_night.csv", float_format="%.2f")
    pilot_nights = ln.loc["Harbour"].sort_values("gp_23h_oct_forecast", ascending=False).head(3).index.tolist()
    scen_year = {f"{int(s * 100)}%": round(float(
        ln[f"value_if_midnight_hour_is_{int(s * 100)}pct"].clip(lower=0).groupby(level=0).sum().sum() * 52), 0)
        for s in (0.25, 0.5, 0.75)}

    # ---------------- chart: profit per open hour in October, with the hours below cost marked
    oct_ = heat[heat.month == "Oct"]
    fig, axes = plt.subplots(3, 1, figsize=(13, 7.6), sharex=True)
    cmap = plt.get_cmap("Reds")
    for ax, b in zip(axes, ["Harbour", "Garden", "Uptown"]):
        m = oct_[oct_.branch == b].pivot(index="weekday", columns="hour", values="gp").loc[DOW]
        ax.imshow(np.log1p(m.values), cmap=cmap, vmin=np.log1p(2), vmax=np.log1p(160), aspect="auto")
        for i in range(m.shape[0]):
            for j, hcol in enumerate(m.columns):
                v = m.values[i, j]
                below = v < HOUR_COST
                ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=7.5,
                        color="white" if v > 45 else "black", fontweight="bold" if below else "normal")
                if below:
                    ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False, ec="black", lw=1.6))
        ax.add_patch(plt.Rectangle((len(m.columns) - 0.5, -0.5), 1, 7, fc="#EEEEEE", ec="none", clip_on=False))
        for i in range(7):
            ax.text(len(m.columns), i, "?", ha="center", va="center", fontsize=9, color=GREY)
        ax.set_xlim(-0.5, len(m.columns) + 0.5)
        ax.set_yticks(range(7))
        ax.set_yticklabels(DOW, fontsize=8)
        ax.set_title(b, loc="left", fontsize=10)
        for s in ax.spines.values():
            s.set_visible(False)
    cols = list(m.columns) + [24]
    axes[-1].set_xticks(range(len(cols)))
    axes[-1].set_xticklabels([f"{c}:00" if c < 24 else "00:00\n(no data)" for c in cols], fontsize=8)
    axes[-1].set_xlabel("Hour of the day. Number = expected gross profit (USD) earned in that hour, October; "
                        "boxed = below the $8 it costs to stay open")
    n_below = int((oct_.gp < HOUR_COST).sum())
    eve = oct_[oct_.hour >= 18].gp / HOUR_COST
    last_below = int(oct_[oct_.gp < HOUR_COST].hour.max()) + 1
    fig.suptitle(f"Every evening hour earns {eve.min():.1f}-{eve.max():.0f}x its running cost; only {n_below} of 357 "
                 f"branch-hours a week fall below $8, all before {last_below}am", x=0.01, ha="left", fontsize=12,
                 fontweight="bold")
    fig.text(0.01, 0.005, SOURCE, fontsize=7.5, color=GREY)
    fig.tight_layout(rect=(0, 0.02, 1, 0.95))
    fig.savefig(out / "chart_hours_october.png", dpi=150)
    plt.close(fig)

    # ---------------- key numbers
    oct_dec = decisions[(decisions.month == "Oct") & (decisions.policy == "by weekday")]
    nums = {
        "assumptions": {"hour_cost_usd": HOUR_COST, "shift_share": SHIFT_SHARE},
        "measured_gp_per_receipt_range_by_branch": {b: [round(float(gp_r[b].min()), 2), round(float(gp_r[b].max()), 2)]
                                                    for b in BRANCHES},
        "oct_branch_hours_below_cost": n_below,
        "gp_per_day_07h_jan_vs_jun": {b: [round(float(r[(r.branch == b) & (r.hour == 7) & (r.date.dt.month == m)].gp.sum()
                                                     / r[r.date.dt.month == m].date.nunique()), 2) for m in (1, 6)]
                                      for b in BRANCHES},
        "yearly_gross_profit_all_branches": round(float(r.gp.sum() * 365 / r.date.nunique()), 0),
        "oct_min_gp_hour_after_6pm": round(float(oct_[oct_.hour >= 18].gp.min()), 2),
        "oct_min_gp_hour_after_6pm_ratio_to_cost": round(float(oct_[oct_.hour >= 18].gp.min() / HOUR_COST), 2),
        "oct_max_gp_hour_23h_ratio_to_cost": round(float(oct_[oct_.hour == 23].gp.max() / HOUR_COST), 2),
        "oct_decision_by_weekday": {f"{x.branch} {x.key}": f"{x.open}:00-{x.close}:00" for x in oct_dec.itertuples()
                                    if x.hours_cut_per_day > 0},
        "yearly_value_of_trimming": yearly,
        "june_test": {f"{x.decision_from} | ${x.hour_cost}": {"hours_cut_per_week": x.hours_cut_per_week,
                                                              "realised_value_june": round(x.realised_value_june, 2),
                                                              "predicted_value_june": round(x.predicted_value_june, 2)}
                      for x in june_df.itertuples()},
        "late_night": {"orders_per_10min_block": {str(h): v for h, v in blocks.items()},
                       "uniform_test_p_value": {str(h): round(p, 3) for h, p in chi_p.items()},
                       "last_sale_time": last_sale,
                       "harbour_best_pilot_nights": pilot_nights,
                       "break_even_share_range": [round(float(ln.break_even_share_of_23h.min()), 3),
                                                  round(float(ln.break_even_share_of_23h.max()), 3)],
                       "yearly_value_if_midnight_hour_earns_share_of_23h": scen_year,
                       "harbour_only_yearly_value_if_share": {
                           f"{int(sh * 100)}%": round(float(ln.loc["Harbour", f"value_if_midnight_hour_is_{int(sh * 100)}pct"]
                                                            .clip(lower=0).sum() * 52), 0) for sh in (0.25, 0.5, 0.75)}},
        "oct_decision_same_every_day": {x.branch: f"{x.open}:00-{x.close}:00" for x in decisions[
            (decisions.month == "Oct") & (decisions.policy == "same every day")].itertuples()},
    }
    (out / "hours_numbers.json").write_text(json.dumps(nums, indent=2, default=float))
    print(json.dumps({k: nums[k] for k in ["oct_branch_hours_below_cost", "oct_decision_by_weekday",
                                           "yearly_value_of_trimming", "late_night"]}, indent=1))
    print(june_df.round(1).to_string(index=False))


if __name__ == "__main__":
    main()
