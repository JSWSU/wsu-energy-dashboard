#!/bin/bash
# ==============================================================
# update-data.sh — Merge new SkySpark exports and push to GitHub
# ==============================================================
# Usage:
#   1. Export 1-2 months from SkySpark Shell:
#        task_exportToIO(2026-03-01..2026-03-31)
#   2. Download 7 JSON files from SkySpark Files > io/
#   3. Copy them into Desktop/Git/data/new/
#   4. Run: bash update-data.sh
# ==============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
NEW_DIR="$SCRIPT_DIR/data/new"

# Check staging folder exists and has files
if [ ! -d "$NEW_DIR" ]; then
    echo "Error: $NEW_DIR does not exist."
    echo "Create it and place new SkySpark JSON exports there."
    exit 1
fi

file_count=$(ls -1 "$NEW_DIR"/*.json 2>/dev/null | wc -l)
if [ "$file_count" -eq 0 ]; then
    echo "Error: No JSON files found in $NEW_DIR"
    exit 1
fi

echo "Found $file_count JSON file(s) in data/new/"
echo ""

# Step 1: Merge
echo "Step 1: Merging new data into existing files..."
echo ""
py "$SCRIPT_DIR/merge-data.py" "$NEW_DIR"

echo ""

# Step 2: Push
echo "Step 2: Pushing to GitHub..."
echo ""
bash "$SCRIPT_DIR/push-data.sh"

echo ""
echo "Step 3: Cleaning up staging folder..."
rm -f "$NEW_DIR"/*.json
echo "  Removed JSON files from data/new/"

echo ""
echo "Done! Dashboard will update in ~60 seconds."
echo "  https://jswsu.github.io/wsu-energy-dashboard/metering.html"
