"""Null any (bldg, service) row where value exceeds 20x its Jan-Oct 2025 median baseline.

Applies to all 5 metering JSON files. CSV importer row-shift bug can corrupt rows in any
metering file — this is a defensive sweep for anything obviously anomalous vs baseline.

Rules:
- Compute median of Jan-Oct 2025 positive values per (bldgNo, service, meters)
- For any row in Nov 2025 - Mar 2026 with value > 20 * median AND > 50k, null it
- Require median > 100 to avoid amplifying noise on near-zero baseline
- Require at least 4 baseline months to trust the median
"""
import json
import shutil
from datetime import datetime
from pathlib import Path

DATA = Path(r"C:\Users\john.slagboom\Desktop\Git\data")
FILES = ["domestic_water.json", "irrigation.json", "electric.json", "chw.json", "condensate.json"]

SUSPECT_MONTHS = {"11-01-2025", "12-01-2025", "01-01-2026", "02-01-2026", "03-01-2026"}
BASELINE_2025 = {f"{m:02d}-01-2025" for m in range(1, 11)}

THRESHOLD_RATIO = 20
THRESHOLD_ABSOLUTE = 50_000


def is_num(x):
    return isinstance(x, (int, float))


def write_grid(path, grid):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("{\n")
        f.write('"_kind": "grid",\n')
        f.write('"meta": ' + json.dumps(grid["meta"], ensure_ascii=False) + ",\n")
        f.write('"cols": [\n')
        cols = grid["cols"]
        for i, col in enumerate(cols):
            comma = "," if i < len(cols) - 1 else ""
            f.write(json.dumps(col, ensure_ascii=False) + comma + "\n")
        f.write("],\n")
        f.write('"rows":[\n')
        rows = grid["rows"]
        for i, row in enumerate(rows):
            comma = "," if i < len(rows) - 1 else ""
            f.write(json.dumps(row, ensure_ascii=False, separators=(", ", ":")) + comma + "\n")
        f.write("]\n")
        f.write("}\n")


def main():
    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    grand_total = 0
    for fname in FILES:
        path = DATA / fname
        if not path.exists():
            print(f"SKIP {fname}")
            continue
        backup = path.with_suffix(f".json.nullscan.{ts}.bak")
        shutil.copy2(path, backup)

        with open(path, encoding="utf-8") as f:
            grid = json.load(f)

        groups = {}
        for r in grid["rows"]:
            key = (r.get("bldgNo", ""), r.get("service", ""), r.get("meters", ""))
            groups.setdefault(key, []).append(r)

        nulled = 0
        changes = []
        for key, rows in groups.items():
            baseline = sorted([
                r["usage"] for r in rows
                if r.get("startDate") in BASELINE_2025
                and is_num(r.get("usage")) and r["usage"] > 0
            ])
            if len(baseline) < 4:
                continue
            median = baseline[len(baseline) // 2]
            if median < 100:
                continue
            limit = max(THRESHOLD_ABSOLUTE, THRESHOLD_RATIO * median)
            for r in rows:
                if r.get("startDate") not in SUSPECT_MONTHS:
                    continue
                u = r.get("usage")
                if not is_num(u) or u <= 0:
                    continue
                if u > limit:
                    old = u
                    r["usage"] = None
                    nulled += 1
                    changes.append((r["startDate"], key[0][:20], r.get("bldgName", "")[:30], median, old, old / median))

        if nulled == 0:
            print(f"{fname}: no changes; backup {backup.name} can be discarded")
            backup.unlink(missing_ok=True)
            continue

        write_grid(path, grid)
        grand_total += nulled
        print(f"\n{fname}: nulled {nulled} rows; backup -> {backup.name}")
        for c in sorted(changes, key=lambda x: -x[5]):
            print(f"  {c[0]} {c[1]:<20} {c[2]:<30} base={c[3]:>10,.0f}  was={c[4]:>12,.0f}  ({c[5]:.0f}x)")

    print(f"\nTOTAL NULLED: {grand_total} rows across {len(FILES)} files")


if __name__ == "__main__":
    main()
