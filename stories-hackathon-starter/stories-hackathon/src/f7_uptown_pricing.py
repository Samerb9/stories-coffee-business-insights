"""F7: Uptown price level = testable opportunity (no elasticity estimate).

Owner: Person A   (see AGENTS.md section 11 for the team split)
Spec:  AGENTS.md section 7 (F7)   Write-up: docs/03_findings/f7_uptown_pricing.md

Steps:
  1. Show relative prices identical across branches and constant over time (why elasticity is not identifiable)
  2. Scenarios: Uptown to Garden level and to Harbour level; GP gain if volume holds; break-even volume loss
  3. Record: uptown_price_gap_vs_harbour, gain_to_garden_level, breakeven_loss_garden_level, ...

Outputs: outputs/tables/f7_uptown_pricing_*.csv, outputs/figures/f7_uptown_pricing_*.png, outputs/numbers/f7_uptown_pricing.json
"""
from .config import FIGURES, SEED, TABLES  # noqa: F401
from .load import lines, transactions  # noqa: F401
from .numbers import Recorder


def main():
    rec = Recorder("f7_uptown_pricing")
    # TODO(A): implement the steps above. Record every headline number with rec.record(...).
    print("  f7_uptown_pricing: TODO (not implemented yet)")
    rec.save()


if __name__ == "__main__":
    main()
