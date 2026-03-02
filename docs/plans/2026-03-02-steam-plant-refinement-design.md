# Steam Plant Dashboard Refinement Design

**Date:** 2026-03-02
**Scope:** Two refinements to `steam-plant.html`

---

## Refinement 1: Executive FYTD Overview Tab

### Problem
Overview KPIs show all-time totals (66 months). Management needs current Fiscal Year To Date comparisons for budget planning.

### Design

**FY Selector:** Dropdown in the Overview section, auto-populated from data (FY21-FY26). Defaults to latest FY. Only affects Overview tab.

**6 KPI Cards** each display:
- **FYTD actual** (primary value, large font)
- **Prior FY same-period comparison** with % change (sub line)
- **Full-year projection** based on current pace: `(FYTD / months elapsed) * 12` (sub line)
- **Expandable table** with month-by-month current vs prior FY comparison

KPIs: Campus Gas, Campus Steam, Boiler Runtime, Generator kWh, Plant Water, Data Period.

**% change coloring:** Up = red arrow, Down = green arrow (simple directional, no cost judgment).

**Charts:**
- Monthly Gas & Steam trend: selected FY drawn thicker (3px, solid), other FYs thinner (1px, semi-transparent)
- FY bar chart: selected FY full opacity, others at 50%. Incomplete FY shows dashed outline at projected total.

### Projection Logic
```
monthsInFY = 12
monthsElapsed = count of months in selected FY that have data
fytdTotal = sum of selected FY months
projection = (fytdTotal / monthsElapsed) * monthsInFY
```

For prior-year same-period comparison, count the same number of months from prior FY start (July):
```
priorFYMonths = prior FY's first N months, where N = monthsElapsed
priorSamePeriod = sum of those months
pctChange = ((fytdTotal - priorSamePeriod) / priorSamePeriod) * 100
```

---

## Refinement 2: Info-Box Explainers on All Charts/Tables

### Problem
Charts and tables lack context. Users unfamiliar with steam plant operations cannot interpret the visualizations without training.

### Design
Add a blue `info-box` div above every chart and table (inside the `.card`, between the `h2` and the chart/table). Each contains 1-2 sentences explaining what the visualization shows and how to read it.

### Explainer Text (16 total)

**Overview Tab:**
1. Monthly Gas & Steam Trends: "Monthly gas consumption (left axis) and steam production (right axis). The selected fiscal year is highlighted. Gas and steam rise and fall together — divergence may indicate efficiency changes."
2. Gas by Fiscal Year: "Total gas consumed per fiscal year. The current year shows actual-to-date with projected full-year total. Compare year-over-year to identify consumption trends."

**Gas Consumption Tab:**
3. Monthly Gas by Boiler: "Each bar shows one month's total gas consumption, stacked by boiler. Boilers 1-2 are at CASP (Central), Boilers 3-5 at GWSP (Grimes Way). Taller bars indicate higher heating demand."
4. CASP vs GWSP vs Campus: "Gas consumption comparison between the two steam plants. The Campus line equals CASP + GWSP combined."
5. Oil Usage: "Fuel oil burned by dual-fuel boilers (B3, B4, B5). Oil firing is uncommon — non-zero months indicate gas supply constraints or scheduled testing."
6. Gas Detail Table: "Monthly gas breakdown by boiler with plant and campus totals. Months with fuel oil usage are highlighted in red."

**Steam & Efficiency Tab:**
7. Monthly Steam by Boiler: "Steam production stacked by boiler. B1-B2 produce steam from gas only. B3-B5 are dual-fuel and show total steam (gas + oil combined)."
8. Efficiency Ratio: "Steam output (lbs) divided by gas input (scf) for each boiler over time. Higher ratios indicate better efficiency. Gaps mean the boiler was offline that month."
9. Economizer Delta-T: "Temperature gain across economizer heat exchangers (outlet minus inlet, degrees F). Higher delta-T means more heat recovered from exhaust gases, improving efficiency."

**Runtime & Availability Tab:**
10. Monthly Boiler Runtime: "Total run hours per boiler per month. Higher runtime during winter heating season is expected. Significant drops may indicate maintenance outages."
11. Availability Heatmap: "Boiler runtime over the last 24 months. Green (>500 hrs) = heavily used, Yellow (100-500) = moderate, Red (<100) = light use, Dash = offline or idle."
12. Generator Runtime & Output: "Monthly electricity generated (kWh) by each on-site generator. Generators typically run during peak demand periods or utility outages."

**Plant Water Tab:**
13. Monthly Water by Source: "Total plant water from all sources, stacked by type. GWSP sources include raw water, potable (city), and RO permeate. CASP tracks east and west sides separately."
14. GWSP Water Trends: "Individual GWSP water source trends. Raw water is untreated intake, potable is city supply, permeate is reverse osmosis system output."
15. Makeup Water Temperature: "GWSP boiler makeup water temperature follows seasonal patterns. Colder inlet water in winter requires more energy to heat, affecting boiler efficiency."
16. CASP East vs West: "Side-by-side comparison of CASP east and west water consumption. Significant or persistent imbalance may indicate a leak or valve issue."

---

## Files Modified

| File | Changes |
|------|---------|
| `steam-plant.html` | Rewrite Overview tab KPIs + charts, add FY selector dropdown, add 16 info-box explainers, add FY calculation helpers |

## No New Files

All changes are within the existing `steam-plant.html`.
