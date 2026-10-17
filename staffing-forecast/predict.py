"""Load the trained model and predict visits for any branch, date and hour.

Example:  python predict.py --branch Harbour --date 2026-07-14 --hour 21
Run forecast.py first: it trains the model and writes outputs/model.json.
Dates after Jun 30, 2026 are forecasts; the model was tested up to 4 months ahead (Oct 31).
"""
import argparse
import json

import numpy as np
import pandas as pd
from scipy import stats

from forecast import BRANCHES, HOURS, design

ap = argparse.ArgumentParser()
ap.add_argument("--branch", required=True, choices=BRANCHES)
ap.add_argument("--date", required=True, help="YYYY-MM-DD")
ap.add_argument("--hour", required=True, type=int, choices=HOURS)
ap.add_argument("--model", default="outputs/model.json")
args = ap.parse_args()

m = json.load(open(args.model))
date = pd.Timestamp(args.date)
row = pd.DataFrame({"branch": [args.branch], "dow": [date.dayofweek], "hour": [args.hour],
                    "trend": [(date - pd.Timestamp(m["start_date"])).days]})
if date > pd.Timestamp("2026-10-31"):
    print("Note: beyond Oct 31, 2026 the forecast has not been tested (max tested: 4 months ahead).")
mu = float(np.exp(design(row, m["spec"]).values @ np.array(m["params"]))[0])
lo, hi = stats.poisson.ppf([0.1, 0.9], mu)
print(f"{args.branch}, {date:%a %d %b %Y}, {args.hour:02d}:00 -> expected {mu:.1f} visits "
      f"(80% range for this hour: {lo:.0f}-{hi:.0f})")
