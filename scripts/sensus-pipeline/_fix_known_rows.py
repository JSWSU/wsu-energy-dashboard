"""Apply two structural fixes that aren't judgment calls: hardcoded historical spikes
and the 0092 virtual-meter double-count. Idempotent.

Rules:
- Null 3 known Sensus/CSV accumulation spikes in domestic_water.json, matched by
  (bldgNo, meters, startDate). Guard: only null when usage is a number > 1,000,000; if
  already null/absent, skip silently. These predate the raw AMR snapshots
  (Feb 2026 onward) so they cannot be rebuilt from reads.
- Remove 0092 FRENCH ADMINISTRATION virtual compound-meter rows (meters contain
  both "Calsense" and "Domestic") from domestic_water.json, but only for months
  where the physical 0092_DW_001 row also exists (any usage state). The dashboard
  sums by bldgNo, so the virtual row double-counted 0092.

Heuristic spike detection (former passes 1 and 2) is handled in scan-only mode
by _review_outliers.py. Negative-usage rows are also surfaced there. No row in
this script is silently modified beyond the two structural fixes above.
"""
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

DATA = Path(r"C:\Users\john.slagboom\Desktop\Git\data")
FILES = ["domestic_water.json", "irrigation.json"]

# Known spike rows keyed per file as (bldgNo, meters, startDate) -> guard.
# Guard = only null when usage is a number above this (idempotent; already-null rows skip).
# Default guard is SPIKE_GUARD; sub-million phantoms carry a tailored guard set safely
# above the building's real monthly usage so a legitimate future value survives.
KNOWN_SPIKES = {
    "domestic_water.json": {
        ("0121", "0121_DW_001 (CSV)", "05-01-2025"): None,  # TUKEY HORTICULTURE ORCHARD, ~40.8M gal
        ("0816", "0816_DW_001 (CSV), 0816_DW_002 (CSV)", "03-01-2025"): None,  # FOOD SCIENCE/HUMAN NUTRITION, ~10.2M gal
        ("0078", "0078_DW_001 (CSV)", "08-01-2025"): None,  # SLOAN HALL, ~4.7M gal
        ("0109E", "0109EDW_001 (CSV)", "02-01-2026"): None,  # USDA POTTING SHED 109E, 11.89B phantom (row-shift, hisClear'd 2026-07-16)
        ("0109G", "0109GDW_001 (CSV)", "02-01-2026"): None,  # USDA GREENHOUSE EAST, 1.69B phantom (row-shift, hisClear'd 2026-07-21)
        ("0299C", "0299CDW_001 (CSV)", "02-01-2026"): None,  # AIRPORT NEW TERMINAL, 39.68M phantom (meter dead since Aug 2025, hisClear'd 2026-07-16)
        ("0114", "0114_DW_001B (CSV), 0114_DW_001 (CSV), 0114_DW_002 (CSV), 0114_DW_003 (CSV)", "02-01-2026"): None,  # PLANT SCIENCES GREENHOUSE, 348M phantom (1,639x prior-yr median)
        ("0372G", "0372GDW_002 (CSV), 0372GDW_001 (CSV)", "02-01-2026"): None,  # BAILEY-BRAYTON FIELD, 28.6M phantom (492x prior-yr median)
        ("0165D", "0165DDW_001 (CSV)", "02-01-2026"): None,  # VET FEED LOT SHELTER, 14.9M phantom (50,822x prior-yr median)
        # Added 07/21/2026: Feb/Mar 2026 row-shift residue confirmed phantom against the
        # 07/10/2026 register file (meter registers flat/zero while these values exist).
        ("0033E", "0033EDW_001 (CSV)", "02-01-2026"): None,  # MURROW HALL, 1.23M phantom (register delta 0)
        ("0183", "0183_DW_001 (CSV)", "02-01-2026"): None,  # BOTANY FIELD LAB, 1.32M phantom (historian Feb = 0)
        ("0180", "0180_DW_001 (CSV), 0180_DW_002 (CSV)", "03-01-2026"): None,  # STEFFEN CENTER, 1.25M (Ref 200020 Feb-typo residue)
        ("0180", "0180_DW_001 (CSV), 0180_DW_002 (CSV)", "02-01-2026"): 200_000,  # STEFFEN CENTER, 483k (same typo residue)
        ("0111", "0111_DW_001 (CSV)", "02-01-2026"): 500_000,  # ENTOMOLOGY GREENHOUSES, 934k phantom (historian Feb = 0)
        ("0111A", "0111ADW_001 (CSV)", "01-01-2026"): 50_000,  # ENTOM SHOP, 376k phantom (Ref 200045 register zero all 2026)
        ("0111A", "0111ADW_001 (CSV)", "02-01-2026"): 50_000,  # ENTOM SHOP, 108k phantom (same)
        ("0118", "0118_DW_001 (CSV)", "02-01-2026"): 200_000,  # INSTRUCTIONAL GREENHOUSE, 458k phantom (register delta 0)
        ("0357", "0357_DW_001 (CSV)", "02-01-2026"): 100_000,  # RECYCLING FACILITY, 223k phantom (historian Feb = 3,000)
        ("0124A,B", "0124ADW_001 (CSV)", "04-01-2026"): None,  # HORTICULTURE GREENHOUSE, 1.15M = real 11,464-unit delta x suspect x100 mult; null until meter-face verified
        ("0071", "0071_DW_001 (CSV)", "02-01-2026"): None,  # ALBROOK HYDRAULICS LAB, 1.66M phantom (register moved 1 unit in Feb; dodges sanitizer, 2025 baseline < 1,000 gal floor)
    },
}
SPIKE_GUARD = 1_000_000  # default guard when an entry's guard is None


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
        spikes = KNOWN_SPIKES.get(fname, {})
        for r in rows:
            key = (r.get("bldgNo"), r.get("meters"), r.get("startDate"))
            if key in spikes:
                guard = spikes[key] if spikes[key] is not None else SPIKE_GUARD
                u = r.get("usage")
                if is_num(u) and u > guard:
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

        # (Negatives are surfaced in the sanity review report, not nulled here.)

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
