#!/usr/bin/env python3
"""
merge-data.py — Merge new SkySpark exports into existing metering data files.

Usage:
    py merge-data.py <new-data-dir>

Example:
    py merge-data.py data/new

Merges new JSON exports (1-2 months) into the existing data/ files without
re-exporting the full history. Backs up originals before writing.

Utility files (electric, condensate, domestic_water, irrigation, chw) are
merged by key (bldgNo, meters, startDate). Sites and connectors are replaced.
"""
import json
import os
import shutil
import sys
from datetime import datetime

# ── Configuration ──────────────────────────────────────────────

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
BACKUP_DIR = os.path.join(DATA_DIR, "backup")
MAX_BACKUPS = 3

MERGE_FILES = [
    "electric.json",
    "condensate.json",
    "domestic_water.json",
    "irrigation.json",
    "chw.json",
]

REPLACE_FILES = [
    "sites.json",
    "connectors.json",
]

# ── Helpers ────────────────────────────────────────────────────

def row_key(row):
    """Unique key for deduplication: (bldgNo, meters, startDate)."""
    return (row.get("bldgNo", ""), row.get("meters", ""), row.get("startDate", ""))


def has_usage(row):
    """True if the row has a non-null numeric usage value."""
    u = row.get("usage")
    return u is not None and isinstance(u, (int, float))


def sort_key(row):
    """Sort rows by building number, then chronologically by startDate."""
    bldg = row.get("bldgNo", "")
    sd = row.get("startDate", "")
    # Parse MM-DD-YYYY to (YYYY, MM) for proper chronological sort
    parts = sd.split("-")
    if len(parts) == 3:
        return (bldg, parts[2], parts[0])
    return (bldg, sd, "")


def load_grid(path):
    """Load a SkySpark JSON grid file. Returns the full parsed dict."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_grid(path, grid):
    """Write a SkySpark JSON grid file in the original compact format.

    Format: meta/cols pretty, each row on one compact line.
    """
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


def backup_file(path):
    """Create a timestamped backup, keep only the last MAX_BACKUPS."""
    if not os.path.exists(path):
        return None
    os.makedirs(BACKUP_DIR, exist_ok=True)
    name = os.path.basename(path)
    ts = datetime.now().strftime("%Y-%m-%dT%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"{name}.{ts}.bak")
    shutil.copy2(path, backup_path)

    # Prune old backups for this file
    prefix = name + "."
    backups = sorted(
        [f for f in os.listdir(BACKUP_DIR) if f.startswith(prefix) and f.endswith(".bak")]
    )
    while len(backups) > MAX_BACKUPS:
        os.remove(os.path.join(BACKUP_DIR, backups.pop(0)))

    return backup_path


def format_size(size_bytes):
    """Format file size for display."""
    if size_bytes >= 1_000_000:
        return f"{size_bytes / 1_000_000:.1f} MB"
    return f"{size_bytes / 1_000:.0f} KB"


def count_months(rows):
    """Count unique months in a row set."""
    return len(set(r.get("startDate", "")[:2] + "-" + r.get("startDate", "")[-4:] for r in rows if r.get("startDate")))


def count_buildings(rows):
    """Count unique buildings in a row set."""
    return len(set(r.get("bldgNo", "") for r in rows if has_usage(r)))


# ── Merge Logic ────────────────────────────────────────────────

def merge_rows(existing_rows, new_rows):
    """Merge new rows into existing rows by key.

    Returns (merged_rows, stats) where stats is a dict with counts.
    """
    # Index existing rows by key
    index = {}
    for row in existing_rows:
        k = row_key(row)
        index[k] = row

    added = 0
    updated = 0
    unchanged = 0
    skipped_no_regress = 0

    for row in new_rows:
        k = row_key(row)
        if k in index:
            old = index[k]
            if has_usage(row):
                if not has_usage(old):
                    # Fill null with actual — primary use case
                    index[k] = row
                    updated += 1
                elif row.get("usage") != old.get("usage"):
                    # Correction — new value replaces old
                    index[k] = row
                    updated += 1
                else:
                    unchanged += 1
            else:
                # New row lacks usage — keep existing (no regression)
                skipped_no_regress += 1
                unchanged += 1
        else:
            # New key — append
            index[k] = row
            added += 1

    # Count unchanged (existing rows not touched by new data)
    total_existing_keys = set(row_key(r) for r in existing_rows)
    total_new_keys = set(row_key(r) for r in new_rows)
    untouched = len(total_existing_keys - total_new_keys)
    unchanged += untouched

    merged = sorted(index.values(), key=sort_key)

    stats = {
        "added": added,
        "updated": updated,
        "unchanged": unchanged,
        "skipped_no_regress": skipped_no_regress,
    }
    return merged, stats


# ── Validation ─────────────────────────────────────────────────

def validate_merge(merged_rows, existing_rows):
    """Validate merged result. Returns list of error strings (empty = pass)."""
    errors = []

    # Check no duplicate keys
    keys = [row_key(r) for r in merged_rows]
    if len(keys) != len(set(keys)):
        dupes = len(keys) - len(set(keys))
        errors.append(f"Duplicate keys found: {dupes} duplicates")

    # Check no data regression (rows that had usage still have it)
    existing_index = {row_key(r): r for r in existing_rows}
    for row in merged_rows:
        k = row_key(row)
        if k in existing_index:
            old = existing_index[k]
            if has_usage(old) and not has_usage(row):
                errors.append(f"Data regression: {k} had usage, now missing")

    # Check row count didn't decrease
    if len(merged_rows) < len(existing_rows):
        errors.append(f"Row count decreased: {len(existing_rows)} -> {len(merged_rows)}")

    return errors


# ── Main ───────────────────────────────────────────────────────

def main():
    if len(sys.argv) != 2:
        print("Usage: py merge-data.py <new-data-dir>")
        print("Example: py merge-data.py data/new")
        sys.exit(1)

    new_dir = sys.argv[1]

    # Resolve relative to script directory
    if not os.path.isabs(new_dir):
        new_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), new_dir)

    if not os.path.isdir(new_dir):
        print(f"Error: Directory not found: {new_dir}", file=sys.stderr)
        print(f"Create it and place new SkySpark JSON exports there.", file=sys.stderr)
        sys.exit(1)

    # Check what files are available
    new_files = set(os.listdir(new_dir))
    merge_targets = [f for f in MERGE_FILES if f in new_files]
    replace_targets = [f for f in REPLACE_FILES if f in new_files]

    if not merge_targets and not replace_targets:
        print("No matching files found in " + new_dir)
        print("Expected: " + ", ".join(MERGE_FILES + REPLACE_FILES))
        sys.exit(0)

    print("=" * 60)
    print("  Metering Data Merge")
    print("=" * 60)
    print(f"  Source:  {new_dir}")
    print(f"  Target:  {DATA_DIR}")
    print(f"  Merge:   {len(merge_targets)} file(s)")
    print(f"  Replace: {len(replace_targets)} file(s)")
    print("=" * 60)

    total_added = 0
    total_updated = 0
    total_unchanged = 0
    had_errors = False

    # ── Merge utility files ──

    for filename in merge_targets:
        existing_path = os.path.join(DATA_DIR, filename)
        new_path = os.path.join(new_dir, filename)

        print(f"\n  {filename}")
        print("  " + "-" * 40)

        if not os.path.exists(existing_path):
            print(f"    Warning: No existing {filename} in data/ — copying as new file")
            shutil.copy2(new_path, existing_path)
            new_grid = load_grid(new_path)
            print(f"    Copied: {len(new_grid.get('rows', []))} rows")
            continue

        # Load both files
        existing_grid = load_grid(existing_path)
        new_grid = load_grid(new_path)

        existing_rows = existing_grid.get("rows", [])
        new_rows = new_grid.get("rows", [])

        print(f"    Existing:  {len(existing_rows):,} rows ({count_buildings(existing_rows)} buildings, {count_months(existing_rows)} months)")
        print(f"    New:       {len(new_rows):,} rows ({count_buildings(new_rows)} buildings, {count_months(new_rows)} months)")

        # Merge
        merged_rows, stats = merge_rows(existing_rows, new_rows)

        # Validate
        errors = validate_merge(merged_rows, existing_rows)
        if errors:
            print(f"    ERRORS — skipping write:")
            for e in errors:
                print(f"      - {e}")
            had_errors = True
            continue

        # Backup and write
        backup_path = backup_file(existing_path)
        existing_grid["rows"] = merged_rows
        write_grid(existing_path, existing_grid)
        file_size = os.path.getsize(existing_path)

        print(f"    Updated:   {stats['updated']:,} rows (null -> actual or corrected)")
        print(f"    Appended:  {stats['added']:,} rows (new months)")
        print(f"    Unchanged: {stats['unchanged']:,} rows")
        print(f"    Result:    {len(merged_rows):,} rows ({count_buildings(merged_rows)} buildings, {count_months(merged_rows)} months)")
        print(f"    Written:   {filename} ({format_size(file_size)})")
        if backup_path:
            print(f"    Backup:    {os.path.basename(backup_path)}")

        total_added += stats["added"]
        total_updated += stats["updated"]
        total_unchanged += stats["unchanged"]

    # ── Replace non-date files ──

    for filename in replace_targets:
        existing_path = os.path.join(DATA_DIR, filename)
        new_path = os.path.join(new_dir, filename)

        print(f"\n  {filename}")
        print("  " + "-" * 40)

        backup_path = backup_file(existing_path)
        shutil.copy2(new_path, existing_path)
        new_grid = load_grid(new_path)
        file_size = os.path.getsize(existing_path)

        print(f"    Replaced:  {len(new_grid.get('rows', []))} rows ({format_size(file_size)})")
        if backup_path:
            print(f"    Backup:    {os.path.basename(backup_path)}")

    # ── Summary ──

    print("\n" + "=" * 60)
    print("  Summary")
    print("=" * 60)
    print(f"  Files merged:   {len(merge_targets)}")
    print(f"  Files replaced: {len(replace_targets)}")
    print(f"  Rows added:     {total_added:,}")
    print(f"  Rows updated:   {total_updated:,}")
    print(f"  Rows unchanged: {total_unchanged:,}")
    if had_errors:
        print("\n  WARNING: Some files had errors and were not written.")
        print("  Check output above for details.")
    print("=" * 60)

    sys.exit(1 if had_errors else 0)


if __name__ == "__main__":
    main()
