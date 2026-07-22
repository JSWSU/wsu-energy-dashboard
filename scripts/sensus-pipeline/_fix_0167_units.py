"""0167 unit correction (07/22/2026): John confirmed the 0167 Neptune register
reads GALLONS. The SkySpark point tag says ft3, so the ByMeter fold-in had
multiplied its values by 7.48051948. Divide every 0167 byMeter row back to
gallons. Idempotent via the unitCorrected tag.

The SkySpark point tag itself (unit on @p:wsumeters:r:29d6499f-4f364ca3) still
needs fixing on the SkySpark side or its reports stay inflated.
"""
import json
import shutil
from datetime import datetime
from pathlib import Path

DATA = Path(r"C:\Users\john.slagboom\Desktop\Git\data")
FT3 = 7.48051948
TARGET_METERS = {"0167_DW_001 (CSV)"}


def write_grid(path, grid):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("{\n")
        f.write('"_kind": "grid",\n')
        f.write('"meta": ' + json.dumps(grid["meta"], ensure_ascii=False) + ",\n")
        f.write('"cols": [\n')
        cols = grid["cols"]
        for i, col in enumerate(cols):
            f.write(json.dumps(col, ensure_ascii=False) + ("," if i < len(cols) - 1 else "") + "\n")
        f.write("],\n")
        f.write('"rows":[\n')
        rows = grid["rows"]
        for i, row in enumerate(rows):
            f.write(json.dumps(row, ensure_ascii=False, separators=(", ", ":")) + ("," if i < len(rows) - 1 else "") + "\n")
        f.write("]\n}\n")


def main():
    path = DATA / "domestic_water.json"
    grid = json.load(open(path, encoding="utf-8"))
    shutil.copy2(path, path.with_suffix(f".json.unit0167.{datetime.now():%Y%m%dT%H%M%S}.bak"))
    fixed = 0
    for r in grid["rows"]:
        if (r.get("byMeter") and r.get("meters") in TARGET_METERS
                and not r.get("unitCorrected") and isinstance(r.get("usage"), (int, float))):
            r["usage"] = r["usage"] / FT3
            r["unitCorrected"] = True
            fixed += 1
    write_grid(path, grid)
    print(f"0167 byMeter rows corrected ft3->gal: {fixed}")


if __name__ == "__main__":
    main()
