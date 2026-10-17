# ML staffing forecast: staffing Stories to predicted demand

Every number below comes from a file in `outputs/`.
**[MEASURED]** means computed from the data, including all tests on data the model never saw.
**[ESTIMATED]** means it depends on stated assumptions.

---

## Conclusion

Stories' customer flow is very predictable. Our model forecasts each branch's weekly customers within **3–4%** up to 4 months ahead, tested on months it never saw **[MEASURED]**. Half of all customers arrive after 6pm, and Tuesday brings 1.5× a normal day **[MEASURED]**. At 12 customers per staff-hour, one person covers almost every hour. A second person is needed only in the evening peaks, and a third only at Harbour on Tuesday at 9pm from August **[ESTIMATED]**.

A rota built from the forecast needs **389 staff-hours a week in October**, against 714 for two people on every shift. If Stories runs two people all day today and one person may legally run a quiet hour, that's worth about **$67k a year** at $4 an hour, while losing under 1% of customers to queues **[ESTIMATED]**. If two people must always be present, the saving disappears. Then the forecast's value is timing the extra evening staff at Harbour, which costs about $50 a week in lost profit if skipped **[ESTIMATED]**.

---

## 1. The business problem

Stories pays staff by the hour, but customers don't arrive evenly. Mornings are nearly empty and Tuesday evenings are packed. Too many staff in quiet hours wastes wages; too few in rush hours loses customers who won't wait. The decision is **how many people to schedule in each hour at each branch**, now and as the business grows.

To make that decision, Stories needs:
1. A forecast of customers per branch per hour, tested on data it never saw (§2–§5).
2. A rule that turns customers into staff, with its costs and tradeoffs (§6).
3. A clear statement of which assumptions would change the answer (§7).

## 2. What the model does

The model counts receipts per branch per hour. It treats each hour as the product of four things:
- how busy the branch is;
- how busy that weekday is;
- how busy that hour is at that branch;
- steady growth since January.

It uses nothing else, so it can look months ahead. It's a Poisson regression, a standard model for counts. It learned 58 numbers, listed in `model_coefficients.csv`.

## 3. How we tested it

### The split

| Round | Fit on | Scored on | Purpose |
|---|---|---|---|
| 1 | Jan–Apr | May | choose settings for every model |
| 2 | Jan–May (settings frozen) | **June, used once** | final accuracy |
| Horizon test | Jan–Feb, Jan–Mar, Jan–Apr, Jan–May (settings frozen) | the 1–4 months after each | how far ahead one forecast stays accurate |
| 3 | Jan–Jun | (nothing left) | the Jul–Oct forecast |

- Every June forecast, including the baselines, was made **as if on May 31**, up to 30 days ahead.
- The script checks that no model saw June data before the June test.

### The noise limit

At 2–7 visits an hour, chance alone makes single hours hard to predict. A model that knew the true average of every hour would still be off by **35.8%** per hour in June **[MEASURED]**:
- Harbour **30.4%**, Garden **36.6%**, Uptown **48.2%**;
- **28.1%** in the 19:00–22:59 peak.

### Results on June [MEASURED]

| Forecast | Hourly error | Avg miss (visits/hr) | Peak 19–23h error | Weekly total error | Daily total error | Bias | Avoidable error removed* |
|---|---|---|---|---|---|---|---|
| **M1 Poisson regression (chosen)** | **35.8%** | **1.62** | **30.0%** | **3.4%** | **8.8%** | **+0.4%** | **99.6%** |
| M2 gradient boosting (ML) | 35.9% | 1.62 | 29.8% | 3.9% | 9.2% | −3.0% | 98.7% |
| M2b ML with M1's growth trend | 36.0% | 1.62 | 30.2% | 3.5% | 9.0% | +0.4% | 97.7% |
| B1 same as last week | 48.9% | 2.21 | 39.6% | 3.3% | 11.6% | −3.7% | <0 |
| B2 average of last 4 weeks | 39.2% | 1.77 | 31.3% | 6.2% | 11.5% | −7.5% | 51.1% |
| B3 average for that hour, Jan–May | 42.8% | 1.93 | 37.1% | 20.0% | 26.4% | −22.4% | 0 (reference) |
| *Noise limit* | *35.8%* | | *28.1%* | | | | *100%* |

\*How much of the gap between B3 and the noise limit a forecast closes. Rolling versions of B1 and B2, which see actual June data up to a week before each day, scored 49.6% and 39.6% (`backtest.csv`).

**What the table shows:**
- **Hourly:** M1 is at the noise limit, so no hourly model can do much better with this data.
- **Weekly:** M1 misses each branch's weekly total by 3.4%. "Same as last week" matches it on weekly totals (3.3%) but is 13 points worse per hour.
- **Busiest hour:** M1 picks each day's busiest hour exactly on **57.8%** of branch-days, and within ±1 hour on **91.1%**. A model that knew the true averages would expect 55.8% and 87.2%.
- **Ranges:** the 80% and 95% ranges held **87.4%** and **97.3%** of June's hours. They're slightly wide because whole-number counts can't hit 80% exactly. Variance ≈ mean (dispersion 1.01–1.04), so Poisson ranges are valid.
- **Choosing busy hours fairly:** on the 10% of June hours that turned out busiest, M1 under-predicted by 21.5%. Picking hours by their actual counts selects the lucky ones. On the 10% of hours M1 *expected* to be busiest, its bias was +3.3%.

### Model choice

ML would only be used if it beat M1's hourly error by at least 1 point. It was 0.06 points worse, so **M1 is used [MEASURED]**:
- M2 can't extend the growth trend. Its weekly error rose to 9.7% at the end of June, against 2.4% for M1.
- M2b, given M1's trend, still tied with M1. There is no hourly pattern left for ML to find.

Model versions rejected on May (lower deviance is better):

| Version | Deviance | Why it lost |
|---|---|---|
| A separate weekday effect for every hour | 1.118 against 1.102 | The extra detail only fitted noise; Tuesday's effect is the same at every hour. |
| Separate growth per branch | 1.118 | No better; growth is the same at all three. |
| Slowing (log) growth | 1.162 | Under-predicted May by 10%. |

### How far ahead one forecast stays accurate [MEASURED]

| Months ahead | Tests | Branch-weeks scored | Weekly total error | Bias |
|---|---|---|---|---|
| 1 | 4 | 51 | 4.1% | −0.3% |
| 2 | 3 | 36 | 3.2% | +0.5% |
| 3 | 2 | 24 | 3.6% | +0.9% |
| 4 | 1 | 12 | 2.9% | −0.3% |

Accuracy doesn't worsen up to 4 months, so the report gives **one forecast for July–October**. It gives none beyond October, because nothing past 4 months could be tested. The 4-month figure rests on one test (`horizon_test.csv`).

## 4. Busiest hours, next 4 weeks (Jul 1–28) [ESTIMATED]

The top 3 hours are the same every day: **21:00, then 20:00 and 22:00**. Each cell gives expected visits at 21:00, with an 80% range for a single such hour in brackets.

| Weekday | Harbour | Garden | Uptown |
|---|---|---|---|
| Mon | 14.1 (10–19) | 9.8 (6–14) | 5.6 (3–9) |
| **Tue** | **22.5 (16–29)** | **15.6 (10–20)** | **9.0 (5–13)** |
| Wed | 14.6 (10–20) | 10.1 (6–14) | 5.8 (3–9) |
| Thu | 14.3 (9–19) | 9.9 (6–14) | 5.7 (3–9) |
| Fri | 15.6 (11–21) | 10.8 (7–15) | 6.3 (3–9) |
| Sat | 10.2 (6–14) | 7.0 (4–10) | 4.1 (2–7) |
| Sun | 12.3 (8–17) | 8.5 (5–13) | 4.9 (2–8) |

Every branch × month × weekday × hour for July–October is in `forecast_heatmap.csv`, with expected, 80%-high and 95%-high values.

## 5. Forecast, July–October 2026 [ESTIMATED: tested range, see §3]

The forecast assumes growth continues at the January–June rate of **+1.9% a week**. That was +62% from Jan 1 to Jun 30 on the model's trend, and +57% in raw monthly averages **[MEASURED]**.

| Customers per week | Harbour | Garden | Uptown | All three |
|---|---|---|---|---|
| Jul | 832 | 569 | 326 | 1,727 |
| Aug | 904 | 618 | 354 | 1,876 |
| Sep | 982 | 671 | 384 | 2,036 |
| **Oct** | **1,066** | **728** | **417** | **2,211 (+28%)** |

| Busiest hour (Tue 21:00) | Jul | Aug | Sep | Oct |
|---|---|---|---|---|
| Harbour, expected (one such hour, 80%) | 22.5 (17–29) | 24.3 (18–31) | 26.5 (20–33) | **28.8 (22–36)** |
| Garden | 15.6 (10–21) | 16.8 (12–22) | 18.3 (13–24) | **19.9 (14–26)** |
| Uptown | 9.0 (5–13) | 9.7 (6–14) | 10.6 (7–15) | **11.5 (7–16)** |

Uncertainty in the growth estimate adds only about ±1.2 visits to Harbour's October value; most of the spread in a single hour is chance. The first month each busiest hour passes 10/15/20/25/30 visits is in `thresholds.csv`. For example, Harbour passes 25 in September, and Uptown passes 10 in September.

## 6. The decision: a staffing rota built from the forecast

### Method

For every branch, month, weekday and hour, choose the number of staff *k* that minimises:

> wage × *k* + (profit per customer) × (share who leave) × (expected customers above *k* × 12)

The expected number above capacity comes from the forecast's Poisson distribution, so the busy-day tail counts and not just the average.

| Input | Value | Type |
|---|---|---|
| Customers one staff member serves per hour | **12** | ASSUMPTION (team) |
| Wage, fully loaded | **$4 per staff-hour** | ASSUMPTION (Lebanon's minimum wage is about $1.5–3/h; $4 adds allowances and social security) |
| Share of over-capacity customers who leave | **50%** | ASSUMPTION |
| Minimum staff on the floor | **1** | ASSUMPTION (changes the answer; see §7) |
| Gross profit per receipt | **$5.97 Harbour, $4.18 Garden, $5.45 Uptown** | MEASURED |

### The October rota [ESTIMATED] (chart 3, `staffing_plan.csv`)

- **Uptown:** 1 person every hour, all week. Even its busiest hour (11.5 expected) fits one person's capacity.
- **Garden:** 1 person, plus a second on Tuesday 20:00–22:59 and on Wednesday and Friday at 21:00.
- **Harbour:** 1 person in the mornings. A second on Tuesday 13:00–22:59, on Monday–Friday evenings (about 20:00–22:59), and at the weekend around 21:00. **A third at Tuesday 21:00, from August.**
- In October, 39% of all staff-hours fall after 6pm.

### Costs, value and tradeoffs: weekly totals for all three branches, October [ESTIMATED]

| Plan | Staff-hours | Wages | Customers lost to queues | Profit lost | Total |
|---|---|---|---|---|---|
| **Forecast-based (cost-optimal)** | **389** | **$1,556** | **17.3 (0.8%)** | **$91** | **$1,647** |
| Staff to the forecast average (simple rule) | 392 | $1,568 | 14.8 | $81 | $1,649 |
| Fixed crew of 2, every hour | 714 | $2,856 | 4.7 | $27 | $2,883 |
| Fixed crew sized for each branch's peak | 1,071 | $4,284 | 0.0 | $0 | $4,284 |

- **The tradeoff:** compared with two people all day, the forecast rota accepts about 13 more lost customers a week ($64 of profit) in exchange for 325 fewer staff-hours ($1,300 of wages). In the morning, 1–2 customers an hour don't justify a second person.
- **Value against two people all day:** about **$66.7k a year** (17,485 staff-hours) **[ESTIMATED]**. Where the hours come from in October:

  | Time of day | Forecast rota (staff-hours/week) | Two people all day |
  |---|---|---|
  | 07–10 | 63 | 126 |
  | 10–18 | 173 | 336 |
  | 18–24 | 153 | 252 |

  This value assumes Stories' current rota is two people all day. We don't know the real rota.
- **A simple rule works:** "staff = forecast average ÷ 12, rounded up" is within $2 a week of the optimum. Stories doesn't need the optimiser to use the forecast.
- **Value of updating for growth:** keeping July's rota into October loses about **20 extra customers a week at Harbour ($50/week)** and 6 at Garden ($8/week), and nothing at Uptown. The growth-driven change is small: **+17 staff-hours a week at Harbour by October**, +4 at Garden, 0 at Uptown.
- **Hiring:** no new full-time hire is needed before November. Harbour needs extra **evening** hours, mainly Tuesday, then Friday.

## 7. Assumptions that could change the decision

`staffing_sensitivity.csv` reruns the whole decision with each assumption changed:

| Assumption changed | Staff-hours/week, Jul → Oct | Extra Harbour hours by Oct | Customers lost, Oct | Does the decision change? |
|---|---|---|---|---|
| Base case (12/h, $4, 50% leave, min 1) | 368 → 389 | +17 | 0.8% | — |
| Capacity 8 per hour | 402 → 434 | +21 | 2.3% | More evening staff; same pattern |
| Capacity 10 | 380 → 405 | +19 | 1.3% | No |
| Capacity 15 | 362 → 370 | +7 | 0.5% | Barely any growth hires |
| Capacity 20 | 358 → 361 | +3 | 0.2% | No extra staff needed until November |
| Wage $2 / $3 | 379 → 402 / 371 → 397 | +17 / +18 | 0.4–0.5% | No |
| Wage $6 / $8 | 366 → 380 / 365 → 374 | +12 / +9 | 1.1–1.5% | Leaner; accept a few more lost customers |
| 25% / 75% / 100% of over-capacity customers leave | 365→374 / 374→398 / 379→402 | +9 / +17 / +17 | 0.7–0.9% | No |
| **Minimum crew of 2** | **714 → 715** | **+1** | 0.1% | **Yes: the saving disappears.** Two people cover every hour except Harbour's Tuesday 21:00. |

**The decision holds** for any capacity from 10 to 20, any wage from $2 to $8, and any walk-away rate. **It depends on the minimum crew.** The second biggest factor is capacity: below about 10 customers an hour, Harbour's evenings need noticeably more people.

## 8. Alternative explanations checked

- **Is the growth real demand, or bigger baskets?** Spend per receipt (about $9.0) and items per receipt (about 1.59) stayed flat from January to June **[MEASURED]**. The growth is more customers, and it is the same at all three branches. The data doesn't say why: marketing, a delivery app or a new neighbourhood would all look the same. The forecast only needs the growth to continue, and §14 shows how to catch it if it stops.
- **Are evenings already at capacity?**
  - Evening hours (19–23h) grew more slowly than daytime: Harbour +51% against +66%, Garden +52% against +57%, Uptown +49% against +54% **[MEASURED]**.
  - In a model with separate growth, evening growth is 1.7% a week against 2.0% for daytime (p = 0.07, borderline).
  - In every past test the model over-predicted evenings by 0.4–4.7% and under-predicted daytime by about 2% **[MEASURED]**.

  There are two explanations:
  - (a) Queues are already turning evening customers away, which would mean demand is higher than receipts show and **more** evening staff would raise sales.
  - (b) Daytime customers are simply growing faster.

  Note that the busiest single hour, Tuesday 21:00, grew as fast as everything else (+58% against +56%), which argues against a hard ceiling. The pilot in §10 separates (a) from (b).
- **Why Tuesday?** Tuesday is 1.52× a normal weekday and Saturday is 0.69× (95% CIs 1.48–1.56 and 0.67–0.72) **[ESTIMATED: model]**. The effect is identical at every branch and hour. That pattern is a correlation with the day, not a known cause. The rota should follow it, but no promotion should be planned on a guessed cause until Stories confirms what happens on Tuesdays.
- **Holidays and Ramadan:** over Ramadan, visits were 1.01× the model's expectation. Single holidays ranged from 0.85× to 1.18×, within the normal day-to-day spread (standard deviation ±7.4%) **[MEASURED]**.
- **Receipts aren't people:** a group paying together counts once. For staffing the till and the bar, receipts are the right unit. For seating, they understate headcount.

## 9. Alternative decisions considered and rejected

| Option | Why rejected |
|---|---|
| Hire now for growth | July needs the same staff as June; extra need builds slowly and only in the evenings. |
| Fixed crews (2 all day, or peak-sized) | 325–682 more staff-hours a week for a handful of saved customers (§6). |
| Staff to the 95% high every hour | Pays for rare spikes every single hour; the cost-optimal rule already weighs the tail against the wage. |
| Three growth scenarios to December | Replaced by one forecast tested up to 4 months ahead, refreshed monthly. Beyond 4 months, nothing could be tested. |
| ML model (gradient boosting) | Tied with the simpler model; can't extend the growth trend (§3). |
| Lag features ("visits last hour") | Don't exist months ahead. |
| Change opening hours | Mornings are quiet (07–10h is about 10% of customers), but judging that needs rent and fixed costs per hour, which we don't have. |

## 10. A practical test before wider use

1. **Capacity study (1 week, Harbour):** time how many orders one barista completes in a busy hour. This replaces the 12-per-hour assumption, the input the decision is most sensitive to after the minimum crew.
2. **Rota pilot (4 weeks):**
   - **Setup:** Harbour runs the forecast rota; Garden keeps its current rota as the comparison.
   - **Measure:** staff-hours, receipts per hour against the forecast's 80% range, and walk-outs counted by staff on Tuesday and Friday 19–23h.
   - **Adopt if:** staff-hours fall while Harbour's sales stay in line with Garden's trend (a difference-in-differences).
   - **Bonus:** a temporary extra evening person tests §8(a). If evening sales rise above forecast, demand was being turned away.
3. **Rules:** confirm whether one person may run a branch alone. This is the assumption that decides whether the rota saves money (§7).

## 11. Assumptions, separated from facts

| Measured facts | Assumptions |
|---|---|
| Visits per branch × hour, Jan–Jun; growth +57%; Tuesday ×1.5, Saturday ×0.7 | 1 receipt = 1 customer visit |
| Test accuracy (June; 1–4 months ahead) | Growth continues at the Jan–Jun rate to October |
| Gross profit per receipt by branch | 12 customers per staff-hour |
| Busiest hour: Tuesday 21:00 at every branch | $4 per staff-hour; 50% of over-capacity customers leave; minimum crew of 1 |
| | Stories' current rota (two people all day) for the $67k comparison |

## 12. Weak areas and possible failures

- **Only 6 months of data,** so there's no yearly seasonality (summer, holidays). The forecast could miss a seasonal swing.
- **The test evidence is thin at long range:** the 4-month accuracy rests on one test, and the 1–3-month figures on 2–4 tests.
- **The forecast slightly overstates evenings** (0.4–4.7% in past tests) and understates daytime by about 2% (§8). Erring towards more evening staff is the safer direction.
- **Capacity, current staffing and labour rules are unknown,** and they decide the size of the saving.
- **Receipts can't show customers turned away,** so true evening demand may be higher than recorded.
- **Data quality:**
  - The Tuesday effect is perfectly uniform, customer IDs look randomly assigned, and transaction IDs aren't in time order.
  - These may come from anonymisation. If parts of the data were generated, the patterns describe the generator.

## 13. Missing information

- Real service capacity per barista
- Current rota and wages
- Labour rules on lone working
- Wait times and walk-outs
- Rent and fixed costs per hour
- Holiday and event calendar
- What happens on Tuesdays

## 14. Keeping the forecast honest

- **Weekly:** compare actual customers per branch with the forecast. Several weeks off by more than about 4% means the trend has changed.
- **Monthly:** refit on all data, roll the forecast 4 months ahead, and rebuild the rota with `staffing.py`. Check that about 20% of hours fall outside the 80% range.

## 15. How to reproduce

```bash
pip install -r requirements.txt
python forecast.py      # clean -> model -> tests -> forecast (about 20 s)
python staffing.py      # rota, costs, sensitivity (about 5 s)
```

Then open `app/index.html` in a browser to explore any branch and day, including staff needed per hour.

| Output | Content |
|---|---|
| `backtest.csv`, `tuning_may.csv`, `horizon_test.csv` | all test results |
| `forecast_heatmap.csv`, `busiest_hours_july.csv`, `peak_forecast.csv`, `thresholds.csv` | the Jul–Oct forecast |
| `staffing_plan.csv`, `staffing_summary.csv`, `staffing_sensitivity.csv`, `staffing_numbers.json` | the staffing decision |
| `model.json`, `model_coefficients.csv`, `key_numbers.json` | the trained model and every forecast number |
| `chart1_june_fit.png`, `chart2_peak_forecast.png`, `chart3_staffing_october.png` | charts |
