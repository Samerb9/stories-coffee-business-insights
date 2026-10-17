"""Flag numbers in README.md that don't appear in outputs/key_numbers.json (rule R11).

    python -m src.check_numbers

It's a helper, not a judge: it lists numeric tokens in the README (like $15.9K, 46.9%, 1.43x)
whose text doesn't match any recorded `display` value. Each one should either be recorded by
a script or be harmless (a date, a section number).
"""
import json
import re

from .config import KEY_NUMBERS, ROOT

TOKEN = re.compile(r"(?<![A-Za-z\d])\$?\d[\d,]*\.?\d*\s?(?:%|K|M|×|x|pts)?")
IGNORE = re.compile(r"^(?:20\d\d|\d{1,2})$")  # years, small list/section numbers


def main():
    readme = (ROOT / "README.md").read_text()
    readme = re.sub(r"```.*?```", "", readme, flags=re.S)        # skip code blocks
    readme = re.sub(r"<[^>\n]*>", "", readme)                     # skip <placeholders> and HTML
    readme = re.sub(r"(?m)^#.*$", "", readme)                       # skip headings
    readme = re.sub(r"\bA\d+\b|\bF\d+\b|\bD\d+\b|§\d+", "", readme)  # skip IDs like A6, F2, D1
    displays = {v["display"].replace(" ", "") for v in json.loads(KEY_NUMBERS.read_text()).values()}
    unmatched = []
    for tok in TOKEN.findall(readme):
        t = tok.strip().replace(" ", "").rstrip(".,")
        if IGNORE.match(t) or t in displays:
            continue
        unmatched.append(t)
    if unmatched:
        print("Numbers in README not found in key_numbers.json (record them or confirm harmless):")
        for t in sorted(set(unmatched)):
            print("  ", t)
    else:
        print("All README numbers trace to key_numbers.json")


if __name__ == "__main__":
    main()
