"""F2: Harbour 15% promotion did not pay back.

Owner: Person B   (see AGENTS.md section 11 for the team split)
Spec:  AGENTS.md section 7 (F2)   Write-up: docs/03_findings/f2_promo_eval.md

Steps:
  1. Derive promo SKUs + windows from disc == 0.15 lines (don't hard-code)
  2. DiD on daily log units of promo SKUs: Harbour vs Garden+Uptown, branch + date fixed effects, robust SE
  3. Each window separately + pooled; triple-diff vs non-promo SKUs; halo on other items/tx; 14-day post dip
  4. Placebo: many fake 8-day windows at Harbour outside promo -> distribution of estimates
  5. Break-even lift = d / (m - d) at Harbour list-price GM on promo SKUs
  6. Record: promo_lift, promo_lift_ci_low/high, breakeven_lift, placebo_pvalue, discount_given

Outputs: outputs/tables/f2_promo_eval_*.csv, outputs/figures/f2_promo_eval_*.png, outputs/numbers/f2_promo_eval.json
"""
from .config import FIGURES, SEED, TABLES  # noqa: F401
from .load import lines, transactions  # noqa: F401
from .numbers import Recorder


def main():
    rec = Recorder("f2_promo_eval")
    # TODO(B): implement the steps above. Record every headline number with rec.record(...).
    print("  f2_promo_eval: TODO (not implemented yet)")
    rec.save()


if __name__ == "__main__":
    main()
