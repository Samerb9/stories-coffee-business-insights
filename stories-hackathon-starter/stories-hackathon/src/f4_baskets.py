"""F4: Pairings and the food attach gap.

Owner: Person B   (see AGENTS.md section 11 for the team split)
Spec:  AGENTS.md section 7 (F4)   Write-up: docs/03_findings/f4_baskets.md

Steps:
  1. Lift + conditional prob within multi-item baskets only (trap T4), min n=25, bootstrap 95% CI
  2. Drink-category x food-category crosstab (chi-square); control for hour band
  3. Food attach rate by drink category / branch / hour band / order type
  4. Record: attach_rate_overall, attach_rate_by_drink_cat, top pairs with n and CI

Outputs: outputs/tables/f4_baskets_*.csv, outputs/figures/f4_baskets_*.png, outputs/numbers/f4_baskets.json
"""
from .config import FIGURES, SEED, TABLES  # noqa: F401
from .load import lines, transactions  # noqa: F401
from .numbers import Recorder


def main():
    rec = Recorder("f4_baskets")
    # TODO(B): implement the steps above. Record every headline number with rec.record(...).
    print("  f4_baskets: TODO (not implemented yet)")
    rec.save()


if __name__ == "__main__":
    main()
