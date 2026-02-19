WSU ENERGY COST PROJECTION DASHBOARD -- FY2026
=================================================

Interactive web dashboard for tracking and projecting energy costs across all WSU Pullman Facility Services utility accounts (Avista electric & gas, Inland Power, Kintec gas commodity).

Live site: https://jswsu.github.io/wsu-energy-dashboard/ (password protected)


WHAT THIS PROJECT DOES
-----------------------

- Displays monthly energy cost data (actuals + forecasts) for FY2026 (July 2025 -- June 2026)
- Compares actual spending to forecasts with budget status tracking
- Breaks down costs by electric vs gas, with supplier detail (Kintec, Avista, Inland Power)
- Shows trends across 9 interactive tabs: Dashboard, Monthly Detail, Gas Analysis, Energy Use, Year-over-Year, Cumulative Summary, Price vs Volume, HDD/Weather, Data Sources
- Includes a print-optimized executive summary for 8.5x11 output


HOW IT WORKS
------------

1. Energy billing data is entered into the Excel workbook (4 sheets)
2. Click "Export data.json" button in Excel (runs VBA macro)
3. Macro reads data, cross-checks against Consolidated Data, writes data.json
4. Upload data.json to this GitHub repo (web upload or git push)
5. GitHub Pages serves the updated dashboard automatically


REPOSITORY FILES
----------------

File                    Size      Description
----                    ----      -----------
index.html              ~58 KB    Complete web application (HTML + CSS + JS, single file)
data.json               ~6 KB     Current data export from Excel workbook
ExportDataJSON.bas      ~24 KB    VBA macro source code for the Excel export
README.txt              --        This file
docs/                   --        Full documentation suite (see below)


QUICK START: MONTHLY DATA UPDATE
----------------------------------

1. Open the Excel workbook and verify the latest month's data is entered
2. Click the crimson "Export data.json" button on the "Executive Summary (Print)" sheet
3. Review the verification message for any discrepancy warnings
4. Upload the new data.json to this GitHub repo
5. Verify the live site: check "Last Updated" date and spot-check a few numbers

For detailed step-by-step instructions, see docs/OPERATIONS-RUNBOOK.txt.


TECHNOLOGY STACK
----------------

Component       Technology
---------       ----------
Web app         Single HTML file with inline CSS and JavaScript
Charts          Chart.js v4.4.7 (loaded via CDN)
Hosting         GitHub Pages (static site, automatic deployment from main branch)
Data export     VBA macro in Excel (compatible with Excel 2016+ / Microsoft 365)
Build tools     None -- no Node.js, no bundler, no package.json


DOCUMENTATION
-------------

Document                            Audience                    What It Covers
--------                            --------                    --------------
docs/OPERATIONS-RUNBOOK.txt         Non-technical operator      Step-by-step monthly update + FY rollover procedure
docs/ARCHITECTURE.txt               Developer / IT              Code structure, auth, charts, KPIs, dark mode, print, tech debt
docs/DATA-DICTIONARY.txt            Anyone                      Every field in data.json: type, unit, Excel source, dashboard usage
docs/VBA-REFERENCE.txt              Developer / Excel user      Macro functions, sheet-to-JSON mapping, verification logic
docs/TROUBLESHOOTING.txt            Anyone                      Common problems with symptoms, causes, and solutions


DASHBOARD FEATURES
-------------------

- 8 interactive KPI cards -- hover for tooltips, click to expand monthly detail
- Budget status banner -- green (under budget), yellow (watch), red (over budget)
- Dark mode -- toggle in header, persists across sessions
- Print report -- clean single-page executive summary optimized for 8.5x11
- Forecast row shading -- subtle blue tint on forecast months in all tables
- Data verification -- "Verified vs Consolidated Data" badge when cross-check passes


CONTACT & OWNERSHIP
--------------------

Department:                   WSU Facilities Services
POC:			      John Slagboom (john.slagboom@wsu.edu / energy.1@wsu.edu)
Campus:                       Pullman
Documentation last reviewed:  February 2026
