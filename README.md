# stories-coffee-business-insights

**EECE490 Stories Coffee Hackathon**

**Team:** Christopher Ferzli, Samer Bannout

Transaction data analysis for the EECE490 Stories Coffee Hackathon, exploring profitability, customer behavior, and sales patterns to develop evidence-based business recommendations.

## Conclusion

Stories' customer flow is very predictable. Our model forecasts each branch's weekly customers within **3–4%** up to 4 months ahead, tested on months it never saw. Half of all customers arrive after 6pm, and Tuesday brings 1.5× a normal day. At 12 customers per staff-hour, one person covers almost every hour; a second is needed only in evening peaks, and a third only at Harbour on Tuesday at 9pm from August.

A rota built from the forecast needs **389 staff-hours a week in October**, against 714 for two people on every shift. That's worth about **$67k a year** at $4 an hour while losing under 1% of customers to queues, provided one person may run a quiet hour. If two people must always be present, the saving disappears, and the forecast's value is timing Harbour's extra evening staff.

Separately, Garden's recorded unit costs are exactly **1.43× Harbour's on all 45 products**, even bottled water. Either Garden overpays about **$32k a year**, or a cost-allocation error understates its margin (47% recorded, about 63% at Harbour's costs). One month of supplier invoices would tell which.

**Full analysis, code and evidence:** [`staffing-forecast/`](staffing-forecast/). Start with its [report](staffing-forecast/forecast_report.md), which covers tests against baselines, assumptions that change the decision, alternative explanations, and a pilot Stories can run.

## Repository layout

| Folder | Contents |
|---|---|
| [`staffing-forecast/`](staffing-forecast/) | Hourly customer forecast, staffing decision, Garden cost finding, browser app |
| [`stories-hackathon-starter/`](stories-hackathon-starter/) | Project plan and analysis scaffold |
