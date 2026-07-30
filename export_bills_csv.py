"""Export every bill in the FY workbook's raw tables to one master CSV.

One row per fuel per bill: an Avista row carrying both electric and gas
becomes two rows. Output goes NEXT TO THE WORKBOOK on the R: drive.
NEVER copy this file into C:\\Users\\john.slagboom\\Desktop\\Git - that folder
publishes to a public website and this CSV carries account numbers.
"""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

import pythoncom
import win32com.client

from inland_workbook import DEFAULT_WORKBOOK

OUT_PATH = DEFAULT_WORKBOOK.parent / "bills-master.csv"

HEADER = ["provider", "utility_type", "account", "premise", "meter",
          "start_date", "end_date", "days", "usage", "usage_unit",
          "usage_charge", "demand", "demand_charge", "other_charges",
          "total_charge", "source"]


def _s(v):
    if v is None:
        return ""
    s = str(v).strip()
    return s[:-2] if s.endswith(".0") else s


def _num(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _date(v):
    """Normalize YYYYMMDD numbers/text and datetimes to MM/DD/YYYY."""
    if v is None:
        return ""
    if hasattr(v, "year"):
        return f"{v.month:02d}/{v.day:02d}/{v.year:04d}"
    s = _s(v)
    if len(s) == 8 and s.isdigit():
        return f"{s[4:6]}/{s[6:8]}/{s[0:4]}"
    return s


def _days(start, end):
    try:
        d0 = datetime.strptime(start, "%m/%d/%Y")
        d1 = datetime.strptime(end, "%m/%d/%Y")
        return (d1 - d0).days
    except (ValueError, TypeError):
        return ""


def main() -> int:
    pythoncom.CoInitialize()
    xl = win32com.client.DispatchEx("Excel.Application")
    xl.Visible = False
    xl.DisplayAlerts = False
    xl.AskToUpdateLinks = False
    xl.EnableEvents = False
    xl.AutomationSecurity = 3
    rows_out = []
    counts = {}
    wb = xl.Workbooks.Open(str(DEFAULT_WORKBOOK), UpdateLinks=0, ReadOnly=True,
                           IgnoreReadOnlyRecommended=True, Notify=False)
    try:
        # ---- AvistaData: 23 cols; one workbook row may hold elec AND gas ----
        av = wb.Sheets("Avista Data").ListObjects("AvistaData").DataBodyRange.Value
        counts["AvistaData"] = len(av)
        for r in av:
            acct, prem = _s(r[6]), _s(r[1])
            start, end = _date(r[8]), _date(r[9])
            days = _s(r[21]) or _days(start, end)
            emeter, kwh, elec_d = _s(r[10]), _num(r[11]), _num(r[12])
            demand_q, demand_d = _num(r[13]), _num(r[14])
            gmeter, thrm, gas_d = _s(r[15]), _num(r[16]), _num(r[17])
            lights_d = _num(r[20])
            total = _num(r[22])
            has_elec = bool(emeter) or kwh is not None
            has_gas = bool(gmeter) or thrm is not None
            if has_elec:
                rows_out.append(["Avista", "electric", acct, prem, emeter, start, end,
                                 days, kwh, "kWh", elec_d, demand_q, demand_d,
                                 lights_d, total if not has_gas else elec_d, "AvistaData"])
            if has_gas:
                rows_out.append(["Avista", "gas", acct, prem, gmeter, start, end,
                                 days, thrm, "therm", gas_d, None, None, None,
                                 total if not has_elec else gas_d, "AvistaData"])
            if not has_elec and not has_gas:
                rows_out.append(["Avista", "other", acct, prem, "", start, end,
                                 days, None, "", None, None, None, lights_d, total,
                                 "AvistaData"])

        # ---- InlandData: 23 cols, electric only ----
        inl = wb.Sheets("Inland Data").ListObjects("InlandData").DataBodyRange.Value
        counts["InlandData"] = len(inl)
        for r in inl:
            start, end = _date(r[5]), _date(r[6])
            other = sum(x for x in (_num(r[17]), _num(r[18])) if x is not None)
            rows_out.append(["Inland Power", "electric", _s(r[0]), _s(r[4]), _s(r[3]),
                             start, end, _s(r[7]) or _days(start, end),
                             _num(r[11]), "kWh", _num(r[13]), _num(r[14]),
                             _num(r[16]), other or None, _num(r[19]), "InlandData"])

        # ---- KintecData: 6 cols, gas supply (no account/meter granularity) ----
        kin = wb.Sheets("Kintec Data").ListObjects("KintecData").DataBodyRange.Value
        counts["KintecData"] = len(kin)
        for r in kin:
            start, end = _date(r[1]), _date(r[2])
            rows_out.append(["Kinect Energy", "gas", "supply contract", "WSU Pullman campus",
                             "", start, end, _days(start, end),
                             _num(r[5]), "Dth", None, None, None, _num(r[3]),
                             _num(r[4]), "KintecData"])
    finally:
        wb.Close(SaveChanges=False)
        xl.Quit()

    with open(OUT_PATH, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        for row in rows_out:
            w.writerow(["" if v is None else v for v in row])

    print(f"Wrote {OUT_PATH}")
    print(f"  table rows in:  {counts}")
    print(f"  bill rows out:  {len(rows_out)} "
          f"(Avista rows split per fuel, so out >= in is expected)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
