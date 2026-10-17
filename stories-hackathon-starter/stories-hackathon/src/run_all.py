"""Run the whole pipeline in order:  python -m src.run_all

Each module exposes main(). Stubs that are not implemented yet print TODO and are skipped.
"""
import importlib
import time

from .numbers import merge

PIPELINE = [
    "audit", "clean",
    "f1_garden_cost", "f2_promo_eval", "f3_customer_signal",
    "f4_baskets", "f5_demand_timing", "f6_discount_policy", "f7_uptown_pricing",
    "value_model",
]


def main():
    for name in PIPELINE:
        t = time.time()
        mod = importlib.import_module(f"src.{name}")
        mod.main()
        print(f"  [{name}] {time.time() - t:.1f}s")
    merged = merge()
    print(f"key_numbers.json: {len(merged)} numbers")


if __name__ == "__main__":
    main()
