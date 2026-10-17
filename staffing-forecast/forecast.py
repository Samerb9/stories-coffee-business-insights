"""Stories Coffee: hourly visitor forecast.

Predicts how many receipts (visits) each branch will have in each hour,
tests it on June 2026 and on forecasts 1-4 months ahead, and forecasts Jul-Oct 2026
(the range the tests cover). The staffing decision built on it is in staffing.py.

Run:  python forecast.py --data data/stories_transactions.csv --out outputs/
"""
import argparse
import hashlib
import json
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from sklearn.ensemble import HistGradientBoostingRegressor

SEED = 490
BRANCHES = ["Garden", "Harbour", "Uptown"]
HOURS = list(range(7, 24))
DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
START = pd.Timestamp("2026-01-01")
TRAIN_END = pd.Timestamp("2026-04-30")
VAL_END = pd.Timestamp("2026-05-31")
TEST_END = pd.Timestamp("2026-06-30")
PEAK_HOURS = [19, 20, 21, 22]          # 19:00-22:59
NORMAL_DAYS = [0, 2, 3, 4]             # Mon, Wed, Thu, Fri: "normal weekday" for multipliers
THRESHOLDS = [10, 15, 20, 25, 30]
N_DRAWS = 2000
FORECAST_END = pd.Timestamp("2026-10-31")   # 4 months ahead: the longest horizon we could test
MONTHS = ["Jul", "Aug", "Sep", "Oct"]
HORIZON_ORIGINS = ["2026-02-28", "2026-03-31", "2026-04-30", "2026-05-31"]
ACCENT, GREY = "#C0392B", "#7F7F7F"
SOURCE = "Source: Stories POS receipts, Jan-Jun 2026 (1 receipt = 1 visit); team analysis."

FIT_LOG = []   # (model, last training date) for every fit; used by the leakage check


# ---------------------------------------------------------------- 1. data
def load_and_clean(path):
    """Drop exact duplicate lines, then collapse to one row per receipt."""
    raw = pd.read_csv(path)
    lines = raw.drop_duplicates()
    lines = lines.assign(Date=pd.to_datetime(lines["Date"]),
                         hour=lines["Time"].str[:2].astype(int))
    per = lines.groupby("Transaction ID").agg(
        Date=("Date", "first"), hour=("hour", "first"), Branch=("Branch", "first"),
        n_date=("Date", "nunique"), n_time=("Time", "nunique"), n_branch=("Branch", "nunique"))
    # every line of a receipt must share date, time and branch
    assert (per[["n_date", "n_time", "n_branch"]] == 1).all().all()
    receipts = per[["Date", "hour", "Branch"]].reset_index()
    info = {"n_raw_rows": len(raw), "n_duplicates": len(raw) - len(lines),
            "n_receipts": len(receipts)}
    print(f"[data] {info['n_raw_rows']} lines, {info['n_duplicates']} duplicates dropped, "
          f"{info['n_receipts']} receipts")
    return receipts, info


def build_hourly_table(receipts):
    """Receipts per branch x date x hour (07-23), zero-filled."""
    idx = pd.MultiIndex.from_product(
        [BRANCHES, pd.date_range(START, TEST_END), HOURS], names=["branch", "date", "hour"])
    counts = receipts.groupby(["Branch", "Date", "hour"]).size()
    counts.index.names = ["branch", "date", "hour"]
    assert counts.index.isin(idx).all(), "receipts outside 07-23 or outside the date range"
    t = counts.reindex(idx, fill_value=0).rename("y").reset_index()
    t["dow"] = t.date.dt.dayofweek
    t["trend"] = (t.date - START).dt.days
    t["month"] = t.date.dt.month
    t["week_start"] = t.date - pd.to_timedelta(t.dow, unit="D")
    print(f"[data] hourly table {len(t)} rows, {t.y.sum()} receipts, "
          f"{(t.y == 0).mean():.1%} zero hours")
    return t


# ---------------------------------------------------------------- 2. models
M1_SPECS = {
    "M1-full":  dict(dh=True,  trend="linear", bt=False),  # branch, dow*hour, branch:hour, trend
    "M1-noDH":  dict(dh=False, trend="linear", bt=False),  # no dow:hour (Tuesday effect same every hour)
    "M1-log":   dict(dh=True,  trend="log",    bt=False),  # slowing growth, log(1+t)
    "M1-bt":    dict(dh=True,  trend="linear", bt=True),   # growth differs by branch
}


def trend_value(t, kind):
    t = np.asarray(t, dtype=float)
    return t / 100.0 if kind == "linear" else np.log1p(t)


def design(df, spec):
    """One-hot design matrix for the Poisson GLM (reference: Garden, Monday, 07h)."""
    b, d, h = df.branch.values, df.dow.values, df.hour.values
    cols = {"intercept": np.ones(len(df))}
    for bb in BRANCHES[1:]:
        cols[f"branch={bb}"] = (b == bb) * 1.0
    for dd in range(1, 7):
        cols[f"dow={dd}"] = (d == dd) * 1.0
    for hh in HOURS[1:]:
        cols[f"hour={hh}"] = (h == hh) * 1.0
    if spec["dh"]:
        for dd in range(1, 7):
            for hh in HOURS[1:]:
                cols[f"dow={dd}:hour={hh}"] = ((d == dd) & (h == hh)) * 1.0
    for bb in BRANCHES[1:]:
        for hh in HOURS[1:]:
            cols[f"branch={bb}:hour={hh}"] = ((b == bb) & (h == hh)) * 1.0
    f = trend_value(df.trend.values, spec["trend"])
    cols["trend"] = f
    if spec["bt"]:
        for bb in BRANCHES[1:]:
            cols[f"branch={bb}:trend"] = (b == bb) * f
    return pd.DataFrame(cols, index=df.index)


class GLMModel:
    """M1: Poisson regression with log link."""

    def __init__(self, name):
        self.name, self.spec = name, M1_SPECS[name]

    def fit(self, df):
        X = design(df, self.spec)
        self.columns = list(X.columns)
        self.res = sm.GLM(df.y.values, X.values, family=sm.families.Poisson()).fit()
        FIT_LOG.append((self.name, df.date.max()))
        return self

    def eta(self, df, params=None):
        """Linear predictor; params may be a 2-D array of coefficient draws."""
        p = self.res.params if params is None else params
        return design(df, self.spec).values @ (p.T if np.ndim(p) == 2 else p)

    def predict(self, df):
        return np.exp(self.eta(df))

    def trend_offset(self, df):
        """Log-contribution of the trend relative to Jan 1 (used by M2b)."""
        return self.eta(df) - self.eta(df.assign(trend=0))


def hgb_features(df, with_trend):
    cols = [df.branch.map({b: i for i, b in enumerate(BRANCHES)}).values,
            df.dow.values, df.hour.values]
    if with_trend:
        cols.append(df.trend.values)
    return np.column_stack(cols).astype(float)


class HGBModel:
    """M2: gradient boosting with Poisson loss. If `trend_from` is a GLM, this is the
    M2b hybrid: the GLM supplies the trend as an offset and boosting learns the shape."""

    def __init__(self, name, lr, depth, iters, trend_from=None):
        self.name, self.trend_from = name, trend_from
        self.params = dict(learning_rate=lr, max_depth=depth, max_iter=iters)
        self.model = HistGradientBoostingRegressor(
            loss="poisson", random_state=SEED, early_stopping=False,
            categorical_features=[0, 1, 2], **self.params)

    def fit(self, df):
        if self.trend_from is None:
            self.model.fit(hgb_features(df, True), df.y.values)
        else:
            # Poisson with offset == fit the rate y/e with weight e
            e = np.exp(self.trend_from.trend_offset(df))
            self.model.fit(hgb_features(df, False), df.y.values / e, sample_weight=e)
        FIT_LOG.append((self.name, df.date.max()))
        return self

    def predict(self, df):
        if self.trend_from is None:
            return self.model.predict(hgb_features(df, True))
        return self.model.predict(hgb_features(df, False)) * np.exp(self.trend_from.trend_offset(df))


def poisson_deviance(y, mu):
    mu = np.clip(mu, 1e-9, None)
    with np.errstate(divide="ignore", invalid="ignore"):
        term = np.where(y > 0, y * np.log(y / mu), 0.0)
    return float(2 * np.mean(term - (y - mu)))


def baselines(table, origin, target):
    """B1-B3 made from data up to `origin` only, plus rolling B1/B2 (which see actuals
    up to 7 days before each target day, an advantage the models don't have)."""
    hist = table[table.date <= origin]
    key = ["branch", "dow", "hour"]

    def lookup(series, keys):
        return target[keys].merge(series.rename("p").reset_index(), on=keys, how="left").p.values

    out = {
        "B1 last week": lookup(hist[hist.date > origin - pd.Timedelta(days=7)].groupby(key).y.mean(), key),
        "B2 4-week avg": lookup(hist[hist.date > origin - pd.Timedelta(days=28)].groupby(key).y.mean(), key),
        "B3 flat avg": lookup(hist.groupby(["branch", "hour"]).y.mean(), ["branch", "hour"]),
    }
    full = table.set_index(["branch", "date", "hour"]).y

    def lag(k):
        idx = pd.MultiIndex.from_arrays([target.branch, target.date - pd.Timedelta(days=k), target.hour])
        return full.reindex(idx).values

    out["B1r last week (rolling)"] = lag(7)
    out["B2r 4-week avg (rolling)"] = np.mean([lag(7 * k) for k in range(1, 5)], axis=0)
    return out


# ---------------------------------------------------------------- 3. evaluation
def expected_abs_error(mu):
    """E|Y - mu| for Y ~ Poisson(mu): the error a perfect model still makes."""
    mu = np.clip(np.asarray(mu, float), 1e-9, None)
    k = np.arange(0, int(mu.max() * 3 + 30))
    pmf = stats.poisson.pmf(k[None, :], mu[:, None])
    return (pmf * np.abs(k[None, :] - mu[:, None])).sum(axis=1)


def interval(mu, level, nb_alpha=None):
    mu = np.clip(np.asarray(mu, float), 1e-9, None)
    q = (1 - level) / 2
    if nb_alpha is None:
        return stats.poisson.ppf(q, mu), stats.poisson.ppf(1 - q, mu)
    n = 1 / nb_alpha
    p = n / (n + mu)
    return stats.nbinom.ppf(q, n, p), stats.nbinom.ppf(1 - q, n, p)


def basic_metrics(y, p, prefix=""):
    e = p - y
    return {f"{prefix}mae": np.mean(np.abs(e)), f"{prefix}wape": np.abs(e).sum() / y.sum(),
            f"{prefix}rmse": np.sqrt(np.mean(e ** 2)), f"{prefix}bias": p.sum() / y.sum() - 1}


def busiest_hour_hits(df, pred):
    """Share of branch-days where the predicted busiest hour is the actual one
    (ties count as hits) or within +-1 hour."""
    exact, near = [], []
    for _, g in df.assign(p=pred).groupby(["branch", "date"]):
        ph = g.hour.values[np.argmax(g.p.values)]
        tops = g.hour.values[g.y.values == g.y.values.max()]
        exact.append(ph in tops)
        near.append(np.any(np.abs(tops - ph) <= 1))
    return float(np.mean(exact)), float(np.mean(near))


def busiest_hour_ceiling(df, mu, n_sim=1000, rng=None):
    """Hit rate a perfect model would get if the truth were Poisson(mu)."""
    exact, near = [], []
    for _, g in df.assign(mu=mu).groupby(["branch", "date"]):
        m = g.mu.values
        ph = int(np.argmax(m))
        sims = rng.poisson(m, size=(n_sim, len(m)))
        top = sims == sims.max(axis=1, keepdims=True)
        exact.append(top[:, ph].mean())
        near.append(top[:, max(ph - 1, 0):ph + 2].any(axis=1).mean())
    return float(np.mean(exact)), float(np.mean(near))


def weekly_errors(df, pred):
    d = df.assign(p=pred)
    days = d.groupby("week_start").date.nunique()
    full_weeks = days[days == 7].index
    w = d.groupby(["branch", "week_start"])[["y", "p"]].sum().reset_index()
    w["ape"] = (w.p - w.y).abs() / w.y
    full = w[w.week_start.isin(full_weeks)]
    part = w[~w.week_start.isin(full_weeks)]
    return float(full.ape.mean()), float(part.ape.mean()) if len(part) else np.nan, w


def evaluate(name, df, pred, ctx):
    y = df.y.values
    r = {"model": name}
    r.update(basic_metrics(y, pred))
    r["wape_floor"] = ctx["floor"]["overall"]
    pk = ctx["peak"]
    r.update(basic_metrics(y[pk], pred[pk], "peak_"))
    r["peak_wape_floor"] = ctx["floor"]["peak"]
    ta = ctx["top10_actual"]
    r.update({k: v for k, v in basic_metrics(y[ta], pred[ta], "top10act_").items() if "rmse" not in k})
    tp = ctx["top10_pred"]
    r.update({k: v for k, v in basic_metrics(y[tp], pred[tp], "top10pred_").items() if "rmse" not in k})
    r["busiest_hit_exact"], r["busiest_hit_pm1"] = busiest_hour_hits(df, pred)
    r["busiest_hit_ceiling_exact"], r["busiest_hit_ceiling_pm1"] = ctx["ceiling"]
    r["weekly_ape_full_weeks"], r["weekly_ape_partial_week"], _ = weekly_errors(df, pred)
    daily = df.assign(p=pred).groupby(["branch", "date"])[["y", "p"]].sum()
    r["daily_wape"] = (daily.p - daily.y).abs().sum() / daily.y.sum()
    for b in BRANCHES:
        m = (df.branch == b).values
        r[f"wape_{b}"] = np.abs(pred[m] - y[m]).sum() / y[m].sum()
        r[f"wape_floor_{b}"] = ctx["floor"][b]
    for lvl in (0.8, 0.95):
        lo, hi = interval(pred, lvl, ctx["nb_alpha"])
        r[f"coverage_{int(lvl * 100)}"] = float(np.mean((y >= lo) & (y <= hi)))
    r["avoidable_error_removed"] = np.nan   # filled once B3 is known
    return r


def save_model(model, out, filename="model.json", end=TEST_END, coefficients=True):
    """Save the trained GLM as plain JSON (loaded by predict.py) and a readable
    coefficient table where each multiplier says how much that term scales visits."""
    ci = model.res.conf_int()
    coef = pd.DataFrame({"term": model.columns, "coef": model.res.params, "std_err": model.res.bse,
                         "multiplier": np.exp(model.res.params),
                         "multiplier_lo95": np.exp(ci[:, 0]), "multiplier_hi95": np.exp(ci[:, 1])})
    def meaning(term):
        if term == "intercept":
            return "visits/hour at Garden, Monday 07:00, on Jan 1"
        if term == "trend":
            return "x visits per 100 days of growth"
        if ":" in term:
            return "extra x for this branch at this hour"
        kind, val = term.split("=")
        if kind == "dow":
            return f"x visits on {DOW[int(val)]} vs Monday"
        return {"branch": "x visits vs Garden (at 07:00)", "hour": "x visits vs 07:00 (at Garden)"}[kind]

    coef["meaning"] = coef.term.map(meaning)
    if coefficients:
        coef.to_csv(out / "model_coefficients.csv", index=False, float_format="%.4f")
    (out / filename).write_text(json.dumps({
        "model": model.name, "spec": model.spec, "start_date": str(START.date()),
        "trained_on": f"{START.date()} to {end.date()}", "columns": model.columns,
        "params": [float(v) for v in model.res.params],
        "cov": [[float(v) for v in row] for row in model.res.cov_params()]}, indent=1))


# ---------------------------------------------------------------- 4. projections
def make_cells(trend):
    g = pd.MultiIndex.from_product([BRANCHES, range(7), HOURS], names=["branch", "dow", "hour"])
    return g.to_frame(index=False).assign(trend=trend)


def project(final, nb_alpha, rng):
    """Expected visits per branch x weekday x hour on each day Jul 1 - Oct 31, with growth
    continuing at the fitted rate, for the point estimate (row 0) and N_DRAWS coefficient draws."""
    beta = final.res.params
    P = np.vstack([beta, rng.multivariate_normal(beta, final.res.cov_params(), N_DRAWS)])
    t_end = int((TEST_END - START).days)                       # Jun 30
    future = pd.date_range(TEST_END + pd.Timedelta(days=1), FORECAST_END)
    cells = make_cells(t_end)
    shape = final.eta(cells, P)                                # (357, 1+draws), level at Jun 30

    # trend contribution relative to Jun 30, per branch, day and draw
    steps = np.arange(1, len(future) + 1)
    growth_log = np.zeros((len(BRANCHES), len(future), P.shape[0]))
    for i, b in enumerate(BRANCHES):
        rows = pd.DataFrame({"branch": b, "dow": 0, "hour": 7, "trend": np.r_[t_end, t_end + steps]})
        e = final.eta(rows, P)
        growth_log[i] = e[1:] - e[0]
    bidx = cells.branch.map({b: i for i, b in enumerate(BRANCHES)}).values

    def period_mean(day_mask):
        """Mean expected visits per cell over the selected future days -> (357, 1+draws)."""
        out = np.zeros_like(shape)
        for d in range(7):
            days = np.where(day_mask & (future.dayofweek == d))[0]
            c = np.where(cells.dow.values == d)[0]
            # exp(shape + trend) = exp(shape) * exp(trend): average the trend factor over days first
            growth = np.exp(growth_log[:, days, :]).mean(axis=1)    # (branches, draws)
            out[c] = np.exp(shape[c]) * growth[bidx[c]]
        return out

    def single_hour(means):
        """One simulated hour per draw: coefficient uncertainty + count noise."""
        m = np.clip(means[:, 1:], 1e-9, None)
        if nb_alpha is None:
            return rng.poisson(m)
        n = 1 / nb_alpha
        return rng.negative_binomial(n, n / (n + m))

    return cells, future, period_mean, single_hour


def horizon_test(table, model_name):
    """How accurate is one forecast 1, 2, 3 and 4 months ahead? Fit on data up to the end of
    Feb, Mar, Apr and May (settings already fixed), forecast everything after, and score each
    full Mon-Sun week by how many months after the fit it starts."""
    rows = []
    for origin in map(pd.Timestamp, HORIZON_ORIGINS):
        m = GLMModel(model_name).fit(table[table.date <= origin])
        fut = table[table.date > origin].assign(p=lambda d: m.predict(d))
        fut = fut[fut.week_start > origin]
        fut = fut[fut.groupby("week_start").date.transform("nunique") == 7]
        fut = fut.assign(months_ahead=(fut.week_start.dt.year - origin.year) * 12
                         + fut.week_start.dt.month - origin.month)
        w = fut.groupby(["months_ahead", "branch", "week_start"])[["y", "p"]].sum().reset_index()
        w["ape"] = (w.p - w.y).abs() / w.y
        for a, g in w.groupby("months_ahead"):
            h = fut[fut.months_ahead == a]
            rows.append({"trained_up_to": str(origin.date()), "months_ahead": int(a),
                         "branch_weeks": len(g), "weekly_error": g.ape.mean(),
                         "bias": g.p.sum() / g.y.sum() - 1,
                         "hourly_wape": np.abs(h.p - h.y).sum() / h.y.sum()})
    detail = pd.DataFrame(rows)
    summary = (detail.assign(wsum=detail.weekly_error * detail.branch_weeks,
                             bsum=detail.bias * detail.branch_weeks)
               .groupby("months_ahead")
               .agg(tests=("trained_up_to", "count"), branch_weeks=("branch_weeks", "sum"),
                    wsum=("wsum", "sum"), bsum=("bsum", "sum")))
    summary["weekly_error"] = summary.wsum / summary.branch_weeks
    summary["bias"] = summary.bsum / summary.branch_weeks
    return detail, summary.drop(columns=["wsum", "bsum"]).reset_index()


def first_month(values, months, thr):
    for m, v in zip(months, values):
        if v > thr:
            return m
    return "not before Nov (beyond tested range)"


# ---------------------------------------------------------------- 5. charts
def style(ax):
    ax.grid(color="#E5E5E5", linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def chart_june(df, pred, nb_alpha, week_start, title, path):
    wk = df.assign(p=pred)
    wk = wk[wk.week_start == week_start].sort_values(["branch", "date", "hour"])
    fig, axes = plt.subplots(3, 1, figsize=(12, 8.5), sharex=True)
    for ax, b in zip(axes, ["Harbour", "Garden", "Uptown"]):
        g = wk[wk.branch == b]
        x = np.arange(len(g))
        lo, hi = interval(g.p.values, 0.8, nb_alpha)
        ax.fill_between(x, lo, hi, color=ACCENT, alpha=0.15, step="mid", label="80% range")
        ax.plot(x, g.p.values, color=ACCENT, lw=1.6, label="Predicted")
        ax.scatter(x, g.y.values, s=9, color=GREY, zorder=3, label="Actual")
        ax.set_ylabel("Visits per hour")
        ax.set_title(b, loc="left", fontsize=10)
        style(ax)
    days = sorted(wk.date.unique())
    axes[-1].set_xticks(np.arange(len(days)) * len(HOURS) + len(HOURS) / 2)
    axes[-1].set_xticklabels([pd.Timestamp(d).strftime("%a %d %b") for d in days])
    axes[-1].set_xlabel("Hour of the week (each day 07:00-23:59)")
    axes[0].legend(loc="upper left", frameon=False, ncol=3, fontsize=9)
    fig.suptitle(title, x=0.01, ha="left", fontsize=12, fontweight="bold")
    fig.text(0.01, 0.005, SOURCE, fontsize=8, color=GREY)
    fig.tight_layout(rect=(0, 0.02, 1, 0.96))
    fig.savefig(path, dpi=150)
    plt.close(fig)


def chart_projection(proj, june_actual, june_se, june_fit, peak_label, title, path):
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.8), sharey=True)
    for ax, b in zip(axes, ["Harbour", "Garden", "Uptown"]):
        p = proj[proj.branch == b]
        x = np.arange(1, len(MONTHS) + 1)
        ax.fill_between(x, p.single_hour_lo80, p.single_hour_hi80, color=ACCENT, alpha=0.13,
                        label="80% range for one such hour")
        ax.plot(np.r_[0, x], np.r_[june_fit[b], p.expected_visits], color=ACCENT, lw=2, marker="o", ms=4,
                label="Forecast (expected)")
        ax.errorbar([0], [june_actual[b]], yerr=[june_se[b]], fmt="o", color="black", ms=4, capsize=3,
                    zorder=4, label="June actual (5 Tuesdays, +-1 s.e.)")
        for lvl in (10, 20, 30):
            ax.axhline(lvl, color="#BBBBBB", ls="--", lw=0.8)
        ax.set_xticks(np.r_[0, x])
        ax.set_xticklabels(["Jun"] + MONTHS)
        ax.set_title(f"{b} ({peak_label[b]})", loc="left", fontsize=10)
        ax.set_xlabel("Month of 2026")
        style(ax)
    axes[0].set_ylabel("Visits in the busiest hour of the week")
    axes[0].legend(loc="upper left", frameon=False, fontsize=8)
    fig.suptitle(title, x=0.01, ha="left", fontsize=12, fontweight="bold")
    fig.text(0.01, 0.005, SOURCE + " Forecast assumes growth continues at the Jan-Jun rate; "
             "tested up to 4 months ahead.", fontsize=8, color=GREY)
    fig.tight_layout(rect=(0, 0.03, 1, 0.94))
    fig.savefig(path, dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/stories_transactions.csv")
    ap.add_argument("--out", default="outputs")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    rng = np.random.default_rng(SEED)

    # --- data
    receipts, info = load_and_clean(args.data)
    table = build_hourly_table(receipts)
    train = table[table.date <= TRAIN_END]
    val = table[(table.date > TRAIN_END) & (table.date <= VAL_END)]
    trainval = table[table.date <= VAL_END]
    test = table[table.date > VAL_END].reset_index(drop=True)

    # --- round 1: choose settings on May (fit on Jan-Apr)
    tuning = []
    m1_r1 = {}
    for name in M1_SPECS:
        m = GLMModel(name).fit(train)
        mu = m.predict(val)
        m1_r1[name] = m
        tuning.append({"model": name, "settings": json.dumps(M1_SPECS[name]),
                       "may_deviance": poisson_deviance(val.y.values, mu),
                       "may_wape": np.abs(mu - val.y.values).sum() / val.y.sum(),
                       "may_bias": mu.sum() / val.y.sum() - 1})
    m1_name = min((r for r in tuning if r["model"].startswith("M1")), key=lambda r: r["may_deviance"])["model"]
    m1 = m1_r1[m1_name]
    print(f"[tune] M1 version chosen on May: {m1_name}")

    # dispersion: on training fit, and on May residuals (used for intervals)
    pearson_disp = float(m1.res.pearson_chi2 / m1.res.df_resid)
    mu_val = m1.predict(val)
    phi_may = float(np.mean((val.y.values - mu_val) ** 2 / mu_val))
    nb_alpha = None
    if phi_may > 1.2:
        nb_alpha = max(float(((val.y.values - mu_val) ** 2 - mu_val).sum() / (mu_val ** 2).sum()), 1e-6)
    print(f"[tune] dispersion: train Pearson {pearson_disp:.2f}, May residuals {phi_may:.2f} "
          f"-> {'Poisson' if nb_alpha is None else 'negative binomial'} intervals")

    grid = [(lr, d, 300) for lr in (0.03, 0.1) for d in (3, 5, None)]
    best = {}
    for kind in ("M2", "M2b"):
        for lr, d, it in grid:
            m = HGBModel(kind, lr, d, it, trend_from=m1 if kind == "M2b" else None).fit(train)
            mu = m.predict(val)
            row = {"model": kind, "settings": json.dumps(m.params),
                   "may_deviance": poisson_deviance(val.y.values, mu),
                   "may_wape": np.abs(mu - val.y.values).sum() / val.y.sum(),
                   "may_bias": mu.sum() / val.y.sum() - 1}
            tuning.append(row)
            if kind not in best or row["may_deviance"] < best[kind][0]:
                best[kind] = (row["may_deviance"], (lr, d, it))
        print(f"[tune] {kind} best settings on May: lr={best[kind][1][0]}, depth={best[kind][1][1]}, "
              f"iters={best[kind][1][2]}")
    may_base = baselines(table, TRAIN_END, val.reset_index(drop=True))
    for name in ("B1 last week", "B2 4-week avg", "B3 flat avg"):
        p = may_base[name]
        tuning.append({"model": name, "settings": "", "may_deviance": poisson_deviance(val.y.values, p),
                       "may_wape": np.abs(p - val.y.values).sum() / val.y.sum(),
                       "may_bias": p.sum() / val.y.sum() - 1})
    tuning_df = pd.DataFrame(tuning)
    tuning_df.to_csv(out / "tuning_may.csv", index=False, float_format="%.4f")

    # --- round 2: refit chosen settings on Jan-May, test on June once
    M1 = GLMModel(m1_name).fit(trainval)
    save_model(M1, out, "model_test.json", VAL_END, coefficients=False)   # never saw June (for the app)
    M2 = HGBModel("M2", *best["M2"][1]).fit(trainval)
    M2b = HGBModel("M2b", *best["M2b"][1], trend_from=M1).fit(trainval)
    fits_before_test = list(FIT_LOG)
    assert max(d for _, d in fits_before_test) <= VAL_END, "June leaked into a fit"

    preds = {"M1 Poisson GLM": M1.predict(test), "M2 gradient boosting": M2.predict(test),
             "M2b GLM trend + boosting": M2b.predict(test)}
    preds.update(baselines(table, VAL_END, test))

    mu_ref = preds["M1 Poisson GLM"]
    ea = expected_abs_error(mu_ref)
    peak = test.hour.isin(PEAK_HOURS).values
    n10 = int(np.ceil(0.10 * len(test)))
    top_act = np.zeros(len(test), bool)
    top_act[np.argsort(-test.y.values, kind="stable")[:n10]] = True
    top_pred = np.zeros(len(test), bool)
    top_pred[np.argsort(-mu_ref, kind="stable")[:n10]] = True
    ctx = {"floor": {"overall": ea.sum() / mu_ref.sum(), "peak": ea[peak].sum() / mu_ref[peak].sum(),
                     **{b: ea[(test.branch == b).values].sum() / mu_ref[(test.branch == b).values].sum()
                        for b in BRANCHES}},
           "peak": peak, "top10_actual": top_act, "top10_pred": top_pred, "nb_alpha": nb_alpha,
           "ceiling": busiest_hour_ceiling(test, mu_ref, rng=rng)}
    rows = [evaluate(n, test, p, ctx) for n, p in preds.items()]
    bt = pd.DataFrame(rows)
    b3 = bt.loc[bt.model == "B3 flat avg", "wape"].item()
    bt["avoidable_error_removed"] = (b3 - bt.wape) / (b3 - ctx["floor"]["overall"])
    others = {b: bt[f"wape_{b}"] - bt[f"wape_floor_{b}"] for b in BRANCHES}
    for b in BRANCHES:
        rest = np.mean([others[o] for o in BRANCHES if o != b], axis=0)
        bt[f"flag_{b}"] = others[b] > 2 * rest
    bt.to_csv(out / "backtest.csv", index=False, float_format="%.4f")
    print("[test] June WAPE: " + ", ".join(f"{r['model']} {r['wape']:.1%}" for r in rows))

    # model choice rule: ML only if it beats M1 by >= 1 percentage point of WAPE
    w = bt.set_index("model").wape
    ml_best = min(["M2 gradient boosting", "M2b GLM trend + boosting"], key=lambda k: w[k])
    margin_pp = (w["M1 Poisson GLM"] - w[ml_best]) * 100
    chosen = ml_best if margin_pp >= 1.0 else "M1 Poisson GLM"
    print(f"[choose] best ML = {ml_best}, M1 minus ML = {margin_pp:+.2f} pp -> {chosen}")
    chosen_pred = preds[chosen]

    # --- how far ahead does one forecast stay accurate? (June is scored here, never tuned on)
    horizon_detail, horizon = horizon_test(table, m1_name)
    horizon_detail.to_csv(out / "horizon_test.csv", index=False, float_format="%.4f")
    print("[horizon] weekly error by months ahead: " +
          ", ".join(f"{r.months_ahead}m {r.weekly_error:.1%}" for r in horizon.itertuples()))

    # --- round 3: refit on Jan-Jun and forecast Jul-Oct (the GLM is used: it is the
    # only candidate whose growth trend can be carried forward)
    final = GLMModel(m1_name).fit(table)
    save_model(final, out)
    table[["branch", "date", "hour", "y"]].to_csv(out / "hourly_actuals.csv", index=False,
                                                  date_format="%Y-%m-%d")
    cells, future, period_mean, single_hour = project(final, nb_alpha, rng)

    # 6a busiest hours Jul 1-28
    m28 = period_mean(np.asarray(future <= pd.Timestamp("2026-07-28")))
    s28 = single_hour(m28)
    c28 = cells.assign(expected_visits=m28[:, 0], lo80=np.quantile(s28, 0.1, axis=1),
                       hi80=np.quantile(s28, 0.9, axis=1))
    busiest = (c28.sort_values(["branch", "dow", "expected_visits"], ascending=[True, True, False])
               .groupby(["branch", "dow"]).head(3).copy())
    busiest["rank"] = busiest.groupby(["branch", "dow"]).cumcount() + 1
    busiest["weekday"] = busiest.dow.map(dict(enumerate(DOW)))
    busiest = busiest[["branch", "weekday", "rank", "hour", "expected_visits", "lo80", "hi80"]]
    busiest.columns = ["branch", "weekday", "rank", "hour", "estimate_visits_per_hour",
                       "estimate_single_hour_lo80", "estimate_single_hour_hi80"]
    busiest.to_csv(out / "busiest_hours_july.csv", index=False, float_format="%.2f")

    # 6b heat map per month, Jul-Oct (mean + high end of a single hour, for the team's staffing maths)
    heat_rows = []
    for mi, mname in enumerate(MONTHS, start=7):
        mm = period_mean(np.asarray(future.month == mi))
        sm = single_hour(mm)
        heat_rows.append(cells.assign(month=mname, weekday=cells.dow.map(dict(enumerate(DOW))),
                                      estimate_mean=mm[:, 0],
                                      estimate_p80_high=np.quantile(sm, 0.8, axis=1),
                                      estimate_p95_high=np.quantile(sm, 0.95, axis=1),
                                      _draws=list(mm[:, 1:]), _single=list(sm)))
    heat_all = pd.concat(heat_rows, ignore_index=True)
    heat_all[["branch", "month", "weekday", "hour", "estimate_mean", "estimate_p80_high", "estimate_p95_high"]] \
        .to_csv(out / "forecast_heatmap.csv", index=False, float_format="%.2f")
    heat = heat_all[heat_all.month == "Jul"]

    # 6c busiest weekday-hour of the week per branch, forecast by month
    peak_cell = {}
    for b in BRANCHES:
        cb = heat[heat.branch == b]
        r = cb.loc[cb.estimate_mean.idxmax()]
        peak_cell[b] = (int(r.dow), int(r.hour))
    prow = []
    for mname in MONTHS:
        for b, (d, h) in peak_cell.items():
            r = heat_all[(heat_all.month == mname) & (heat_all.branch == b) & (heat_all.dow == d)
                         & (heat_all.hour == h)].iloc[0]
            prow.append({"branch": b, "month": mname, "busiest_hour": f"{DOW[d]} {h:02d}:00",
                         "expected_visits": r.estimate_mean,
                         "expected_lo80": np.quantile(r._draws, 0.1), "expected_hi80": np.quantile(r._draws, 0.9),
                         "single_hour_lo80": np.quantile(r._single, 0.1),
                         "single_hour_hi80": np.quantile(r._single, 0.9),
                         "p_single_hour_above": {t: float(np.mean(r._single > t)) for t in THRESHOLDS}})
    proj = pd.DataFrame(prow).sort_values(["branch", "month"], key=lambda c: c.map(
        {m: i for i, m in enumerate(MONTHS)}) if c.name == "month" else c).reset_index(drop=True)
    proj.drop(columns="p_single_hour_above").to_csv(out / "peak_forecast.csv", index=False,
                                                    float_format="%.2f")

    # 6d thresholds
    june = table[table.date.dt.month == 6]
    june_peak = {b: june[(june.branch == b) & (june.dow == peak_cell[b][0]) & (june.hour == peak_cell[b][1])].y
                 for b in BRANCHES}
    trow = []
    for b in BRANCHES:
        p = proj[proj.branch == b]
        for thr in THRESHOLDS:
            a = "already above in June" if june_peak[b].mean() > thr else first_month(p.expected_visits, MONTHS, thr)
            if (june_peak[b] > thr).mean() >= 0.5:
                s_ = "already in June"
            else:
                s_ = first_month([d[thr] for d in p.p_single_hour_above], MONTHS, 0.5 - 1e-12)
            trow.append({"branch": b, "threshold_visits_per_hour": thr,
                         "first_month_average_above": a, "first_month_single_hour_likely_above": s_})
    pd.DataFrame(trow).to_csv(out / "thresholds.csv", index=False)

    # --- interpretation numbers from the final model
    t_end = int((TEST_END - START).days)
    base = make_cells(t_end)
    mu_cells = final.predict(base)
    P = np.vstack([final.res.params,
                   rng.multivariate_normal(final.res.params, final.res.cov_params(), N_DRAWS)])
    daily = np.exp(final.eta(base, P))
    tot = pd.DataFrame(daily).assign(dow=base.dow.values).groupby("dow").sum().values  # (7, draws)
    normal = tot[NORMAL_DAYS].mean(axis=0)
    tue, sat = tot[1] / normal, tot[5] / normal
    grow = {}
    for b in BRANCHES:
        rows_b = pd.DataFrame({"branch": b, "dow": 0, "hour": 7, "trend": [0, t_end, t_end + 7]})
        e = final.eta(rows_b, P)
        grow[b] = {"week": np.exp(e[2] - e[1]) - 1, "janjun": np.exp(e[1] - e[0]) - 1}
    raw_dow = table.groupby("dow").y.mean()
    raw_month = table.groupby("month").y.mean()

    # diagnostics: daily actual / fitted on approximate public-holiday dates (not used for tuning)
    holidays = {"2026-01-01": "New Year", "2026-01-06": "Armenian Christmas", "2026-02-09": "St Maroun",
                "2026-03-20": "Eid al-Fitr (approx.)", "2026-03-25": "Annunciation",
                "2026-04-03": "Good Friday (Western)", "2026-04-10": "Good Friday (Orthodox)",
                "2026-05-01": "Labour Day", "2026-05-25": "Liberation Day",
                "2026-05-27": "Eid al-Adha (approx.)", "2026-06-16": "Islamic New Year (approx.)"}
    fitted = table.assign(mu=final.predict(table))
    day = fitted.groupby("date")[["y", "mu"]].sum()
    day["ratio"] = day.y / day.mu
    hol = {f"{d} {n}": round(float(day.loc[d, "ratio"]), 3) for d, n in holidays.items()}
    ram = day.loc["2026-02-18":"2026-03-19", "ratio"]
    month_ratio = (fitted.groupby("month")[["y", "mu"]].sum().pipe(lambda m: m.y / m.mu)).round(3)

    # --- charts
    _, _, wk = weekly_errors(test, chosen_pred)
    wk_overall = wk.groupby("week_start")[["y", "p"]].sum()
    full_weeks = test.groupby("week_start").date.nunique().pipe(lambda s: s[s == 7].index)
    hourly_wk = {ws: np.abs(chosen_pred[(test.week_start == ws).values] -
                            test.y.values[(test.week_start == ws).values]).sum() /
                     test.y.values[(test.week_start == ws).values].sum() for ws in full_weeks}
    chart_week = sorted(hourly_wk, key=hourly_wk.get)[1]   # rule: 2nd-best of the 4 full weeks
    r_ch = bt.set_index("model").loc[chosen]
    chart_june(test, chosen_pred, nb_alpha, chart_week,
               f"Model predicts June's weekly visits within {r_ch.weekly_ape_full_weeks:.0%} on average; "
               f"hourly error {r_ch.wape:.0%}, close to the {ctx['floor']['overall']:.0%} limit set by chance",
               out / "chart1_june_fit.png")
    oct_h = proj[(proj.branch == "Harbour") & (proj.month == "Oct")]
    peak_label = {b: f"busiest hour: {DOW[d]} {h:02d}:00" for b, (d, h) in peak_cell.items()}
    june_fit = {b: float(fitted[(fitted.month == 6) & (fitted.branch == b) & (fitted.dow == peak_cell[b][0])
                                & (fitted.hour == peak_cell[b][1])].mu.mean()) for b in BRANCHES}
    chart_projection(proj, {b: june_peak[b].mean() for b in BRANCHES},
                     {b: june_peak[b].std(ddof=1) / np.sqrt(len(june_peak[b])) for b in BRANCHES},
                     june_fit, peak_label,
                     f"Harbour's busiest hour forecast to reach {oct_h.expected_visits.item():.0f} visits by October "
                     f"(range for one such hour {oct_h.single_hour_lo80.item():.0f}-{oct_h.single_hour_hi80.item():.0f})",
                     out / "chart2_peak_forecast.png")

    # --- key numbers
    def q(a):
        return [round(float(np.quantile(a[1:], 0.025)), 4), round(float(np.quantile(a[1:], 0.975)), 4)]

    rc = bt.set_index("model")
    measured = {
        "n_raw_rows": {"value": info["n_raw_rows"], "unit": "lines", "source_step": "load"},
        "n_duplicates": {"value": info["n_duplicates"], "unit": "lines", "source_step": "load"},
        "n_receipts": {"value": info["n_receipts"], "unit": "receipts", "source_step": "load"},
        "n_table_rows": {"value": len(table), "unit": "branch-hours", "source_step": "table"},
        "share_zero_hours": {"value": round(float((table.y == 0).mean()), 4), "unit": "share", "source_step": "table"},
        "raw_mean_visits_per_hour_by_month": {"value": raw_month.round(3).to_dict(), "unit": "visits/hour",
                                              "source_step": "table"},
        "raw_growth_jan_to_jun": {"value": round(float(raw_month[6] / raw_month[1] - 1), 4), "unit": "share",
                                  "source_step": "table"},
        "raw_tuesday_vs_normal_weekday": {"value": round(float(raw_dow[1] / raw_dow[NORMAL_DAYS].mean()), 3),
                                          "unit": "ratio", "source_step": "table"},
        "raw_saturday_vs_normal_weekday": {"value": round(float(raw_dow[5] / raw_dow[NORMAL_DAYS].mean()), 3),
                                           "unit": "ratio", "source_step": "table"},
        "m1_version_chosen_on_may": {"value": m1_name, "unit": "", "source_step": "round 1"},
        "m2_settings": {"value": dict(zip(["learning_rate", "max_depth", "max_iter"], best["M2"][1])),
                        "unit": "", "source_step": "round 1"},
        "m2b_settings": {"value": dict(zip(["learning_rate", "max_depth", "max_iter"], best["M2b"][1])),
                         "unit": "", "source_step": "round 1"},
        "dispersion_train_pearson": {"value": round(pearson_disp, 3), "unit": "ratio", "source_step": "round 1"},
        "dispersion_may_residuals": {"value": round(phi_may, 3), "unit": "ratio", "source_step": "round 1"},
        "interval_distribution": {"value": "Poisson" if nb_alpha is None else f"NB alpha={nb_alpha:.3f}",
                                  "unit": "", "source_step": "round 1"},
        "chosen_model": {"value": chosen, "unit": "", "source_step": "choice rule"},
        "best_ml_model": {"value": ml_best, "unit": "", "source_step": "choice rule"},
        "m1_minus_ml_wape_pp": {"value": round(float(margin_pp), 2), "unit": "percentage points",
                                "source_step": "choice rule"},
        "june_test": {"value": {m: {k: (round(float(v), 4) if isinstance(v, (float, np.floating)) else v)
                                    for k, v in rc.loc[m].items()} for m in rc.index},
                      "unit": "see backtest.csv", "source_step": "round 2"},
        "june_wape_floor": {"value": {k: round(float(v), 4) for k, v in ctx["floor"].items()}, "unit": "share",
                            "source_step": "round 2"},
        "june_busiest_hour_ceiling": {"value": [round(c, 3) for c in ctx["ceiling"]], "unit": "[exact, +-1h]",
                                      "source_step": "round 2"},
        "chart1_week_start": {"value": str(pd.Timestamp(chart_week).date()), "unit": "", "source_step": "charts"},
        "june_actual_peak_hour_mean": {"value": {b: round(float(june_peak[b].mean()), 2) for b in BRANCHES},
                                       "unit": "visits/hour", "source_step": "thresholds"},
        "june_model_peak_hour_mean": {"value": {b: round(june_fit[b], 2) for b in BRANCHES},
                                      "unit": "visits/hour (final model, June Tuesdays)", "source_step": "charts"},
        "june_actual_peak_hour_max": {"value": {b: int(june_peak[b].max()) for b in BRANCHES},
                                      "unit": "visits/hour", "source_step": "thresholds"},
        "horizon_test": {"value": {f"{r.months_ahead} months ahead": {
                             "weekly_error": round(float(r.weekly_error), 4), "bias": round(float(r.bias), 4),
                             "tests": int(r.tests), "branch_weeks": int(r.branch_weeks)}
                             for r in horizon.itertuples()},
                         "unit": "weekly total error, bias", "source_step": "horizon test"},
        "diag_holiday_actual_over_fitted": {"value": hol, "unit": "ratio (1 = as expected)", "source_step": "diagnostics"},
        "diag_all_days_ratio_sd": {"value": round(float(day.ratio.std()), 3), "unit": "sd of daily ratio",
                                   "source_step": "diagnostics"},
        "diag_share_days_outside_15pct": {"value": round(float(((day.ratio - 1).abs() > 0.15).mean()), 3),
                                          "unit": "share of 181 days", "source_step": "diagnostics"},
        "projection_model": {"value": f"{m1_name} refit on Jan-Jun", "unit": "", "source_step": "round 3"},
        "diag_ramadan_actual_over_fitted": {"value": round(float(ram.sum() / len(ram)), 3), "unit": "mean daily ratio",
                                            "source_step": "diagnostics"},
        "diag_month_actual_over_fitted": {"value": month_ratio.to_dict(), "unit": "ratio", "source_step": "diagnostics"},
    }
    estimated = {
        "fitted_weekly_growth_at_jun30": {"value": {b: [round(float(grow[b]["week"][0]), 4), q(grow[b]["week"])]
                                                    for b in BRANCHES},
                                          "unit": "[share/week, 95% CI]", "source_step": "final fit"},
        "fitted_growth_jan1_to_jun30": {"value": {b: [round(float(grow[b]["janjun"][0]), 4), q(grow[b]["janjun"])]
                                                  for b in BRANCHES},
                                        "unit": "[share, 95% CI]", "source_step": "final fit"},
        "tuesday_multiplier": {"value": [round(float(tue[0]), 3), q(tue)], "unit": "[x normal weekday, 95% CI]",
                               "source_step": "final fit"},
        "saturday_multiplier": {"value": [round(float(sat[0]), 3), q(sat)], "unit": "[x normal weekday, 95% CI]",
                                "source_step": "final fit"},
        "busiest_hour_of_week": {"value": {b: f"{DOW[d]} {h:02d}:00" for b, (d, h) in peak_cell.items()},
                                 "unit": "", "source_step": "final fit"},
        "peak_forecast": {"value": {f"{r.branch} {r.month}":
                                      [round(r.expected_visits, 2), round(r.expected_lo80, 2), round(r.expected_hi80, 2),
                                       round(r.single_hour_lo80, 2), round(r.single_hour_hi80, 2)]
                                      for r in proj.itertuples()},
                            "unit": "[expected, exp lo80, exp hi80, one-hour lo80, one-hour hi80]",
                            "source_step": "forecast"},
    }
    key = {"measured": measured, "estimated": estimated}
    blob = json.dumps(key, indent=2, default=str, sort_keys=True)
    (out / "key_numbers.json").write_text(blob)

    # --- data for the browser app (a .js file, so app/index.html also works when opened by double-click)
    app_data = {"model": json.loads((out / "model.json").read_text()),
                "model_test": json.loads((out / "model_test.json").read_text()),
                "actuals": {"start": str(START.date()), "branches": BRANCHES, "hours": HOURS,
                            "y": table.sort_values(["branch", "date", "hour"]).y.astype(int).tolist()},
                "backtest": json.loads(bt.to_json(orient="records"))}
    (out / "app_data.js").write_text("window.APP_DATA = " + json.dumps(app_data, separators=(",", ":")) + ";\n")

    # --- self-check
    runtime = time.perf_counter() - t0
    assert info["n_duplicates"] == 132 and info["n_receipts"] == 33887
    assert len(table) == 3 * 181 * 17 and table.y.sum() == info["n_receipts"]
    assert all(d <= VAL_END for _, d in fits_before_test)
    assert (proj.groupby("branch").expected_visits.apply(lambda v: v.is_monotonic_increasing)).all()
    assert set(horizon.months_ahead) == {1, 2, 3, 4}
    cov_cols = [c for c in bt.columns if c.startswith("coverage")]
    assert bt[cov_cols].apply(lambda s: s.between(0, 1)).all().all()
    assert set(preds) == set(bt.model)
    assert runtime < 120, f"runtime {runtime:.0f}s"
    print(f"[done] {runtime:.1f}s, key_numbers sha256 {hashlib.sha256(blob.encode()).hexdigest()[:12]}")


if __name__ == "__main__":
    main()
