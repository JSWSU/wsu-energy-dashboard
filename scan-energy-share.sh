#!/bin/bash
# scan-energy-share.sh — Scan the Energy Group shared drive and produce folder-scan.json
# Usage: bash scan-energy-share.sh [share-path]
# Default share: //fais007/ENERGY GROUP
# READ-ONLY: This script never writes to the share.

set -euo pipefail

SHARE="${1:-//fais007/ENERGY GROUP}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUTFILE="$SCRIPT_DIR/folder-scan.json"

echo "=== Energy Group Share Scanner ==="
echo "Share:  $SHARE"
echo "Output: $OUTFILE"
echo ""

# -------------------------------------------------------------------
# The entire scan is done in Python using os.walk() because:
#   1. MINGW64 find lacks -printf
#   2. os.walk() handles UNC paths and spaces natively on Windows
#   3. Python builds the JSON tree directly — no intermediate files
# -------------------------------------------------------------------

export SCAN_SHARE="$SHARE"
export SCAN_OUTFILE="$OUTFILE"

py << 'PYEOF'
import os
import sys
import json
import time
from datetime import datetime, date
from collections import defaultdict

SHARE = os.environ.get("SCAN_SHARE", r"//fais007/ENERGY GROUP")
OUTFILE = os.environ.get("SCAN_OUTFILE", os.path.join(os.getcwd(), "folder-scan.json"))

# --- Configuration ---
MAX_DEPTH = 4          # Tree depth limit; beyond this, aggregate into "(other)"
DEEP_NEST_THRESHOLD = 5
LARGE_FILE_BYTES = 10 * 1024 * 1024   # 10 MB
OLD_FILE_CUTOFF = datetime(2020, 1, 1).timestamp()
MAX_OLD_FILES = 200
MAX_LEGACY_FILES = 500

LEGACY_EXTENSIONS = {'.kva', '.eu', '.wks', '.wk1', '.wps', '.rdb'}

# --- Helpers ---
def rel_path(full_path):
    """Return path relative to share root, using backslash for display."""
    r = os.path.relpath(full_path, SHARE)
    if r == ".":
        return ""
    return r.replace("/", "\\")

def ts_to_date(ts):
    """Timestamp to YYYY-MM-DD string."""
    try:
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
    except (OSError, ValueError):
        return "unknown"

def ts_to_year(ts):
    """Timestamp to year int."""
    try:
        return datetime.fromtimestamp(ts).year
    except (OSError, ValueError):
        return None

def safe_stat(path):
    """Return (size_bytes, mtime_timestamp) or None on error."""
    try:
        s = os.stat(path)
        return (s.st_size, s.st_mtime)
    except (OSError, PermissionError):
        return None

# --- Phase 1: Walk and collect raw data ---
print("Phase 1: Walking directory tree ...")
t0 = time.time()

# dir_info[full_path] = { size, files, mtime, depth, children_names }
dir_info = {}
# file_list = [(full_path, size, mtime, ext, depth)]
file_list = []
# For duplicate detection: dir name -> [paths]
dir_names = defaultdict(list)

share_norm = os.path.normpath(SHARE)
share_depth = len(share_norm.replace("\\", "/").rstrip("/").split("/"))

walk_count = 0
error_count = 0

for dirpath, dirnames, filenames in os.walk(SHARE):
    walk_count += 1
    if walk_count % 500 == 0:
        print(f"  ... scanned {walk_count} directories, {len(file_list)} files so far")

    dp_norm = os.path.normpath(dirpath)
    depth = len(dp_norm.replace("\\", "/").rstrip("/").split("/")) - share_depth

    # Get dir mtime
    dir_stat = safe_stat(dirpath)
    dir_mtime = dir_stat[1] if dir_stat else 0

    dir_info[dp_norm] = {
        "size": 0,
        "files": 0,
        "mtime": dir_mtime,
        "depth": depth,
        "child_dirs": [os.path.normpath(os.path.join(dirpath, d)) for d in dirnames],
        "direct_files": 0,
    }

    # Track dir name for duplicate detection (skip root)
    if depth > 0:
        dname = os.path.basename(dp_norm)
        dir_names[dname.lower()].append(dp_norm)

    for fname in filenames:
        fpath = os.path.join(dirpath, fname)
        fstat = safe_stat(fpath)
        if fstat is None:
            error_count += 1
            continue
        fsize, fmtime = fstat
        ext = os.path.splitext(fname)[1].lower()
        fdepth = depth + 1  # file is one level deeper than its dir

        file_list.append((fpath, fsize, fmtime, ext, fdepth))

        # Accumulate into parent dir
        dir_info[dp_norm]["size"] += fsize
        dir_info[dp_norm]["files"] += 1
        dir_info[dp_norm]["direct_files"] += 1

elapsed_walk = time.time() - t0
print(f"Phase 1 complete: {walk_count} dirs, {len(file_list)} files in {elapsed_walk:.1f}s")
if error_count:
    print(f"  ({error_count} files could not be stat'd — permission errors)")

# --- Phase 2: Roll up sizes bottom-up ---
print("Phase 2: Rolling up directory sizes ...")

# Sort dirs deepest-first for bottom-up aggregation
sorted_dirs = sorted(dir_info.keys(), key=lambda d: dir_info[d]["depth"], reverse=True)

for d in sorted_dirs:
    info = dir_info[d]
    for child in info["child_dirs"]:
        if child in dir_info:
            info["size"] += dir_info[child]["size"]
            info["files"] += dir_info[child]["files"]
            # Propagate newest mtime upward
            if dir_info[child]["mtime"] > info["mtime"]:
                info["mtime"] = dir_info[child]["mtime"]

# --- Phase 3: Build the tree (depth-limited) ---
print("Phase 3: Building JSON tree ...")

def build_node(full_path, depth):
    """Recursively build tree node. At MAX_DEPTH, aggregate children."""
    info = dir_info.get(os.path.normpath(full_path))
    if info is None:
        return None

    name = os.path.basename(full_path) or os.path.basename(SHARE)
    node = {
        "name": name,
        "size": info["size"],
        "files": info["files"],
        "modified": ts_to_date(info["mtime"]),
    }

    child_dirs = info.get("child_dirs", [])

    if depth < MAX_DEPTH and child_dirs:
        children = []
        for cd in sorted(child_dirs, key=lambda x: os.path.basename(x).lower()):
            child_node = build_node(cd, depth + 1)
            if child_node:
                children.append(child_node)
        if children:
            node["children"] = children
    elif depth >= MAX_DEPTH and child_dirs:
        # Aggregate: don't expand further, just show summary
        # The size/files are already rolled up in info
        pass  # node already has rolled-up size and files

    return node

root_norm = os.path.normpath(SHARE)
tree = build_node(root_norm, 0)
if tree is None:
    print("ERROR: Could not build tree for root path")
    sys.exit(1)

# Fix root name
tree["name"] = os.path.basename(root_norm)

# --- Phase 4: Audit findings ---
print("Phase 4: Collecting audit findings ...")

audit = {
    "duplicates": [],
    "deepNesting": [],
    "legacyFormats": [],
    "largeFiles": [],
    "emptyFolders": [],
    "oldFiles": [],
}

# 4a. Duplicates — directories with same name at multiple paths
for dname, paths in sorted(dir_names.items()):
    if len(paths) < 2:
        continue
    # Only report if at least one copy has files
    copies_with_files = [p for p in paths if dir_info[p]["files"] > 0]
    if len(copies_with_files) < 2 and len(paths) < 3:
        continue
    total_size = sum(dir_info[p]["size"] for p in paths)
    total_files = sum(dir_info[p]["files"] for p in paths)
    audit["duplicates"].append({
        "name": os.path.basename(paths[0]),
        "count": len(paths),
        "paths": [rel_path(p) for p in paths],
        "totalSize": total_size,
        "totalFiles": total_files,
    })

# Sort duplicates by total size descending, limit to 200
audit["duplicates"].sort(key=lambda x: x["totalSize"], reverse=True)
audit["duplicates"] = audit["duplicates"][:200]

# 4b. Deep nesting — directories deeper than threshold
for d, info in dir_info.items():
    if info["depth"] > DEEP_NEST_THRESHOLD:
        audit["deepNesting"].append({
            "path": rel_path(d),
            "depth": info["depth"],
            "size": info["size"],
            "files": info["files"],
            "modified": ts_to_date(info["mtime"]),
        })
audit["deepNesting"].sort(key=lambda x: x["depth"], reverse=True)

# 4c. Legacy formats
legacy_found = []
for fpath, fsize, fmtime, ext, fdepth in file_list:
    if ext in LEGACY_EXTENSIONS:
        legacy_found.append({
            "path": rel_path(fpath),
            "extension": ext.lstrip('.').upper(),
            "size": fsize,
            "modified": ts_to_date(fmtime),
        })
legacy_found.sort(key=lambda x: x["size"], reverse=True)
audit["legacyFormats"] = legacy_found[:MAX_LEGACY_FILES]

# 4d. Large files (>10 MB)
for fpath, fsize, fmtime, ext, fdepth in file_list:
    if fsize > LARGE_FILE_BYTES:
        audit["largeFiles"].append({
            "path": rel_path(fpath),
            "size": fsize,
            "modified": ts_to_date(fmtime),
        })
audit["largeFiles"].sort(key=lambda x: x["size"], reverse=True)

# 4e. Empty folders
for d, info in dir_info.items():
    if info["files"] == 0 and info["depth"] > 0:
        audit["emptyFolders"].append({
            "path": rel_path(d),
            "modified": ts_to_date(info["mtime"]),
        })
audit["emptyFolders"].sort(key=lambda x: x["path"])

# 4f. Old files — not modified since 2020-01-01 (largest first, capped)
old_candidates = []
for fpath, fsize, fmtime, ext, fdepth in file_list:
    if fmtime < OLD_FILE_CUTOFF:
        old_candidates.append({
            "path": rel_path(fpath),
            "size": fsize,
            "modified": ts_to_date(fmtime),
        })
old_candidates.sort(key=lambda x: x["size"], reverse=True)
audit["oldFiles"] = old_candidates[:MAX_OLD_FILES]

# --- Phase 5: Compute summary stats ---
print("Phase 5: Computing summary statistics ...")

total_size = dir_info[root_norm]["size"]
total_files = dir_info[root_norm]["files"]
max_depth = max((info["depth"] for info in dir_info.values()), default=0)

years = []
for fpath, fsize, fmtime, ext, fdepth in file_list:
    y = ts_to_year(fmtime)
    if y and y > 1980:  # filter out obviously wrong dates
        years.append(y)

date_range = {
    "oldest": str(min(years)) if years else "unknown",
    "newest": str(max(years)) if years else "unknown",
}

# --- Phase 6: Write JSON ---
print("Phase 6: Writing JSON output ...")

output = {
    "scanDate": date.today().isoformat(),
    "root": SHARE.replace("/", "\\"),
    "totalSize": total_size,
    "totalFiles": total_files,
    "totalDirs": len(dir_info),
    "maxDepth": max_depth,
    "dateRange": date_range,
    "scanDuration": round(time.time() - t0, 1),
    "tree": tree,
    "audit": audit,
}

with open(OUTFILE, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"\nDone! Wrote {OUTFILE}")
print(f"  Total size: {total_size / 1e9:.1f} GB")
print(f"  Total files: {total_files:,}")
print(f"  Total dirs: {len(dir_info):,}")
print(f"  Max depth: {max_depth}")
print(f"  Date range: {date_range['oldest']} - {date_range['newest']}")
print(f"  Audit findings:")
for k, v in audit.items():
    print(f"    {k}: {len(v)}")
PYEOF
