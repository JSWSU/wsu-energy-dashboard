"""Build data-forecast-demo.json and data-rates-demo.json.

Everything computed from data already extracted this week:
- data-trends.json (monthly total cost/MMBTU, FY2020-FY2027)
- data-fy2X.json archives (fuel splits, forecasts, HDD)
- KPUW HDD via the ACIS API (Jul 2018 - Jul 2026)
- Kinect invoice PDFs (hedge packages: volume + fixed $/Dth + swing supply)
"""
from __future__ import annotations

import json
import re
import urllib.request
from datetime import datetime
from pathlib import Path

import pdfplumber

GIT = Path(r"C:\Users\john.slagboom\Desktop\Git")
KIN = Path(r"R:\Energy Services Admin\Energy Files\Utility Invoices\Shell Kinect Natural Gas")
OUT_DIR = Path(r"R:\Energy Services Admin\Energy Files\Annual Elect & Steam Use\1A. Cost Projection Report")

MONTH_NAMES = ["July", "August", "September", "October", "November", "December",
               "January", "February", "March", "April", "May", "June"]


def load(name):
    return json.loads((GIT / name).read_text(encoding="utf-8"))


def fetch_hdd_by_fy():
    req = {"sid": "KPUW", "sdate": "2018-07-01", "edate": "2026-07-31",
           "elems": [{"name": "hdd", "interval": "mly", "duration": "mly", "reduce": "sum"}]}
    r = urllib.request.Request("https://data.rcc-acis.org/StnData",
                               data=json.dumps(req).encode(),
                               headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=30) as resp:
        rows = json.loads(resp.read())["data"]
    hdd = {d: (int(v) if str(v).lstrip("-").isdigit() else 0) for d, v in rows}

    def series(fy):
        out = []
        for i in range(12):
            y = (fy - 1) + (1 if i >= 6 else 0)
            m = [7, 8, 9, 10, 11, 12, 1, 2, 3, 4, 5, 6][i]
            out.append(hdd.get(f"{y}-{m:02d}", 0))
        return out
    return {fy: series(fy) for fy in range(2019, 2027)}


def parse_hedge_book():
    """Package lines from every FY-26 invoice: month -> hedged/swing volumes + prices."""
    months = []
    for i, mn in enumerate(MONTH_NAMES):
        yr = 2025 if i < 6 else 2026
        p = KIN / "FY-26" / f"{mn} {yr} Washington State University NG Invoice.pdf"
        with pdfplumber.open(p) as pdf:
            t = pdf.pages[0].extract_text()
        m_usage = re.search(r"Usage\s*=\s*([\d,]+)\s*Dths", t)
        usage = int(m_usage.group(1).replace(",", "")) if m_usage else 0
        pkgs, swing_vol = [], 0.0
        seen = set()
        for line in t.splitlines():
            pm = re.match(r"Package (\d+), .*? ([\d,]+\.?\d*) \$(\d+\.\d+) \$", line)
            if pm:
                vol = float(pm.group(2).replace(",", ""))
                rate = float(pm.group(3))
                if rate > 1.0 and pm.group(1) not in seen:   # skip $0.02 service fees
                    seen.add(pm.group(1))
                    pkgs.append({"id": pm.group(1), "dths": vol, "price": rate})
            sm = re.match(r"Swing Supply \(?\-?([\d,]+\.?\d*)\)? \$(\d+\.\d+)", line)
            if sm:
                swing_vol = float(sm.group(1).replace(",", ""))
                if "(" in line:
                    swing_vol = -swing_vol
        hedged = sum(p["dths"] for p in pkgs)
        months.append({
            "label": f"{mn[:3]} {yr}",
            "usageDths": usage,
            "hedgedDths": int(hedged),
            "swingDths": int(swing_vol),
            "hedgedPct": round(hedged / usage * 100, 1) if usage else 0,
            "wtdHedgePrice": round(sum(p["dths"] * p["price"] for p in pkgs) / hedged, 3) if hedged else 0,
            "packages": pkgs,
        })
    return months


def linreg(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    b = sxy / sxx
    a = my - b * mx
    ss_res = sum((y - (a + b * x)) ** 2 for x, y in zip(xs, ys))
    ss_tot = sum((y - my) ** 2 for y in ys)
    r2 = 1 - ss_res / ss_tot if ss_tot else 0
    return a, b, r2


def main() -> int:
    trends = load("data-trends.json")
    hdd_fy = fetch_hdd_by_fy()

    # ---------------- FORECAST DEMO ----------------
    # 1. Gas volume vs HDD regression (monthly points, FY2020-FY2025 actual years)
    pts_x, pts_y, pts_label = [], [], []
    for fy in range(2020, 2026):
        arch = load(f"data-fy{fy % 100}.json") if fy <= 2024 else load("data-fy25.json")
        gas_mm = arch["energyUse"]["gasActual"]
        hdd = hdd_fy.get(fy, arch["hdd"]["fy27"])
        for i in range(12):
            if gas_mm[i] > 0:
                pts_x.append(hdd[i])
                pts_y.append(gas_mm[i])
                pts_label.append(f"FY{fy} {['Jul','Aug','Sep','Oct','Nov','Dec','Jan','Feb','Mar','Apr','May','Jun'][i]}")
    a, b, r2 = linreg(pts_x, pts_y)

    # 2. FY2023 miss decomposition: price vs volume
    fy23 = load("data-fy23.json")
    act_cost = sum(fy23["fy27"]["totalActual"])
    fc_cost = sum(fy23["fy27"]["totalFcast"])
    act_mm = sum(fy23["energyUse"]["totalActual"])
    fc_mm = sum(fy23["energyUse"]["totalFcast"])
    act_rate, fc_rate = act_cost / act_mm, fc_cost / fc_mm
    vol_effect = (act_mm - fc_mm) * fc_rate           # cost miss due to volume
    price_effect = (act_rate - fc_rate) * act_mm      # cost miss due to price
    decomp = {
        "missTotal": int(act_cost - fc_cost),
        "volumeEffect": int(vol_effect),
        "priceEffect": int(price_effect),
        "actRate": round(act_rate, 2), "fcRate": round(fc_rate, 2),
        "actMM": int(act_mm), "fcMM": int(fc_mm),
    }

    # 3. Method backtest: official 5-yr-avg forecast vs actual, FY2020-FY2026
    backtest = []
    for fy in range(2020, 2027):
        src = (f"data-fy{fy % 100}.json" if fy <= 2025 else "data-fy26.json")
        d = load(src)
        aa, ff = sum(d["fy27"]["totalActual"]), sum(d["fy27"]["totalFcast"])
        backtest.append({"fy": f"FY{fy}", "actual": aa, "forecast": ff,
                         "missPct": round((aa - ff) / ff * 100, 1)})

    # 4. Hedge book from FY-26 invoices
    hedge = parse_hedge_book()

    # 5. Volume stability: annual MMBTU CV
    mm_years = [trends["annual"][f"FY{y}"]["mmbtu"] for y in range(2020, 2026)]
    mean_mm = sum(mm_years) / len(mm_years)
    cv_mm = (sum((x - mean_mm) ** 2 for x in mm_years) / len(mm_years)) ** 0.5 / mean_mm * 100
    cost_years = [trends["annual"][f"FY{y}"]["cost"] for y in range(2020, 2026)]
    mean_c = sum(cost_years) / len(cost_years)
    cv_c = (sum((x - mean_c) ** 2 for x in cost_years) / len(cost_years)) ** 0.5 / mean_c * 100

    forecast_demo = {
        "lastUpdated": datetime.now().strftime("%B %#d, %Y"),
        "regression": {
            "slope": round(b, 2), "intercept": round(a, 0), "r2": round(r2, 3),
            "points": [{"x": x, "y": int(y), "l": l} for x, y, l in zip(pts_x, pts_y, pts_label)],
        },
        "fy23Decomp": decomp,
        "backtest": backtest,
        "hedge": hedge,
        "stability": {"cvMMBTU": round(cv_mm, 1), "cvCost": round(cv_c, 1)},
        "normalHdd": load("data-fy25.json")["hdd"]["normal"],
    }
    for dest in [OUT_DIR / "data-forecast-demo.json", GIT / "data-forecast-demo.json"]:
        dest.write_text(json.dumps(forecast_demo, indent=2), encoding="utf-8")
    print(f"forecast demo: regression slope={b:.2f} MMBTU/HDD r2={r2:.3f}; "
          f"FY23 miss = {decomp['priceEffect']:+,} price / {decomp['volumeEffect']:+,} volume; "
          f"CV cost {cv_c:.1f}% vs CV volume {cv_mm:.1f}%")

    # ---------------- RATES DEMO ----------------
    # Cost-basis simulation: internal rate proxy = basis-period blended $/MMBTU
    # applied one year ahead (rates for FY N built from data through FY N-1).
    ann = {int(k[2:]): v for k, v in trends["annual"].items()}
    sims = []
    for fy in range(2021, 2028):
        realized = ann[fy]["rate"] if fy in ann else None
        row = {"fy": f"FY{fy}", "realized": realized,
               "isForecast": bool(ann.get(fy, {}).get("forecast"))}
        for nyrs in (1, 2, 3):
            yrs = [y for y in range(fy - nyrs, fy) if y in ann]
            tc = sum(ann[y]["cost"] for y in yrs)
            tm = sum(ann[y]["mmbtu"] for y in yrs)
            row[f"basis{nyrs}"] = round(tc / tm, 2) if tm else None
        sims.append(row)

    # Fuel-specific $/MMBTU series (FY2020-FY2026 from archive/report JSONs)
    fuel = []
    for fy in range(2020, 2027):
        src = (f"data-fy{fy % 100}.json" if fy <= 2025 else "data-fy26.json")
        d = load(src)
        ec, em = sum(d["fy27"]["elecActual"]), sum(d["energyUse"]["elecActual"])
        gc, gm = sum(d["fy27"]["gasActual"]), sum(d["energyUse"]["gasActual"])
        fuel.append({"fy": f"FY{fy}",
                     "elecRate": round(ec / em, 2) if em else 0,
                     "gasRate": round(gc / gm, 2) if gm else 0})

    # Error each basis would have produced vs realized (actual years only)
    basis_err = {n: [] for n in (1, 2, 3)}
    for row in sims:
        if row["realized"] and not row["isForecast"]:
            for n in (1, 2, 3):
                if row[f"basis{n}"]:
                    basis_err[n].append(abs(row[f"basis{n}"] - row["realized"]) / row["realized"] * 100)
    basis_summary = {n: round(sum(v) / len(v), 1) for n, v in basis_err.items() if v}

    rates_demo = {
        "lastUpdated": datetime.now().strftime("%B %#d, %Y"),
        "sims": sims,
        "basisSummary": basis_summary,
        "fuel": fuel,
        "hedgeFwd": {"note": "FY-26 hedge coverage from Kinect invoices",
                     "months": [{"label": h["label"], "hedgedPct": h["hedgedPct"],
                                 "wtdPrice": h["wtdHedgePrice"]} for h in hedge]},
    }
    for dest in [OUT_DIR / "data-rates-demo.json", GIT / "data-rates-demo.json"]:
        dest.write_text(json.dumps(rates_demo, indent=2), encoding="utf-8")
    print(f"rates demo: basis avg abs error {basis_summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
