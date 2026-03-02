# UP Report Automation — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a "UP Report" tab to steam-plant.html that auto-fills ~60% of the monthly Utilities Production report from existing JSON data, accepts manual entry for remaining fields, and generates a formatted Excel file.

**Architecture:** Single new tab in the existing steam-plant.html dashboard. Reads `steam_plant.json` (already loaded) and `data.json` (new fetch) to auto-populate boiler/gas/generator/weather fields. Manual entry fields saved per-month in localStorage. SheetJS (already loaded) generates the output Excel with live formulas.

**Tech Stack:** Vanilla JS, Chart.js (existing), SheetJS xlsx.min.js (existing), no build step

---

### Task 1: Add UP Report Tab Button and Empty Section

**Files:**
- Modify: `steam-plant.html:385-392` (nav tabs)
- Modify: `steam-plant.html:551` (before help section, add new section div)

**Step 1: Add the tab button**

Find the nav-tabs div (line ~385-392). Add a new button before the Help tab button:

```html
<button class="nav-tab" data-tab="up">UP Report</button>
```

The nav-tabs should now have 8 buttons: overview, gas, steam, runtime, water, data, **up**, help.

**Step 2: Add the empty section div**

Insert a new section div before `<div class="section" id="sec-help">` (line ~551):

```html
<div class="section" id="sec-up">
  <div class="card">
    <h2>Utilities Production (UP) Report Generator</h2>
    <p>Select a month and generate the monthly UP report Excel file.</p>
  </div>
</div>
```

**Step 3: Verify**

Open `steam-plant.html` in browser. Log in. Verify:
- "UP Report" tab button appears between "Data Mgmt" and "Help"
- Clicking it shows the placeholder content
- Other tabs still work

**Step 4: Commit**

```bash
git add steam-plant.html
git commit -m "feat: add empty UP Report tab to steam plant dashboard"
```

---

### Task 2: Load data.json and Store as Global

**Files:**
- Modify: `steam-plant.html` — near line 923 where `let DATA = null` is defined, and in the `init()` function near line 934

**Step 1: Add ENERGY_DATA global**

Near line 923, after `let DATA = null;`, add:

```javascript
let ENERGY_DATA = null;
```

**Step 2: Load data.json in init()**

In the `init()` function (line ~934), after loading steam_plant.json but before the cumulative delta computation, add a fetch for data.json:

```javascript
try {
  const eresp = await fetch('data.json');
  if (eresp.ok) ENERGY_DATA = await eresp.json();
} catch(e) { console.warn('data.json not loaded — UP Report electric/weather fields will be empty'); }
```

This is a soft dependency — the dashboard works without it, but UP Report fields from data.json will be empty.

**Step 3: Verify**

Open browser dev tools console. Reload the page. Type `ENERGY_DATA` — should show the data.json object with keys like `fy26`, `hdd`, `variance`, etc. If data.json fails to load, a warning appears in console but the dashboard still works.

**Step 4: Commit**

```bash
git add steam-plant.html
git commit -m "feat: load data.json for UP Report energy/weather fields"
```

---

### Task 3: UP Report Data Constants and Mapping

**Files:**
- Modify: `steam-plant.html` — add constants block after the COLORS object (line ~720)

**Step 1: Add the UP_MAP constant**

This is the core mapping from JSON data to UP report cells. Each entry defines: the UP report row/column, description, data source, and transform.

Insert this after the `COLORS` object and before `applyChartTheme()`:

```javascript
/* ── UP Report cell mapping ─────────────────────────────────────── */
const UP_BOILERS = ['b1','b2','b3','b4','b5'];
const UP_BOILER_LABELS = ['Boiler #1','Boiler #2','Boiler #3','Boiler #4','Boiler #5'];

// Map of UP report fields → steam_plant.json keys
// "delta" means use the _delta field (cumulative counter → monthly value)
const UP_AUTO = {
  // Row 3: Boiler Days = runtime_delta / 24
  b1_days: { key: 'b1_runtime', delta: true, divide: 24 },
  b2_days: { key: 'b2_runtime', delta: true, divide: 24 },
  b3_days: { key: 'b3_runtime_total', delta: true, divide: 24 },
  b4_days: { key: 'b4_runtime_total', delta: true, divide: 24 },
  b5_days: { key: 'b5_runtime_total', delta: true, divide: 24 },
  // Row 5: Lbs Steam by Gas
  b1_steam: { key: 'b1_steam_gas' },
  b2_steam: { key: 'b2_steam_gas' },
  b3_steam: { key: 'b3_steam_gas' },
  b4_steam: { key: 'b4_steam_gas' },
  b5_steam: { key: 'b5_steam_gas' },
  // Row 6: Lbs Steam by Oil (B3-B5 only)
  b3_steam_oil: { key: 'b3_steam_oil' },
  b4_steam_oil: { key: 'b4_steam_oil' },
  b5_steam_oil: { key: 'b5_steam_oil' },
  // Row 7: Oil Burned gallons (B3-B5 only)
  b3_oil: { key: 'b3_oil' },
  b4_oil: { key: 'b4_oil' },
  b5_oil: { key: 'b5_oil' },
  // Row 10: Boiler Gas Use (SCF)
  b1_gas: { key: 'b1_gas' },
  b2_gas: { key: 'b2_gas' },
  b3_gas: { key: 'b3_gas' },
  b4_gas: { key: 'b4_gas' },
  b5_gas: { key: 'b5_gas' },
  // Row 11: Generator Gas (SCF) — cumulative
  gen1_gas: { key: 'gen1_gas', delta: true },
  gen2_gas: { key: 'gen2_gas', delta: true },
  // Generator kWh — cumulative
  gen1_kwh: { key: 'gen1_kwh', delta: true },
  gen2_kwh: { key: 'gen2_kwh', delta: true },
  gen3_kwh: { key: 'gen3_kwh', delta: true },
  // Generator 3 fuel
  gen3_fuel: { key: 'gen3_fuel_gal', delta: true }
};

// Fiscal year month index: Jul=0, Aug=1, ..., Jun=11
function fyMonthIndex(monthStr) {
  const m = parseInt(monthStr.split('-')[1]);
  return m >= 7 ? m - 7 : m + 5;
}
```

**Step 2: Verify**

Open console, type `UP_AUTO.b1_steam` — should return `{ key: 'b1_steam_gas' }`. Type `fyMonthIndex('2025-07')` — should return `0`.

**Step 3: Commit**

```bash
git add steam-plant.html
git commit -m "feat: add UP Report data mapping constants"
```

---

### Task 4: Month Selector UI and Auto-Fill Display

**Files:**
- Modify: `steam-plant.html` — replace the placeholder content in `#sec-up` section, and add `renderUPTab()` function after the other render functions (after line ~1317)

**Step 1: Replace the sec-up HTML**

Replace the placeholder `<div class="section" id="sec-up">` content with the full tab structure:

```html
<div class="section" id="sec-up">
  <div class="card">
    <h2>Utilities Production (UP) Report Generator</h2>
    <div class="info-box" style="margin-bottom:1rem;">
      Select a month to auto-populate steam production, gas consumption, and generator data from the Steam Plant database. Fill in manual fields (gas costs, electric, water) from invoices, then generate the Excel report.
    </div>
    <div style="display:flex;align-items:center;gap:1rem;flex-wrap:wrap;margin-bottom:1.5rem;">
      <label for="upMonth" style="font-weight:600;">Report Month:</label>
      <select id="upMonth" style="padding:6px 12px;border:1px solid var(--border);border-radius:6px;background:var(--card-bg);color:var(--text);font-size:0.95rem;"></select>
      <button id="upLoadBtn" class="btn-sm primary">Load Data</button>
      <span id="upStatus" style="color:var(--text-light);font-size:0.85rem;"></span>
    </div>
  </div>

  <!-- Auto-filled section -->
  <div class="card" id="upAutoCard" style="display:none;">
    <h2>Auto-Populated Data <span style="font-size:0.75rem;color:var(--green);font-weight:400;">(from Steam Plant database)</span></h2>
    <div class="table-wrap">
      <table id="upAutoTable" class="data-table" style="font-size:0.85rem;">
        <thead id="upAutoHead"></thead>
        <tbody id="upAutoBody"></tbody>
      </table>
    </div>
  </div>

  <!-- Manual entry section -->
  <div class="card" id="upManualCard" style="display:none;">
    <h2>Manual Entry Fields <span style="font-size:0.75rem;color:var(--blue);font-weight:400;">(from invoices &amp; reports)</span></h2>

    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:1.5rem;">
      <!-- Gas & Fuel -->
      <fieldset style="border:1px solid var(--border);border-radius:8px;padding:1rem;">
        <legend style="font-weight:600;color:var(--primary);padding:0 0.5rem;">Gas &amp; Fuel Costs</legend>
        <div class="up-field"><label>Gas Delivered (MMBTU):</label><input type="number" id="up_gas_mmbtu" step="any" placeholder="From Kintec bill"></div>
        <div class="up-field"><label>Gas BTU/cuft:</label><input type="number" id="up_btu_cuft" step="any" placeholder="From BTU report"></div>
        <div class="up-field"><label>Gas Cost/Therm ($):</label><input type="number" id="up_gas_cost_therm" step="any" placeholder="From Kintec invoice"></div>
        <div class="up-field"><label>Oil Cost/Gallon ($):</label><input type="number" id="up_oil_cost_gal" step="any" placeholder="From Coleman invoice"></div>
      </fieldset>

      <!-- Weather -->
      <fieldset style="border:1px solid var(--border);border-radius:8px;padding:1rem;">
        <legend style="font-weight:600;color:var(--primary);padding:0 0.5rem;">Weather &amp; Steam Stats</legend>
        <div class="up-field"><label>Heating Degree Days:</label><input type="number" id="up_hdd" step="any" placeholder="Auto-filled if available"></div>
        <div class="up-field"><label>Cooling Degree Days:</label><input type="number" id="up_cdd" step="any" placeholder="Auto-filled if available"></div>
        <div class="up-field"><label>Max Lbs/Hr Steam:</label><input type="number" id="up_max_lbs_hr" step="any" placeholder="From operator log"></div>
        <div class="up-field"><label>Min Lbs/Hr Steam:</label><input type="number" id="up_min_lbs_hr" step="any" placeholder="From operator log"></div>
      </fieldset>

      <!-- Electric -->
      <fieldset style="border:1px solid var(--border);border-radius:8px;padding:1rem;">
        <legend style="font-weight:600;color:var(--primary);padding:0 0.5rem;">Avista Electric (per circuit)</legend>
        <div class="table-wrap">
          <table style="width:100%;font-size:0.85rem;" id="upElecTable">
            <thead>
              <tr><th>Circuit</th><th>kWh</th><th>Cost ($)</th><th>Peak KVA</th></tr>
            </thead>
            <tbody>
              <tr><td>MP-A (TUR-111)</td><td><input type="number" class="up-circ-kwh" step="any"></td><td><input type="number" class="up-circ-cost" step="any"></td><td><input type="number" class="up-circ-kva" step="any"></td></tr>
              <tr><td>MP-C (SPU124+TVW131)</td><td><input type="number" class="up-circ-kwh" step="any"></td><td><input type="number" class="up-circ-cost" step="any"></td><td><input type="number" class="up-circ-kva" step="any"></td></tr>
              <tr><td>MP-D (SPU-122)</td><td><input type="number" class="up-circ-kwh" step="any"></td><td><input type="number" class="up-circ-cost" step="any"></td><td><input type="number" class="up-circ-kva" step="any"></td></tr>
              <tr><td>MP-E (TUR-115)</td><td><input type="number" class="up-circ-kwh" step="any"></td><td><input type="number" class="up-circ-cost" step="any"></td><td><input type="number" class="up-circ-kva" step="any"></td></tr>
              <tr><td>MP-G (SPU-125)</td><td><input type="number" class="up-circ-kwh" step="any"></td><td><input type="number" class="up-circ-cost" step="any"></td><td><input type="number" class="up-circ-kva" step="any"></td></tr>
            </tbody>
          </table>
        </div>
        <div class="up-field" style="margin-top:0.75rem;"><label>Biotech kWh:</label><input type="number" id="up_biotech_kwh" step="any" placeholder="Route A meter"></div>
      </fieldset>

      <!-- Water -->
      <fieldset style="border:1px solid var(--border);border-radius:8px;padding:1rem;">
        <legend style="font-weight:600;color:var(--primary);padding:0 0.5rem;">Fresh Water (well readings)</legend>
        <div class="up-field"><label>Well #4 (gal):</label><input type="number" id="up_well4" step="any"></div>
        <div class="up-field"><label>Well #6 (gal):</label><input type="number" id="up_well6" step="any"></div>
        <div class="up-field"><label>Well #7 (gal):</label><input type="number" id="up_well7" step="any"></div>
        <div class="up-field"><label>Well #8 (gal):</label><input type="number" id="up_well8" step="any"></div>
        <div class="up-field"><label>Lbs Chlorine:</label><input type="number" id="up_chlorine" step="any"></div>
      </fieldset>

      <!-- Budget -->
      <fieldset style="border:1px solid var(--border);border-radius:8px;padding:1rem;">
        <legend style="font-weight:600;color:var(--primary);padding:0 0.5rem;">Budget &amp; Labor</legend>
        <div class="up-field"><label>Steam Plant Labor ($):</label><input type="number" id="up_labor" step="any"></div>
        <div class="up-field"><label>Goods &amp; Services ($):</label><input type="number" id="up_gs" step="any"></div>
      </fieldset>
    </div>

    <div style="margin-top:1.5rem;display:flex;gap:1rem;flex-wrap:wrap;">
      <button id="upSaveBtn" class="btn-sm primary">Save Manual Entries</button>
      <button id="upGenBtn" class="btn-sm primary" style="background:#059669;">Generate UP Report Excel</button>
      <span id="upSaveStatus" style="color:var(--green);font-size:0.85rem;"></span>
    </div>
  </div>

  <!-- Preview section -->
  <div class="card" id="upPreviewCard" style="display:none;">
    <h2>Report Preview</h2>
    <div class="info-box" style="margin-bottom:1rem;">
      <span style="display:inline-block;width:12px;height:12px;background:#dcfce7;border:1px solid #86efac;border-radius:2px;margin-right:4px;"></span> Auto-filled &nbsp;
      <span style="display:inline-block;width:12px;height:12px;background:#dbeafe;border:1px solid #93c5fd;border-radius:2px;margin-right:4px;"></span> Manual entry &nbsp;
      <span style="display:inline-block;width:12px;height:12px;background:#f3f4f6;border:1px solid #d1d5db;border-radius:2px;margin-right:4px;"></span> Calculated
    </div>
    <div class="table-wrap" id="upPreviewWrap"></div>
  </div>
</div>
```

**Step 2: Add UP-specific CSS**

In the `<style>` block (before the closing `</style>` tag, around line 342), add:

```css
.up-field { display:flex; align-items:center; gap:0.5rem; margin-bottom:0.5rem; }
.up-field label { min-width:160px; font-size:0.85rem; color:var(--text); }
.up-field input, #upElecTable input { width:100%; max-width:160px; padding:4px 8px; border:1px solid var(--border); border-radius:4px; background:var(--card-bg); color:var(--text); font-size:0.85rem; }
.up-field input:focus, #upElecTable input:focus { border-color:var(--primary); outline:none; }
#upElecTable input { max-width:110px; }
.up-auto { background:#dcfce7; }
html.dark .up-auto { background:#064e3b; }
.up-manual { background:#dbeafe; }
html.dark .up-manual { background:#1e3a5f; }
.up-calc { background:#f3f4f6; }
html.dark .up-calc { background:#1f2937; }
```

**Step 3: Add renderUPTab() function**

After the `renderWaterTab()` function (around line ~1317, before `renderDataManagement()`), add:

```javascript
/* ── UP Report Tab ──────────────────────────────────────────────── */
function renderUPTab() {
  const M = DATA.monthly;
  const sel = document.getElementById('upMonth');
  sel.innerHTML = '';
  // Populate month selector — most recent first
  const months = M.map(m => m.month).reverse();
  months.forEach(m => {
    const opt = document.createElement('option');
    opt.value = m;
    opt.textContent = monthLabel(m);
    sel.appendChild(opt);
  });

  document.getElementById('upLoadBtn').addEventListener('click', loadUPMonth);
  document.getElementById('upSaveBtn').addEventListener('click', saveUPManual);
  document.getElementById('upGenBtn').addEventListener('click', generateUPExcel);
}
```

**Step 4: Call renderUPTab() from init()**

In the `init()` function (around line ~970, where other render functions are called), add:

```javascript
renderUPTab();
```

**Step 5: Add stub functions** (so the page doesn't error)

```javascript
function loadUPMonth() { console.log('loadUPMonth stub'); }
function saveUPManual() { console.log('saveUPManual stub'); }
function generateUPExcel() { console.log('generateUPExcel stub'); }
```

**Step 6: Verify**

Open in browser. Click "UP Report" tab. Should see:
- Month selector with all months (most recent first)
- Load Data button
- No errors in console

Click "Load Data" — should log "loadUPMonth stub" in console.

**Step 7: Commit**

```bash
git add steam-plant.html
git commit -m "feat: add UP Report tab UI with month selector and manual entry form"
```

---

### Task 5: Implement loadUPMonth() — Auto-Fill and Manual Entry Loading

**Files:**
- Modify: `steam-plant.html` — replace the `loadUPMonth` stub function

**Step 1: Replace the loadUPMonth stub**

Replace `function loadUPMonth() { console.log('loadUPMonth stub'); }` with:

```javascript
let UP_CURRENT = null; // Holds the loaded UP data for current month

function loadUPMonth() {
  const monthStr = document.getElementById('upMonth').value;
  if (!monthStr) return;
  const M = DATA.monthly;
  const idx = M.findIndex(m => m.month === monthStr);
  if (idx < 0) { document.getElementById('upStatus').textContent = 'Month not found'; return; }

  const row = M[idx];
  const auto = {};

  // Resolve each auto-populated field
  for (const [field, cfg] of Object.entries(UP_AUTO)) {
    let val = 0;
    if (cfg.delta) {
      val = row[cfg.key + '_delta'] || 0;
    } else {
      val = row[cfg.key] || 0;
    }
    if (cfg.divide) val = val / cfg.divide;
    auto[field] = val;
  }

  // Compute totals
  auto.total_steam_gas = UP_BOILERS.reduce((s, b) => s + (auto[b + '_steam'] || 0), 0);
  auto.total_steam_oil = (auto.b3_steam_oil || 0) + (auto.b4_steam_oil || 0) + (auto.b5_steam_oil || 0);
  auto.total_steam = auto.total_steam_gas + auto.total_steam_oil;
  auto.total_oil_gal = (auto.b3_oil || 0) + (auto.b4_oil || 0) + (auto.b5_oil || 0);
  auto.total_gas_scf = UP_BOILERS.reduce((s, b) => s + (auto[b + '_gas'] || 0), 0);
  auto.total_days = UP_BOILERS.reduce((s, b) => s + (auto[b + '_days'] || 0), 0);

  // Load HDD/CDD from data.json if available
  auto.hdd = 0;
  auto.cdd = 0;
  if (ENERGY_DATA) {
    const mi = fyMonthIndex(monthStr);
    const [yr] = monthStr.split('-').map(Number);
    const mo = parseInt(monthStr.split('-')[1]);
    // Determine which FY dataset to use
    // FY26 = Jul 2025 - Jun 2026, data.json arrays index 0=Jul
    // We only have current FY in data.json, so check if month is in range
    if (ENERGY_DATA.hdd && ENERGY_DATA.hdd.fy26 && mi < ENERGY_DATA.hdd.fy26.length) {
      auto.hdd = ENERGY_DATA.hdd.fy26[mi] || 0;
    }
    if (ENERGY_DATA.variance && ENERGY_DATA.variance.fy26hdd) {
      // CDD not directly in data.json — set to 0, user enters manually
    }
  }

  UP_CURRENT = { month: monthStr, auto, manual: {} };

  // Display auto-filled table
  renderAutoTable(auto);

  // Load saved manual entries
  loadUPManual(monthStr);

  // Show cards
  document.getElementById('upAutoCard').style.display = '';
  document.getElementById('upManualCard').style.display = '';
  document.getElementById('upPreviewCard').style.display = '';
  document.getElementById('upStatus').textContent = 'Data loaded for ' + monthLabel(monthStr);

  // Populate HDD/CDD inputs if auto-available
  if (auto.hdd) document.getElementById('up_hdd').value = auto.hdd;
  if (auto.cdd) document.getElementById('up_cdd').value = auto.cdd;

  renderUPPreview();
}
```

**Step 2: Add renderAutoTable()**

```javascript
function renderAutoTable(auto) {
  const head = document.getElementById('upAutoHead');
  const body = document.getElementById('upAutoBody');
  head.innerHTML = '<tr><th></th>' + UP_BOILER_LABELS.map(b => '<th>' + b + '</th>').join('') + '<th>Total</th></tr>';

  const rows = [
    { label: 'Boiler Days', keys: UP_BOILERS.map(b => b + '_days'), total: 'total_days', dec: 1 },
    { label: 'Lbs Steam (Gas)', keys: UP_BOILERS.map(b => b + '_steam'), total: 'total_steam_gas', dec: 0 },
    { label: 'Lbs Steam (Oil)', keys: [null, null, 'b3_steam_oil', 'b4_steam_oil', 'b5_steam_oil'], total: 'total_steam_oil', dec: 0 },
    { label: 'Oil Burned (gal)', keys: [null, null, 'b3_oil', 'b4_oil', 'b5_oil'], total: 'total_oil_gal', dec: 0 },
    { label: 'Gas Use (SCF)', keys: UP_BOILERS.map(b => b + '_gas'), total: 'total_gas_scf', dec: 0 },
  ];

  body.innerHTML = rows.map(r => {
    const cells = r.keys.map(k => {
      if (!k) return '<td style="text-align:right;color:var(--text-light);">—</td>';
      const v = auto[k] || 0;
      return '<td style="text-align:right;" class="up-auto">' + fmt(v, r.dec) + '</td>';
    }).join('');
    const totalVal = auto[r.total] || 0;
    return '<tr><td style="font-weight:600;">' + r.label + '</td>' + cells + '<td style="text-align:right;font-weight:600;" class="up-auto">' + fmt(totalVal, r.dec) + '</td></tr>';
  }).join('');

  // Generator row
  body.innerHTML += '<tr style="border-top:2px solid var(--border);"><td style="font-weight:600;">Generator kWh</td>'
    + '<td style="text-align:right;" class="up-auto">' + fmt(auto.gen1_kwh || 0, 0) + '</td>'
    + '<td style="text-align:right;" class="up-auto">' + fmt(auto.gen2_kwh || 0, 0) + '</td>'
    + '<td style="text-align:right;" class="up-auto">' + fmt(auto.gen3_kwh || 0, 0) + '</td>'
    + '<td colspan="2"></td>'
    + '<td style="text-align:right;font-weight:600;" class="up-auto">' + fmt((auto.gen1_kwh||0)+(auto.gen2_kwh||0)+(auto.gen3_kwh||0), 0) + '</td></tr>';

  body.innerHTML += '<tr><td style="font-weight:600;">Generator Gas (SCF)</td>'
    + '<td style="text-align:right;" class="up-auto">' + fmt(auto.gen1_gas || 0, 0) + '</td>'
    + '<td style="text-align:right;" class="up-auto">' + fmt(auto.gen2_gas || 0, 0) + '</td>'
    + '<td colspan="3"></td>'
    + '<td style="text-align:right;font-weight:600;" class="up-auto">' + fmt((auto.gen1_gas||0)+(auto.gen2_gas||0), 0) + '</td></tr>';
}
```

**Step 3: Add renderUPPreview stub** (to be implemented in Task 7)

```javascript
function renderUPPreview() {
  // Will be implemented in Task 7
  document.getElementById('upPreviewWrap').innerHTML = '<p style="color:var(--text-light);">Preview will appear here after implementation.</p>';
}
```

**Step 4: Verify**

Open browser. Go to UP Report tab. Select "July 2025" from dropdown. Click "Load Data".
- Auto-Populated Data card should appear with a table showing boiler days, steam lbs, gas SCF, etc.
- Values should match what the Overview/Gas tabs show for July 2025
- Generator kWh and Gas rows should appear below the boiler data
- Manual entry form should be visible (empty fields)

**Step 5: Commit**

```bash
git add steam-plant.html
git commit -m "feat: implement loadUPMonth with auto-fill table from steam plant data"
```

---

### Task 6: Implement Manual Entry Save/Load with localStorage

**Files:**
- Modify: `steam-plant.html` — replace the `saveUPManual` stub and add `loadUPManual()`

**Step 1: Define the manual field IDs**

Add this constant near the other UP constants:

```javascript
const UP_MANUAL_FIELDS = [
  'up_gas_mmbtu', 'up_btu_cuft', 'up_gas_cost_therm', 'up_oil_cost_gal',
  'up_hdd', 'up_cdd', 'up_max_lbs_hr', 'up_min_lbs_hr',
  'up_biotech_kwh',
  'up_well4', 'up_well6', 'up_well7', 'up_well8', 'up_chlorine',
  'up_labor', 'up_gs'
];
```

**Step 2: Implement saveUPManual()**

Replace the stub with:

```javascript
function saveUPManual() {
  if (!UP_CURRENT) return;
  const data = {};
  // Save scalar fields
  UP_MANUAL_FIELDS.forEach(id => {
    const el = document.getElementById(id);
    if (el) data[id] = el.value ? parseFloat(el.value) : null;
  });
  // Save circuit table (5 rows x 3 columns)
  data.circuit_kwh = [...document.querySelectorAll('.up-circ-kwh')].map(el => el.value ? parseFloat(el.value) : null);
  data.circuit_cost = [...document.querySelectorAll('.up-circ-cost')].map(el => el.value ? parseFloat(el.value) : null);
  data.circuit_kva = [...document.querySelectorAll('.up-circ-kva')].map(el => el.value ? parseFloat(el.value) : null);

  localStorage.setItem('wsu_up_manual_' + UP_CURRENT.month, JSON.stringify(data));
  UP_CURRENT.manual = data;
  document.getElementById('upSaveStatus').textContent = 'Saved ' + new Date().toLocaleTimeString();
  renderUPPreview();
}
```

**Step 3: Implement loadUPManual()**

```javascript
function loadUPManual(monthStr) {
  const saved = localStorage.getItem('wsu_up_manual_' + monthStr);
  if (!saved) {
    // Clear all manual fields
    UP_MANUAL_FIELDS.forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
    document.querySelectorAll('.up-circ-kwh, .up-circ-cost, .up-circ-kva').forEach(el => el.value = '');
    // Try loading static values (oil cost carries forward)
    const statics = localStorage.getItem('wsu_up_static');
    if (statics) {
      const s = JSON.parse(statics);
      if (s.up_oil_cost_gal) document.getElementById('up_oil_cost_gal').value = s.up_oil_cost_gal;
    }
    if (UP_CURRENT) UP_CURRENT.manual = {};
    return;
  }
  const data = JSON.parse(saved);
  // Restore scalar fields
  UP_MANUAL_FIELDS.forEach(id => {
    const el = document.getElementById(id);
    if (el && data[id] != null) el.value = data[id];
    else if (el) el.value = '';
  });
  // Restore circuit table
  if (data.circuit_kwh) document.querySelectorAll('.up-circ-kwh').forEach((el, i) => el.value = data.circuit_kwh[i] ?? '');
  if (data.circuit_cost) document.querySelectorAll('.up-circ-cost').forEach((el, i) => el.value = data.circuit_cost[i] ?? '');
  if (data.circuit_kva) document.querySelectorAll('.up-circ-kva').forEach((el, i) => el.value = data.circuit_kva[i] ?? '');
  if (UP_CURRENT) UP_CURRENT.manual = data;
}
```

**Step 4: Auto-save static values on save**

Add at the end of `saveUPManual()`, before the status message:

```javascript
// Persist oil cost as static (carries forward to new months)
const statics = JSON.parse(localStorage.getItem('wsu_up_static') || '{}');
if (data.up_oil_cost_gal != null) statics.up_oil_cost_gal = data.up_oil_cost_gal;
localStorage.setItem('wsu_up_static', JSON.stringify(statics));
```

**Step 5: Verify**

1. Load July 2025 data
2. Enter "1056.52" in Gas BTU/cuft, "0.5298" in Gas Cost/Therm, "3.95" in Oil Cost/Gallon
3. Enter some kWh values in the circuit table
4. Click "Save Manual Entries"
5. See "Saved 3:45:12 PM" confirmation
6. Switch to a different month, click Load Data (fields should be empty)
7. Switch back to July 2025, click Load Data — saved values should be restored
8. Check localStorage in dev tools: key `wsu_up_manual_2025-07` should have the data

**Step 6: Commit**

```bash
git add steam-plant.html
git commit -m "feat: implement UP Report manual entry save/load with localStorage"
```

---

### Task 7: Implement UP Report Preview Table

**Files:**
- Modify: `steam-plant.html` — replace the `renderUPPreview` stub

**Step 1: Replace renderUPPreview()**

This renders a table that matches the UP report layout with color-coded cells.

```javascript
function renderUPPreview() {
  if (!UP_CURRENT) return;
  const a = UP_CURRENT.auto;
  const m = UP_CURRENT.manual || {};

  // Helper: read manual field value
  const mv = (id) => m[id] != null ? m[id] : (document.getElementById(id) ? parseFloat(document.getElementById(id).value) || 0 : 0);

  const btuCuft = mv('up_btu_cuft');
  const gasCostTherm = mv('up_gas_cost_therm');
  const oilCostGal = mv('up_oil_cost_gal');
  const gasDeliveredMmbtu = mv('up_gas_mmbtu');

  // Compute derived values
  // Row 8: Gas delivered therms = MMBTU * 10
  const gasDeliveredTherms = gasDeliveredMmbtu * 10;

  // Row 9: Gas Use Therms per boiler = BTU/cuft * SCF / 100000
  const gasTerms = UP_BOILERS.map(b => btuCuft * (a[b + '_gas'] || 0) / 100000);
  const totalGasTherms = gasTerms.reduce((s, v) => s + v, 0);

  // Row 11: Gen gas therms
  const genGasTherms = btuCuft * ((a.gen1_gas || 0) + (a.gen2_gas || 0)) / 100000;

  // Row 12: Internal gas = delivered - boiler gas - gen gas (therms)
  const internalGas = gasDeliveredTherms - totalGasTherms - genGasTherms;

  // Row 14: Lbs steam per gallon oil
  const lbsPerGalOil = UP_BOILERS.slice(2).map((b, i) => {
    const oil = a[b + '_oil'] || 0;
    return oil > 0 ? (a[b + '_steam_oil'] || 0) / oil : 0;
  });

  // Row 15: Lbs steam per therm gas
  const lbsPerThermGas = UP_BOILERS.map((b, i) => {
    return gasTerms[i] > 0 ? (a[b + '_steam'] || 0) / gasTerms[i] : 0;
  });

  // Row 17-19: Fuel costs
  const oilCosts = UP_BOILERS.slice(2).map((b) => (a[b + '_oil'] || 0) * oilCostGal);
  const gasCosts = gasTerms.map(t => t * gasCostTherm);
  const totalFuelCosts = UP_BOILERS.map((b, i) => {
    const oc = i >= 2 ? oilCosts[i - 2] : 0;
    return oc + gasCosts[i];
  });

  // Build preview HTML
  const fmtC = (v, dec, cls) => '<td class="' + cls + '" style="text-align:right;">' + (v ? fmt(v, dec || 0) : '—') + '</td>';
  const fmtA = (v, dec) => fmtC(v, dec, 'up-auto');
  const fmtM = (v, dec) => fmtC(v, dec, 'up-manual');
  const fmtF = (v, dec) => fmtC(v, dec, 'up-calc');
  const hdr = '<th></th>' + UP_BOILER_LABELS.map(b => '<th>' + b + '</th>').join('') + '<th>Future #6</th><th>Future #7</th><th>TOTALS</th>';

  let html = '<table class="data-table" style="font-size:0.8rem;"><thead><tr>' + hdr + '</tr></thead><tbody>';

  // Row 3: Boiler Days
  html += '<tr><td style="font-weight:600;">Boiler Days</td>';
  UP_BOILERS.forEach(b => { html += fmtA(a[b + '_days'], 1); });
  html += '<td></td><td></td>' + fmtA(a.total_days, 1) + '</tr>';

  // Row 4: Total Lbs Steam (formula)
  html += '<tr><td style="font-weight:600;">Total Lbs. of Steam</td>';
  UP_BOILERS.forEach(b => {
    const v = (a[b + '_steam'] || 0) + (a[b + '_steam_oil'] || 0);
    html += fmtF(v, 0);
  });
  html += '<td></td><td></td>' + fmtF(a.total_steam, 0) + '</tr>';

  // Row 5: Lbs Steam by Gas
  html += '<tr><td>Lbs. of Steam by Gas</td>';
  UP_BOILERS.forEach(b => { html += fmtA(a[b + '_steam'], 0); });
  html += '<td></td><td></td>' + fmtA(a.total_steam_gas, 0) + '</tr>';

  // Row 6: Lbs Steam by Oil
  html += '<tr><td>Lbs. of Steam by Oil</td><td>—</td><td>—</td>';
  ['b3','b4','b5'].forEach(b => { html += fmtA(a[b + '_steam_oil'], 0); });
  html += '<td></td><td></td>' + fmtA(a.total_steam_oil, 0) + '</tr>';

  // Row 7: Oil Burned (gal)
  html += '<tr><td>Boiler Oil Burned (gal)</td><td>—</td><td>—</td>';
  ['b3','b4','b5'].forEach(b => { html += fmtA(a[b + '_oil'], 0); });
  html += '<td></td><td></td>' + fmtA(a.total_oil_gal, 0) + '</tr>';

  // Row 8: Gas Delivered Therms
  html += '<tr><td>Therms of Gas Delivered</td><td colspan="7"></td>' + fmtM(gasDeliveredTherms, 0) + '</tr>';

  // Row 9: Gas Use Therms
  html += '<tr><td>Boiler Gas Use (Therms)</td>';
  gasTerms.forEach(t => { html += fmtF(t, 0); });
  html += '<td></td><td></td>' + fmtF(totalGasTherms, 0) + '</tr>';

  // Row 10: Gas Use SCF
  html += '<tr><td>Boiler Gas Use (SCF)</td>';
  UP_BOILERS.forEach(b => { html += fmtA(a[b + '_gas'], 0); });
  html += '<td></td><td></td>' + fmtA(a.total_gas_scf, 0) + '</tr>';

  // Row 11: Gen Gas
  html += '<tr><td>Gens 1&amp;2 Gas Use (Therms)</td><td></td>' + fmtA(a.gen1_gas, 0) + '<td></td>' + fmtA(a.gen2_gas, 0) + '<td colspan="3"></td>' + fmtF(genGasTherms, 0) + '</tr>';

  // Row 12: Internal Gas
  html += '<tr><td>Plant Internal Gas (Therms)</td><td colspan="7"></td>' + fmtF(internalGas, 0) + '</tr>';

  // Separator + Efficiency
  html += '<tr><td colspan="9" style="font-weight:600;background:var(--table-head-bg);padding:6px;">LBS. OF STEAM PER UNIT OF FUEL</td></tr>';

  // Row 14: per gallon oil
  html += '<tr><td>Gallon of oil</td><td>—</td><td>—</td>';
  lbsPerGalOil.forEach(v => { html += fmtF(v, 1); });
  html += '<td></td><td></td><td></td></tr>';

  // Row 15: per therm gas
  html += '<tr><td>Therm of gas</td>';
  lbsPerThermGas.forEach(v => { html += fmtF(v, 1); });
  html += '<td></td><td></td><td></td></tr>';

  // Separator + Fuel Costs
  html += '<tr><td colspan="9" style="font-weight:600;background:var(--table-head-bg);padding:6px;">BOILER FUEL COSTS</td></tr>';

  // Row 17: Oil cost
  html += '<tr><td>Oil cost ($)</td><td>—</td><td>—</td>';
  oilCosts.forEach(v => { html += fmtF(v, 2); });
  html += '<td></td><td></td>' + fmtF(oilCosts.reduce((s,v) => s+v, 0), 2) + '</tr>';

  // Row 18: Gas cost
  html += '<tr><td>Gas cost ($)</td>';
  gasCosts.forEach(v => { html += fmtF(v, 2); });
  html += '<td></td><td></td>' + fmtF(gasCosts.reduce((s,v) => s+v, 0), 2) + '</tr>';

  // Row 19: Total fuel cost
  html += '<tr><td style="font-weight:600;">Total fuel cost ($)</td>';
  totalFuelCosts.forEach(v => { html += fmtF(v, 2); });
  html += '<td></td><td></td>' + fmtF(totalFuelCosts.reduce((s,v) => s+v, 0), 2) + '</tr>';

  // Weather & Stats
  html += '<tr><td colspan="9" style="font-weight:600;background:var(--table-head-bg);padding:6px;">WEATHER, STEAM &amp; FUEL COST STATS</td></tr>';
  html += '<tr><td>Degree Days Heating</td>' + fmtM(mv('up_hdd'), 0) + '<td>Gas Btu/Cuft</td>' + fmtM(btuCuft, 2) + '<td>St Plant Labor</td>' + fmtM(mv('up_labor'), 2) + '<td colspan="2"></td></tr>';
  html += '<tr><td>Degree Days Cooling</td>' + fmtM(mv('up_cdd'), 0) + '<td>Gas Cost/Therm</td>' + fmtM(gasCostTherm, 4) + '<td>Goods &amp; Srvcs</td>' + fmtM(mv('up_gs'), 2) + '<td colspan="2"></td></tr>';
  html += '<tr><td>Max Lbs/Hr Steam</td>' + fmtM(mv('up_max_lbs_hr'), 0) + '<td>Oil Cost/Gallon</td>' + fmtM(oilCostGal, 2) + '<td colspan="4"></td></tr>';
  html += '<tr><td>Min Lbs/Hr Steam</td>' + fmtM(mv('up_min_lbs_hr'), 0) + '<td colspan="7"></td></tr>';

  // Electric
  html += '<tr><td colspan="9" style="font-weight:600;background:var(--table-head-bg);padding:6px;">AVISTA 13.2kV CAMPUS MASTER-METERED ELECTRIC</td></tr>';
  const circKwh = [...document.querySelectorAll('.up-circ-kwh')].map(el => parseFloat(el.value) || 0);
  const circCost = [...document.querySelectorAll('.up-circ-cost')].map(el => parseFloat(el.value) || 0);
  const totalKwh = circKwh.reduce((s,v) => s+v, 0);
  const totalCost = circCost.reduce((s,v) => s+v, 0);
  html += '<tr><td>kWh Received</td>';
  circKwh.forEach(v => { html += fmtM(v, 0); });
  html += '<td></td><td></td>' + fmtF(totalKwh, 0) + '</tr>';
  html += '<tr><td>Total Cost ($)</td>';
  circCost.forEach(v => { html += fmtM(v, 2); });
  html += '<td></td><td></td>' + fmtF(totalCost, 2) + '</tr>';

  // Gen kWh
  html += '<tr><td>Generator kWh</td><td>Gen 1: ' + fmt(a.gen1_kwh||0, 0) + '</td><td>Gen 2: ' + fmt(a.gen2_kwh||0, 0) + '</td><td>Gen 3: ' + fmt(a.gen3_kwh||0, 0) + '</td><td colspan="4">Biotech: ' + fmt(mv('up_biotech_kwh'), 0) + '</td></tr>';

  html += '</tbody></table>';
  document.getElementById('upPreviewWrap').innerHTML = html;
}
```

**Step 2: Wire up auto-refresh of preview**

Add at the end of `loadUPMonth()` (after `renderUPPreview()`):

```javascript
// Auto-refresh preview when any manual field changes
document.querySelectorAll('#upManualCard input').forEach(el => {
  el.removeEventListener('input', renderUPPreview);
  el.addEventListener('input', renderUPPreview);
});
```

**Step 3: Verify**

1. Load July 2025 data
2. Preview table should appear with green (auto) cells filled, blue (manual) cells showing 0 or —
3. Enter Gas BTU/cuft = 1056.52, Gas Cost/Therm = 0.5298
4. Preview should immediately update: Gas Use Therms row should show calculated values
5. Enter Oil Cost/Gallon = 3.95 — fuel cost rows should update
6. Enter some kWh values in the circuit table — Electric section should update
7. Toggle dark mode — colors should still be visible and readable

**Step 4: Commit**

```bash
git add steam-plant.html
git commit -m "feat: implement UP Report preview table with live auto-refresh"
```

---

### Task 8: Implement Excel Generation

**Files:**
- Modify: `steam-plant.html` — replace the `generateUPExcel` stub

**Step 1: Replace the generateUPExcel stub**

```javascript
function generateUPExcel() {
  if (!UP_CURRENT) { alert('Load a month first.'); return; }
  const a = UP_CURRENT.auto;
  const mv = (id) => {
    const el = document.getElementById(id);
    return el && el.value ? parseFloat(el.value) : 0;
  };

  const btuCuft = mv('up_btu_cuft');
  const gasCostTherm = mv('up_gas_cost_therm');
  const oilCostGal = mv('up_oil_cost_gal');
  const gasMMBTU = mv('up_gas_mmbtu');

  // Month label for title
  const [yr, mo] = UP_CURRENT.month.split('-');
  const mName = new Date(parseInt(yr), parseInt(mo) - 1).toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
  const mmyy = mo + yr.slice(2); // e.g. "0725"

  // Create workbook
  const wb = XLSX.utils.book_new();
  const ws = {};

  // Helper: set cell with value
  const setCell = (ref, val, type) => {
    if (type === 'f') ws[ref] = { t: 'n', f: val }; // formula
    else if (type === 's') ws[ref] = { t: 's', v: val };
    else if (typeof val === 'number') ws[ref] = { t: 'n', v: val };
    else ws[ref] = { t: 's', v: val || '' };
  };

  // Row 1: Title (merged A1:I1)
  setCell('A1', 'UTILITY PRODUCTION (UP) REPORT for CASP and GWSP', 's');

  // Row 2: Month + headers
  setCell('A2', mName);
  ['Boiler #1','Boiler #2','Boiler #3','Boiler #4','Boiler #5','Future #6','Future #7','TOTALS'].forEach((h, i) => {
    setCell(XLSX.utils.encode_cell({r:1, c:i+1}), h, 's');
  });

  // Row 3: Boiler Days — formula: hours/24
  setCell('A3', 'Boiler Days');
  const runtimeKeys = ['b1_runtime','b2_runtime','b3_runtime_total','b4_runtime_total','b5_runtime_total'];
  const boilerHours = runtimeKeys.map(k => a[k.replace('_runtime','_days').replace('_total_days','_days')] ? a[k.replace('_runtime','_days').replace('_total_days','_days')] * 24 : 0);
  UP_BOILERS.forEach((b, i) => {
    const hrs = (a[b + '_days'] || 0) * 24;
    setCell(XLSX.utils.encode_cell({r:2, c:i+1}), hrs > 0 ? '=' + Math.round(hrs) + '/24' : 0, hrs > 0 ? 'f' : undefined);
  });
  setCell('I3', '=SUM(B3:H3)', 'f');

  // Row 4: Total Lbs Steam = gas + oil
  setCell('A4', 'Total Lbs. of Steam');
  UP_BOILERS.forEach((b, i) => {
    const col = XLSX.utils.encode_col(i + 1);
    setCell(col + '4', '=' + col + '5+' + col + '6', 'f');
  });
  setCell('I4', '=SUM(B4:H4)', 'f');

  // Row 5: Lbs Steam by Gas (input values)
  setCell('A5', 'Lbs. of Steam by Gas');
  UP_BOILERS.forEach((b, i) => { setCell(XLSX.utils.encode_cell({r:4, c:i+1}), a[b + '_steam'] || 0); });
  setCell('I5', '=SUM(B5:H5)', 'f');

  // Row 6: Lbs Steam by Oil (B3-B5 only)
  setCell('A6', 'Lbs. of Steam by Oil');
  setCell('B6', 0); setCell('C6', 0);
  setCell('D6', a.b3_steam_oil || 0);
  setCell('E6', a.b4_steam_oil || 0);
  setCell('F6', a.b5_steam_oil || 0);
  setCell('I6', '=SUM(B6:H6)', 'f');

  // Row 7: Oil Burned (gal)
  setCell('A7', 'Boiler Oil Burned (gallons)');
  setCell('B7', 0); setCell('C7', 0);
  setCell('D7', a.b3_oil || 0);
  setCell('E7', a.b4_oil || 0);
  setCell('F7', a.b5_oil || 0);
  setCell('I7', '=SUM(B7:H7)', 'f');
  setCell('J7', '=I7*0.14', 'f');
  setCell('K7', 'MMBTU (Oil)', 's');

  // Row 8: Gas Delivered Therms
  setCell('A8', 'Therms of Gas Delivered to Steam Plants');
  setCell('I8', gasMMBTU > 0 ? '=' + gasMMBTU + '*10' : 0, gasMMBTU > 0 ? 'f' : undefined);

  // Row 9: Gas Use Therms = BTU/cuft * SCF / 100000
  setCell('A9', 'Boiler Gas Use (Therms)');
  UP_BOILERS.forEach((b, i) => {
    const col = XLSX.utils.encode_col(i + 1);
    setCell(col + '9', '=$D$24*' + col + '10/100000', 'f');
  });
  setCell('I9', '=SUM(B9:H9)', 'f');
  setCell('J9', '=I9/10', 'f');
  setCell('K9', 'MMBTU (Gas)', 's');

  // Row 10: Gas Use SCF (input)
  setCell('A10', 'Boiler Gas Use (SCF)');
  UP_BOILERS.forEach((b, i) => { setCell(XLSX.utils.encode_cell({r:9, c:i+1}), a[b + '_gas'] || 0); });
  setCell('I10', '=SUM(B10:H10)', 'f');
  setCell('J10', '=(J7+J9)', 'f');
  setCell('K10', 'MMBTU (Total)', 's');

  // Row 11: Generator Gas SCF → Therms
  setCell('A11', 'Gens 1&2 Gas Use (Therms)');
  setCell('C11', a.gen1_gas || 0); // Gen1 SCF in col C
  setCell('E11', a.gen2_gas || 0); // Gen2 SCF in col E
  setCell('I11', '=(C11+E11)*D24/100000', 'f');

  // Row 12: Internal Gas
  setCell('A12', 'Plant Internal Gas Used (Therms)');
  setCell('I12', '=I8-I9-I11', 'f');

  // Row 13: Section header
  setCell('A13', 'LBS. OF STEAM PER UNIT OF FUEL', 's');

  // Row 14: Lbs/gal oil
  setCell('A14', 'Gallon of oil');
  ['D','E','F'].forEach(col => {
    setCell(col + '14', '=IF(' + col + '7=0,0,' + col + '6/' + col + '7)', 'f');
  });

  // Row 15: Lbs/therm gas
  setCell('A15', 'Therm of gas');
  ['B','C','D','E','F'].forEach(col => {
    setCell(col + '15', '=IF(' + col + '9=0,0,' + col + '5/' + col + '9)', 'f');
  });

  // Row 16: Section header
  setCell('A16', 'BOILER FUEL COSTS', 's');

  // Row 17: Oil cost
  setCell('A17', 'Oil cost');
  ['B','C','D','E','F'].forEach(col => {
    setCell(col + '17', '=' + col + '7*$D$26', 'f');
  });
  setCell('I17', '=SUM(B17:H17)', 'f');

  // Row 18: Gas cost
  setCell('A18', 'Gas cost');
  ['B','C','D','E','F'].forEach(col => {
    setCell(col + '18', '=' + col + '9*$D$25', 'f');
  });
  setCell('I18', '=SUM(B18:H18)', 'f');

  // Row 19: Total fuel cost
  setCell('A19', 'Total fuel cost');
  ['B','C','D','E','F'].forEach(col => {
    setCell(col + '19', '=SUM(' + col + '17+' + col + '18)', 'f');
  });
  setCell('I19', '=SUM(B19:H19)', 'f');

  // Row 20: Section header
  setCell('A20', 'FUEL COSTS PER 1000 LBS. STEAM', 's');

  // Row 21: Oil cost per 1000 lbs
  setCell('A21', 'Oil cost per 1000 lbs');
  ['D','E','F'].forEach(col => {
    setCell(col + '21', '=IF(' + col + '17=0,0,' + col + '17/' + col + '6)*1000', 'f');
  });

  // Row 22: Gas cost per 1000 lbs
  setCell('A22', 'Gas cost per 1000 lbs');
  ['B','C','D','E','F'].forEach(col => {
    setCell(col + '22', '=IF(' + col + '18=0,0,' + col + '18/' + col + '5)*1000', 'f');
  });

  // Row 23: Section header
  setCell('A23', 'WEATHER, STEAM & FUEL COST STATS', 's');

  // Row 24: HDD + BTU/cuft + Labor
  setCell('A24', 'Degree Days Heating');
  setCell('B24', mv('up_hdd'));
  setCell('C24', 'Gas Btu/Cuft', 's');
  setCell('D24', btuCuft);
  setCell('E24', 'St Plant Labor', 's');
  setCell('F24', mv('up_labor'));

  // Row 25: CDD + Gas Cost/Therm + G&S
  setCell('A25', 'Degree Days Cooling');
  setCell('B25', mv('up_cdd'));
  setCell('C25', 'Gas Cost/Therm', 's');
  setCell('D25', gasCostTherm);
  setCell('E25', 'Goods & Srvcs', 's');
  setCell('F25', mv('up_gs'));

  // Row 26: Max lbs/hr + Oil Cost/Gal + Fuel Cost budget
  setCell('A26', 'Max Lbs per Hour Steam');
  setCell('B26', mv('up_max_lbs_hr'));
  setCell('C26', 'Oil Cost/Gallon', 's');
  setCell('D26', oilCostGal);
  setCell('E26', 'Fuel Cost', 's');
  setCell('F26', '=I19', 'f');

  // Row 27: Min lbs/hr + Makeup Water
  setCell('A27', 'Min Lbs per Hour Steam');
  setCell('B27', mv('up_min_lbs_hr'));
  setCell('C27', 'Make Up Water', 's');
  setCell('D27', '=(739600)*8.33/I4', 'f'); // placeholder formula
  setCell('E27', 'Total Prod. Cost', 's');
  setCell('F27', '=SUM(F24:F26)', 'f');

  // Row 28: Section header
  setCell('A28', 'FRESH WATER PUMPED', 's');

  // Row 29: Column headers
  setCell('B29', 'Gal Pumped', 's');
  setCell('C29', 'Electric Cost', 's');
  setCell('H29', 'Total Cost', 's');

  // Rows 30-33: Wells
  const wells = [
    { label: 'Well #4', id: 'up_well4' },
    { label: 'Well #6', id: 'up_well6' },
    { label: 'Well #7', id: 'up_well7' },
    { label: 'Well #8', id: 'up_well8' }
  ];
  wells.forEach((w, i) => {
    const row = 30 + i;
    setCell('A' + row, w.label);
    setCell('B' + row, mv(w.id));
  });
  setCell('A34', 'Total');
  setCell('B34', '=SUM(B30:B33)', 'f');

  // Row 38: Chlorine
  setCell('A38', 'Lbs Chlorine Used');
  setCell('B38', mv('up_chlorine'));

  // Row 43: Electric section header
  setCell('A43', 'AVISTA 13.2kV CAMPUS MASTER-METERED ELECTRIC', 's');

  // Row 44-45: Circuit labels
  const circuitNames = ['MP-A', 'MP-C', 'MP-D', 'MP-E', 'MP-G'];
  const circuitIds = ['TUR-111', 'SPU124+TVW131', 'SPU-122', 'TUR-115', 'SPU-125'];
  circuitNames.forEach((c, i) => { setCell(XLSX.utils.encode_cell({r:43, c:i+1}), c, 's'); });
  circuitIds.forEach((c, i) => { setCell(XLSX.utils.encode_cell({r:44, c:i+1}), c, 's'); });

  // Row 49: kWh per circuit
  setCell('A49', 'KWH Received');
  const circKwh = [...document.querySelectorAll('.up-circ-kwh')].map(el => parseFloat(el.value) || 0);
  circKwh.forEach((v, i) => { setCell(XLSX.utils.encode_cell({r:48, c:i+1}), v); });
  setCell('G49', '=SUM(B49:F49)', 'f');
  setCell('I49', mv('up_biotech_kwh'));

  // Row 50: Cost per circuit
  setCell('A50', 'Total Cost for Service');
  const circCost = [...document.querySelectorAll('.up-circ-cost')].map(el => parseFloat(el.value) || 0);
  circCost.forEach((v, i) => { setCell(XLSX.utils.encode_cell({r:49, c:i+1}), v); });
  setCell('G50', '=SUM(B50:F50)', 'f');

  // Row 51: Cost per kWh
  setCell('A51', 'Cost per KWH');
  ['B','C','D','E','F'].forEach(col => {
    setCell(col + '51', '=IF(' + col + '49=0,0,' + col + '50/' + col + '49)', 'f');
  });

  // Row 46-48: Generator kWh
  setCell('H46', 'Gen 1', 's'); setCell('I46', a.gen1_kwh || 0);
  setCell('H47', 'Gen 2', 's'); setCell('I47', a.gen2_kwh || 0);
  setCell('H48', 'Gen 3', 's'); setCell('I48', a.gen3_kwh || 0);
  setCell('H50', 'Total Gen kWh:', 's'); setCell('I50', '=SUM(I46:I49)', 'f');

  // Row 48: Peak KVA
  setCell('A48', 'Demand Peak KVA');
  const circKva = [...document.querySelectorAll('.up-circ-kva')].map(el => parseFloat(el.value) || 0);
  circKva.forEach((v, i) => { setCell(XLSX.utils.encode_cell({r:47, c:i+1}), v); });

  // Row 52: Account numbers
  setCell('A52', 'AVISTA ACCT NUM:', 's');
  const accts = ['15400-44701-0', '15400-45902-0', '15400-44201-1', '15400-43001-2', '15400-44801-0'];
  accts.forEach((a, i) => { setCell(XLSX.utils.encode_cell({r:51, c:i+1}), a, 's'); });

  // Set sheet range
  ws['!ref'] = 'A1:K53';

  // Merged cells
  ws['!merges'] = [
    { s: {r:0,c:0}, e: {r:0,c:8} },  // A1:I1 title
    { s: {r:12,c:0}, e: {r:12,c:8} }, // A13:I13
    { s: {r:15,c:0}, e: {r:15,c:8} }, // A16:I16
    { s: {r:19,c:0}, e: {r:19,c:8} }, // A20:I20
    { s: {r:22,c:0}, e: {r:22,c:8} }, // A23:I23
    { s: {r:27,c:0}, e: {r:27,c:8} }, // A28:I28
  ];

  // Column widths
  ws['!cols'] = [
    { wch: 38 }, // A
    { wch: 14 }, { wch: 14 }, { wch: 14 }, { wch: 14 }, { wch: 14 }, // B-F
    { wch: 10 }, { wch: 10 }, // G-H
    { wch: 16 }, // I
    { wch: 12 }, { wch: 12 } // J-K
  ];

  XLSX.utils.book_append_sheet(wb, ws, 'UP' + mmyy);

  try {
    const wbout = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
    const blob = new Blob([wbout], { type: 'application/octet-stream' });
    downloadBlob(blob, 'UP' + mmyy + '.xlsx');
  } catch (e) {
    alert('Excel generation error: ' + e.message);
    console.error(e);
  }
}
```

**Step 2: Verify**

1. Load July 2025 data
2. Enter manual values: Gas MMBTU = 39668, BTU/cuft = 1056.52, Gas Cost/Therm = 0.5298, Oil Cost/Gallon = 3.95
3. Enter some circuit kWh/cost values
4. Click "Generate UP Report Excel"
5. File `UP0725.xlsx` should download
6. Open in Excel:
   - Row 1 should show title merged across A-I
   - Row 5 should show steam values for each boiler
   - Row 9 should have formulas (click cell, check formula bar shows `=$D$24*B10/100000`)
   - Row 17-19 should show fuel costs calculated from formulas
   - Column widths should be reasonable

**Step 3: Commit**

```bash
git add steam-plant.html
git commit -m "feat: implement UP Report Excel generation with formulas"
```

---

### Task 9: Final Integration Testing and Push

**Files:**
- No new changes, just verification and push

**Step 1: Full workflow test**

1. Open `steam-plant.html` in browser
2. Log in with password
3. Click "UP Report" tab
4. Select "July 2025" → click "Load Data"
5. Verify: Auto-Populated Data table shows boiler days, steam, gas, oil, generator data
6. Enter manual fields:
   - Gas Delivered MMBTU: 39668
   - Gas BTU/cuft: 1056.52
   - Gas Cost/Therm: 0.5298
   - Oil Cost/Gallon: 3.95
   - HDD: 18
7. Click "Save Manual Entries" — see confirmation
8. Check Preview table updates with all calculated fields
9. Click "Generate UP Report Excel" — download UP0725.xlsx
10. Open in Excel — verify formulas work
11. Switch to a different month (e.g., Jan 2026), load, verify different values
12. Switch back to July 2025 — verify manual entries were preserved
13. Toggle dark mode — verify all cards/tables readable
14. Test all other tabs still work (Overview, Gas, Steam, Runtime, Water, Data Mgmt, Help)

**Step 2: Push to GitHub Pages**

```bash
cd "C:/Users/john.slagboom/Desktop/Git"
git push origin main
```

**Step 3: Verify live deployment**

Open `https://jswsu.github.io/wsu-energy-dashboard/steam-plant.html` and verify the UP Report tab works on the live site.
