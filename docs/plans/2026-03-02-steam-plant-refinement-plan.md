# Steam Plant Dashboard Refinement — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the Overview tab into an executive FYTD dashboard with FY selector, prior-year comparison, and full-year projection. Add info-box explainers to all 16 charts/tables across all tabs.

**Architecture:** All changes are in `steam-plant.html` (single-file dashboard with inline CSS+JS). New FY helper functions compute FYTD totals, prior-year comparison, and projections. The FY selector dropdown triggers a re-render of Overview KPIs and chart highlighting. Info-box explainers are static HTML inserted between card headings and chart canvases.

**Tech Stack:** Chart.js v4.4.7, vanilla JS, CSS variables, inline HTML

**Design Doc:** `docs/plans/2026-03-02-steam-plant-refinement-design.md`

---

### Task 1: Add FY Selector Dropdown to Overview HTML

**Files:**
- Modify: `steam-plant.html:394-407` (Overview tab section HTML)

**Step 1: Add FY selector and info-boxes to Overview section HTML**

Replace the current Overview section (lines 394-407) with:

```html
  <!-- ==================== OVERVIEW TAB ==================== -->
  <div class="section active" id="sec-overview">
    <div style="display:flex; align-items:center; gap:1rem; margin-bottom:1rem;">
      <label for="fySelect" style="font-weight:600; font-size:0.9rem; color:var(--text);">Fiscal Year:</label>
      <select id="fySelect" style="padding:0.4rem 0.8rem; border:2px solid var(--border); border-radius:6px; font-size:0.85rem; background:var(--card-bg); color:var(--text); cursor:pointer;"></select>
    </div>
    <div class="kpi-grid" id="kpiOverview"></div>
    <div class="chart-row">
      <div class="card">
        <h2>Monthly Gas &amp; Steam Trends</h2>
        <div class="info-box">Monthly gas consumption (left axis) and steam production (right axis). The selected fiscal year is highlighted with thicker lines. Gas and steam rise and fall together &mdash; divergence may indicate efficiency changes.</div>
        <div class="chart-container"><canvas id="chartOverviewTrend"></canvas></div>
      </div>
      <div class="card">
        <h2>Gas Consumption by Fiscal Year</h2>
        <div class="info-box">Total gas consumed per fiscal year. The selected year is highlighted. Incomplete years show actual-to-date. Compare year-over-year to identify consumption trends.</div>
        <div class="chart-container"><canvas id="chartFYGas"></canvas></div>
      </div>
    </div>
  </div>
```

**Step 2: Verify** — Open `steam-plant.html` in browser, confirm dropdown appears above KPI cards, info-boxes appear above charts.

**Step 3: Commit**

```bash
git add steam-plant.html
git commit -m "feat: add FY selector dropdown and Overview info-boxes"
```

---

### Task 2: Add FY Helper Functions

**Files:**
- Modify: `steam-plant.html` — insert after the `fyLabel()` function (~line 854) and before the chart factory section

**Step 1: Add FY computation helpers**

Insert these functions after `function fyLabel(monthKey) { ... }`:

```javascript
function getFYMonths(M, fy) {
  // fy = "FY26" -> fiscal year starting July 2025
  const fyNum = parseInt(fy.slice(2), 10);
  const startYear = 2000 + fyNum - 1;
  const startMonth = startYear + '-07';
  const endMonth = (startYear + 1) + '-06';
  return M.filter(m => m.month >= startMonth && m.month <= endMonth);
}

function getAllFYs(M) {
  const fys = new Set();
  M.forEach(m => fys.add(fyLabel(m.month)));
  return [...fys].sort();
}

function priorFY(fy) {
  const fyNum = parseInt(fy.slice(2), 10);
  return 'FY' + String(fyNum - 1).padStart(2, '0');
}

function computeFYTD(M, fy) {
  const months = getFYMonths(M, fy);
  const monthsElapsed = months.length;
  return { months, monthsElapsed };
}

function fytdSum(months, keyFn) {
  return sum(months.map(keyFn));
}

function fytdProjection(total, monthsElapsed) {
  if (monthsElapsed === 0) return 0;
  return (total / monthsElapsed) * 12;
}

function fytdPctChange(current, prior) {
  if (prior === 0) return null;
  return ((current - prior) / prior) * 100;
}

function pctChangeHtml(pct) {
  if (pct === null) return 'N/A';
  const arrow = pct >= 0 ? '\u25B2' : '\u25BC';
  const color = pct >= 0 ? 'var(--red)' : 'var(--green)';
  return '<span style="color:' + color + '; font-weight:600;">' + arrow + ' ' + Math.abs(pct).toFixed(1) + '%</span>';
}

function fmtShort(v) {
  if (v >= 1e9) return (v / 1e9).toFixed(1) + 'B';
  if (v >= 1e6) return (v / 1e6).toFixed(1) + 'M';
  if (v >= 1e3) return (v / 1e3).toFixed(1) + 'K';
  return fmt(v);
}
```

**Step 2: Verify** — No visual change yet, but confirm no JS errors in browser console.

**Step 3: Commit**

```bash
git add steam-plant.html
git commit -m "feat: add FY calculation helper functions"
```

---

### Task 3: Rewrite renderOverviewTab for FYTD Executive View

**Files:**
- Modify: `steam-plant.html` — replace entire `renderOverviewTab` function (lines 885-935)

**Step 1: Replace `renderOverviewTab` with FYTD version**

Replace the function body (from `function renderOverviewTab(M, labels) {` through its closing `}` before the Gas tab comment) with:

```javascript
function renderOverviewTab(M, labels) {
  // Populate FY selector
  const allFYs = getAllFYs(M);
  const fySelect = document.getElementById('fySelect');
  fySelect.innerHTML = allFYs.map(fy => `<option value="${fy}">${fy}</option>`).join('');
  fySelect.value = allFYs[allFYs.length - 1]; // default to latest

  function renderForFY(fy) {
    const { months: fyMonths, monthsElapsed } = computeFYTD(M, fy);
    const prior = priorFY(fy);
    const { months: priorMonths } = computeFYTD(M, prior);
    // Same-period: first N months of prior FY
    const priorSame = priorMonths.slice(0, monthsElapsed);

    // Metric definitions: [label, keyFn, unit, cls, tip]
    const metrics = [
      ['Campus Total Gas', m => m.campus_gas || 0, 'scf', 'campus', 'Total natural gas consumed across all boilers'],
      ['Campus Total Steam', m => m.campus_steam || 0, 'lbs', 'casp', 'Total steam produced across all boilers'],
      ['Total Boiler Runtime', m => (m.b1_runtime||0)+(m.b2_runtime||0)+(m.b3_runtime_total||0)+(m.b4_runtime_total||0)+(m.b5_runtime_total||0), 'hrs', 'b3', 'Sum of monthly runtime for all 5 boilers'],
      ['Generator Output', m => (m.gen1_kwh||0)+(m.gen2_kwh||0)+(m.gen3_kwh||0), 'kWh', 'gen', 'Total electricity generated by on-site generators'],
      ['Total Plant Water', m => (m.gwsp_raw_water||0)+(m.gwsp_potable||0)+(m.gwsp_permeate||0)+(m.casp_east_water||0)+(m.casp_west_water||0), '', 'water', 'Sum of GWSP raw, potable, permeate + CASP east/west water'],
    ];

    const kpis = metrics.map(([label, keyFn, unit, cls, tip]) => {
      const fytd = fytdSum(fyMonths, keyFn);
      const priorTotal = fytdSum(priorSame, keyFn);
      const pct = fytdPctChange(fytd, priorTotal);
      const proj = fytdProjection(fytd, monthsElapsed);
      const unitStr = unit ? ' ' + unit : '';

      // Build comparison expand table
      let tableHtml = '<thead><tr><th>Month</th><th>' + fy + '</th><th>' + prior + '</th><th>Change</th></tr></thead><tbody>';
      for (let i = 0; i < fyMonths.length; i++) {
        const cv = keyFn(fyMonths[i]);
        const pv = i < priorSame.length ? keyFn(priorSame[i]) : 0;
        const mp = fytdPctChange(cv, pv);
        tableHtml += '<tr><td>' + monthLabel(fyMonths[i].month) + '</td><td>' + fmt(cv) + '</td><td>' + fmt(pv) + '</td><td>' + pctChangeHtml(mp) + '</td></tr>';
      }
      const totalPct = fytdPctChange(fytd, priorTotal);
      tableHtml += '<tr><td>FYTD Total</td><td>' + fmt(fytd) + '</td><td>' + fmt(priorTotal) + '</td><td>' + pctChangeHtml(totalPct) + '</td></tr></tbody>';

      return {
        label: label, value: fmtShort(fytd) + unitStr,
        sub: prior + ' same period: ' + fmtShort(priorTotal) + ' ' + pctChangeHtml(pct) + '<br>Projected ' + fy + ' total: ' + fmtShort(proj) + unitStr,
        cls: cls, tip: tip, table: tableHtml
      };
    });

    // Data period KPI
    kpis.push({
      label: 'Data Period', value: fy + ' (' + monthsElapsed + ' of 12 mo)',
      sub: fyMonths.length > 0 ? monthLabel(fyMonths[0].month) + ' \u2013 ' + monthLabel(fyMonths[fyMonths.length-1].month) : 'No data',
      cls: 'info', tip: DATA.meta.dayCount + ' daily rows total in dataset'
    });

    renderKPIs('kpiOverview', kpis);

    // --- Charts ---
    // Destroy existing overview charts
    const overviewChartIds = ['chartOverviewTrend', 'chartFYGas'];
    for (let i = chartInstances.length - 1; i >= 0; i--) {
      if (overviewChartIds.includes(chartInstances[i].canvas.id)) {
        chartInstances[i].destroy();
        chartInstances.splice(i, 1);
      }
    }

    // Dual-axis trend with FY highlighting
    const fyStartIdx = labels.findIndex((_, i) => fyLabel(M[i].month) === fy);
    const fyEndIdx = labels.length - 1 - [...labels].reverse().findIndex((_, i) => fyLabel(M[M.length - 1 - i].month) === fy);

    lineChart('chartOverviewTrend', labels, [
      { label: 'Campus Gas (scf)', data: M.map(m => m.campus_gas || 0), borderColor: COLORS.campus, backgroundColor: COLORS.campus + '33', fill: false, tension: 0.3, yAxisID: 'y',
        segment: { borderWidth: ctx => (ctx.p0DataIndex >= fyStartIdx && ctx.p0DataIndex <= fyEndIdx) ? 3 : 1 },
        borderWidth: 1 },
      { label: 'Campus Steam (lbs)', data: M.map(m => m.campus_steam || 0), borderColor: COLORS.casp, backgroundColor: COLORS.casp + '33', fill: false, tension: 0.3, yAxisID: 'y2',
        segment: { borderWidth: ctx => (ctx.p0DataIndex >= fyStartIdx && ctx.p0DataIndex <= fyEndIdx) ? 3 : 1 },
        borderWidth: 1 },
    ], 'Gas (scf)', { y2: true, y2Label: 'Steam (lbs)' });

    // FY bar chart with selected FY highlighted
    const fyMap = {};
    M.forEach(m => {
      const f = fyLabel(m.month);
      fyMap[f] = (fyMap[f] || 0) + (m.campus_gas || 0);
    });
    const fyKeys = Object.keys(fyMap).sort();
    barChart('chartFYGas', fyKeys, [
      { label: 'Campus Gas (scf)',
        data: fyKeys.map(k => fyMap[k]),
        backgroundColor: fyKeys.map(k => k === fy ? COLORS.campus + 'cc' : COLORS.campus + '44'),
        borderColor: COLORS.campus, borderWidth: 1 }
    ], 'Gas (scf)');
  }

  renderForFY(fySelect.value);
  fySelect.addEventListener('change', () => renderForFY(fySelect.value));
}
```

**Step 2: Verify** — Open dashboard, confirm:
- FY dropdown appears with FY21-FY26 options
- KPIs show FYTD values with prior year comparison and % change arrows
- Expanding KPIs shows month-by-month comparison table
- Changing FY selector updates all KPIs and chart highlighting
- Charts show thicker lines for selected FY

**Step 3: Commit**

```bash
git add steam-plant.html
git commit -m "feat: executive FYTD KPIs with FY selector and projections"
```

---

### Task 4: Add Info-Box Explainers to Gas Consumption Tab

**Files:**
- Modify: `steam-plant.html:409-429` (Gas tab HTML section)

**Step 1: Add info-boxes between card headings and chart canvases**

Replace the Gas tab section HTML with:

```html
  <!-- ==================== GAS CONSUMPTION TAB ==================== -->
  <div class="section" id="sec-gas">
    <div class="kpi-grid" id="kpiGas"></div>
    <div class="card">
      <h2>Monthly Gas by Boiler (scf)</h2>
      <div class="info-box">Each bar shows one month's total gas consumption, stacked by boiler. Boilers 1-2 are at CASP (Central), Boilers 3-5 at GWSP (Grimes Way). Taller bars indicate higher heating demand.</div>
      <div class="chart-container tall"><canvas id="chartGasBoiler"></canvas></div>
    </div>
    <div class="chart-row">
      <div class="card">
        <h2>CASP vs GWSP vs Campus Gas</h2>
        <div class="info-box">Gas consumption comparison between the two steam plants. The Campus line equals CASP + GWSP combined.</div>
        <div class="chart-container"><canvas id="chartGasPlant"></canvas></div>
      </div>
      <div class="card">
        <h2>Oil Usage (lbs) &mdash; Boilers 3, 4, 5</h2>
        <div class="info-box">Fuel oil burned by dual-fuel boilers (B3, B4, B5). Oil firing is uncommon &mdash; non-zero months indicate gas supply constraints or scheduled testing.</div>
        <div class="chart-container"><canvas id="chartOil"></canvas></div>
      </div>
    </div>
    <div class="card">
      <h2>Monthly Gas Detail Table</h2>
      <div class="info-box">Monthly gas breakdown by boiler with plant and campus totals. Months with fuel oil usage are highlighted in red.</div>
      <div class="table-wrap"><table id="tblGas"><thead></thead><tbody></tbody></table></div>
    </div>
  </div>
```

**Step 2: Verify** — Gas tab shows info-boxes above each chart and table.

**Step 3: Commit**

```bash
git add steam-plant.html
git commit -m "feat: add info-box explainers to Gas Consumption tab"
```

---

### Task 5: Add Info-Box Explainers to Steam & Efficiency Tab

**Files:**
- Modify: `steam-plant.html` — Steam tab HTML section

**Step 1: Add info-boxes**

Replace the Steam section HTML with:

```html
  <!-- ==================== STEAM & EFFICIENCY TAB ==================== -->
  <div class="section" id="sec-steam">
    <div class="kpi-grid" id="kpiSteam"></div>
    <div class="card">
      <h2>Monthly Steam Production by Boiler (lbs)</h2>
      <div class="info-box">Steam production stacked by boiler. B1-B2 produce steam from gas only. B3-B5 are dual-fuel and show total steam (gas + oil combined).</div>
      <div class="chart-container tall"><canvas id="chartSteamBoiler"></canvas></div>
    </div>
    <div class="chart-row">
      <div class="card">
        <h2>Efficiency Ratio (steam lbs / gas scf)</h2>
        <div class="info-box">Steam output (lbs) divided by gas input (scf) for each boiler over time. Higher ratios indicate better efficiency. Gaps mean the boiler was offline that month.</div>
        <div class="chart-container"><canvas id="chartEfficiency"></canvas></div>
      </div>
      <div class="card">
        <h2>Economizer Delta-T (&deg;F) by Boiler</h2>
        <div class="info-box">Temperature gain across economizer heat exchangers (outlet minus inlet, degrees F). Higher delta-T means more heat recovered from exhaust gases, improving efficiency.</div>
        <div class="chart-container"><canvas id="chartEconDelta"></canvas></div>
      </div>
    </div>
  </div>
```

**Step 2: Verify** — Steam tab shows info-boxes.

**Step 3: Commit**

```bash
git add steam-plant.html
git commit -m "feat: add info-box explainers to Steam & Efficiency tab"
```

---

### Task 6: Add Info-Box Explainers to Runtime & Availability Tab

**Files:**
- Modify: `steam-plant.html` — Runtime tab HTML section

**Step 1: Add info-boxes**

Replace the Runtime section HTML with:

```html
  <!-- ==================== RUNTIME & AVAILABILITY TAB ==================== -->
  <div class="section" id="sec-runtime">
    <div class="kpi-grid" id="kpiRuntime"></div>
    <div class="card">
      <h2>Monthly Boiler Runtime (hrs)</h2>
      <div class="info-box">Total run hours per boiler per month. Higher runtime during winter heating season is expected. Significant drops may indicate maintenance outages.</div>
      <div class="chart-container tall"><canvas id="chartRuntimeBoiler"></canvas></div>
    </div>
    <div class="card">
      <h2>Boiler Availability Heatmap</h2>
      <div class="info-box">Boiler runtime over the last 24 months. Green (&gt;500 hrs) = heavily used, Yellow (100-500) = moderate, Red (&lt;100) = light use, Dash = offline or idle.</div>
      <div class="heatmap-wrap" id="heatmapWrap"></div>
    </div>
    <div class="card">
      <h2>Generator Runtime &amp; Output</h2>
      <div class="info-box">Monthly electricity generated (kWh) by each on-site generator. Generators typically run during peak demand periods or utility outages.</div>
      <div class="chart-container"><canvas id="chartGenerators"></canvas></div>
    </div>
  </div>
```

**Step 2: Verify** — Runtime tab shows info-boxes.

**Step 3: Commit**

```bash
git add steam-plant.html
git commit -m "feat: add info-box explainers to Runtime & Availability tab"
```

---

### Task 7: Add Info-Box Explainers to Plant Water Tab

**Files:**
- Modify: `steam-plant.html` — Water tab HTML section

**Step 1: Add info-boxes**

Replace the Water section HTML with:

```html
  <!-- ==================== PLANT WATER TAB ==================== -->
  <div class="section" id="sec-water">
    <div class="kpi-grid" id="kpiWater"></div>
    <div class="card">
      <h2>Monthly Plant Water by Source</h2>
      <div class="info-box">Total plant water from all sources, stacked by type. GWSP sources include raw water, potable (city), and RO permeate. CASP tracks east and west sides separately.</div>
      <div class="chart-container tall"><canvas id="chartWaterStacked"></canvas></div>
    </div>
    <div class="chart-row">
      <div class="card">
        <h2>GWSP Water Trends</h2>
        <div class="info-box">Individual GWSP water source trends. Raw water is untreated intake, potable is city supply, permeate is reverse osmosis system output.</div>
        <div class="chart-container"><canvas id="chartGWSPWater"></canvas></div>
      </div>
      <div class="card">
        <h2>Makeup Water Temperature (&deg;F)</h2>
        <div class="info-box">GWSP boiler makeup water temperature follows seasonal patterns. Colder inlet water in winter requires more energy to heat, affecting boiler efficiency.</div>
        <div class="chart-container"><canvas id="chartWaterTemp"></canvas></div>
      </div>
    </div>
    <div class="card">
      <h2>CASP East vs West Water</h2>
      <div class="info-box">Side-by-side comparison of CASP east and west water consumption. Significant or persistent imbalance may indicate a leak or valve issue.</div>
      <div class="chart-container"><canvas id="chartCASPWater"></canvas></div>
    </div>
  </div>
```

**Step 2: Verify** — Water tab shows info-boxes.

**Step 3: Commit**

```bash
git add steam-plant.html
git commit -m "feat: add info-box explainers to Plant Water tab"
```

---

### Task 8: Final Verification and Push

**Step 1: Full visual test**

Open `https://jswsu.github.io/wsu-energy-dashboard/steam-plant.html` (after push).

Verify:
- [ ] Overview: FY selector appears, defaults to FY26
- [ ] Overview: KPIs show FYTD values with FY25 comparison and % arrows
- [ ] Overview: Expanding gas KPI shows month comparison table
- [ ] Overview: Changing to FY24 updates all KPIs and chart highlighting
- [ ] Overview: Charts highlight selected FY with thicker lines / brighter bars
- [ ] Gas tab: 4 info-boxes (stacked bar, CASP/GWSP line, oil bar, detail table)
- [ ] Steam tab: 3 info-boxes (steam bar, efficiency, economizer)
- [ ] Runtime tab: 3 info-boxes (runtime bar, heatmap, generators)
- [ ] Water tab: 4 info-boxes (stacked bar, GWSP trends, temp, CASP east/west)
- [ ] Dark mode: all info-boxes readable in dark mode
- [ ] No console errors

**Step 2: Push to GitHub Pages**

```bash
git push origin main
```

**Step 3: Verify live URL loads**

```bash
curl -s -o /dev/null -w "%{http_code}" "https://jswsu.github.io/wsu-energy-dashboard/steam-plant.html"
# Expected: 200
```
