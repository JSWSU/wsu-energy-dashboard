"""Build data-trends.json: monthly + annual cost and MMBTU, FY2020-FY2027.

Sources (verified 07/30/2026, MMBTU cross-checked across files to within rounding):
- FY2020-FY2023: FY2024 archive 'Energy Data for Projection summary.xlsx', sheet 'all',
  cost/MMBTU column pairs at cols 12-19, rows 2-13 = Jul..Jun.
- FY2024:        FY2025 archive 'Energy Data for Projection summary1.xlsx', cols 20/21.
- FY2025:        data-fy25.json (official archived report numbers).
- FY2026:        data-fy26.json (complete year: Avista + Inland electric bills,
                 Kinect invoices + Avista gas bills).
- FY2027:        data.json blended series: fy27.totalActual = actual bills
                 where a month is billed, forecast elsewhere (same series as
                 the FY page KPI). Flagged forecast until all 12 are actual.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from inland_workbook import DEFAULT_WORKBOOK

BASE = Path(r"R:\Energy Services Admin\Energy Files\Annual Elect & Steam Use")
OUT_PATH = DEFAULT_WORKBOOK.parent / "data-trends.json"
GIT = Path(r"C:\Users\john.slagboom\Desktop\Git")


CURRENT_FY = "FY2027"  # the open fiscal year, read from data.json
MONTH_FY_ORDER = ["July", "August", "September", "October", "November", "December",
                  "January", "February", "March", "April", "May", "June"]
FY2026_NOTE = ("Complete year: 12 actual months. Electric = Avista + Inland bills; "
               "gas = Kinect invoices + Avista gas bills.")
SOURCES_NOTE = ("FY2020-FY2024 from the archived Energy Data for Projection "
                "summaries; FY2025 from the archived Energy Cost Projection "
                "Report July 2025; FY2026-FY2027 from the live FY2027 workbook.")


def actual_month_count(is_actual) -> int:
    """Months in the unbroken run of actual months from July (the report-month
    rule); a gap ends the run. A closed-year file has no isActual: 12."""
    if is_actual is None:
        return 12
    n = 0
    for v in is_actual:
        if not v:
            break
        n += 1
    return n


def current_fy_note(n_actual: int, fy_label: str, hedge) -> str:
    """Note for the open fiscal year, stated from the actual-month count."""
    start = int(fy_label[2:]) - 1
    method = f"same-month prior year, electric trend, {hedge:g}% gas hedge"
    if n_actual >= 12:
        return "Complete year: 12 actual months (actual bills)."
    if n_actual == 0:
        return f"0 actual months; all 12 months are forecast ({method})."
    last = MONTH_FY_ORDER[n_actual - 1]
    last_y = start if n_actual <= 6 else start + 1
    nxt = MONTH_FY_ORDER[n_actual]
    nxt_y = start if n_actual < 6 else start + 1
    unit = "month" if n_actual == 1 else "months"
    return (f"{n_actual} actual {unit} (July {start} to {last} {last_y}, actual bills); "
            f"{nxt} {nxt_y} to June {start + 1} forecast ({method}).")


def current_fy_series(d: dict) -> tuple[dict, int]:
    """(series, actual month count) for the open fiscal year from its FY data
    file. Monthly values = fy27.totalActual / energyUse.totalActual: actual
    where billed, forecast elsewhere (the FY page KPI series), so the trends
    page equals the FY page. 'forecast' stays True until all 12 are actual."""
    fy, eu = d["fy27"], d["energyUse"]
    n = actual_month_count(fy.get("isActual"))
    series = {"cost": list(fy["totalActual"]), "mmbtu": list(eu["totalActual"])}
    if n < 12:
        series["forecast"] = True
    return series, n


def build_trends(years: dict, fy26: dict, cur: dict, updated: str,
                 fy_label: str = CURRENT_FY) -> dict:
    """Pure: archive years (FY2020-FY2025 already in `years`) + the FY2026
    closed file + the open-year FY file -> the data-trends.json dict."""
    years = dict(years)
    years["FY2026"] = {"cost": fy26["fy27"]["totalActual"],
                       "mmbtu": fy26["energyUse"]["totalActual"]}
    years[fy_label], n_actual = current_fy_series(cur)

    annual = {}
    for fy, d in years.items():
        c, m = sum(d["cost"]), sum(d["mmbtu"])
        annual[fy] = {"cost": c, "mmbtu": m,
                      "rate": round(c / m, 2) if m else 0,
                      "forecast": bool(d.get("forecast"))}

    return {
        "lastUpdated": updated,
        "years": years,
        "annual": annual,
        "notes": {
            "FY2026": FY2026_NOTE,
            fy_label: current_fy_note(n_actual, fy_label, cur["fy27"].get("hedge", 10)),
            "sources": SOURCES_NOTE,
        },
    }


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
    import pythoncom
    import win32com.client

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
    cur = json.loads((GIT / "data.json").read_text(encoding="utf-8"))
    out = build_trends(years, fy26, cur, datetime.now().strftime("%B %#d, %Y"))
    annual = out["annual"]
    OUT_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_PATH} ({OUT_PATH.stat().st_size:,} bytes)")
    for fy in sorted(annual):
        a = annual[fy]
        tag = " (forecast)" if a["forecast"] else ""
        print(f"  {fy}: ${a['cost']:>12,}  {a['mmbtu']:>11,} MMBTU  ${a['rate']:.2f}/MMBTU{tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
