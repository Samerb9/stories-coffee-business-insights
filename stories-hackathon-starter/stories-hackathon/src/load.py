"""Loading helpers. Every analysis script starts with `lines()` or `transactions()`."""
import pandas as pd

from .config import COLUMNS, LINES_CSV, RAW_CSV, TX_CSV


def raw() -> pd.DataFrame:
    """Raw file with short column names and parsed types. Read-only source of truth."""
    df = pd.read_csv(RAW_CSV, dtype={"Customer ID": "string"})
    missing = set(COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Raw file is missing expected columns: {missing}")
    df = df.rename(columns=COLUMNS)
    return add_time_fields(df)


def add_time_fields(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["d"] = pd.to_datetime(df["date"])
    df["dt"] = pd.to_datetime(df["date"] + " " + df["time"])
    df["hour"] = df["dt"].dt.hour
    df["dow"] = df["d"].dt.day_name().str[:3]
    df["month"] = df["d"].dt.month
    df["week"] = df["d"].dt.isocalendar().week.astype(int)
    return df


def lines() -> pd.DataFrame:
    """Clean line-level data (run `python -m src.clean` first)."""
    df = pd.read_csv(LINES_CSV, dtype={"cust": "string"})
    return add_time_fields(df.drop(columns=["d", "dt", "hour", "dow", "month", "week"], errors="ignore"))


def transactions() -> pd.DataFrame:
    """One row per receipt (run `python -m src.clean` first)."""
    tx = pd.read_csv(TX_CSV, dtype={"cust": "string"}, parse_dates=["d", "dt"])
    return tx
