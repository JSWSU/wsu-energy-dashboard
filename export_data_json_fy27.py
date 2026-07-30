"""Export data.json for the FY27 dashboard.

Reads Executive Summary (Print), HDD Data, Kintec Data, Consolidated Data
from the FY27-rolled workbook and emits fy27/fy26/fy25 keys matching the
updated dashboard schema.

Replaces the VBA ExportDataJSON macro (which was hardcoded fy26/fy25 labels).
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path

import pythoncom
import win32com.client

from inland_workbook import DEFAULT_WORKBOOK


OUT_PATH = DEFAULT_WORKBOOK.parent / "data.json"


def _num(v, default=0):
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def read_col(ws, start_row: int, end_row: int, col: int, decimals: int | None = None) -> list:
    out = []
    for r in range(start_row, end_row + 1):
        v = ws.Cells(r, col).Value
        n = _num(v)
        out.append(round(n, decimals) if decimals is not None else int(n))
    return out


def read_col_pct(ws, start_row: int, end_row: int, col: int) -> list:
    """Reads a cell formatted as %. Excel stores 8.7% as 0.087."""
    out = []
    for r in range(start_row, end_row + 1):
        v = ws.Cells(r, col).Value
        fmt = ws.Cells(r, col).NumberFormat
        n = _num(v)
        if "%" in (fmt or "") or (0 < abs(n) < 1):
            n *= 100
        out.append(round(n, 1))
    return out


def read_col_pct_text(ws, start_row: int, end_row: int, col: int) -> list:
    """Percent may be stored as text like '(53%)' or '350%'."""
    out = []
    for r in range(start_row, end_row + 1):
        cell = ws.Cells(r, col)
        v = cell.Value
        n = _num(v, None)
        if n is not None:
            fmt = cell.NumberFormat or ""
            if "%" in fmt or (0 < abs(n) < 1):
                n *= 100
            out.append(int(round(n)))
        else:
            txt = str(cell.Text).replace("%", "").replace(",", "")
            m = re.match(r"^\((.+)\)$", txt)
            if m:
                txt = "-" + m.group(1)
            try:
                out.append(int(round(float(txt))))
            except ValueError:
                out.append(0)
    return out


def month_label(dt: datetime) -> str:
    return f"{dt.strftime('%b')}-{dt.strftime('%y')}"


def build_verification(ws_consol, fy_months: list[date]) -> dict:
    """Sum Electric $, Gas $, kWh, Elec MMBTU, Gas MMBTU by FY month from Consolidated Data."""
    last_row = ws_consol.Cells(ws_consol.Rows.Count, 1).End(-4162).Row  # xlUp = -4162
    # Read used range at once for speed
    ur = ws_consol.Range(ws_consol.Cells(2, 1), ws_consol.Cells(last_row, 16)).Value
    n_months = len(fy_months)
    elec = [0.0] * n_months
    gas = [0.0] * n_months
    kwh = [0.0] * n_months
    elec_mm = [0.0] * n_months
    gas_mm = [0.0] * n_months
    fy_set = {(d.year, d.month): i for i, d in enumerate(fy_months)}
    for row in ur:
        src = row[0]  # col A = Source
        if not src:
            continue
        my = row[13]  # col N (14) = Month-Year
        if not hasattr(my, "year"):
            continue
        key = (my.year, my.month)
        if key not in fy_set:
            continue
        i = fy_set[key]
        elec[i] += _num(row[9])   # col J (10) = Electric $
        gas[i] += _num(row[10])   # col K (11) = Gas $
        kwh[i] += _num(row[7])    # col H (8) = kWh
        elec_mm[i] += _num(row[14])  # col O (15) = Elec MMBTU
        gas_mm[i] += _num(row[15])   # col P (16) = Gas MMBTU
    return {
        "source": "Consolidated Data",
        "elecDollar": [int(round(x)) for x in elec],
        "gasDollar": [int(round(x)) for x in gas],
        "kwh": [int(round(x)) for x in kwh],
        "elecMmbtu": [int(round(x)) for x in elec_mm],
        "gasMmbtu": [int(round(x)) for x in gas_mm],
    }


def read_monthly_history(ws_consol) -> dict:
    """Sum Consolidated Data by calendar (year, month): elec $, gas $, kWh, MMBTUs."""
    last_row = ws_consol.Cells(ws_consol.Rows.Count, 1).End(-4162).Row
    ur = ws_consol.Range(ws_consol.Cells(2, 1), ws_consol.Cells(last_row, 16)).Value
    hist = {}
    for row in ur:
        if not row[0]:
            continue
        my = row[13]
        if not hasattr(my, "year"):
            continue
        k = (my.year, my.month)
        h = hist.setdefault(k, {"elec": 0.0, "gas": 0.0, "kwh": 0.0, "elecMM": 0.0, "gasMM": 0.0})
        h["elec"] += _num(row[9])
        h["gas"] += _num(row[10])
        h["kwh"] += _num(row[7])
        h["elecMM"] += _num(row[14])
        h["gasMM"] += _num(row[15])
    return hist


def build_forecast(hist: dict, hedge_pct: float) -> dict:
    """Forecast FY27 (Jul 2026 - Jun 2027) from clean history.

    Method (kept deliberately simple so it captions in one sentence):
    - Base month = most recent COMPLETE same calendar month (falls back one
      more year if the recent one is <50% of the year before, i.e. incomplete).
    - Electric = base month electric $ x YoY trend (Jul-Dec 2025 vs Jul-Dec 2024).
    - Gas      = base month gas $ x (1 + hedge %).
    - Usage (kWh / MMBTU) = base month usage, flat (no growth assumed).
    """
    fy27_cal = [(2026, 7), (2026, 8), (2026, 9), (2026, 10), (2026, 11), (2026, 12),
                (2027, 1), (2027, 2), (2027, 3), (2027, 4), (2027, 5), (2027, 6)]

    def get(y, m, f):
        return hist.get((y, m), {}).get(f, 0.0)

    # Electric YoY trend from two fully-complete half-years
    e_new = sum(get(2025, m, "elec") for m in range(7, 13))
    e_old = sum(get(2024, m, "elec") for m in range(7, 13))
    elec_factor = (e_new / e_old) if e_old else 1.0
    if not (0.8 <= elec_factor <= 1.3):   # incomplete base -> no trend
        elec_factor = 1.0
    gas_factor = 1 + hedge_pct / 100.0

    def base_month(y, m, f):
        """Most recent complete same calendar month for field f."""
        v1, v2 = get(y - 1, m, f), get(y - 2, m, f)
        if v2 and v1 < 0.5 * v2:   # recent year incomplete -> fall back
            return v2
        return v1 if v1 else v2

    out = {"elecFcast": [], "gasFcast": [], "totalFcast": [],
           "kwhFcast": [], "mmbtuFcast": [], "kintecFcast": [], "avistaFcast": []}
    for (y, m) in fy27_cal:
        e = base_month(y, m, "elec") * elec_factor
        g = base_month(y, m, "gas") * gas_factor
        kwh = base_month(y, m, "kwh")
        mm = (base_month(y, m, "elecMM") + base_month(y, m, "gasMM"))
        out["elecFcast"].append(int(round(e)))
        out["gasFcast"].append(int(round(g)))
        out["totalFcast"].append(int(round(e + g)))
        out["kwhFcast"].append(int(round(kwh)))
        out["mmbtuFcast"].append(int(round(mm)))
        # Kintec/Avista gas split from the base month's own history is not
        # tracked separately in hist; use the long-run split (~91% Kintec).
        out["kintecFcast"].append(int(round(g * 0.91)))
        out["avistaFcast"].append(int(round(g * 0.09)))
    out["meta"] = {
        "method": "Same month last complete year; electric x YoY trend, gas + hedge; usage held flat",
        "elecFactor": round(elec_factor, 3),
        "gasHedgePct": round(hedge_pct, 1),
        "baseWindow": "Jul 2024 - Jun 2026 billing history",
    }
    return out


def main() -> int:
    pythoncom.CoInitialize()
    xl = win32com.client.DispatchEx("Excel.Application")
    xl.Visible = False
    xl.DisplayAlerts = False
    xl.AskToUpdateLinks = False
    xl.EnableEvents = False
    xl.AutomationSecurity = 3
    wb = xl.Workbooks.Open(
        str(DEFAULT_WORKBOOK),
        UpdateLinks=0, ReadOnly=True,
        IgnoreReadOnlyRecommended=True, Notify=False,
    )
    try:
        current_fy = int(xl.Range("CurrentFY").Value)
        print(f"CurrentFY = {current_fy}")
        assert current_fy == 2027, f"Expected CurrentFY=2027, got {current_fy}"

        ws_exec = wb.Sheets("Executive Summary (Print)")
        ws_hdd = wb.Sheets("HDD Data")
        ws_kin = wb.Sheets("Kintec Data")
        ws_con = wb.Sheets("Consolidated Data")

        # FY27 current-year section: rows 3-14
        fy27 = {
            "totalActual": read_col(ws_exec, 3, 14, 2),
            "elecActual": read_col(ws_exec, 3, 14, 3),
            "gasActual": read_col(ws_exec, 3, 14, 4),
            "totalFcast": read_col(ws_exec, 3, 14, 5),
            "elecFcast": read_col(ws_exec, 3, 14, 6),
            "gasFcast": read_col(ws_exec, 3, 14, 7),
            "kintecFcast": read_col(ws_exec, 3, 14, 8),
            "avistaFcast": read_col(ws_exec, 3, 14, 9),
        }
        hedge = _num(ws_exec.Cells(3, 11).Value)
        if 0 < hedge < 1:
            hedge *= 100
        fy27["hedge"] = round(hedge, 1)

        # ---- Forecast override -------------------------------------------
        # The workbook's own FY27 forecast scales off an incomplete FY26 base
        # (Kintec 2026 gas missing, June partial) and badly understates.
        # Compute forecasts in Python from clean billing history instead.
        # IsComplete flags live on row 121: month row r -> flag col (r - 1).
        ws_con_hist = read_monthly_history(wb.Sheets("Consolidated Data"))
        fc = build_forecast(ws_con_hist, hedge)
        is_complete = [bool(ws_exec.Cells(121, r - 1).Value) for r in range(3, 15)]
        for i in range(12):
            fy27["totalFcast"][i] = fc["totalFcast"][i]
            fy27["elecFcast"][i] = fc["elecFcast"][i]
            fy27["gasFcast"][i] = fc["gasFcast"][i]
            fy27["kintecFcast"][i] = fc["kintecFcast"][i]
            fy27["avistaFcast"][i] = fc["avistaFcast"][i]
            if not is_complete[i]:
                # Blended convention: no actual bills yet -> show forecast
                fy27["totalActual"][i] = fc["totalFcast"][i]
                fy27["elecActual"][i] = fc["elecFcast"][i]
                fy27["gasActual"][i] = fc["gasFcast"][i]
        fy27["isActual"] = is_complete
        fy27["forecastMeta"] = fc["meta"]

        # FY26 gas section: rows 21-32 (header row 20 says "FY2026 Month")
        fy26gas = {
            "cost": read_col(ws_exec, 21, 32, 2),
            "mmbtu": read_col(ws_exec, 21, 32, 3),
            "perUnit": read_col(ws_exec, 21, 32, 4, decimals=2),
            "kintec": read_col(ws_exec, 21, 32, 8),
            "avista": read_col(ws_exec, 21, 32, 9),
        }

        # Energy Use (FY27 in MMBTU): rows 39-50, same forecast override
        energy_use = {
            "totalActual": read_col(ws_exec, 39, 50, 2),
            "elecActual": read_col(ws_exec, 39, 50, 3),
            "gasActual": read_col(ws_exec, 39, 50, 4),
            "totalFcast": read_col(ws_exec, 39, 50, 5),
            "kwhActual": read_col(ws_exec, 39, 50, 8),
            "kwhRate": read_col(ws_exec, 39, 50, 10, decimals=4),
        }
        for i in range(12):
            energy_use["totalFcast"][i] = fc["mmbtuFcast"][i]
            if not is_complete[i]:
                energy_use["totalActual"][i] = fc["mmbtuFcast"][i]
                energy_use["kwhActual"][i] = fc["kwhFcast"][i]
                kwh_i = fc["kwhFcast"][i]
                energy_use["kwhRate"][i] = round(fc["elecFcast"][i] / kwh_i, 4) if kwh_i else 0

        # Cumulative: rebuild from the overridden fy27 arrays
        cum_a, cum_f, cum_ma, cum_mf = [], [], [], []
        ra = rf = rma = rmf = 0
        for i in range(12):
            ra += fy27["totalActual"][i]; rf += fy27["totalFcast"][i]
            rma += energy_use["totalActual"][i]; rmf += energy_use["totalFcast"][i]
            cum_a.append(ra); cum_f.append(rf); cum_ma.append(rma); cum_mf.append(rmf)

        # YOY: rows 57-68, cols B-D = FY26, cols E-G = FY27
        yoy = {
            "fy26total": read_col(ws_exec, 57, 68, 2),
            "fy26elec": read_col(ws_exec, 57, 68, 3),
            "fy26gas": read_col(ws_exec, 57, 68, 4),
            "fy27total": read_col(ws_exec, 57, 68, 5),
            "fy27elec": read_col(ws_exec, 57, 68, 6),
            "fy27gas": read_col(ws_exec, 57, 68, 7),
        }

        # Cumul: rebuilt from overridden arrays (workbook rows 74-85 carry the
        # broken-base forecast, so recompute instead of reading them)
        cumul = {
            "actual": cum_a,
            "forecast": cum_f,
            "delta": [f - a for a, f in zip(cum_a, cum_f)],
            "deltaPct": [round((f - a) / f * 100, 1) if f else 0.0 for a, f in zip(cum_a, cum_f)],
            "mmbtuAct": cum_ma,
            "mmbtuFcast": cum_mf,
            "mmbtuDelta": [f - a for a, f in zip(cum_ma, cum_mf)],
            "mmbtuDeltaPct": [round((f - a) / f * 100, 1) if f else 0.0 for a, f in zip(cum_ma, cum_mf)],
        }

        # Variance: rows 127-138, prior=FY26 (col B/E/I), current=FY27 (col C/F/J)
        variance = {
            "fy26cost": read_col(ws_exec, 127, 138, 2),
            "fy27cost": read_col(ws_exec, 127, 138, 3),
            "costDelta": read_col(ws_exec, 127, 138, 4),
            "fy26mmbtu": read_col(ws_exec, 127, 138, 5),
            "fy27mmbtu": read_col(ws_exec, 127, 138, 6),
            "mmbtuDelta": read_col(ws_exec, 127, 138, 7),
            "mmbtuDeltaPct": read_col_pct(ws_exec, 127, 138, 8),
            "fy26hdd": read_col(ws_exec, 127, 138, 9),
            "fy27hdd": read_col(ws_exec, 127, 138, 10),
            "hddDeltaPct": read_col_pct_text(ws_exec, 127, 138, 11),
            "normalHdd": read_col(ws_exec, 127, 138, 12),
        }

        # HDD: col C = FY26 (was FY25), col D = FY27 (was FY26)
        hdd = {
            "fy26": read_col(ws_hdd, 6, 17, 3),
            "fy27": read_col(ws_hdd, 6, 17, 4),
            "normal": read_col(ws_hdd, 6, 17, 5),
        }

        # Kintec: variable rows
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

        # Verification: FY27 months = Jul 2026 through Jun 2027
        fy27_months = [
            date(2026, 7, 1), date(2026, 8, 1), date(2026, 9, 1),
            date(2026, 10, 1), date(2026, 11, 1), date(2026, 12, 1),
            date(2027, 1, 1), date(2027, 2, 1), date(2027, 3, 1),
            date(2027, 4, 1), date(2027, 5, 1), date(2027, 6, 1),
        ]
        verification = build_verification(ws_con, fy27_months)

        out = {
            "lastUpdated": datetime.now().strftime("%B %#d, %Y"),
            "fy27": fy27,
            "fy26gas": fy26gas,
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

        # Sanity check
        print(f"fy27.totalActual: {out['fy27']['totalActual']}")
        print(f"fy26gas.cost:     {out['fy26gas']['cost']}")
        print(f"verification.elecDollar: {out['verification']['elecDollar']}")
    finally:
        wb.Close(SaveChanges=False)
        xl.Quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
