# UP Report Automation — Design Document

**Goal:** Add a "UP Report" tab to `steam-plant.html` that auto-fills ~60% of the monthly Utilities Production report from existing JSON data, accepts manual entry for the remaining fields, and generates an Excel file matching the exact UP format.

**Architecture:** New tab in steam-plant.html. Reads `steam_plant.json` (steam/gas/runtime/water data) and `data.json` (electric costs, HDD/CDD). Uses SheetJS to generate `.xlsx` output matching the UP template format. Manual entries saved in localStorage for persistence.

**Tech Stack:** Vanilla JS (existing dashboard), SheetJS (already loaded), Chart.js (already loaded)

---

## UP Report Structure (UP0725.xlsx)

The UP report is a single-sheet Excel workbook with 7 sections across ~53 active rows:

| Section | Rows | Content |
|---------|------|---------|
| Steam Production | 1-12 | Boiler days, steam lbs, oil gallons, gas SCF/therms, generator gas |
| Efficiency Ratios | 13-15 | Lbs steam per gallon oil, per therm gas |
| Boiler Fuel Costs | 16-22 | Oil/gas cost per boiler, cost per 1000 lbs steam |
| Weather & Stats | 23-27 | HDD/CDD, BTU/cuft, gas/oil cost rates, labor/G&S budgets |
| Fresh Water | 28-38 | Well #4/6/7/8 gallons + costs, chlorine |
| Deionized Water | 39-42 | Regen costs (currently "No Data") |
| Avista Electric | 43-53 | Per-circuit kWh/cost, peak demand, generator kWh |

Columns B-F = Boilers 1-5 (or circuits for electric section), G-H = Future/spare, I = Totals/Averages.

---

## Data Mapping

### Auto-populated from steam_plant.json (22 cells)

| UP Cell(s) | Description | JSON Key | Transform |
|-----------|-------------|----------|-----------|
| B5:F5 | Lbs Steam by Gas (per boiler) | `b1_steam_gas` through `b5_steam_gas` | Direct monthly value |
| D6:F6 | Lbs Steam by Oil (B3-B5) | `b3_steam_oil`, `b4_steam_oil`, `b5_steam_oil` | Direct |
| D7:F7 | Oil Burned gallons (B3-B5) | `b3_oil`, `b4_oil`, `b5_oil` | Direct |
| B10:F10 | Gas Use SCF (per boiler) | `b1_gas` through `b5_gas` | Direct |
| B3:F3 | Boiler Days | `b{n}_runtime` delta / 24 | Cumulative delta, divide by 24 |
| C11 | Gen1 Gas SCF | `gen1_gas` delta | Cumulative delta |
| E11 | Gen2 Gas SCF | `gen2_gas` delta | Cumulative delta |
| I46 | Gen1 kWh | `gen1_kwh` delta | Cumulative delta |
| I47 | Gen2 kWh | `gen2_kwh` delta | Cumulative delta |
| I48 | Gen3 kWh | `gen3_kwh` delta | Cumulative delta |

### Auto-populated from data.json (2 cells)

| UP Cell | Description | JSON Key | Transform |
|---------|-------------|----------|-----------|
| B24 | Degree Days Heating | `hdd.fy26[monthIndex]` | Direct (index 0=Jul) |
| B25 | Degree Days Cooling | Derived from `variance` data | Direct |

### Formula cells (auto-calculate, ~20 cells)

These cells contain Excel formulas that compute from the input cells above:

| UP Row | Description | Formula Pattern |
|--------|-------------|----------------|
| 4 | Total Lbs Steam | `=B5+B6` per boiler |
| 9 | Gas Use Therms | `=$D$24*B10/100000` |
| 11 I | Gen Gas Therms Total | `=(C11+E11)*D24/100000` |
| 12 | Plant Internal Gas | `=I8-I9-I11` |
| 14 | Lbs/Gallon Oil | `=IF(D7=0,0,D6/D7)` |
| 15 | Lbs/Therm Gas | `=IF(B9=0,0,B5/B9)` |
| 17 | Oil Cost | `=B7*$D$26` |
| 18 | Gas Cost | `=B9*$D$25` |
| 19 | Total Fuel Cost | `=SUM(B17+B18)` |
| 21-22 | Cost per 1000 lbs | Division formulas |
| 27 D | Makeup Water % | `=(gal)*8.33/I4` |
| 34 | Well Total | `=SUM(B30:B33)` |
| 36-37 | Cost per 1000 gal | Division formulas |
| 51 | Cost per kWh | `=B50/B49` |

### Manual entry required (~25 cells)

| UP Cell | Description | Source |
|---------|-------------|--------|
| I8 | Gas Delivered Therms | Shell/Kintec bill (MMBTU * 10) |
| D24 | Gas BTU/cuft | Avista BTU Rating monthly report |
| D25 | Gas Cost/Therm | Kintec invoice total / therms |
| D26 | Oil Cost/Gallon | Coleman Oil invoice |
| F24-F26 | Budget: Labor, G&S, Fuel | 5280 Budget Statement |
| B26-B27 | Max/Min lbs per hour steam | Operator log |
| B30:B33 | Well gallons (#4, #6, #7, #8) | Well meter readings (or SkySpark future) |
| C30:G34 | Well costs | Cost accounting |
| B38 | Lbs Chlorine | Master Water File |
| B46:F47 | Peak demand date/time | Avista electric bill |
| B48:F48 | Peak demand KVA | Avista electric bill |
| B49:F49 | kWh per circuit | Avista electric bill |
| B50:F50 | Cost per circuit | Avista electric bill |
| I49 | Biotech kWh | Route A meter reading |

---

## UI Design — "UP Report" Tab

### Layout

```
┌──────────────────────────────────────────────────┐
│  Month: [July 2025 ▼]    [Load Data]             │
│                                                    │
│  Status: ✓ Steam data loaded  ✓ Energy data loaded │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│  STEAM PRODUCTION (auto-filled, read-only)        │
│  ┌───────────────────────────────────────────┐    │
│  │       B1      B2      B3      B4      B5  │    │
│  │ Days  31.0    31.0    31.0    31.0    0.0  │    │
│  │ Steam 12.3M   8.1M   34.0M   32.8M   0   │    │
│  │ Gas   11.7M   8.8M   29.5M   28.1M   0   │    │
│  │ Oil   -       -       0       0       0   │    │
│  └───────────────────────────────────────────┘    │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│  MANUAL ENTRY (editable inputs)                   │
│                                                    │
│  Gas & Fuel                                       │
│  Gas Delivered (MMBTU): [_____] (from Kintec bill)│
│  Gas BTU/cuft:          [_____] (from BTU report) │
│  Gas Cost/Therm:        [_____] (from Kintec inv) │
│  Oil Cost/Gallon:       [_____] (from Coleman)    │
│                                                    │
│  Weather                                          │
│  HDD: [18] (auto)    CDD: [105] (auto)           │
│  Max lbs/hr: [_____]  Min lbs/hr: [_____]        │
│                                                    │
│  Electric (from Avista bill)                      │
│  [Per-circuit input table: kWh + Cost x 5 circuits│
│   + peak demand date/time/KVA]                    │
│                                                    │
│  Water (from well meters)                         │
│  [Well #4-#8 gallons + cost inputs]               │
│                                                    │
│  Budget                                           │
│  Labor: [_____]  G&S: [_____]                     │
│  Fuel Budget: [_____]                             │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│  PREVIEW (full UP report layout, read-only)       │
│  [Matches exact Excel row/column structure]       │
│  Formula cells show calculated values             │
│  Color coding: green=auto, blue=manual, gray=calc │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│  [Generate UP Report Excel]  [Save Manual Entries] │
└──────────────────────────────────────────────────┘
```

### Behavior

1. **Month selector** shows months available in `steam_plant.json` (2020-07 through latest)
2. **Load Data** pulls the selected month from both JSON files, populates auto-fill fields
3. **Manual entry fields** are grouped by source (gas/fuel, weather, electric, water, budget)
4. **Auto-filled fields** shown as read-only with green background; user can override any value
5. **Preview table** renders the complete UP report in the same layout as the Excel file
6. **Generate Excel** creates `UP{MMYY}.xlsx` with:
   - All values in correct cells
   - Formulas preserved (not just computed values)
   - Merged cells matching original format
   - Column widths and formatting approximated
7. **Save Manual Entries** persists to localStorage key `wsu_up_manual_{YYYY-MM}`

### localStorage Schema

```javascript
// Key: wsu_up_manual_2025-07
{
  "gas_delivered_mmbtu": 39668,
  "gas_btu_cuft": 1056.52,
  "gas_cost_therm": 0.5298,
  "oil_cost_gallon": 3.95,
  "max_lbs_hr": null,
  "min_lbs_hr": null,
  "well4_gal": 0,
  "well6_gal": 8000,
  "well7_gal": 23924992,
  "well8_gal": 47475968,
  "labor_budget": null,
  "gs_budget": null,
  "fuel_budget": 242087.59,
  "biotech_kwh": null,
  "circuit_kwh": [4710814, 2618479, 2834577, 1765504, 3066807],
  "circuit_cost": [471779, 228946, 239759, 157139, 261583],
  "peak_date": ["7/21/2025", ...],
  "peak_time": ["2:15 PM", ...],
  "peak_kva": [7776, ...],
  "chlorine_lbs": null,
  "well_costs": { ... }
}

// Static values that carry forward month-to-month
// Key: wsu_up_static
{
  "avista_accounts": ["15400-44701-0", ...],
  "oil_cost_gallon": 3.95
}
```

---

## Excel Generation

Using SheetJS (already loaded in steam-plant.html):

1. Create workbook with single sheet named `UP{MMYY}` (e.g., `UP0725`)
2. Place all values in exact cell positions matching the original UP template
3. Write formulas (not computed values) for calculated cells so the Excel file is a live spreadsheet
4. Apply merged cells: A1:I1 (title), section headers (rows 13, 16, 20, 23, 28, 39, 43)
5. Set column widths to approximate the original
6. Download as `UP{MMYY}.xlsx`

### Formula handling

SheetJS supports writing formulas via `{ t: 's', f: 'formula' }` cell objects. All ~20 formula cells will be written as formulas, not pre-computed values. This means the downloaded Excel file works exactly like the manually-created ones.

---

## What This Does NOT Include (future phases)

- **Annual UP consolidation** — combining 12 monthly UP files into a fiscal year summary
- **UP-specific dashboard charts** — trend analysis of UP metrics over time
- **SkySpark well water integration** — auto-populating well gallons from SkySpark export
- **Avista circuit data from SkySpark** — auto-populating per-circuit kWh/cost

---

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `steam-plant.html` | Modify | Add UP Report tab (HTML + CSS + JS) |
| No new files | — | All logic inline in existing dashboard |
