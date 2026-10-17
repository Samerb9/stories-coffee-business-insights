# stories-coffee-business-insights

**EECE490 Stories Coffee Hackathon**

**Team:** Christopher Ferzli, Samer Bannout

Transaction data analysis for the EECE490 Stories Coffee Hackathon, exploring profitability, customer behavior, and sales patterns to develop evidence-based business recommendations.

## Our ideas at a glance

| # | Idea | Action for the CEO | Value (estimated) | Folder |
|---|---|---|---|---|
| 1 | ML staffing forecast: staff each hour to predicted demand | 1 person in quiet hours, 2–3 only at evening peaks; add Harbour evening hours as demand grows | up to ~$67k/year in staff-hours (depends on the minimum-crew rule) | [`Ideas/ml-staffing-forecast/`](Ideas/ml-staffing-forecast/) |
| 2 | Opening hours | Keep evening hours; pilot staying open until 01:00 at Harbour on Tue/Wed/Fri; Uptown can open at 8:00 | ~$1.3k/year from mornings; $1.3k–9.6k/year if the late hour works | [`Ideas/opening-hours/`](Ideas/opening-hours/) |
| 3 | Item mix planning | Plan each item's share from a 5-month average plus a monthly watchlist, not from last month | 19% fewer units mis-planned in a June test; at most ~$6.7k/year of waste | [`Ideas/taste-shift/`](Ideas/taste-shift/) |
| 4 | Habit-building promotions | Judge promotions on 8-week profit; first run one randomised ~$500 test | a $471 discount returned an estimated $971–1,737 | [`Ideas/promotion-habit/`](Ideas/promotion-habit/) |

All ideas start from a [data audit](data-audit/) (20 checks) and share one tested forecast of customers per branch per hour. It's accurate to 3–4% on weekly totals up to 4 months ahead, on months the model never saw.

## Conclusion: Idea 1 (ML staffing forecast)

Stories' customer flow is very predictable. Our model forecasts each branch's weekly customers within **3–4%** up to 4 months ahead, tested on months it never saw. Half of all customers arrive after 6pm, and Tuesday brings 1.5× a normal day. At 12 customers per staff-hour, one person covers almost every hour; a second is needed only in evening peaks, and a third only at Harbour on Tuesday at 9pm from August.

A rota built from the forecast needs **389 staff-hours a week in October**, against 714 for two people on every shift. That's worth about **$67k a year** at $4 an hour while losing under 1% of customers to queues, provided one person may run a quiet hour. If two people must always be present, the saving disappears, and the forecast's value is timing Harbour's extra evening staff.

## Conclusion: Idea 2 (opening hours)

**Don't close earlier; test closing later at Harbour.** Every evening hour earns 1.5–22× the ~$8 it costs to stay open, and only 11 of 357 branch-hours a week fall below cost, all early mornings at Uptown and Garden. Trimming them saves under ~$1.3k a year. Orders stay flat right up to 23:59, so staying open until 01:00 at Harbour pays off if the extra hour brings just 12–25% of the 11pm hour's profit (~$1.3k–9.6k a year). There's no data after midnight, so this needs a 6-week pilot, not a prediction. In a test on June, hours chosen with our forecast delivered 4× the value of hours chosen from plain averages, which ignored growth.

## Conclusion: Idea 3 (item mix planning)

Each branch should plan an item's share of its category from the average of the last five months, adjusting only for a short watchlist of steadily trending items. In a test on June, this mis-planned **19% fewer units** than copying last month (9.3% against 11.4% error). Most monthly swings in item choice are noise that reverses (correlation −0.59 between consecutive periods). A few items drift steadily; Strawberry Matcha gained 4.8 points of its category and Iced Matcha lost 4.5. The value is planning accuracy, at most about $6.7k a year of avoided waste.

## Conclusion: Idea 4 (habit-building promotions)

After Harbour's 15%-off week on cold coffee and desserts, Harbour kept selling an estimated **11–15%** more of those items than the other branches for three months, while its other items didn't change. None of 28 fake start dates or 500 random item sets came close. That turns a $471 discount into about **$971–1,737** of extra gross profit. The evidence is suggestive, not conclusive: the lift is clear against Uptown but uncertain against Garden alone. Stories should run one randomised ~$500 promotion with an 8-week follow-up before changing how it judges promotions.

Every dollar figure rests on stated assumptions. Each idea's report shows which assumptions change the decision, the tests against baselines on unseen data, alternative explanations, and a practical test Stories can run first.

## Repository layout

| Folder | Contents |
|---|---|
| [`Ideas/ml-staffing-forecast/`](Ideas/ml-staffing-forecast/) | Idea 1: ML forecast of customers per branch-hour (shared by all ideas), staffing decision, browser app |
| [`Ideas/opening-hours/`](Ideas/opening-hours/) | Idea 2: opening and closing hours, tested on June, plus a late-night pilot design |
| [`Ideas/taste-shift/`](Ideas/taste-shift/) | Idea 3: item-mix trends within each category and the best planning rule, tested on June |
| [`Ideas/promotion-habit/`](Ideas/promotion-habit/) | Idea 4: lasting effect of Harbour's 15% promotion, with placebo checks |
| [`data-audit/`](data-audit/) | 20 automated data-quality checks run before any analysis |
| [`data/`](data/) | Where to put `stories_transactions.csv` (not committed) |

## Reproduce

Put `stories_transactions.csv` in `data/`, then run:

```bash
pip install -r Ideas/ml-staffing-forecast/requirements.txt
cd data-audit && python -m src.audit && cd ..
python Ideas/ml-staffing-forecast/forecast.py
python Ideas/ml-staffing-forecast/staffing.py
python Ideas/opening-hours/hours.py
python Ideas/taste-shift/taste_shift.py
python Ideas/promotion-habit/promo_habit.py
```

Everything runs in about two minutes. Open `Ideas/ml-staffing-forecast/app/index.html` in a browser to explore the forecast.
