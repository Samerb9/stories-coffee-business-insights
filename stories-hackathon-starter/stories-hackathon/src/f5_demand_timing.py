"""F5: Tuesday + evening demand -> staffing/prep.

Owner: Person A   (see AGENTS.md section 11 for the team split)
Spec:  AGENTS.md section 7 (F5)   Write-up: docs/03_findings/f5_demand_timing.md

Steps:
  1. tx/day by weekday x branch with CIs; stability by month
  2. Hour x category profile; peak-hour load (tx at 21:00) by branch x weekday
  3. Optional model (Phase 6): train Jan-Apr, validate May, TEST June; seasonal-naive + weekday-mean baselines; MAE/MAPE

Outputs: outputs/tables/f5_demand_timing_*.csv, outputs/figures/f5_demand_timing_*.png, outputs/numbers/f5_demand_timing.json
"""
from .config import FIGURES, SEED, TABLES  # noqa: F401
from .load import lines, transactions  # noqa: F401
from .numbers import Recorder


def main():
    rec = Recorder("f5_demand_timing")
    # TODO(A): implement the steps above. Record every headline number with rec.record(...).
    print("  f5_demand_timing: TODO (not implemented yet)")
    rec.save()


if __name__ == "__main__":
    main()
