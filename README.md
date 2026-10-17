# stories-coffee-business-insights

**EECE490 Stories Coffee Hackathon**

**Team:** Christopher Ferzli, Samer Bannout

Transaction data analysis for the EECE490 Stories Coffee Hackathon, exploring profitability, customer behavior, and sales patterns to develop evidence-based business recommendations.

## Our ideas at a glance

| # | Idea | Action for the CEO | Value (estimated) | Folder |
|---|---|---|---|---|
| 1 | Staff each hour to forecast demand | 1 person in quiet hours, 2–3 only at evening peaks; add Harbour evening hours as demand grows | up to ~$67k/year in staff-hours (depends on the minimum-crew rule) | [`staffing-forecast/`](staffing-forecast/) |
| 1b | Garden's cost anomaly | Check one month of Garden supplier invoices | ~$32k/year, or a cost-allocation error hiding ~16 margin points | [`staffing-forecast/`](staffing-forecast/) (§10 of the report) |
| 2 | Opening hours | Keep evening hours; pilot staying open until 01:00 at Harbour on Tue/Wed/Fri; Uptown can open at 8:00 | ~$1.3k/year from mornings; $1.3k–9.6k/year if the late hour works | [`opening-hours/`](opening-hours/) |

All ideas start from a [data audit](data-audit/) (21 checks) and share one tested forecast of customers per branch per hour. It's accurate to 3–4% on weekly totals up to 4 months ahead, on months the model never saw.

## Conclusion: Idea 1 (staffing)

Stories' customer flow is very predictable. Our model forecasts each branch's weekly customers within **3–4%** up to 4 months ahead, tested on months it never saw. Half of all customers arrive after 6pm, and Tuesday brings 1.5× a normal day. At 12 customers per staff-hour, one person covers almost every hour; a second is needed only in evening peaks, and a third only at Harbour on Tuesday at 9pm from August.

A rota built from the forecast needs **389 staff-hours a week in October**, against 714 for two people on every shift. That's worth about **$67k a year** at $4 an hour while losing under 1% of customers to queues, provided one person may run a quiet hour. If two people must always be present, the saving disappears, and the forecast's value is timing Harbour's extra evening staff.

Separately, Garden's recorded unit costs are exactly **1.43× Harbour's on all 45 products**, even bottled water. Either Garden overpays about **$32k a year**, or a cost-allocation error understates its margin (47% recorded, about 63% at Harbour's costs). One month of supplier invoices would tell which.

## Conclusion: Idea 2 (opening hours)

**Don't close earlier; test closing later at Harbour.** Every evening hour earns 1.5–22× the ~$8 it costs to stay open, and only 11 of 357 branch-hours a week fall below cost, all early mornings at Uptown and Garden. Trimming them saves under ~$1.3k a year. Orders stay flat right up to 23:59, so staying open until 01:00 at Harbour pays off if the extra hour brings just 12–25% of the 11pm hour's profit (~$1.3k–9.6k a year). There's no data after midnight, so this needs a 6-week pilot, not a prediction. In a test on June, hours chosen with our forecast delivered 4× the value of hours chosen from plain averages, which ignored growth.

Every dollar figure rests on stated assumptions. Each idea's report shows which assumptions change the decision, the tests against baselines on unseen data, alternative explanations, and a practical test Stories can run first.

## Repository layout

| Folder | Contents |
|---|---|
| [`data-audit/`](data-audit/) | 21 automated data-quality checks run before any analysis |
| [`staffing-forecast/`](staffing-forecast/) | Hourly customer forecast (shared by all ideas), staffing decision, Garden cost finding, browser app |
| [`opening-hours/`](opening-hours/) | Opening and closing hours decision, tested on June, plus a late-night pilot design |
| [`data/`](data/) | Where to put `stories_transactions.csv` (not committed) |

## Reproduce

Put `stories_transactions.csv` in `data/`, then run:

```bash
pip install -r staffing-forecast/requirements.txt
cd data-audit && python -m src.audit && cd ..
python staffing-forecast/forecast.py
python staffing-forecast/staffing.py
python staffing-forecast/cost_check.py
python opening-hours/hours.py
```

Everything runs in under a minute. Open `staffing-forecast/app/index.html` in a browser to explore the forecast.
