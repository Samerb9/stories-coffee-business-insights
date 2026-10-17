"""F6: The 10% discount is untargeted.

Owner: Person B   (see AGENTS.md section 11 for the team split)
Spec:  AGENTS.md section 7 (F6)   Write-up: docs/03_findings/f6_discount_policy.md

Steps:
  1. Incidence of disc == 0.10 by category/hour/branch/basket size/customer type
  2. Basket size + ticket with vs without; total $ given
  3. Record: disc10_line_share, disc10_usd_6mo

Outputs: outputs/tables/f6_discount_policy_*.csv, outputs/figures/f6_discount_policy_*.png, outputs/numbers/f6_discount_policy.json
"""
from .config import FIGURES, SEED, TABLES  # noqa: F401
from .load import lines, transactions  # noqa: F401
from .numbers import Recorder


def main():
    rec = Recorder("f6_discount_policy")
    # TODO(B): implement the steps above. Record every headline number with rec.record(...).
    print("  f6_discount_policy: TODO (not implemented yet)")
    rec.save()


if __name__ == "__main__":
    main()
