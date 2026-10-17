# Idea 3: Are Stories' opening hours right?

**Team:** Christopher Ferzli, Samer Bannout

## Conclusion

**Don't close any branch earlier, but do test staying open later at Harbour.** Profit per customer is the same at every hour, so an hour is worth keeping when it brings enough customers. With the visit forecast for October, every evening hour earns **1.5–22× the roughly $8 it costs to stay open**. Only 11 of 357 branch-hours a week fall below that cost, all early mornings at Uptown and on Garden's weekends. Opening Uptown at 8:00 instead of 7:00 saves under **$1.3k a year**, and is worth doing only if an open hour really costs $10 or more.

The real opportunity is at the other end of the day. Orders stay flat in every 10-minute block right up to 23:59. Staying open until 01:00 at Harbour pays off if the extra hour brings just **12–25% of the 11pm hour's profit**, worth roughly **$1.3k–9.6k a year**. No data exists after midnight, so no model can predict it: a 6-week pilot on Harbour's Tuesday, Wednesday and Friday nights is the way to find out.

Tested on June, a month it never saw: hours chosen with our forecast delivered **4× the value** of hours chosen from plain averages ($156 against $37), because the averages ignored growth.

![Profit per open hour](outputs/chart_hours_october.png)

**Full write-up:** [report.md](report.md), with method, the June test, assumptions that change the decision, alternative explanations, the pilot design and weak areas.

## Run

Run [`../1-ml-staffing-forecast`](../1-ml-staffing-forecast) first (this idea uses its forecast), then:

```bash
python hours.py
```
