"""Build data-fy20.json .. data-fy24.json for the archive dashboard pages.

Actuals (monthly cost + MMBTU, total/gas/electric):
- FY2015-FY2023: FY2024 folder 'Energy Data for Projection summary.xlsx',
  sheets all/gas/electricity, FY column pairs (FY2015 at cols 2/3 ... FY2023 at 18/19).
- FY2024: FY2025 folder 'Energy Data for Projection summary1.xlsx', cols 24/25
  (actual columns; the 20/21 pair on that file is the FY2025-era copy of FY2024
  actuals on sheet 'all' — we read 20/21 for 'all' and 24/25 fuel sheets are
  checked at runtime; whichever pair header says 'Actual' wins).

Forecast: the era's official method was the 5-year average of the prior five
fiscal years' monthly actuals ("FYxxxx Energy cost with average projection").
Reconstructed here and VALIDATED against the stored projections where they
survive (FY2020/21/22/24 - matches to rounding).

HDD: ACIS API (KPUW) monthly, Jul 2018 onward.
"""
from __future__ import annotations

import json
import urllib.request
from datetime import datetime
from pathlib import Path

import pythoncom
import win32com.client

from inland_workbook import DEFAULT_WORKBOOK

BASE = Path(r"R:\Energy Services Admin\Energy Files\Annual Elect & Steam Use")
GIT = Path(r"C:\Users\john.slagboom\Desktop\Git")

# FY -> (cost_col, mmbtu_col) in the FY2024-folder summary (sheets all/gas/electricity)
FY_COLS = {2015: (2, 3), 2016: (4, 5), 2017: (6, 7), 2018: (8, 9), 2019: (10, 11),
           2020: (12, 13), 2021: (14, 15), 2022: (16, 17), 2023: (18, 19)}

SHEETS = {"all": "tot", "gas": "gas", "electricity": "elec"}


def read_year_series(xl):
    """-> {fy_int: {'tot': {'cost': [...], 'mmbtu': [...]}, 'gas': ..., 'elec': ...}}"""
    data = {fy: {} for fy in list(FY_COLS) + [2024]}
    wb = xl.Workbooks.Open(str(BASE / "FY2024" / "Energy Data for Projection summary.xlsx"),
                           UpdateLinks=0, ReadOnly=True, IgnoreReadOnlyRecommended=True, Notify=False)
    try:
        for sheet, key in SHEETS.items():
            ws = wb.Sheets(sheet)
            for fy, (cc, mc) in FY_COLS.items():
                data[fy][key] = {
                    "cost": [float(ws.Cells(r, cc).Value or 0) for r in range(2, 14)],
                    "mmbtu": [float(ws.Cells(r, mc).Value or 0) for r in range(2, 14)],
                }
    finally:
        wb.Close(SaveChanges=False)

    # FY2024 actuals from the FY2025-folder edition
    wb = xl.Workbooks.Open(str(BASE / "FY2025" / "Energy Data for Projection summary1.xlsx"),
                           UpdateLinks=0, ReadOnly=True, IgnoreReadOnlyRecommended=True, Notify=False)
    try:
        for sheet, key in SHEETS.items():
            ws = wb.Sheets(sheet)
            # find the FY2024 actual column pair by header
            cc = mc = None
            for c in range(12, 40):
                h = str(ws.Cells(1, c).Value or "")
                if "FY2024" in h and ("Total" in h or "Actual" in h) and "cost" in h.lower() and "projection" not in h.lower():
                    cc = c
                if "FY2024" in h and ("MMBTU" in h or "MMBtu" in h) and "projection" not in h.lower():
                    mc = c
            assert cc and mc, f"FY2024 actual cols not found on {sheet} (got {cc},{mc})"
            data[2024][key] = {
                "cost": [float(ws.Cells(r, cc).Value or 0) for r in range(2, 14)],
                "mmbtu": [float(ws.Cells(r, mc).Value or 0) for r in range(2, 14)],
            }
    finally:
        wb.Close(SaveChanges=False)
    return data


def five_yr_avg(data, fy, key, field):
    """Monthly mean of the prior five fiscal years."""
    yrs = [fy - i for i in range(1, 6)]
    out = []
    for m in range(12):
        vals = [data[y][key][field][m] for y in yrs if y in data and key in data[y]]
        out.append(sum(vals) / len(vals) if vals else 0.0)
    return out


def fetch_hdd():
    req = {"sid": "KPUW", "sdate": "2018-07-01", "edate": "2024-06-30",
           "elems": [{"name": "hdd", "interval": "mly", "duration": "mly", "reduce": "sum"}]}
    r = urllib.request.Request("https://data.rcc-acis.org/StnData",
                               data=json.dumps(req).encode(),
                               headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=30) as resp:
        rows = json.loads(resp.read())["data"]
    hdd = {d: (int(v) if str(v).lstrip("-").isdigit() else 0) for d, v in rows}

    def fy_series(fy):
        out = []
        for i in range(12):
            y = (fy - 1) + (1 if i >= 6 else 0)
            m = [7, 8, 9, 10, 11, 12, 1, 2, 3, 4, 5, 6][i]
            out.append(hdd.get(f"{y}-{m:02d}", 0))
        return out
    return {fy: fy_series(fy) for fy in range(2019, 2025)}


NORMAL_HDD = None  # filled from existing data-fy25.json (30-yr normals are static)


def build_year(data, hdd_by_fy, fy):
    cur, pri = data[fy], data[fy - 1]
    ri = lambda xs: [int(round(x)) for x in xs]

    tot_f = five_yr_avg(data, fy, "tot", "cost")
    elec_f = five_yr_avg(data, fy, "elec", "cost")
    gas_f = five_yr_avg(data, fy, "gas", "cost")
    mm_f = five_yr_avg(data, fy, "tot", "mmbtu")

    fy_cur = {
        "totalActual": ri(cur["tot"]["cost"]),
        "elecActual": ri(cur["elec"]["cost"]),
        "gasActual": ri(cur["gas"]["cost"]),
        "totalFcast": ri(tot_f),
        "elecFcast": ri(elec_f),
        "gasFcast": ri(gas_f),
        # Kintec/Avista gas split was not archived at monthly level: show all
        # gas under the Kintec slice (Avista transport is a small residual).
        "kintecFcast": ri(cur["gas"]["cost"]),
        "avistaFcast": [0] * 12,
        "hedge": 0.0,
        "isActual": [True] * 12,
        "forecastMeta": {
            "method": f"FY{fy} actuals vs the official 5-year-average projection "
                      f"(monthly mean of FY{fy-5}-FY{fy-1})",
            "elecFactor": 1.0, "gasHedgePct": 0.0,
            "baseWindow": f"FY{fy-5}-FY{fy-1} archived actuals",
            "dataNote": ("Figures from the archived Energy Data for Projection "
                         "summaries. The Kintec/Avista gas split was not archived "
                         "at monthly level; the gas pie slice shows total gas."),
        },
    }

    kwh_a = [m / 0.003412 for m in cur["elec"]["mmbtu"]]
    energy_use = {
        "totalActual": ri(cur["tot"]["mmbtu"]),
        "elecActual": ri(cur["elec"]["mmbtu"]),
        "gasActual": ri(cur["gas"]["mmbtu"]),
        "totalFcast": ri(mm_f),
        "kwhActual": ri(kwh_a),
        "kwhRate": [round(c / k, 4) if k else 0.0
                    for c, k in zip(cur["elec"]["cost"], kwh_a)],
    }

    gp_c, gp_m = pri["gas"]["cost"], pri["gas"]["mmbtu"]
    fy_prior_gas = {
        "cost": ri(gp_c), "mmbtu": ri(gp_m),
        "perUnit": [round(c / m, 2) if m else 0.0 for c, m in zip(gp_c, gp_m)],
        "kintec": ri(gp_c), "avista": [0] * 12,
    }

    yoy = {
        "fy26total": ri(pri["tot"]["mmbtu"]), "fy26elec": ri(pri["elec"]["mmbtu"]),
        "fy26gas": ri(pri["gas"]["mmbtu"]),
        "fy27total": energy_use["totalActual"], "fy27elec": energy_use["elecActual"],
        "fy27gas": energy_use["gasActual"],
    }

    cum = lambda xs: [sum(xs[:i + 1]) for i in range(12)]
    ca, cf = cum(fy_cur["totalActual"]), cum(fy_cur["totalFcast"])
    cma, cmf = cum(energy_use["totalActual"]), cum(energy_use["totalFcast"])
    cumul = {
        "actual": ca, "forecast": cf,
        "delta": [f - a for a, f in zip(ca, cf)],
        "deltaPct": [round((f - a) / f * 100, 1) if f else 0.0 for a, f in zip(ca, cf)],
        "mmbtuAct": cma, "mmbtuFcast": cmf,
        "mmbtuDelta": [f - a for a, f in zip(cma, cmf)],
        "mmbtuDeltaPct": [round((f - a) / f * 100, 1) if f else 0.0 for a, f in zip(cma, cmf)],
    }

    hdd_cur = hdd_by_fy.get(fy, [0] * 12)
    hdd_pri = hdd_by_fy.get(fy - 1, [0] * 12)
    hdd = {"fy26": hdd_pri, "fy27": hdd_cur, "normal": NORMAL_HDD}

    pc, cc_ = ri(pri["tot"]["cost"]), fy_cur["totalActual"]
    pm, cm = yoy["fy26total"], energy_use["totalActual"]
    variance = {
        "fy26cost": pc, "fy27cost": cc_,
        "costDelta": [c - p for p, c in zip(pc, cc_)],
        "fy26mmbtu": pm, "fy27mmbtu": cm,
        "mmbtuDelta": [c - p for p, c in zip(pm, cm)],
        "mmbtuDeltaPct": [round((c - p) / p * 100, 1) if p else 0.0 for p, c in zip(pm, cm)],
        "fy26hdd": hdd_pri, "fy27hdd": hdd_cur,
        "hddDeltaPct": [int(round((c - p) / p * 100)) if p else 0 for p, c in zip(hdd_pri, hdd_cur)],
        "normalHdd": NORMAL_HDD,
    }

    return {
        "lastUpdated": datetime.now().strftime("%B %#d, %Y"),
        "fy27": fy_cur, "fy26gas": fy_prior_gas, "energyUse": energy_use,
        "yoy": yoy, "cumul": cumul, "variance": variance, "hdd": hdd,
        "kintec": {"months": [], "dths": [], "cost": []},
    }


def main() -> int:
    global NORMAL_HDD
    NORMAL_HDD = json.loads((GIT / "data-fy25.json").read_text(encoding="utf-8"))["hdd"]["normal"]

    pythoncom.CoInitialize()
    xl = win32com.client.DispatchEx("Excel.Application")
    xl.Visible = False
    xl.DisplayAlerts = False
    xl.AskToUpdateLinks = False
    xl.EnableEvents = False
    xl.AutomationSecurity = 3
    try:
        data = read_year_series(xl)
    finally:
        xl.Quit()

    hdd_by_fy = fetch_hdd()

    # Validate the 5-yr-average reconstruction against surviving stored projections
    checks = {2020: 17531827.23, 2021: 17638473.79, 2022: 17736785.32, 2024: 20337029.77}
    for fy, stored in checks.items():
        recon = sum(five_yr_avg(data, fy, "tot", "cost"))
        pct = abs(recon - stored) / stored * 100
        status = "OK" if pct < 1.0 else "MISMATCH"
        print(f"  validate FY{fy}: reconstructed ${recon:,.0f} vs stored ${stored:,.0f} ({pct:.2f}%) {status}")

    for fy in range(2020, 2025):
        out = build_year(data, hdd_by_fy, fy)
        name = f"data-fy{fy % 100}.json"
        for dest in [DEFAULT_WORKBOOK.parent / name, GIT / name]:
            dest.write_text(json.dumps(out, indent=2), encoding="utf-8")
        a, f = sum(out["fy27"]["totalActual"]), sum(out["fy27"]["totalFcast"])
        print(f"  FY{fy}: actual ${a:,.0f} vs 5yr-avg forecast ${f:,.0f} "
              f"({(f - a) / f * 100:+.1f}% margin) -> {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
