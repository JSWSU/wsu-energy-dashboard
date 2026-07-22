"""Unit corrections for field/tablet-confirmed meters (07/22/2026, John).

Confirmed GALLONS x1 (SkySpark ft3 tag wrong; divide byMeter rows by 7.48051948):
0016, 0098, 0109B, 0115, 0136, 0141G, 0141H, 0160A, 0167, 0169, 0180,
0183, 0198A, 0358C, 0817A, 0837.

Confirmed CUBIC FEET (SkySpark tag RIGHT, workbook 'Gal' wrong): 0182 — no
dashboard change; its ft3 x 7.48 conversion stands.

Still unverified (unchanged): 0062, 0120C, 0135, 0165D, 0358E, 0372G x2, 0860 x2.

Idempotent via the unitCorrected tag (rows already fixed, e.g. 0167, skip).
"""
import json
import shutil
from datetime import datetime
from pathlib import Path

DATA = Path(r"C:\Users\john.slagboom\Desktop\Git\data")
FT3 = 7.48051948
CONFIRMED_GALLONS = {
    "0016_DW_001 (CSV)", "0098_DW_001 (CSV)", "0109BDW_001 (CSV)",
    "0115_DW_001 (CSV)", "0136_DW_001 (CSV)", "0141GDW_001 (CSV)",
    "0141HDW_001 (CSV)", "0160ADW_001 (CSV)", "0167_DW_001 (CSV)",
    "0169_DW_001 (CSV)", "0180_DW_001 (CSV)", "0183_DW_001 (CSV)",
    "0198ADW_001 (CSV)", "0358CDW_001 (CSV Zero)", "0817ADW_001 (CSV)",
    "0837_DW_001 (CSV Zero)",
}


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
    shutil.copy2(path, path.with_suffix(f".json.unitsfix.{datetime.now():%Y%m%dT%H%M%S}.bak"))
    per_meter = {}
    for r in grid["rows"]:
        if (r.get("byMeter") and r.get("meters") in CONFIRMED_GALLONS
                and not r.get("unitCorrected") and isinstance(r.get("usage"), (int, float))):
            r["usage"] = r["usage"] / FT3
            r["unitCorrected"] = True
            per_meter[r["meters"]] = per_meter.get(r["meters"], 0) + 1
    write_grid(path, grid)
    total = sum(per_meter.values())
    print(f"corrected {total} rows across {len(per_meter)} meters:")
    for m in sorted(per_meter):
        print(f"   {m}: {per_meter[m]} rows")


if __name__ == "__main__":
    main()
