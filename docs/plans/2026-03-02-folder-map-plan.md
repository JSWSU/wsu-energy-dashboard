# Energy Group Folder Map — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a single-file webapp that visualizes the `\\fais007\ENERGY GROUP` network share as an interactive treemap with an audit findings table.

**Architecture:** Self-contained HTML file (`folder-map.html`) with inline CSS/JS, using Chart.js + chartjs-chart-treemap plugin. Folder data embedded as JSON from a bash scan script. Two tabs: Storage Map (treemap with drill-down) and Audit Findings (sortable/filterable table).

**Tech Stack:** HTML/CSS/JS (inline), Chart.js v4.4.7 (local), chartjs-chart-treemap v3.1.0 (CDN), WSU CSS design system.

---

### Task 1: Write the Folder Scan Script

**Files:**
- Create: `scan-energy-share.sh`

**Step 1: Write the scan script**

Create `scan-energy-share.sh` in the repo root. The script must:
- Accept the share path as argument (default: `//fais007/ENERGY GROUP`)
- Use `find` to walk the tree, collecting: path, size, file count, last modified date
- Build a nested JSON tree (depth 4, aggregate beyond that)
- Build the audit arrays: duplicates, deep nesting (>5 levels), legacy formats (KVA, EU, WKS, WK1, WPS, rdb), large files (>10MB), empty folders, old files (not modified since 2020-01-01)
- Output `folder-scan.json` to the repo root
- The script must be READ-ONLY on the share — no writes, no modifications

The scan collects raw data via `find`, then a Python helper (inline heredoc) processes it into the nested JSON structure. Python is available on John's PC and handles JSON generation far better than bash alone.

Script structure:
```bash
#!/bin/bash
SHARE="${1:-//fais007/ENERGY GROUP}"
OUTFILE="folder-scan.json"

echo "Scanning $SHARE ..."

# Step A: Collect all entries (dirs and files) with size, date, type
find "$SHARE" -mindepth 1 \( -type f -o -type d \) -printf '%y\t%s\t%T@\t%p\n' 2>/dev/null > /tmp/folder-scan-raw.txt

echo "Found $(wc -l < /tmp/folder-scan-raw.txt) entries"

# Step B: Python processes raw data into nested JSON
python3 << 'PYEOF'
import json, os, sys
from datetime import datetime
from collections import defaultdict

RAW_FILE = '/tmp/folder-scan-raw.txt'
MAX_DEPTH = 4
# ... (full Python script in implementation)
PYEOF

echo "Wrote $OUTFILE"
```

The Python section:
1. Parses each line from the raw find output
2. Builds a tree dict keyed by path components
3. At depth > MAX_DEPTH, aggregates children into a single `"(other)"` node
4. Computes roll-up sizes and file counts per directory
5. Scans for audit findings (legacy extensions, large files, empty dirs, deep paths, old files)
6. Detects potential duplicates by finding directories/files with identical names at different paths
7. Outputs the full JSON structure matching the design doc schema

**Step 2: Make script executable and verify it runs**

Run: `chmod +x scan-energy-share.sh && bash scan-energy-share.sh`
Expected: Script outputs progress, creates `folder-scan.json` with valid JSON. Verify with `python3 -c "import json; d=json.load(open('folder-scan.json')); print(d['totalFiles'], 'files,', len(d['audit']['largeFiles']), 'large files found')"`

**Step 3: Commit**

```bash
git add scan-energy-share.sh
git commit -m "feat: add folder scan script for Energy Group share"
```

---

### Task 2: Run the Scan and Validate Data

**Files:**
- Uses: `scan-energy-share.sh`
- Creates: `folder-scan.json` (temporary, will be embedded into HTML)

**Step 1: Run the full scan**

Run: `bash scan-energy-share.sh "//fais007/ENERGY GROUP"`

This takes 2-5 minutes over the network. Wait for completion.

**Step 2: Validate the output**

Run:
```bash
python3 -c "
import json
d = json.load(open('folder-scan.json'))
print('Scan date:', d['scanDate'])
print('Total size:', round(d['totalSize']/1e9, 1), 'GB')
print('Total files:', d['totalFiles'])
print('Max depth:', d['maxDepth'])
print('Tree children:', len(d['tree']['children']))
print('Audit findings:')
for k, v in d['audit'].items():
    print(f'  {k}: {len(v)}')
"
```

Expected output should roughly match:
- Total size: ~30.3 GB
- Total files: ~58,685
- Tree children: 24 (top-level folders)
- Audit findings across all categories

**Step 3: Spot-check specific findings**

Verify these known findings appear:
- `largeFiles` includes the 55 MB water meter PDF
- `emptyFolders` includes `Waller Hall`
- `deepNesting` includes paths 18 levels deep in `ECS Enercon SCADA`
- `legacyFormats` includes KVA and WKS files

Do NOT commit `folder-scan.json` — it will be embedded into the HTML file in Task 5.

---

### Task 3: Build HTML Skeleton with CSS and Dark Mode

**Files:**
- Create: `folder-map.html`

**Step 1: Create the HTML file with full CSS**

Create `folder-map.html` in the repo root with:

1. `<!DOCTYPE html>` with `<html lang="en">`
2. `<head>` with:
   - Meta charset + viewport
   - Title: "WSU Energy Group — Folder Map"
   - `<script src="chart.umd.min.js"></script>`
   - `<script src="https://cdn.jsdelivr.net/npm/chartjs-chart-treemap@3.1.0"></script>`
   - Inline `<style>` with all CSS

3. CSS must include:
   - All `:root` variables from CLAUDE.md (--primary through --info-text)
   - All `html.dark` overrides
   - Standard classes: `.container`, `.card`, `.nav-tabs`, `.nav-tab`, `.kpi-grid`, `.kpi-card`, `.dark-toggle`, `.filter-bar`, `.filter-btn`, `.table-wrap`, `.total-row`, `.status-pill`, `.search-bar`
   - Header with crimson gradient (same as metering.html)
   - Treemap-specific: `.breadcrumb` (flex row with clickable path segments), `.treemap-wrap` (container for the canvas)
   - Audit table: `.audit-table` with standard table styling
   - Status pill variants for each audit category: `.pill-duplicate`, `.pill-deep`, `.pill-legacy`, `.pill-large`, `.pill-empty`, `.pill-old`

4. `<body>` structure:
   ```html
   <header>
     <div class="header-text">
       <h1>Energy Group Folder Map</h1>
       <p>\\fais007\ENERGY GROUP — Scanned [date]</p>
     </div>
     <div class="header-actions">
       <a href="metering.html">Metering</a>
       <a href="water-conservation.html">Water Conservation</a>
       <div class="dark-toggle">
         <span class="dark-toggle-label">Dark Mode</span>
         <button class="dark-toggle-switch" id="darkToggle"></button>
       </div>
     </div>
   </header>
   <div class="container">
     <div class="nav-tabs">
       <button class="nav-tab active" data-tab="map">Storage Map</button>
       <button class="nav-tab" data-tab="audit">Audit Findings</button>
     </div>
     <div class="section active" id="sec-map">
       <!-- KPI cards + treemap go here in Task 4-5 -->
       <p>Storage Map (coming soon)</p>
     </div>
     <div class="section" id="sec-audit">
       <!-- Audit table goes here in Task 6 -->
       <p>Audit Findings (coming soon)</p>
     </div>
   </div>
   ```

5. Inline `<script>` with:
   - Dark mode toggle (localStorage key: `wsuFolderMapDark`)
   - Tab switching handler (same pattern as metering.html)
   - `applyChartTheme()` function
   - `const chartInstances = [];`
   - Placeholder `const SCAN_DATA = {};`

**Step 2: Verify in browser**

Open `folder-map.html` in a browser.
Expected: WSU crimson header, two tab buttons, dark mode toggle works, tabs switch between placeholder content. No console errors.

**Step 3: Commit**

```bash
git add folder-map.html
git commit -m "feat: add folder-map.html skeleton with CSS and dark mode"
```

---

### Task 4: Build KPI Cards

**Files:**
- Modify: `folder-map.html`

**Step 1: Add KPI card HTML to the Storage Map section**

Inside `#sec-map`, before the treemap area, add:

```html
<div class="kpi-grid">
  <div class="kpi-card" style="border-left-color: var(--primary);">
    <div class="kpi-label">Total Size</div>
    <div class="kpi-value" id="kpiSize">—</div>
    <div class="kpi-sub">across entire share</div>
    <div class="kpi-tooltip">Combined size of all files and folders</div>
  </div>
  <div class="kpi-card" style="border-left-color: var(--accent);">
    <div class="kpi-label">Total Files</div>
    <div class="kpi-value" id="kpiFiles">—</div>
    <div class="kpi-sub">all file types</div>
    <div class="kpi-tooltip">Count of all files (not folders)</div>
  </div>
  <div class="kpi-card" style="border-left-color: var(--red);">
    <div class="kpi-label">Max Depth</div>
    <div class="kpi-value" id="kpiDepth">—</div>
    <div class="kpi-sub">deepest nesting level</div>
    <div class="kpi-tooltip">Deepest subfolder nesting in the hierarchy</div>
  </div>
  <div class="kpi-card" style="border-left-color: var(--blue);">
    <div class="kpi-label">Date Span</div>
    <div class="kpi-value" id="kpiDates">—</div>
    <div class="kpi-sub">oldest to newest file</div>
    <div class="kpi-tooltip">Range from oldest to newest last-modified date</div>
  </div>
</div>
```

**Step 2: Add JS to populate KPI cards from SCAN_DATA**

In the `<script>` section, add a function:

```javascript
function fmtBytes(bytes) {
  if (bytes >= 1e9) return (bytes / 1e9).toFixed(1) + ' GB';
  if (bytes >= 1e6) return (bytes / 1e6).toFixed(1) + ' MB';
  if (bytes >= 1e3) return (bytes / 1e3).toFixed(1) + ' KB';
  return bytes + ' B';
}

function populateKPIs() {
  document.getElementById('kpiSize').textContent = fmtBytes(SCAN_DATA.totalSize);
  document.getElementById('kpiFiles').textContent = SCAN_DATA.totalFiles.toLocaleString();
  document.getElementById('kpiDepth').textContent = SCAN_DATA.maxDepth + ' levels';
  document.getElementById('kpiDates').textContent = SCAN_DATA.dateRange.oldest + '–' + SCAN_DATA.dateRange.newest;
}
```

Call `populateKPIs()` in the init block.

**Step 3: Add test data to SCAN_DATA**

Temporarily populate `SCAN_DATA` with minimal test values:
```javascript
const SCAN_DATA = {
  scanDate: "2026-03-02",
  totalSize: 30300000000,
  totalFiles: 58685,
  maxDepth: 18,
  dateRange: { oldest: "1983", newest: "2026" },
  tree: { name: "ENERGY GROUP", size: 30300000000, files: 58685, children: [] },
  audit: { duplicates: [], deepNesting: [], legacyFormats: [], largeFiles: [], emptyFolders: [], oldFiles: [] }
};
```

**Step 4: Verify in browser**

Open `folder-map.html`. Expected: Four KPI cards showing "30.3 GB", "58,685", "18 levels", "1983–2026". Dark mode toggle still works.

**Step 5: Commit**

```bash
git add folder-map.html
git commit -m "feat: add KPI cards to folder map"
```

---

### Task 5: Build Treemap View with Drill-Down

**Files:**
- Modify: `folder-map.html`

**Step 1: Add treemap HTML structure**

Below the KPI grid in `#sec-map`, add:

```html
<div class="card">
  <div class="breadcrumb" id="breadcrumb">
    <span class="breadcrumb-item active">ENERGY GROUP</span>
  </div>
  <div class="treemap-wrap">
    <canvas id="treemapChart"></canvas>
  </div>
</div>
```

Add CSS for breadcrumb:
```css
.breadcrumb { display: flex; gap: 0.25rem; align-items: center; padding: 0.75rem 1rem; font-size: 0.85rem; flex-wrap: wrap; }
.breadcrumb-item { color: var(--text-light); cursor: pointer; }
.breadcrumb-item:hover { color: var(--primary); text-decoration: underline; }
.breadcrumb-item.active { color: var(--text); font-weight: 600; cursor: default; }
.breadcrumb-sep { color: var(--text-light); margin: 0 0.25rem; }
.treemap-wrap { position: relative; width: 100%; height: 500px; }
.treemap-wrap canvas { width: 100% !important; height: 100% !important; }
```

**Step 2: Implement treemap rendering with drill-down**

Add to the `<script>` section:

```javascript
let treemapChart = null;
let treemapPath = []; // stack of node references for drill-down

// Color assignment: hash folder name to a color from a palette
const TREEMAP_COLORS = [
  '#981e32', '#c69214', '#2563eb', '#059669', '#7c3aed',
  '#dc2626', '#0891b2', '#ca8a04', '#6366f1', '#16a34a',
  '#e11d48', '#0d9488', '#9333ea', '#ea580c', '#4f46e5'
];

function nodeColor(name, depth) {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = ((hash << 5) - hash) + name.charCodeAt(i);
  const idx = Math.abs(hash) % TREEMAP_COLORS.length;
  // Lighten at deeper levels
  return TREEMAP_COLORS[idx] + (depth === 0 ? 'cc' : depth === 1 ? 'aa' : '88');
}

function renderTreemap(node) {
  const ctx = document.getElementById('treemapChart').getContext('2d');
  if (treemapChart) {
    treemapChart.destroy();
    const idx = chartInstances.indexOf(treemapChart);
    if (idx > -1) chartInstances.splice(idx, 1);
  }

  const children = (node.children || []).map(c => ({
    name: c.name,
    size: c.size,
    files: c.files,
    modified: c.modified,
    hasChildren: !!(c.children && c.children.length)
  }));

  if (children.length === 0) return;

  treemapChart = new Chart(ctx, {
    type: 'treemap',
    data: {
      datasets: [{
        tree: children,
        key: 'size',
        groups: ['name'],
        spacing: 2,
        borderWidth: 2,
        borderColor: 'rgba(255,255,255,0.5)',
        backgroundColor: function(ctx) {
          if (!ctx.raw || !ctx.raw._data) return '#ccc';
          return nodeColor(ctx.raw._data.name, treemapPath.length);
        },
        labels: {
          display: true,
          align: 'left',
          position: 'top',
          color: '#fff',
          font: { size: 12, weight: 'bold' },
          overflow: 'fit',
          formatter: function(ctx) {
            if (!ctx.raw || !ctx.raw._data) return '';
            const d = ctx.raw._data;
            return d.name + '\n' + fmtBytes(d.size);
          }
        },
        captions: { display: false }
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            title: function(items) {
              if (!items.length || !items[0].raw._data) return '';
              return items[0].raw._data.name;
            },
            label: function(item) {
              if (!item.raw._data) return '';
              const d = item.raw._data;
              const lines = ['Size: ' + fmtBytes(d.size)];
              if (d.files !== undefined) lines.push('Files: ' + d.files.toLocaleString());
              if (d.modified) lines.push('Modified: ' + d.modified);
              if (d.hasChildren) lines.push('Click to drill down');
              return lines;
            }
          }
        }
      },
      onClick: function(evt, elements) {
        if (!elements.length) return;
        const el = elements[0];
        const name = el.element.$context.raw._data.name;
        // Find the matching child node in our tree
        const currentNode = treemapPath.length === 0 ? SCAN_DATA.tree : treemapPath[treemapPath.length - 1];
        const child = (currentNode.children || []).find(c => c.name === name);
        if (child && child.children && child.children.length > 0) {
          treemapPath.push(child);
          renderTreemap(child);
          updateBreadcrumb();
        }
      }
    }
  });
  chartInstances.push(treemapChart);
}

function updateBreadcrumb() {
  const bc = document.getElementById('breadcrumb');
  let html = '';
  // Root
  html += `<span class="breadcrumb-item${treemapPath.length === 0 ? ' active' : ''}" data-depth="-1">ENERGY GROUP</span>`;
  treemapPath.forEach((node, i) => {
    html += '<span class="breadcrumb-sep">/</span>';
    const isLast = i === treemapPath.length - 1;
    html += `<span class="breadcrumb-item${isLast ? ' active' : ''}" data-depth="${i}">${node.name}</span>`;
  });
  bc.innerHTML = html;

  // Bind click handlers for non-active breadcrumb items
  bc.querySelectorAll('.breadcrumb-item:not(.active)').forEach(el => {
    el.addEventListener('click', function() {
      const depth = parseInt(this.dataset.depth);
      if (depth === -1) {
        treemapPath = [];
        renderTreemap(SCAN_DATA.tree);
      } else {
        treemapPath = treemapPath.slice(0, depth + 1);
        renderTreemap(treemapPath[treemapPath.length - 1]);
      }
      updateBreadcrumb();
    });
  });
}
```

Call `renderTreemap(SCAN_DATA.tree)` in the init block.

**Step 3: Add realistic test data to SCAN_DATA.tree**

Replace the empty `children: []` with at least 5-6 representative folders with sizes matching the scan results (Energy Services Admin 27GB, Skyspark 1.6GB, Energy Data By Year 606MB, etc.). Include 2-3 levels of nesting for drill-down testing.

**Step 4: Verify in browser**

Open `folder-map.html`. Expected:
- Treemap renders showing blocks proportional to folder size
- Energy Services Admin dominates the view
- Hovering shows tooltip with name, size, file count
- Clicking a folder drills down, breadcrumb updates
- Clicking breadcrumb segments navigates back up
- Dark mode toggle updates chart colors

**Step 5: Commit**

```bash
git add folder-map.html
git commit -m "feat: add treemap view with drill-down navigation"
```

---

### Task 6: Build Audit Findings Table with Filters

**Files:**
- Modify: `folder-map.html`

**Step 1: Add audit table HTML to the Audit section**

Replace the placeholder in `#sec-audit` with:

```html
<div class="card">
  <h2>Audit Findings</h2>
  <div class="info-box">
    <strong>Summary:</strong> <span id="auditSummary">Loading...</span>
  </div>
  <input type="text" class="search-bar" id="auditSearch" placeholder="Search by path...">
  <div class="filter-bar" id="auditFilterBar">
    <button class="filter-btn active" data-filter="all">All</button>
    <button class="filter-btn" data-filter="duplicate">Duplicates</button>
    <button class="filter-btn" data-filter="deep">Deep Nesting</button>
    <button class="filter-btn" data-filter="legacy">Legacy Formats</button>
    <button class="filter-btn" data-filter="large">Large Files</button>
    <button class="filter-btn" data-filter="empty">Empty Folders</button>
    <button class="filter-btn" data-filter="old">Old Files</button>
  </div>
  <div class="table-wrap">
    <table class="audit-table">
      <thead id="auditThead"><tr></tr></thead>
      <tbody id="auditTbody"></tbody>
    </table>
  </div>
</div>
```

**Step 2: Add status pill CSS for each category**

```css
.status-pill {
  display: inline-block; padding: 0.15rem 0.5rem; border-radius: 999px;
  font-size: 0.7rem; font-weight: 600; text-transform: uppercase;
}
.pill-duplicate { background: #fef3c7; color: #92400e; }
.pill-deep { background: #fce7f3; color: #9d174d; }
.pill-legacy { background: #fee2e2; color: #991b1b; }
.pill-large { background: #dbeafe; color: #1e40af; }
.pill-empty { background: #e5e7eb; color: #374151; }
.pill-old { background: #f3e8ff; color: #6b21a8; }
html.dark .pill-duplicate { background: #78350f; color: #fde68a; }
html.dark .pill-deep { background: #831843; color: #fbcfe8; }
html.dark .pill-legacy { background: #7f1d1d; color: #fecaca; }
html.dark .pill-large { background: #1e3a5f; color: #93c5fd; }
html.dark .pill-empty { background: #374151; color: #d1d5db; }
html.dark .pill-old { background: #4c1d95; color: #e9d5ff; }
```

**Step 3: Implement audit table rendering with sort, filter, search**

```javascript
const AUDIT_COLS = [
  { key: 'category', label: 'Category', align: 'left', sortable: true },
  { key: 'path', label: 'Path', align: 'left', sortable: true },
  { key: 'size', label: 'Size', align: 'right', sortable: true, valFn: r => r.sizeBytes },
  { key: 'files', label: 'Files', align: 'right', sortable: true },
  { key: 'modified', label: 'Last Modified', align: 'left', sortable: true },
  { key: 'details', label: 'Details', align: 'left', sortable: false }
];

function buildAuditRows() {
  const rows = [];
  const a = SCAN_DATA.audit;

  (a.duplicates || []).forEach(d => rows.push({
    category: 'duplicate', pill: 'pill-duplicate', label: 'Duplicate',
    path: d.path, sizeBytes: d.size, size: fmtBytes(d.size),
    files: d.files || '', modified: d.modified || '', details: d.details || 'Duplicate name found'
  }));
  (a.deepNesting || []).forEach(d => rows.push({
    category: 'deep', pill: 'pill-deep', label: 'Deep Nesting',
    path: d.path, sizeBytes: d.size || 0, size: d.size ? fmtBytes(d.size) : '—',
    files: d.files || '', modified: d.modified || '', details: d.depth + ' levels deep'
  }));
  (a.legacyFormats || []).forEach(d => rows.push({
    category: 'legacy', pill: 'pill-legacy', label: 'Legacy',
    path: d.path, sizeBytes: d.size || 0, size: d.size ? fmtBytes(d.size) : '—',
    files: '', modified: d.modified || '', details: d.extension + ' format'
  }));
  (a.largeFiles || []).forEach(d => rows.push({
    category: 'large', pill: 'pill-large', label: 'Large File',
    path: d.path, sizeBytes: d.size, size: fmtBytes(d.size),
    files: '', modified: d.modified || '', details: fmtBytes(d.size) + ' file'
  }));
  (a.emptyFolders || []).forEach(d => rows.push({
    category: 'empty', pill: 'pill-empty', label: 'Empty',
    path: d.path, sizeBytes: 0, size: '0 B',
    files: '0', modified: d.modified || '', details: 'Empty folder'
  }));
  (a.oldFiles || []).forEach(d => rows.push({
    category: 'old', pill: 'pill-old', label: 'Old',
    path: d.path, sizeBytes: d.size || 0, size: d.size ? fmtBytes(d.size) : '—',
    files: '', modified: d.modified || '', details: 'Not modified since 2020'
  }));

  return rows;
}

let auditSortCol = 'category';
let auditSortDir = 'asc';
let auditFilter = 'all';
let auditSearch = '';

function renderAuditTable() {
  const allRows = buildAuditRows();

  // Filter
  let rows = auditFilter === 'all' ? allRows : allRows.filter(r => r.category === auditFilter);
  // Search
  if (auditSearch) {
    const q = auditSearch.toLowerCase();
    rows = rows.filter(r => r.path.toLowerCase().includes(q) || r.details.toLowerCase().includes(q));
  }

  // Sort
  rows.sort((a, b) => {
    let va = a[auditSortCol], vb = b[auditSortCol];
    if (auditSortCol === 'size') { va = a.sizeBytes; vb = b.sizeBytes; }
    if (typeof va === 'number' && typeof vb === 'number') return auditSortDir === 'asc' ? va - vb : vb - va;
    return auditSortDir === 'asc' ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
  });

  // Summary
  document.getElementById('auditSummary').textContent =
    rows.length + ' findings' + (auditFilter !== 'all' ? ' (' + auditFilter + ')' : '') +
    ' — ' + fmtBytes(rows.reduce((s, r) => s + (r.sizeBytes || 0), 0)) + ' total';

  // Header
  const thead = document.getElementById('auditThead');
  thead.innerHTML = '<tr>' + AUDIT_COLS.map(c => {
    let arrow = '▴▾';
    if (c.sortable && auditSortCol === c.key) arrow = auditSortDir === 'asc' ? '▲' : '▼';
    return `<th style="text-align:${c.align}" class="${c.sortable ? 'th-sort' : ''}" data-col="${c.key}">${c.label}${c.sortable ? ' <span class="sort-arrow">' + arrow + '</span>' : ''}</th>`;
  }).join('') + '</tr>';

  // Bind sort
  thead.querySelectorAll('.th-sort').forEach(th => {
    th.style.cursor = 'pointer';
    th.addEventListener('click', function() {
      const col = this.dataset.col;
      if (auditSortCol === col) auditSortDir = auditSortDir === 'asc' ? 'desc' : 'asc';
      else { auditSortCol = col; auditSortDir = 'asc'; }
      renderAuditTable();
    });
  });

  // Body
  const tbody = document.getElementById('auditTbody');
  tbody.innerHTML = rows.slice(0, 500).map(r => {
    const shortPath = r.path.length > 80 ? '...' + r.path.slice(-77) : r.path;
    return `<tr>
      <td style="text-align:left"><span class="status-pill ${r.pill}">${r.label}</span></td>
      <td style="text-align:left" title="${r.path}">${shortPath}</td>
      <td style="text-align:right">${r.size}</td>
      <td style="text-align:right">${r.files}</td>
      <td style="text-align:left">${r.modified}</td>
      <td style="text-align:left">${r.details}</td>
    </tr>`;
  }).join('');

  if (rows.length > 500) {
    tbody.innerHTML += `<tr class="total-row"><td colspan="6" style="text-align:center">Showing 500 of ${rows.length} findings. Use search to narrow results.</td></tr>`;
  }
}
```

**Step 4: Wire up filter buttons and search**

```javascript
document.querySelectorAll('#auditFilterBar .filter-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('#auditFilterBar .filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    auditFilter = btn.dataset.filter;
    renderAuditTable();
  });
});
document.getElementById('auditSearch').addEventListener('input', function() {
  auditSearch = this.value;
  renderAuditTable();
});
```

Call `renderAuditTable()` in the init block.

**Step 5: Add test audit data to SCAN_DATA**

Add representative entries to each audit category array in the test SCAN_DATA.

**Step 6: Verify in browser**

Open `folder-map.html`, click the "Audit Findings" tab. Expected:
- Filter buttons work (clicking "Large Files" shows only large files)
- Search box filters by path
- Column headers sort on click
- Status pills show correct colors
- Summary text updates with count and total size
- Dark mode toggle changes pill colors

**Step 7: Commit**

```bash
git add folder-map.html
git commit -m "feat: add audit findings table with sort/filter/search"
```

---

### Task 7: Embed Real Scan Data and Final Integration

**Files:**
- Modify: `folder-map.html`
- Uses: `folder-scan.json` (from Task 2)

**Step 1: Embed scan data into the HTML file**

Read the contents of `folder-scan.json` and replace the test `SCAN_DATA` object in `folder-map.html` with the real data:

```javascript
const SCAN_DATA = /* paste contents of folder-scan.json here */;
```

Also update the header subtitle to show the actual scan date:
```html
<p>\\fais007\ENERGY GROUP — Scanned 2026-03-02</p>
```

**Step 2: Verify treemap with real data**

Open `folder-map.html`. Expected:
- Treemap shows all 24 top-level folders
- Energy Services Admin dominates (89%)
- Click to drill into Energy Services Admin → see its subfolders
- Breadcrumb navigation works at all levels
- KPI cards show correct totals

**Step 3: Verify audit table with real data**

Click "Audit Findings" tab. Expected:
- All filter categories have findings
- "Large Files" shows 20+ entries including the 55 MB PDF
- "Empty Folders" shows Waller Hall
- "Deep Nesting" shows paths 18 levels deep
- "Legacy Formats" shows KVA, WKS, etc.
- Search works (try "Meter Reads" to find duplicates)
- Sort by Size descending puts largest files first

**Step 4: Clean up folder-scan.json**

Add `folder-scan.json` to `.gitignore` (it's embedded in the HTML now):

```
# Folder scan intermediate file
folder-scan.json
```

**Step 5: Commit**

```bash
git add folder-map.html .gitignore
git commit -m "feat: embed real scan data into folder map webapp"
```

---

### Task 8: Push to GitHub and Verify Live

**Files:** None modified

**Step 1: Push to main**

```bash
git push origin main
```

**Step 2: Verify on GitHub Pages**

Wait 1-2 minutes for GitHub Pages deploy. Open:
`https://jswsu.github.io/wsu-energy-dashboard/folder-map.html`

Verify:
- Page loads without auth gate
- Treemap renders correctly
- Drill-down works
- Audit table loads with all findings
- Dark mode toggle works
- Links to Metering and Water Conservation dashboards work
- No console errors

**Step 3: Test on a colleague's machine**

Share the link with a team member and confirm they can access it.
