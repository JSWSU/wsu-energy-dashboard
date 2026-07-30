"""Parse Kinect (Kintec) NG invoice PDFs: Invoicing Month, Total Amount Due, Usage Dths."""
import re
import sys
from pathlib import Path

import pdfplumber

BASE = Path(r"R:\Energy Services Admin\Energy Files\Utility Invoices\Shell Kinect Natural Gas")

MONTHS = {m: i + 1 for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June",
     "July", "August", "September", "October", "November", "December"])}


def parse_invoice(pdf_path: Path) -> dict:
    with pdfplumber.open(pdf_path) as pdf:
        text = pdf.pages[0].extract_text()
    m_month = re.search(r"Invoicing Month\s+(\w+)\s+(\d{4})", text)
    m_total = re.search(r"Total Amount Due:\s*\$([\d,]+\.\d{2})", text)
    m_usage = re.search(r"Usage\s*=\s*([\d,]+)\s*Dths", text)
    rec = {"file": pdf_path.name}
    if m_month:
        rec["month_name"] = m_month.group(1)
        rec["year"] = int(m_month.group(2))
        rec["month"] = MONTHS.get(m_month.group(1))
    if m_total:
        rec["total"] = float(m_total.group(1).replace(",", ""))
    if m_usage:
        rec["usage_dths"] = int(m_usage.group(1).replace(",", ""))
    return rec


def append_to_workbook(recs: list[dict], dry_run: bool = False) -> int:
    """Append parsed invoices to KintecData for months not already present.

    Row pattern (matches existing table): Invoicing Month = 1st of month,
    Start Date = month start minus 1 day, End Date = month end,
    Avista Charges = 0 (transport invoice arrives separately; backfill later).
    """
    from datetime import date, timedelta

    import pythoncom
    import win32com.client

    from inland_workbook import DEFAULT_WORKBOOK, check_workbook_integrity, make_backup

    good = [r for r in recs if "total" in r and "usage_dths" in r and "month" in r]
    if not good:
        print("No parseable invoices to append")
        return 0

    if not dry_run:
        bak = make_backup(DEFAULT_WORKBOOK)
        print(f"Backup: {bak}")

    pythoncom.CoInitialize()
    xl = win32com.client.DispatchEx("Excel.Application")
    xl.Visible = False
    xl.DisplayAlerts = False
    xl.AskToUpdateLinks = False
    xl.EnableEvents = False
    xl.AutomationSecurity = 3
    appended = 0
    try:
        wb = xl.Workbooks.Open(str(DEFAULT_WORKBOOK), UpdateLinks=0, ReadOnly=dry_run,
                               IgnoreReadOnlyRecommended=True, Notify=False)
        try:
            ws = wb.Sheets("Kintec Data")
            lo = ws.ListObjects("KintecData")
            existing = set()
            for i in range(1, lo.ListRows.Count + 1):
                v = lo.ListRows(i).Range.Cells(1, 1).Value
                if hasattr(v, "year"):
                    existing.add((v.year, v.month))
            new = [r for r in good if (r["year"], r["month"]) not in existing]
            print(f"{len(good)} parsed, {len(good) - len(new)} already in workbook, {len(new)} new")
            if not new or dry_run:
                return len(new)
            start_row = lo.ListRows.Count + 2   # sheet row (header = row 1)
            rows = []
            for r in sorted(new, key=lambda x: (x["year"], x["month"])):
                y, m = r["year"], r["month"]
                inv = date(y, m, 1)
                start = inv - timedelta(days=1)
                end = date(y + (m == 12), (m % 12) + 1, 1) - timedelta(days=1)
                rows.append([inv.strftime("%m/%d/%Y"), start.strftime("%m/%d/%Y"),
                             end.strftime("%m/%d/%Y"), 0.0, r["total"], float(r["usage_dths"])])
                print(f"  appending {y}-{m:02d}: ${r['total']:,.2f} / {r['usage_dths']:,} Dths")
            rng = ws.Range(ws.Cells(start_row, 1), ws.Cells(start_row + len(rows) - 1, 6))
            rng.Value = rows
            lo.Resize(ws.Range(ws.Cells(1, 1), ws.Cells(start_row + len(rows) - 1, 6)))
            for c in (1, 2, 3):
                ws.Range(ws.Cells(start_row, c),
                         ws.Cells(start_row + len(rows) - 1, c)).NumberFormat = "m/d/yyyy"
            wb.Save()
            appended = len(rows)
        finally:
            wb.Close(SaveChanges=False)
    finally:
        xl.Quit()
    if not dry_run:
        print("Integrity:", check_workbook_integrity(DEFAULT_WORKBOOK))
    return appended


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    do_append = "--append" in sys.argv
    dry = "--dry-run" in sys.argv
    fys = args or ["FY-25", "FY-26"]
    all_recs = []
    for fy in fys:
        folder = BASE / fy
        if not folder.exists():
            print(f"NOTE: folder {folder} does not exist, skipping")
            continue
        for p in sorted(folder.glob("*.pdf")):
            rec = parse_invoice(p)
            rec["fy_folder"] = fy
            all_recs.append(rec)
    all_recs.sort(key=lambda r: (r.get("year", 0), r.get("month", 0)))
    for r in all_recs:
        ok = "OK" if ("total" in r and "usage_dths" in r and "month" in r) else "PARSE FAIL"
        print(f"{r['fy_folder']} | {r.get('year','????')}-{r.get('month',0):02d} "
              f"{r.get('month_name','?'):<10} | total=${r.get('total',0):>12,.2f} "
              f"| usage={r.get('usage_dths',0):>8,} Dths | {ok}  ({r['file']})")
    if do_append:
        append_to_workbook(all_recs, dry_run=dry)
    return all_recs


if __name__ == "__main__":
    main()
