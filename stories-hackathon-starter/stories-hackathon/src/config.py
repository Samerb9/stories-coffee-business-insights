"""Shared constants. Import from here; never hard-code paths or seeds elsewhere."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_CSV = ROOT / "data" / "raw" / "stories_transactions.csv"
PROCESSED = ROOT / "data" / "processed"
LINES_CSV = PROCESSED / "lines.csv"            # one row per product line (deduplicated)
TX_CSV = PROCESSED / "transactions.csv"        # one row per receipt
TABLES = ROOT / "outputs" / "tables"
FIGURES = ROOT / "outputs" / "figures"
NUMBERS_DIR = ROOT / "outputs" / "numbers"     # one JSON per module (avoids merge conflicts)
KEY_NUMBERS = ROOT / "outputs" / "key_numbers.json"  # merged by run_all; README quotes this

SEED = 490
BRANCHES = ["Harbour", "Garden", "Uptown"]
DRINK_CATEGORIES = {"Hot Coffee", "Cold Coffee", "Matcha & Tea", "Cold Drinks"}

# Raw column name -> short name used in code
COLUMNS = {
    "Transaction ID": "tid",
    "Date": "date",
    "Time": "time",
    "Branch": "branch",
    "Customer ID": "cust",
    "Order Type": "otype",
    "Product": "product",
    "Category": "cat",
    "Quantity": "qty",
    "Unit Price (USD)": "price",
    "Discount Rate": "disc",
    "Unit Cost (USD)": "cost",
    "Line Revenue (USD)": "rev",
    "Line Gross Profit (USD)": "gp",
}

for p in (PROCESSED, TABLES, FIGURES, NUMBERS_DIR):
    p.mkdir(parents=True, exist_ok=True)
