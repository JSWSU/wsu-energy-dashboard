"""Pass 2: catch post-Aug-2025 data-gap bump-ups that my 20x baseline median missed.

Many buildings had Aug-Oct 2025 null readings, then a giant Nov 2025 value where
accumulated usage landed in one month. This distorts the chart even though the
total is real. Null any Nov 2025 - Mar 2026 value > 5x the max Jan-Jul 2025 value
for that meter — exclude chiller plants (seasonal by design).
"""
import json
import shutil
from datetime import datetime
from pathlib import Path

DATA = Path(r"C:\Users\john.slagboom\Desktop\Git\data")
FILES = ["domestic_water.json", "irrigation.json", "electric.json", "chw.json", "condensate.json"]

SUSPECT = {"11-01-2025", "12-01-2025", "01-01-2026", "02-01-2026", "03-01-2026"}
PRE_GAP = {f"{m:02d}-01-2025" for m in range(1, 8)}  # Jan-Jul 2025

RATIO_LIMIT = 5
ABS_LIMIT = 100_000


def is_num(x):
    return isinstance(x, (int, float))


def is_chw_plant(bldg_no, bldg_name):
    t = (bldg_no + " " + bldg_name).upper()
    return "CHW" in t or "CHILL" in t or "COOLING" in t


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
    total = 0
    for fname in FILES:
        path = DATA / fname
        if not path.exists():
            continue
        backup = path.with_suffix(f".json.nullv2.{ts}.bak")
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
            bldg_no, service, meters = key
            name_row = next((r for r in rows if r.get("bldgName")), {})
            bldg_name = name_row.get("bldgName", "")
            if is_chw_plant(bldg_no, bldg_name):
                continue
            pre = [r["usage"] for r in rows if r.get("startDate") in PRE_GAP and is_num(r.get("usage")) and r["usage"] > 0]
            if len(pre) < 3:
                continue
            pre_max = max(pre)
            if pre_max < 1000:
                continue
            limit = max(ABS_LIMIT, RATIO_LIMIT * pre_max)
            for r in rows:
                if r.get("startDate") not in SUSPECT:
                    continue
                u = r.get("usage")
                if not is_num(u) or u <= 0:
                    continue
                if u > limit:
                    old = u
                    r["usage"] = None
                    nulled += 1
                    changes.append((r["startDate"], bldg_no[:20], bldg_name[:30], pre_max, old, old / pre_max))

        if nulled == 0:
            print(f"{fname}: no changes")
            backup.unlink(missing_ok=True)
            continue
        write_grid(path, grid)
        total += nulled
        print(f"\n{fname}: nulled {nulled} rows")
        for c in sorted(changes, key=lambda x: -x[5]):
            print(f"  {c[0]} {c[1]:<20} {c[2]:<30} pre_max={c[3]:>10,.0f}  was={c[4]:>12,.0f}  ({c[5]:.1f}x)")

    print(f"\nTOTAL NULLED (pass 2): {total}")


if __name__ == "__main__":
    main()
