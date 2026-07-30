"""Build data-trends.json: monthly + annual cost and MMBTU, FY2020-FY2027.

Sources (verified 07/30/2026, MMBTU cross-checked across files to within rounding):
- FY2020-FY2023: FY2024 archive 'Energy Data for Projection summary.xlsx', sheet 'all',
  cost/MMBTU column pairs at cols 12-19, rows 2-13 = Jul..Jun.
- FY2024:        FY2025 archive 'Energy Data for Projection summary1.xlsx', cols 20/21.
- FY2025:        data-fy25.json (official archived report numbers).
- FY2026:        data-fy26.json (June electric partial; noted).
- FY2027:        data.json forecast series.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pythoncom
import win32com.client

from inland_workbook import DEFAULT_WORKBOOK

BASE = Path(r"R:\Energy Services Admin\Energy Files\Annual Elect & Steam Use")
OUT_PATH = DEFAULT_WORKBOOK.parent / "data-trends.json"
GIT = Path(r"C:\Users\john.slagboom\Desktop\Git")


def read_pairs(xl, path, pairs):
    """pairs: {fy_label: (cost_col, mmbtu_col)} -> {fy: {'cost': [...12], 'mmbtu': [...12]}}"""
    wb = xl.Workbooks.Open(str(path), UpdateLinks=0, ReadOnly=True,
                           IgnoreReadOnlyRecommended=True, Notify=False)
    out = {}
    try:
        ws = wb.Sheets("all")
        for fy, (cc, mc) in pairs.items():
            cost = [float(ws.Cells(r, cc).Value or 0) for r in range(2, 14)]
            mmbtu = [float(ws.Cells(r, mc).Value or 0) for r in range(2, 14)]
            out[fy] = {"cost": [int(round(x)) for x in cost],
                       "mmbtu": [int(round(x)) for x in mmbtu]}
    finally:
        wb.Close(SaveChanges=False)
    return out


def main() -> int:
    pythoncom.CoInitialize()
    xl = win32com.client.DispatchEx("Excel.Application")
    xl.Visible = False
    xl.DisplayAlerts = False
    xl.AskToUpdateLinks = False
    xl.EnableEvents = False
    xl.AutomationSecurity = 3

    years = {}
    try:
        years.update(read_pairs(
            xl, BASE / "FY2024" / "Energy Data for Projection summary.xlsx",
            {"FY2020": (12, 13), "FY2021": (14, 15),
             "FY2022": (16, 17), "FY2023": (18, 19)}))
        years.update(read_pairs(
            xl, BASE / "FY2025" / "Energy Data for Projection summary1.xlsx",
            {"FY2024": (20, 21)}))
    finally:
        xl.Quit()

    fy25 = json.loads((GIT / "data-fy25.json").read_text(encoding="utf-8"))
    years["FY2025"] = {"cost": fy25["fy27"]["totalActual"],
                       "mmbtu": fy25["energyUse"]["totalActual"]}

    fy26 = json.loads((GIT / "data-fy26.json").read_text(encoding="utf-8"))
    years["FY2026"] = {"cost": fy26["fy27"]["totalActual"],
                       "mmbtu": fy26["energyUse"]["totalActual"]}

    fy27 = json.loads((GIT / "data.json").read_text(encoding="utf-8"))
    years["FY2027"] = {"cost": fy27["fy27"]["totalFcast"],
                       "mmbtu": fy27["energyUse"]["totalFcast"],
                       "forecast": True}

    annual = {}
    for fy, d in years.items():
        c, m = sum(d["cost"]), sum(d["mmbtu"])
        annual[fy] = {"cost": c, "mmbtu": m,
                      "rate": round(c / m, 2) if m else 0,
                      "forecast": bool(d.get("forecast"))}

    out = {
        "lastUpdated": datetime.now().strftime("%B %#d, %Y"),
        "years": years,
        "annual": annual,
        "notes": {
            "FY2026": "June 2026 electric partial until the next Avista pull; "
                      "Kintec gas Jan-Jun 2026 excludes the small Avista transport charge.",
            "FY2027": "Forecast (same-month prior year, electric trend, 10% gas hedge). "
                      "No actual bills posted yet.",
            "sources": "FY2020-FY2024 from the archived Energy Data for Projection "
                       "summaries; FY2025 from the archived Energy Cost Projection "
                       "Report July 2025; FY2026-FY2027 from the live FY2027 workbook.",
        },
    }
    OUT_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_PATH} ({OUT_PATH.stat().st_size:,} bytes)")
    for fy in sorted(annual):
        a = annual[fy]
        tag = " (forecast)" if a["forecast"] else ""
        print(f"  {fy}: ${a['cost']:>12,}  {a['mmbtu']:>11,} MMBTU  ${a['rate']:.2f}/MMBTU{tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
