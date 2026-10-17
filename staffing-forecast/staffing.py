"""Turn the visit forecast into a staffing decision, with costs, value and sensitivity.

Run after forecast.py:  python staffing.py
Reads outputs/forecast_heatmap.csv (expected visits per branch x month x weekday x hour,
Jul-Oct 2026) and the raw CSV (gross profit per receipt). Writes the staffing outputs.

Decision per hour: choose the number of staff k that minimises
    wage * k  +  (gross profit per receipt) * (share who leave) * E[visits above k * capacity]
where visits ~ Poisson(forecast). Every input except the forecast is an ASSUMPTION, listed below
and varied in staffing_sensitivity.csv.
"""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from forecast import find_data

# ---- assumptions (not in the data); see the report for why each value was chosen
CAPACITY = 12      # customers one staff member can serve per hour (team assumption)
WAGE = 4.0         # USD per staff-hour, fully loaded (Lebanon minimum wage is ~1.5-3 USD/h)
LEAVE_SHARE = 0.5  # share of customers above capacity who leave without buying
MIN_CREW = 1       # minimum staff on the floor in any open hour
MAX_STAFF = 8

BRANCHES = ["Harbour", "Garden", "Uptown"]
MONTHS = ["Jul", "Aug", "Sep", "Oct"]
DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
ACCENT, GREY = "#C0392B", "#7F7F7F"
SOURCE = ("Source: Stories POS receipts Jan-Jun 2026; forecast Jul-Oct. Staffing assumes 12 customers per "
          "staff-hour, $4/staff-hour, half of over-capacity customers leave.")


def expected_excess(mu, cap):
    """E[(Y - cap)+] for Y ~ Poisson(mu), vectorised."""
    mu = np.asarray(mu, float)
    cap = np.asarray(cap, float)
    k = np.arange(0, 200)
    pmf = stats.poisson.pmf(k[None, :], mu.reshape(-1, 1))
    return (pmf * np.clip(k[None, :] - cap.reshape(-1, 1), 0, None)).sum(axis=1)


def hour_cost(mu, k, gp, capacity, wage, leave):
    lost = leave * expected_excess(mu, k * capacity)
    return wage * k + gp * lost, lost


def optimal_staff(mu, gp, capacity, wage, leave, min_crew):
    """Cost-minimising staff for each hour (vectorised over hours)."""
    best_k = np.full(len(mu), min_crew)
    best_c, _ = hour_cost(mu, best_k, gp, capacity, wage, leave)
    for k in range(min_crew + 1, MAX_STAFF + 1):
        c, _ = hour_cost(mu, np.full(len(mu), k), gp, capacity, wage, leave)
        better = c < best_c - 1e-12
        best_k[better], best_c[better] = k, c[better]
    return best_k


def plans(h, gp_map, capacity, wage, leave, min_crew):
    """Staff per hour under each plan. h: one row per branch x month x weekday x hour."""
    gp = h.branch.map(gp_map).values
    mu = h.estimate_mean.values
    out = {"Forecast-based (cost-optimal)": optimal_staff(mu, gp, capacity, wage, leave, min_crew),
           "Staff to the average": np.maximum(min_crew, np.ceil(mu / capacity)).astype(int)}
    # fixed crews: the same number of staff every open hour of the month
    p95 = np.maximum(min_crew, np.ceil(h.estimate_p95_high.values / capacity)).astype(int)
    peak = pd.Series(p95).groupby([h.branch.values, h.month.values]).transform("max").values
    out["Fixed crew sized for the peak"] = peak
    out["Fixed crew of 2"] = np.full(len(h), max(2, min_crew))
    return out, gp, mu


def summarise(h, plan_staff, gp, mu, capacity, wage, leave):
    rows = []
    for name, k in plan_staff.items():
        cost, lost = hour_cost(mu, k, gp, capacity, wage, leave)
        d = h.assign(staff=k, lost=lost, lost_gp=gp * lost, wage_cost=wage * k)
        g = d.groupby(["branch", "month"]).agg(staff_hours=("staff", "sum"), wage_cost=("wage_cost", "sum"),
                                               lost_customers=("lost", "sum"), lost_gp=("lost_gp", "sum"),
                                               customers=("estimate_mean", "sum")).reset_index()
        g["plan"] = name
        rows.append(g)
    s = pd.concat(rows, ignore_index=True)
    s["total_cost"] = s.wage_cost + s.lost_gp
    s["lost_share"] = s.lost_customers / s.customers
    return s   # all per week (each cell is one hour of one weekday)


def chart_rota(h, k, month, path, title):
    fig, axes = plt.subplots(3, 1, figsize=(12, 7.2), sharex=True)
    cmap = matplotlib.colors.ListedColormap(["#F6E3E0", "#E8A79E", "#D0604F", "#A3281B", "#6E1209"])
    for ax, b in zip(axes, BRANCHES):
        m = h.assign(staff=k)
        m = m[(m.branch == b) & (m.month == month)].pivot(index="weekday", columns="hour", values="staff").loc[DOW]
        ax.imshow(m.values, cmap=cmap, vmin=0.5, vmax=5.5, aspect="auto")
        for i in range(m.shape[0]):
            for j in range(m.shape[1]):
                v = int(m.values[i, j])
                ax.text(j, i, v, ha="center", va="center", fontsize=8, color="white" if v >= 3 else "black")
        ax.set_yticks(range(7))
        ax.set_yticklabels(DOW, fontsize=8)
        ax.set_title(f"{b}: {int(m.values.sum())} staff-hours per week", loc="left", fontsize=10)
        for s in ax.spines.values():
            s.set_visible(False)
    axes[-1].set_xticks(range(len(m.columns)))
    axes[-1].set_xticklabels([f"{c}:00" for c in m.columns], fontsize=8)
    axes[-1].set_xlabel("Hour of the day (number = staff needed in that hour)")
    fig.suptitle(title, x=0.01, ha="left", fontsize=12, fontweight="bold")
    fig.text(0.01, 0.005, SOURCE, fontsize=7.5, color=GREY)
    fig.tight_layout(rect=(0, 0.02, 1, 0.95))
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=None)
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "outputs"))
    args = ap.parse_args()
    args.data = find_data(args.data)
    out = Path(args.out)

    # measured input: gross profit per receipt, by branch
    lines = pd.read_csv(args.data).drop_duplicates()
    gp_map = (lines.groupby(["Transaction ID", "Branch"])["Line Gross Profit (USD)"].sum()
              .groupby("Branch").mean().round(4).to_dict())
    h = pd.read_csv(out / "forecast_heatmap.csv")

    # --- base case
    staff, gp, mu = plans(h, gp_map, CAPACITY, WAGE, LEAVE_SHARE, MIN_CREW)
    summ = summarise(h, staff, gp, mu, CAPACITY, WAGE, LEAVE_SHARE)
    summ.to_csv(out / "staffing_summary.csv", index=False, float_format="%.2f")
    best = staff["Forecast-based (cost-optimal)"]
    _, lost = hour_cost(mu, best, gp, CAPACITY, WAGE, LEAVE_SHARE)
    h.assign(staff_recommended=best, expected_lost_customers=lost)[
        ["branch", "month", "weekday", "hour", "estimate_mean", "estimate_p95_high", "staff_recommended",
         "expected_lost_customers"]].to_csv(out / "staffing_plan.csv", index=False, float_format="%.2f")

    # --- value of updating the rota with the forecast: keep July's rota into October vs re-plan
    hk = h.assign(k=best, gp=gp, mu=mu)
    jul_k = hk[hk.month == "Jul"].set_index(["branch", "weekday", "hour"]).k
    octr = hk[hk.month == "Oct"]
    k_old = jul_k.reindex(pd.MultiIndex.from_frame(octr[["branch", "weekday", "hour"]])).values
    c_old, l_old = hour_cost(octr.mu.values, k_old, octr.gp.values, CAPACITY, WAGE, LEAVE_SHARE)
    c_new, l_new = hour_cost(octr.mu.values, octr.k.values, octr.gp.values, CAPACITY, WAGE, LEAVE_SHARE)
    keep_july = pd.DataFrame({"branch": octr.branch.values, "old_cost": c_old, "new_cost": c_new,
                              "old_lost": l_old, "new_lost": l_new, "old_k": k_old, "new_k": octr.k.values}) \
        .groupby("branch").sum()

    # where the staff-hours go: forecast plan vs a fixed crew of 2, October, by time of day
    tod = pd.cut(h.hour, [6, 9, 17, 23], labels=["07-10", "10-18", "18-24"])
    by_tod = pd.DataFrame({"time": tod, "month": h.month, "forecast": best,
                           "fixed2": staff["Fixed crew of 2"]})
    by_tod = by_tod[by_tod.month == "Oct"].groupby("time", observed=True)[["forecast", "fixed2"]].sum()

    # --- sensitivity: which assumptions change the decision?
    def run(capacity=CAPACITY, wage=WAGE, leave=LEAVE_SHARE, min_crew=MIN_CREW):
        st, g, m = plans(h, gp_map, capacity, wage, leave, min_crew)
        s = summarise(h, st, g, m, capacity, wage, leave)
        t = s.groupby(["plan", "month"])[["staff_hours", "total_cost", "lost_customers", "customers"]].sum()
        fb, fp = t.loc["Forecast-based (cost-optimal)"], t.loc["Fixed crew sized for the peak"]
        hb = s[(s.plan == "Forecast-based (cost-optimal)") & (s.branch == "Harbour")].set_index("month")
        ub = s[(s.plan == "Forecast-based (cost-optimal)") & (s.branch == "Uptown")].set_index("month")
        return {"forecast_staff_hours_jul": fb.loc["Jul", "staff_hours"],
                "forecast_staff_hours_oct": fb.loc["Oct", "staff_hours"],
                "weekly_saving_vs_fixed_peak_oct": fp.loc["Oct", "total_cost"] - fb.loc["Oct", "total_cost"],
                "lost_customer_share_oct": fb.loc["Oct", "lost_customers"] / fb.loc["Oct", "customers"],
                "harbour_extra_staff_hours_oct_vs_jul": hb.loc["Oct", "staff_hours"] - hb.loc["Jul", "staff_hours"],
                "uptown_extra_staff_hours_oct_vs_jul": ub.loc["Oct", "staff_hours"] - ub.loc["Jul", "staff_hours"]}

    sens = [{"assumption": "base case", "value": "", **run()}]
    for v in (8, 10, 15, 20):
        sens.append({"assumption": "capacity (customers/staff-hour)", "value": v, **run(capacity=v)})
    for v in (2, 3, 6, 8):
        sens.append({"assumption": "wage (USD/staff-hour)", "value": v, **run(wage=v)})
    for v in (0.25, 0.75, 1.0):
        sens.append({"assumption": "share of over-capacity customers who leave", "value": v, **run(leave=v)})
    sens.append({"assumption": "minimum crew", "value": 2, **run(min_crew=2)})
    sens_df = pd.DataFrame(sens)
    sens_df.to_csv(out / "staffing_sensitivity.csv", index=False, float_format="%.3f")

    # --- key numbers
    t = summ.groupby(["plan", "month"])[["staff_hours", "wage_cost", "lost_customers", "lost_gp",
                                         "total_cost", "customers"]].sum().round(2)
    by_branch = summ[summ.plan == "Forecast-based (cost-optimal)"].set_index(["branch", "month"])
    peak_hours = h.assign(staff=best)
    evening_share = float(peak_hours[(peak_hours.month == "Oct") & (peak_hours.hour >= 18)].staff.sum() /
                          peak_hours[peak_hours.month == "Oct"].staff.sum())
    nums = {
        "assumptions": {"capacity_customers_per_staff_hour": CAPACITY, "wage_usd_per_staff_hour": WAGE,
                        "leave_share_over_capacity": LEAVE_SHARE, "min_crew": MIN_CREW},
        "measured_gp_per_receipt": gp_map,
        "weekly_by_plan_and_month": {f"{p} | {m}": r.to_dict() for (p, m), r in t.iterrows()},
        "forecast_plan_by_branch": {f"{b} {m}": {"staff_hours": int(r.staff_hours), "wage_cost": round(r.wage_cost, 2),
                                                 "lost_customers": round(r.lost_customers, 2)}
                                    for (b, m), r in by_branch.iterrows()},
        "oct_share_of_staff_hours_after_6pm": round(evening_share, 3),
        "yearly_saving_vs_fixed_crew_of_2": round(float(
            (t.xs("Fixed crew of 2").total_cost - t.xs("Forecast-based (cost-optimal)").total_cost).mean() * 52), 0),
        "yearly_staff_hours_saved_vs_fixed_crew_of_2": round(float(
            (t.xs("Fixed crew of 2").staff_hours - t.xs("Forecast-based (cost-optimal)").staff_hours).mean() * 52), 0),
        "keep_july_rota_in_october": {b: {"extra_lost_customers_per_week": round(r.old_lost - r.new_lost, 2),
                                          "extra_cost_per_week": round(r.old_cost - r.new_cost, 2),
                                          "staff_hours_july_rota": int(r.old_k), "staff_hours_october_rota": int(r.new_k)}
                                      for b, r in keep_july.iterrows()},
        "oct_staff_hours_by_time_of_day": {t: {"forecast_plan": int(r.forecast), "fixed_crew_of_2": int(r.fixed2)}
                                           for t, r in by_tod.iterrows()},
        "max_staff_any_hour": {m: {b: int(peak_hours[(peak_hours.month == m) & (peak_hours.branch == b)].staff.max())
                                   for b in BRANCHES} for m in MONTHS},
    }
    (out / "staffing_numbers.json").write_text(json.dumps(nums, indent=2, default=float))

    # --- data for the browser app
    (out / "staffing_data.js").write_text("window.STAFFING = " + json.dumps(
        {"capacity": CAPACITY, "wage": WAGE, "leave": LEAVE_SHARE, "min_crew": MIN_CREW, "gp": gp_map}) + ";\n")

    oct_fb = t.loc[("Forecast-based (cost-optimal)", "Oct")]
    oct_f2 = t.loc[("Fixed crew of 2", "Oct")]
    chart_rota(h, best, "Oct", out / "chart3_staffing_october.png",
               f"October: one person covers most hours; extra staff only at evening peaks "
               f"({int(oct_fb.staff_hours)} staff-hours/week vs {int(oct_f2.staff_hours)} for 2 people all day)")

    print("[staffing] keeping July's rota in October:", {b: (round(r.old_lost - r.new_lost, 1),
          round(r.old_cost - r.new_cost, 1)) for b, r in keep_july.iterrows()}, "(extra lost customers, extra $/week)")
    print("[staffing] Oct staff-hours by time of day:", by_tod.to_dict())
    print("[staffing] weekly totals, Oct:")
    for p in staff:
        r = t.loc[(p, "Oct")]
        print(f"  {p:32s} staff-hours {r.staff_hours:5.0f}  wages ${r.wage_cost:7.0f}  "
              f"lost customers {r.lost_customers:6.1f}  lost GP ${r.lost_gp:6.0f}  total ${r.total_cost:7.0f}")


if __name__ == "__main__":
    main()
