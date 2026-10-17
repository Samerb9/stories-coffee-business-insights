"""Phase 5: Value, costs, tradeoffs, sensitivity for all findings.

Owner: Person A   (see AGENTS.md section 11 for the team split)
Spec:  AGENTS.md section 7 (Phase 5)   Write-up: docs/03_findings/value_model.md

Steps:
  1. Read outputs/key_numbers.json inputs from each finding
  2. Low/base/high per finding; annualise on full-period average AND June run-rate
  3. Flip point per key assumption -> outputs/tables/value_summary.csv

Outputs: outputs/tables/value_model_*.csv, outputs/figures/value_model_*.png, outputs/numbers/value_model.json
"""
from .config import FIGURES, SEED, TABLES  # noqa: F401
from .load import lines, transactions  # noqa: F401
from .numbers import Recorder


def main():
    rec = Recorder("value_model")
    # TODO(A): implement the steps above. Record every headline number with rec.record(...).
    print("  value_model: TODO (not implemented yet)")
    rec.save()


if __name__ == "__main__":
    main()
