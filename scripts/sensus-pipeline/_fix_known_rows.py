"""Fix known bad rows in the water files: CSV spikes, 0092 double-count, negatives.

Corrections from the 06/2026 audit, kept in the pipeline so a re-merge of old
exports cannot reintroduce them. Idempotent: a second run changes nothing.

Rules:
- Null 3 known Sensus/CSV accumulation spikes in domestic_water.json, matched by
  (bldgNo, meters, startDate). Guard: only null when usage is a number > 1,000,000; if
  already null/absent, skip silently. These predate the raw AMR snapshots
  (Feb 2026 onward) so they cannot be rebuilt from reads.
- Remove 0092 FRENCH ADMINISTRATION virtual compound-meter rows (meters contain
  both "Calsense" and "Domestic") from domestic_water.json, but only for months
  where the physical 0092_DW_001 row also exists (any usage state). The dashboard
  sums by bldgNo, so the virtual row double-counted 0092.
- Null any negative usage value (physically impossible) in both water files.
"""
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

DATA = Path(r"C:\Users\john.slagboom\Desktop\Git\data")
FILES = ["domestic_water.json", "irrigation.json"]

# Known spike rows keyed per file as (bldgNo, meters, startDate)
KNOWN_SPIKES = {
    "domestic_water.json": {
        ("0121", "0121_DW_001 (CSV)", "05-01-2025"),  # TUKEY HORTICULTURE ORCHARD, ~40.8M gal
        ("0816", "0816_DW_001 (CSV), 0816_DW_002 (CSV)", "03-01-2025"),  # FOOD SCIENCE/HUMAN NUTRITION, ~10.2M gal
        ("0078", "0078_DW_001 (CSV)", "08-01-2025"),  # SLOAN HALL, ~4.7M gal
    },
}
SPIKE_GUARD = 1_000_000  # only null when current value is a number above this


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
    total_nulled = 0
    total_removed = 0
    for fname in FILES:
        path = DATA / fname
        if not path.exists():
            print(f"SKIP {fname}")
            continue
        backup = path.with_suffix(f".json.fixknown.{ts}.bak")
        shutil.copy2(path, backup)

        try:
            with open(path, encoding="utf-8") as f:
                grid = json.load(f)
            rows = grid["rows"]
            if not isinstance(rows, list):
                raise ValueError("rows is not a list")
        except (ValueError, KeyError, TypeError) as e:
            print(f"ERROR: {fname} is malformed ({e})")
            backup.unlink(missing_ok=True)
            sys.exit(1)

        nulled = 0
        removed = 0

        # 1. Null known spike rows (guarded, idempotent)
        spikes = KNOWN_SPIKES.get(fname, set())
        for r in rows:
            key = (r.get("bldgNo"), r.get("meters"), r.get("startDate"))
            if key in spikes:
                u = r.get("usage")
                if is_num(u) and u > SPIKE_GUARD:
                    r["usage"] = None
                    nulled += 1
                    print(f"  NULL spike     {fname} {key[0]} {key[2]}  was={u:,.0f}")

        # 2. Drop 0092 virtual compound rows for months that have the physical row
        if fname == "domestic_water.json":
            phys_months = {
                r.get("startDate") for r in rows
                if r.get("bldgNo") == "0092" and "0092_DW_001" in (r.get("meters") or "")
            }
            kept = []
            for r in rows:
                m = r.get("meters") or ""
                if (r.get("bldgNo") == "0092" and "Calsense" in m and "Domestic" in m
                        and r.get("startDate") in phys_months):
                    removed += 1
                    print(f"  DROP 0092 virtual  {r.get('startDate')}  usage={r.get('usage')}")
                    continue
                kept.append(r)
            grid["rows"] = rows = kept

        # 3. Null any negative usage (physically impossible)
        for r in rows:
            u = r.get("usage")
            if is_num(u) and u < 0:
                r["usage"] = None
                nulled += 1
                print(f"  NULL negative  {fname} {r.get('bldgNo')} {r.get('startDate')}  was={u:,.2f}")

        if nulled == 0 and removed == 0:
            print(f"{fname}: no changes")
            backup.unlink(missing_ok=True)
            continue

        write_grid(path, grid)
        total_nulled += nulled
        total_removed += removed
        print(f"{fname}: nulled {nulled}, removed {removed}; backup -> {backup.name}")

    print(f"\nTOTAL: nulled {total_nulled}, removed {total_removed} across {len(FILES)} files")


if __name__ == "__main__":
    main()
