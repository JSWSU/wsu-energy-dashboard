"""One-time label realignment for Sensus AMR meters (07/22/2026).

The 2025 historian load labeled each AMR pull interval by its START month;
the 2026 reingest labels the same interval by its READ month, one month
later. Any label-to-label year-over-year comparison on an AMR meter is
therefore off by one month across the 2025/2026 boundary (proven on 0167
by register reconciliation).

Fix: shift every 2025-dated row belonging to an AMR-class meter forward
one month. The shifted December 2025 interval becomes January 2026 and
REPLACES the existing January 2026 row for that meter, which is the known
Jan-duplicates-February reingest artifact (blank Jan lastMonth). January
2025 is left empty: that interval lives in the 2024 data we do not carry.

Idempotent: shifted rows are tagged "labelShifted": true and skipped on
re-run. AMR membership comes from data/meter_class.json; building-total
rows are shifted only when every meter they name is AMR.
"""
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

DATA = Path(r"C:\Users\john.slagboom\Desktop\Git\data")
FILES = ["domestic_water.json", "irrigation.json"]
LAST_DAY = {1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30, 7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}

mc = json.load(open(DATA / "meter_class.json", encoding="utf-8"))


def norm_key(name):
    if not name:
        return None
    s = str(name).strip().upper()
    if s.startswith("W/"):
        s = s[2:]
    s = s.replace("(CSV ZERO)", "").replace("(CSV)", "").replace("(CS3000)", "").strip()
    s = s.split()[0] if s.split() else s
    m = re.match(r"^(\d{1,3})(?=[A-Z_])(.*)$", s)
    if m and len(m.group(1)) < 4:
        s = m.group(1).zfill(4) + m.group(2)
    return s


def all_amr(meters_field):
    parts = [p.strip() for p in str(meters_field or "").split(",") if p.strip()]
    if not parts:
        return False
    for p in parts:
        info = mc.get(norm_key(p))
        if not info or info.get("cls") != "AMR":
            return False
    return True


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
    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    for fname in FILES:
        path = DATA / fname
        grid = json.load(open(path, encoding="utf-8"))
        rows = grid["rows"]
        shutil.copy2(path, path.with_suffix(f".json.labelshift.{ts}.bak"))

        shifted = 0
        replaced = 0
        skipped_mixed = set()
        # index existing Jan 2026 rows by (bldgNo, meters, byMeter) for replacement
        jan26 = {}
        for r in rows:
            if (r.get("startDate") or "").endswith("2026") and (r.get("startDate") or "").startswith("01-"):
                jan26[(r.get("bldgNo"), r.get("meters"), bool(r.get("byMeter")))] = r

        drop = set()
        for r in rows:
            sd = r.get("startDate") or ""
            if not sd.endswith("2025") or r.get("labelShifted"):
                continue
            meters_field = r.get("meters") or ""
            if not all_amr(meters_field):
                if meters_field and any(mc.get(norm_key(p.strip()), {}).get("cls") == "AMR"
                                        for p in meters_field.split(",")):
                    skipped_mixed.add((r.get("bldgNo"), meters_field))
                continue
            mm = int(sd[:2])
            new_m = mm + 1
            new_y = 2025
            if new_m == 13:
                new_m, new_y = 1, 2026
                key = (r.get("bldgNo"), r.get("meters"), bool(r.get("byMeter")))
                old = jan26.get(key)
                if old is not None and id(old) != id(r):
                    drop.add(id(old))
                    replaced += 1
            r["startDate"] = f"{new_m:02d}-01-{new_y}"
            r["endDate"] = f"{new_m:02d}-{LAST_DAY[new_m]:02d}-{new_y}"
            r["labelShifted"] = True
            shifted += 1

        grid["rows"] = [r for r in rows if id(r) not in drop]
        write_grid(path, grid)
        print(f"{fname}: shifted {shifted} rows (+1 month), Dec->Jan replacements {replaced}, "
              f"dropped {len(drop)} broken Jan-2026 rows, mixed-meter buildings skipped: {len(skipped_mixed)}")
        for x in sorted(skipped_mixed):
            print("   SKIP mixed:", x)


if __name__ == "__main__":
    main()
