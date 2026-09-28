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

# Step 2: Apply structural fixes (hardcoded historical spikes + 0092 dedup)
echo "Step 2: Applying structural fixes (historical spikes, 0092 dedup)..."
echo ""
py "$SCRIPT_DIR/scripts/sensus-pipeline/_fix_known_rows.py"

echo ""
echo "Step 3: Generating QA/QC report (report only -- no rows modified)..."
echo ""
py "$SCRIPT_DIR/scripts/sensus-pipeline/_qa_report.py"

echo ""
echo "REVIEW the QA report at C:\\Users\\john.slagboom\\Desktop\\Git\\data\\reports\\qaqc-metering-*.html before pushing."
echo "If it lists CRITICAL rows you have not addressed, stop and edit files under"
echo "C:\\Users\\john.slagboom\\Desktop\\Git\\data\\ first."
echo ""

# Step 4: Refresh the INTERNAL process register (sops\_register, copied to R:; never published)
echo "Step 4: Refreshing the internal process register..."
py "$SCRIPT_DIR/sops/_register/export_processes_json.py" || echo "  (register refresh failed; continuing)"

echo ""

# Step 4b: Schweitzer Engineering Hall (0802) snapshot (non-fatal)
echo "Step 4b: Refreshing Schweitzer Engineering Hall (0802) data for seh-energy.html..."
if py "$SCRIPT_DIR/export_0802.py"; then
    bash "$SCRIPT_DIR/push-data.sh" data/0802/points.json data/0802/meters.json || echo "  (0802 push failed; continuing)"
else
    echo "  (0802 export failed; continuing)"
fi
echo ""
# Step 5: Push
echo "Step 5: Pushing to GitHub..."
echo ""
if ! bash "$SCRIPT_DIR/push-data.sh"; then
    echo ""
    echo "Push reported failures. Keeping data/new/ staging files so the run can be repeated."
    echo "Fix the problem (PAT, network), then run: bash update-data.sh"
    exit 1
fi

echo ""
echo "Step 6: Cleaning up staging folder..."
rm -f "$NEW_DIR"/*.json
echo "  Removed JSON files from data/new/"

echo ""
echo "Done! Dashboard will update in ~60 seconds."
echo "  https://jswsu.github.io/wsu-energy-dashboard/metering.html"
