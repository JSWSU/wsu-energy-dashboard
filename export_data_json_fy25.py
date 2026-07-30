"""Export data-fy25.json for the FY2025 (Jul 2024 - Jun 2025) dashboard page.

Computes everything from the workbook's ConsolidatedData / HDD Data / Kintec
Data sheets directly (the Executive Summary rows are CurrentFY=2027-framed and
can't serve a prior-year page). Emits the SAME schema slot names index.html
consumes (fy27 = current year of the page, fy26gas = prior-year gas, etc.) so
fy26.html is a config-only copy of index.html.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

import pythoncom
import win32com.client

from inland_workbook import DEFAULT_WORKBOOK

OUT_PATH = DEFAULT_WORKBOOK.parent / "data-fy25.json"


def _num(v, default=0.0):
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def month_label(dt) -> str:
    return f"{dt.strftime('%b')}-{dt.strftime('%y')}"


FY26_CAL = [(2024, 7), (2024, 8), (2024, 9), (2024, 10), (2024, 11), (2024, 12),
            (2025, 1), (2025, 2), (2025, 3), (2025, 4), (2025, 5), (2025, 6)]
FY25_CAL = [(2023, 7), (2023, 8), (2023, 9), (2023, 10), (2023, 11), (2023, 12),
            (2024, 1), (2024, 2), (2024, 3), (2024, 4), (2024, 5), (2024, 6)]


def read_history(ws_consol) -> dict:
    """(year, month) -> sums incl. per-source gas split."""
    last_row = ws_consol.Cells(ws_consol.Rows.Count, 1).End(-4162).Row
    ur = ws_consol.Range(ws_consol.Cells(2, 1), ws_consol.Cells(last_row, 16)).Value
    hist = {}
    for row in ur:
        src = row[0]
        if not src:
            continue
        my = row[13]
        if not hasattr(my, "year"):
            continue
        k = (my.year, my.month)
        h = hist.setdefault(k, {"elec": 0.0, "gas": 0.0, "kwh": 0.0,
                                "elecMM": 0.0, "gasMM": 0.0,
                                "kintecGas": 0.0, "avistaGas": 0.0})
        h["elec"] += _num(row[9])
        h["gas"] += _num(row[10])
        h["kwh"] += _num(row[7])
        h["elecMM"] += _num(row[14])
        h["gasMM"] += _num(row[15])
        if str(src) == "Kintec":
            h["kintecGas"] += _num(row[10])
        elif str(src) == "Avista":
            h["avistaGas"] += _num(row[10])
    return hist


def main() -> int:
    pythoncom.CoInitialize()
    xl = win32com.client.DispatchEx("Excel.Application")
    xl.Visible = False
    xl.DisplayAlerts = False
    xl.AskToUpdateLinks = False
    xl.EnableEvents = False
    xl.AutomationSecurity = 3
    wb = xl.Workbooks.Open(str(DEFAULT_WORKBOOK), UpdateLinks=0, ReadOnly=True,
                           IgnoreReadOnlyRecommended=True, Notify=False)
    try:
        hist = read_history(wb.Sheets("Consolidated Data"))
        ws_hdd = wb.Sheets("HDD Data")
        ws_kin = wb.Sheets("Kintec Data")

        def g(cal, f):
            return [hist.get(k, {}).get(f, 0.0) for k in cal]

        # ---- current year of this page = FY26 actuals ----
        elec26, gas26 = g(FY26_CAL, "elec"), g(FY26_CAL, "gas")
        kwh26 = g(FY26_CAL, "kwh")
        emm26, gmm26 = g(FY26_CAL, "elecMM"), g(FY26_CAL, "gasMM")
        kin26, avi26 = g(FY26_CAL, "kintecGas"), g(FY26_CAL, "avistaGas")

        # Forecast comparison series: same method as the FY27 page, based on
        # FY25 with elec YoY trend from Jul-Dec 2024 vs Jul-Dec 2023.
        e_new = sum(hist.get((2023, m), {}).get("elec", 0.0) for m in range(7, 13))
        e_old = sum(hist.get((2022, m), {}).get("elec", 0.0) for m in range(7, 13))
        elec_factor = (e_new / e_old) if e_old else 1.0
        # Guard: incomplete base history produces a nonsense ratio. A real YoY
        # trend for campus electric is a few percent; outside that, base data
        # is missing -> no trend adjustment.
        if not (0.8 <= elec_factor <= 1.3):
            elec_factor = 1.0
        hedge = 10.0
        elecF = [hist.get(k, {}).get("elec", 0.0) * elec_factor for k in FY25_CAL]
        gasF = [hist.get(k, {}).get("gas", 0.0) * (1 + hedge / 100) for k in FY25_CAL]
        totF = [e + gsc for e, gsc in zip(elecF, gasF)]

        fy_cur = {
            "totalActual": [int(round(e + gsc)) for e, gsc in zip(elec26, gas26)],
            "elecActual": [int(round(x)) for x in elec26],
            "gasActual": [int(round(x)) for x in gas26],
            "totalFcast": [int(round(x)) for x in totF],
            "elecFcast": [int(round(x)) for x in elecF],
            "gasFcast": [int(round(x)) for x in gasF],
            # Pie + gas tables want the Kintec/Avista split; use FY26 actuals.
            "kintecFcast": [int(round(x)) for x in kin26],
            "avistaFcast": [int(round(x)) for x in avi26],
            "hedge": hedge,
            "forecastMeta": {
                "method": "FY2025 actuals vs a same-month-FY2024 forecast",
                "elecFactor": round(elec_factor, 3),
                "gasHedgePct": hedge,
                "baseWindow": "Jul 2023 - Jun 2024 billing history",
                
            },
        }

        # ---- prior-year gas section = FY25 ----
        gas25 = g(FY25_CAL, "gas")
        gmm25 = g(FY25_CAL, "gasMM")
        fy_prior_gas = {
            "cost": [int(round(x)) for x in gas25],
            "mmbtu": [int(round(x)) for x in gmm25],
            "perUnit": [round(c / m, 2) if m else 0.0 for c, m in zip(gas25, gmm25)],
            "kintec": [int(round(x)) for x in g(FY25_CAL, "kintecGas")],
            "avista": [int(round(x)) for x in g(FY25_CAL, "avistaGas")],
        }

        # ---- energy use (FY26) ----
        totmm26 = [e + gm for e, gm in zip(emm26, gmm26)]
        totmm25F = [hist.get(k, {}).get("elecMM", 0.0) + hist.get(k, {}).get("gasMM", 0.0)
                    for k in FY25_CAL]
        energy_use = {
            "totalActual": [int(round(x)) for x in totmm26],
            "elecActual": [int(round(x)) for x in emm26],
            "gasActual": [int(round(x)) for x in gmm26],
            "totalFcast": [int(round(x)) for x in totmm25F],
            "kwhActual": [int(round(x)) for x in kwh26],
            "kwhRate": [round(e / k, 4) if k else 0.0 for e, k in zip(elec26, kwh26)],
        }

        # ---- YoY MMBTU: prior = FY25, current = FY26 ----
        emm25, gmm25b = g(FY25_CAL, "elecMM"), g(FY25_CAL, "gasMM")
        yoy = {
            "fy26total": [int(round(e + gm)) for e, gm in zip(emm25, gmm25b)],
            "fy26elec": [int(round(x)) for x in emm25],
            "fy26gas": [int(round(x)) for x in gmm25b],
            "fy27total": [int(round(x)) for x in totmm26],
            "fy27elec": [int(round(x)) for x in emm26],
            "fy27gas": [int(round(x)) for x in gmm26],
        }

        # ---- cumulative ----
        cum = lambda xs: [sum(xs[:i + 1]) for i in range(len(xs))]
        act = fy_cur["totalActual"]; fca = fy_cur["totalFcast"]
        mact = energy_use["totalActual"]; mfc = energy_use["totalFcast"]
        ca, cf, cma, cmf = cum(act), cum(fca), cum(mact), cum(mfc)
        cumul = {
            "actual": ca, "forecast": cf,
            "delta": [f - a for a, f in zip(ca, cf)],
            "deltaPct": [round((f - a) / f * 100, 1) if f else 0.0 for a, f in zip(ca, cf)],
            "mmbtuAct": cma, "mmbtuFcast": cmf,
            "mmbtuDelta": [f - a for a, f in zip(cma, cmf)],
            "mmbtuDeltaPct": [round((f - a) / f * 100, 1) if f else 0.0 for a, f in zip(cma, cmf)],
        }

        # ---- HDD: sheet cols C=FY25, D=FY26, E=normal ----
        hdd_cur = [int(_num(ws_hdd.Cells(r, 3).Value)) for r in range(6, 18)]   # sheet col C = FY25
        hdd_n = [int(_num(ws_hdd.Cells(r, 5).Value)) for r in range(6, 18)]
        hdd_prior = [0] * 12   # FY2024 HDD not tracked
        hdd = {"fy26": hdd_prior, "fy27": hdd_cur, "normal": hdd_n}
        hdd_25 = hdd_prior   # variance section prior slot
        hdd_26 = hdd_cur     # variance section current slot

        # ---- variance: prior = FY25 cost, current = FY26 ----
        cost25 = [int(round(hist.get(k, {}).get("elec", 0.0) + hist.get(k, {}).get("gas", 0.0)))
                  for k in FY25_CAL]
        mm25 = [int(round(x)) for x in totmm25F]
        variance = {
            "fy26cost": cost25,
            "fy27cost": act,
            "costDelta": [c - p for p, c in zip(cost25, act)],
            "fy26mmbtu": mm25,
            "fy27mmbtu": [int(round(x)) for x in totmm26],
            "mmbtuDelta": [c - p for p, c in zip(mm25, [int(round(x)) for x in totmm26])],
            "mmbtuDeltaPct": [round((c - p) / p * 100, 1) if p else 0.0
                              for p, c in zip(mm25, [int(round(x)) for x in totmm26])],
            "fy26hdd": hdd_25,
            "fy27hdd": hdd_26,
            "hddDeltaPct": [int(round((c - p) / p * 100)) if p else 0
                            for p, c in zip(hdd_25, hdd_26)],
            "normalHdd": hdd_n,
        }

        # ---- Kintec table (all months, unchanged) ----
        last_kin = ws_kin.Cells(ws_kin.Rows.Count, 1).End(-4162).Row
        months, dths, cost = [], [], []
        for r in range(2, last_kin + 1):
            v = ws_kin.Cells(r, 1).Value
            if not v:
                continue
            months.append(month_label(v))
            dths.append(int(_num(ws_kin.Cells(r, 6).Value)))
            cost.append(int(_num(ws_kin.Cells(r, 5).Value)))
        kintec = {"months": months, "dths": dths, "cost": cost}

        verification = {
            "source": "Consolidated Data",
            "elecDollar": [int(round(x)) for x in elec26],
            "gasDollar": [int(round(x)) for x in gas26],
            "kwh": [int(round(x)) for x in kwh26],
            "elecMmbtu": [int(round(x)) for x in emm26],
            "gasMmbtu": [int(round(x)) for x in gmm26],
        }

        out = {
            "lastUpdated": datetime.now().strftime("%B %#d, %Y"),
            "fy27": fy_cur,
            "fy26gas": fy_prior_gas,
            "energyUse": energy_use,
            "yoy": yoy,
            "cumul": cumul,
            "variance": variance,
            "hdd": hdd,
            "kintec": kintec,
            "verification": verification,
        }
        OUT_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(f"Wrote {OUT_PATH} ({OUT_PATH.stat().st_size:,} bytes)")
        print(f"FY26 totalActual: {fy_cur['totalActual']}")
        print(f"FY26 total: ${sum(fy_cur['totalActual']):,.0f}")
    finally:
        wb.Close(SaveChanges=False)
        xl.Quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
