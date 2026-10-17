"""Record every headline number so the README can be checked against script output.

Usage inside an analysis module:

    from .numbers import Recorder
    rec = Recorder("f1_garden_cost")
    rec.record("garden_gm", 0.469, "MEASURED", display="46.9%", note="Jan-Jun 2026 gross margin")
    rec.save()

Each module writes outputs/numbers/<module>.json (so two people never edit the same file).
`merge()` (called by run_all) combines them into outputs/key_numbers.json.
"""
import json

from .config import KEY_NUMBERS, NUMBERS_DIR

VALID_TAGS = {"MEASURED", "ESTIMATED", "ASSUMPTION"}


class Recorder:
    def __init__(self, module: str):
        self.module = module
        self.items: dict = {}

    def record(self, key, value, tag, display=None, note=""):
        if tag not in VALID_TAGS:
            raise ValueError(f"tag must be one of {VALID_TAGS}, got {tag!r}")
        if hasattr(value, "item"):  # numpy scalar -> python
            value = value.item()
        self.items[key] = {
            "value": value,
            "tag": tag,
            "display": display if display is not None else str(value),
            "note": note,
            "source": f"src/{self.module}.py",
        }
        return value

    def save(self):
        path = NUMBERS_DIR / f"{self.module}.json"
        path.write_text(json.dumps(self.items, indent=2, ensure_ascii=False))
        return path


def merge():
    merged = {}
    for f in sorted(NUMBERS_DIR.glob("*.json")):
        module = f.stem
        for k, v in json.loads(f.read_text()).items():
            merged[f"{module}.{k}"] = v
    KEY_NUMBERS.write_text(json.dumps(merged, indent=2, ensure_ascii=False))
    return merged
