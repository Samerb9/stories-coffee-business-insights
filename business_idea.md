# Habit-building promotions: judge discounts over eight weeks, not two

## Conclusion
Harbour's one-week, 15% discount on cold coffee and desserts looked like a small loss when it was judged on the promotion week and the week or two after. Once the discount ended, though, Harbour kept selling about 15% more of those items than the other branches did, for three months. Measured that way, the $470 discount brought in between $971 and $1,737 of extra gross profit. The evidence is strong but not conclusive. We recommend that Stories run one randomised test costing about $500 and follow it for eight weeks before it changes how it judges promotions.

## Evidence
We compared Harbour with Garden and Uptown over the same days, before the first promotion (January 1 to March 11) and after it (March 20 to June 30). Comparing branches on the same days takes out overall growth, the weekly pattern, and anything else that affected all three branches together. After the promotion, Harbour's cold coffee and dessert sales were 15.0% higher than expected. Its sales of every other item didn't change. In other words, customers added these items to what they already bought rather than swapping something out for them.

![Week by week](../outputs/figures/f2b_promo_habit_event_study.png)

The timing matches the promotion. Before March, Harbour sat above the other branches in 5 of 10 weeks, which is what chance alone would give. After the first promotion it sat above them in all 14 weeks, and the gap didn't shrink.

![Chance](../outputs/figures/f2b_promo_habit_chance.png)

## Value and the main caveat
The value is an estimate, not a measurement. The extra profit depends on which branch Harbour is compared with. Against both branches together it's $1,737. Against Garden alone it's a more cautious $971. Either way it exceeds the $470 discount, and it was still adding about $128 a week in June.

![Money](../outputs/figures/f2b_promo_habit_money.png)

The main weakness is that Uptown's sales of these items fell over the same months. Against Uptown alone, Harbour's lift is a clear 23%. Against Garden alone it's 8%, and that could be chance. We also assume that no other marketing ran at Harbour from March onwards. We can't confirm that the same customers kept returning, because the customer IDs in the data carry no usable signal.

## Recommended test
Pick one branch at random and give it a week of 15% off cold coffee and desserts, with the other two branches as the comparison. Track all three for eight weeks after the offer ends. Treat the promotion as successful if the lift stays clearly above zero and the extra profit over those eight weeks is larger than the discount. If the result holds, repeat the test at a second branch. If it doesn't, keep judging promotions on short-term break-even only.

*Full analysis: [`f2b_promo_habit.md`](03_findings/f2b_promo_habit.md) · Code: `src/f2b_promo_habit.py`*
