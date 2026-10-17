"""F3: Customer IDs carry no behavioural signal (null test).

Owner: Person B   (see AGENTS.md section 11 for the team split)
Spec:  AGENTS.md section 7 (F3)   Write-up: docs/03_findings/f3_customer_signal.md

Steps:
  1. Permutation tests (>=1000, SEED): branch loyalty, product/category repeat, H1-vs-H2 frequency and ticket persistence
  2. Known vs anonymous baskets/ticket/discount comparison
  3. Record observed vs null mean and empirical p-value for each test

Outputs: outputs/tables/f3_customer_signal_*.csv, outputs/figures/f3_customer_signal_*.png, outputs/numbers/f3_customer_signal.json
"""
from .config import FIGURES, SEED, TABLES  # noqa: F401
from .load import lines, transactions  # noqa: F401
from .numbers import Recorder


def main():
    rec = Recorder("f3_customer_signal")
    # TODO(B): implement the steps above. Record every headline number with rec.record(...).
    print("  f3_customer_signal: TODO (not implemented yet)")
    rec.save()


if __name__ == "__main__":
    main()
