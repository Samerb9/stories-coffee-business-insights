"""F1: Garden's unit costs ~1.43x Harbour's.

Owner: Person A   (see AGENTS.md section 11 for the team split)
Spec:  AGENTS.md section 7 (F1)   Write-up: docs/03_findings/f1_garden_cost.md

Steps:
  1. Per-product cost ratio Garden/Harbour and Uptown/Harbour; weekly stability
  2. Margin bridge Harbour -> Garden: swap mix, then price, then cost (GM pts and $)
  3. Excess cost $ = sum(Garden qty x (Garden cost - Harbour cost)); by category + top-10 SKUs
  4. Check interaction with Garden's dessert-heavy mix
  5. Record: garden_gm, harbour_gm, bridge_cost_pts, bridge_price_pts, bridge_mix_pts, excess_cost_6mo, excess_cost_june_runrate

Outputs: outputs/tables/f1_garden_cost_*.csv, outputs/figures/f1_garden_cost_*.png, outputs/numbers/f1_garden_cost.json
"""
from .config import FIGURES, SEED, TABLES  # noqa: F401
from .load import lines, transactions  # noqa: F401
from .numbers import Recorder


def main():
    rec = Recorder("f1_garden_cost")
    # TODO(A): implement the steps above. Record every headline number with rec.record(...).
    print("  f1_garden_cost: TODO (not implemented yet)")
    rec.save()


if __name__ == "__main__":
    main()
