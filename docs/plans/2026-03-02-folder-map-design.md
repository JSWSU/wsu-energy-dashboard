# Energy Group Folder Map — Design Document

**Date:** 2026-03-02
**Purpose:** Interactive webapp to visualize and audit the `\\fais007\ENERGY GROUP` network share
**Audience:** WSU Energy Group team (knowledge base + cleanup/audit tool)

---

## Overview

A single self-contained HTML file (`folder-map.html`) that presents an interactive treemap of the Energy Group shared drive (~30 GB, ~58K files, 24 top-level folders spanning 1983–2026) alongside an audit findings table that surfaces cleanup opportunities.

## Architecture

- **Single HTML file** with inline `<style>` + `<script>` (same pattern as existing dashboards)
- **WSU CSS design system** — uses `--primary`, `--accent`, `--bg`, etc. plus dark mode toggle
- **No auth gate** — internal team tool, no sensitive data exposed
- **Chart.js** loaded from existing local `chart.umd.min.js`
- **chartjs-chart-treemap** plugin (~15KB) loaded via CDN or bundled inline
- **Scan data embedded** as `const SCAN_DATA = {...};` in the HTML file
- **Location:** `wsu-energy-dashboard/` repo, standalone alongside existing dashboards

## Data Model

### Scan Script

A bash script (`scan-energy-share.sh`) that:
1. Runs `find` across the network share to collect paths, sizes, dates, types
2. Outputs structured JSON (`folder-scan.json`)
3. JSON is embedded into the HTML file

### JSON Structure

```json
{
  "scanDate": "2026-03-02",
  "root": "\\\\fais007\\ENERGY GROUP",
  "totalSize": 30300000000,
  "totalFiles": 58685,
  "maxDepth": 18,
  "dateRange": { "oldest": "1983", "newest": "2026" },
  "tree": {
    "name": "ENERGY GROUP",
    "size": 30300000000,
    "files": 58685,
    "modified": "2026-02-05",
    "children": [
      {
        "name": "Energy Services Admin",
        "size": 27000000000,
        "files": 47033,
        "modified": "...",
        "children": [...]
      }
    ]
  },
  "audit": {
    "duplicates": [...],
    "deepNesting": [...],
    "legacyFormats": [...],
    "largeFiles": [...],
    "emptyFolders": [...],
    "oldFiles": [...]
  }
}
```

### Depth Limit

Treemap data goes to **depth 4**. Beyond that, children are aggregated into a single summary node. This keeps the embedded JSON manageable (~2,000 tree nodes from ~58K files). The audit table references full paths regardless of depth.

## Tab 1: Storage Map (Treemap View)

### KPI Cards

Four `.kpi-card` elements above the treemap:
- **Total Size:** 30.3 GB
- **Total Files:** ~58,685
- **Max Depth:** 18 levels
- **Date Span:** 1983–2026

### Treemap Chart

- Full-width treemap filling a `.card` container
- Blocks sized proportionally to folder/file size in bytes
- Color coded by category (folders in crimson/gray shades, file types highlighted: spreadsheets=gold, PDFs=blue, images=green, legacy=red)
- **Hover:** Tooltip with folder name, size (human-readable), file count, last modified date
- **Click:** Drill into that folder — treemap re-renders with children. Breadcrumb trail at top shows path with click-to-navigate-back
- **Top-level view:** Shows all 24 folders with `Energy Services Admin` dominating at 89%

## Tab 2: Audit Findings (Table View)

### Filter Buttons

`.filter-btn` row across the top:
- **All** — all findings
- **Duplicates** — folders/files that appear to be copies (nested "Energy Files" inside itself, multiple copies of "Meter Reads since FY2011.xlsx")
- **Deep Nesting** — paths exceeding 5+ levels deep (18-level paths in ECS Enercon SCADA)
- **Legacy Formats** — obsolete file types (KVA, EU, WKS, WK1, WPS, rdb — Lotus 1-2-3, WordPerfect)
- **Large Files** — files over 10 MB
- **Empty** — folders with 0 files (Waller Hall)
- **Old** — files not modified since 2020

### Table Columns

| Column | Description |
|--------|-------------|
| Category | Issue type with `.status-pill` badge styling |
| Path | Full path relative to share root (truncated with tooltip for long paths) |
| Size | Human-readable file/folder size |
| Files | File count (for folder entries) |
| Last Modified | Date of most recent change |
| Details | Specific finding description |

### Summary

`.total-row` at top showing total count of findings and potential storage savings.

Sortable column headers (reusing existing `.th-sort` pattern). Search bar for filtering by path.

## Scan Findings Summary (from exploration)

| Category | Count | Example |
|----------|-------|---------|
| Dominant folder | 1 | `Energy Services Admin/` — 27 GB, 47K files (89% of share) |
| Deep nesting | 10+ | Paths 18 levels deep in `ECS Enercon SCADA/` |
| Duplicate structures | Several | "Energy Files" nested inside itself at multiple levels |
| Legacy formats | ~2,188 | KVA (896), EU (780), WKS (224), WK1 (202), WPS (86) |
| Large files | 20+ | 55 MB PDF, 41 MB XLS, multiple 25 MB Excel copies |
| Empty folders | 1+ | `Waller Hall/` (0 files, 0 bytes) |
| Old files | Thousands | Data from 1983–2019 that may be archivable |
| Duplicate files | 5+ | Multiple copies of "Meter Reads since FY2011.xlsx" in Archive/ |

## CSS/UI Details

- Reuses all standard WSU CSS variables and classes from CLAUDE.md
- Dark mode toggle (localStorage key: `wsuFolderMapDark`)
- No print layout needed
- Responsive: treemap and table work on smaller screens via `.table-wrap` overflow

## What This Is NOT

- NOT a live file browser — it's a point-in-time snapshot
- NOT a file management tool — no rename/delete/move capabilities
- NOT auto-updating — requires re-running the scan script to refresh data
