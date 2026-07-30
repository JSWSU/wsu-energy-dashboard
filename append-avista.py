"""Append filtered Avista V2 CSV rows to AvistaData table via Excel COM.

Modeled on inland_workbook.py:
 - Pre-check Power Query integrity
 - Backup
 - Open via COM (ReadOnly=False, hidden)
 - Bulk-append below table, Resize ListObject
 - Save (NO refresh — user runs Data > Refresh All manually in Excel)
 - Post-save integrity check; restore backup if customXml/connections/queryTables missing

Usage:
    py append-avista.py <csv_path> [--dry-run] [--visible]
"""
from __future__ import annotations

import argparse
import csv
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

import pythoncom
import win32com.client

from inland_workbook import (
    DEFAULT_WORKBOOK,
    assert_power_query_intact,
    check_workbook_integrity,
    make_backup,
)

SHEET = "Avista Data"
TABLE = "AvistaData"

# Index: (0-based col in V2 CSV, type) — types: 's'=string, 'd'=date YYYYMMDD, 'n'=numeric, 'i'=int
CSV_TO_WB = [
    ("MAIN_PERSON_FIRST_LAST_NAME", "s"),
    ("PREMISE_ADDRESS", "s"),
    ("PREMISE_IDENTIFIER", "s"),
    ("PREMISE_CITY", "s"),
    ("PREMISE_STATE", "s"),
    ("PREMISE_POSTAL", "s"),
    ("ACCOUNT_KEY", "n"),       # stored as number in WB (leading zeros lost)
    ("PREM_ID", "n"),
    ("START_DATE", "d"),
    ("END_DATE", "d"),
    ("ELECTRIC_METER", "s"),    # keep as string (meters have leading zeros)
    ("KWH", "n"),
    ("ELEC_$", "n"),
    ("DEMAND_QUANTITY", "n"),
    ("DEMAND_KW_$", "n"),
    ("GAS_METER", "s"),         # keep as string
    ("THRM", "n"),
    ("GAS_$", "n"),
    ("BILL_DATE", "d"),
    ("STREET_LIGHTS", "n"),
    ("STREET_LIGHT_$", "n"),
    ("DAYS_OF_SERVICE", "i"),
    ("TOTAL_BILL", "n"),
]


def _parse_num(s: str):
    s = (s or "").strip().replace(",", "")
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _parse_int(s: str):
    s = (s or "").strip().replace(",", "")
    if s == "":
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def _parse_date(s: str):
    """Return YYYYMMDD as int to match workbook's original numeric-date format.
    Avista PQ M code does Text.From([End Date]) and expects "20260413"; writing
    a datetime here produces "4/13/2026 7:00:00 AM" which the M code slices to
    garbage and drops the row."""
    s = (s or "").strip()
    if s == "":
        return None
    try:
        # Validate it's a real date, then return as int YYYYMMDD
        datetime.strptime(s, "%Y%m%d")
        return int(s)
    except ValueError:
        return None


def row_to_values(row: dict) -> list:
    out = []
    for col, typ in CSV_TO_WB:
        v = row.get(col, "")
        if typ == "s":
            out.append(str(v).strip() if v is not None else "")
        elif typ == "n":
            out.append(_parse_num(v))
        elif typ == "i":
            out.append(_parse_int(v))
        elif typ == "d":
            out.append(_parse_date(v))
        else:
            out.append(v)
    return out


def load_csv(path: Path) -> list[list]:
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return [row_to_values(r) for r in reader]


# Column indexes in the 23-col row layout (0-based)
_ACCT, _PREM, _START, _END, _EMETER, _KWH, _GMETER = 6, 7, 8, 9, 10, 11, 15


def _knorm(v):
    """Normalize a dedup-key element: strip whitespace, drop trailing .0,
    strip leading zeros. Values drift across Avista pulls and between the CSV
    and what Excel stored (float coercion, blank vs None, padded state)."""
    if v is None:
        return ""
    s = str(v).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s.lstrip("0") if s.replace("0", "") else s


def _row_key(row) -> tuple:
    return (_knorm(row[_ACCT]), _knorm(row[_PREM]), _knorm(row[_EMETER]),
            _knorm(row[_GMETER]), _knorm(row[_START]), _knorm(row[_END]))


def dedup_rows(rows: list[list]) -> tuple[list[list], int, int]:
    """In-CSV dedup: exact-bill repeats across pulls, then feeder
    label-duplicates (same acct+prem+dates+kWh under different meter labels
    - Avista posts feeder bills once per label). Returns (kept, n_exact, n_label)."""
    seen, kept, n_exact = set(), [], 0
    for r in rows:
        k = _row_key(r) + (_knorm(r[_KWH]),)
        if k in seen:
            n_exact += 1
            continue
        seen.add(k)
        kept.append(r)
    by_bill, out, n_label = set(), [], 0
    for r in kept:
        bk = (_knorm(r[_ACCT]), _knorm(r[_PREM]), _knorm(r[_START]),
              _knorm(r[_END]), _knorm(r[_KWH]))
        if bk in by_bill:
            n_label += 1
            continue
        by_bill.add(bk)
        out.append(r)
    return out, n_exact, n_label


def read_existing_keys(wb_path: Path) -> set:
    """Read AvistaData dedup keys from the workbook (read-only COM open)."""
    pythoncom.CoInitialize()
    xl = win32com.client.DispatchEx("Excel.Application")
    xl.Visible = False
    xl.DisplayAlerts = False
    xl.AskToUpdateLinks = False
    xl.EnableEvents = False
    try:
        xl.AutomationSecurity = 3
    except Exception:
        pass
    keys = set()
    try:
        wb = xl.Workbooks.Open(str(wb_path), UpdateLinks=0, ReadOnly=True,
                               IgnoreReadOnlyRecommended=True, Notify=False)
        try:
            table = wb.Sheets(SHEET).ListObjects(TABLE)
            vals = table.DataBodyRange.Value
            for row in vals:
                # workbook date cells may hold datetimes; normalize to YYYYMMDD
                r = list(row)
                for ci in (_START, _END):
                    v = r[ci]
                    if hasattr(v, "year"):
                        r[ci] = f"{v.year:04d}{v.month:02d}{v.day:02d}"
                keys.add(_row_key(r))
        finally:
            wb.Close(SaveChanges=False)
    finally:
        xl.Quit()
    return keys


def append_to_workbook(rows: list[list], dry_run: bool = False, visible: bool = False) -> dict:
    wb_path = DEFAULT_WORKBOOK
    result = {
        "workbook": str(wb_path),
        "backup": None,
        "appended": 0,
        "pre_integrity": None,
        "post_integrity": None,
        "warnings": [],
    }

    def log(m): print(f"  [com] {m}", flush=True)

    log("pre-check integrity")
    assert_power_query_intact(wb_path, label="PRE:")
    result["pre_integrity"] = check_workbook_integrity(wb_path)

    log("backup")
    backup = make_backup(wb_path)
    result["backup"] = str(backup)
    assert_power_query_intact(backup, label="BACKUP:")

    pythoncom.CoInitialize()
    xl = win32com.client.DispatchEx("Excel.Application")
    xl.Visible = visible
    xl.DisplayAlerts = False
    xl.ScreenUpdating = False
    xl.AskToUpdateLinks = False
    xl.EnableEvents = False
    try:
        xl.AutomationSecurity = 3
    except Exception:
        pass

    wb = None
    try:
        log(f"opening {wb_path}")
        wb = xl.Workbooks.Open(
            str(wb_path),
            UpdateLinks=0,
            ReadOnly=False,
            IgnoreReadOnlyRecommended=True,
            Notify=False,
        )
        log("opened")

        ws = wb.Sheets(SHEET)
        table = ws.ListObjects(TABLE)

        current_last_row = table.Range.Row + table.Range.Rows.Count - 1
        n_cols = table.Range.Columns.Count
        n_new = len(rows)

        if n_cols != len(CSV_TO_WB):
            raise RuntimeError(
                f"Column count mismatch: table has {n_cols}, script expects {len(CSV_TO_WB)}"
            )

        log(f"table last row={current_last_row}, cols={n_cols}, appending {n_new} rows")

        start_row = current_last_row + 1
        end_row = current_last_row + n_new

        block = ws.Range(
            ws.Cells(start_row, 1),
            ws.Cells(end_row, n_cols),
        )
        # Convert list of lists to tuple of tuples for COM
        block.Value = tuple(tuple(r) for r in rows)
        log(f"wrote rows {start_row}..{end_row}")

        # Resize table to include new rows
        new_range = ws.Range(
            ws.Cells(table.Range.Row, 1),
            ws.Cells(end_row, n_cols),
        )
        table.Resize(new_range)
        log(f"table resized to include new rows")

        result["appended"] = n_new

        if dry_run:
            log("dry-run: closing without save")
            wb.Close(SaveChanges=False)
            return result

        log("saving (no refresh)")
        wb.Save()
        log("saved")
        wb.Close(SaveChanges=False)
        wb = None

        # Post integrity
        try:
            assert_power_query_intact(wb_path, label="POST:")
            result["post_integrity"] = check_workbook_integrity(wb_path)
            log(f"post integrity OK: {result['post_integrity']}")
        except RuntimeError as e:
            log(f"POST-SAVE INTEGRITY FAILED: {e}")
            shutil.copy2(backup, wb_path)
            result["warnings"].append(f"POST-SAVE INTEGRITY FAILED; restored backup. {e}")
            raise

    finally:
        try:
            if wb is not None:
                wb.Close(SaveChanges=False)
        except Exception:
            pass
        try:
            xl.Quit()
        except Exception:
            pass
        del xl
        pythoncom.CoUninitialize()

    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--visible", action="store_true")
    args = ap.parse_args()

    csv_path = args.csv.resolve()
    if not csv_path.exists():
        print(f"ERROR: CSV not found: {csv_path}")
        return 1

    print(f"Loading CSV: {csv_path}")
    rows = load_csv(csv_path)
    print(f"Loaded {len(rows)} rows")
    if not rows:
        print("Nothing to append")
        return 0

    # Dedup: within the CSV (repeat pulls + feeder label copies), then
    # against rows already in the workbook. Root-caused 07/24/2026 after
    # blind appends double-posted Jan 2026 and every feeder bill.
    rows, n_exact, n_label = dedup_rows(rows)
    print(f"CSV dedup: dropped {n_exact} exact repeats, {n_label} feeder label copies")
    print("Reading existing workbook keys...")
    existing = read_existing_keys(DEFAULT_WORKBOOK)
    before = len(rows)
    rows = [r for r in rows if _row_key(r) not in existing]
    print(f"Workbook dedup: dropped {before - len(rows)} already-present rows; {len(rows)} net-new")
    if not rows:
        print("Nothing new to append - workbook already has every row in this CSV")
        return 0

    # Preview first and last
    print(f"First row: {rows[0][:8]}...")
    print(f"Last row:  {rows[-1][:8]}...")
    print()

    try:
        result = append_to_workbook(rows, dry_run=args.dry_run, visible=args.visible)
    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}")
        return 3

    print()
    print("=" * 70)
    print("RESULT")
    print("=" * 70)
    print(f"  Workbook:       {result['workbook']}")
    print(f"  Backup:         {result['backup']}")
    print(f"  Appended:       {result['appended']}")
    print(f"  Pre integrity:  {result['pre_integrity']}")
    print(f"  Post integrity: {result['post_integrity']}")
    if result["warnings"]:
        print("  Warnings:")
        for w in result["warnings"]:
            print(f"    {w}")
    if args.dry_run:
        print("\nDRY RUN COMPLETE — no changes saved")
    else:
        print("\nDONE")
        print("NEXT: Open workbook in Excel, click Data > Refresh All")
    return 0


if __name__ == "__main__":
    sys.exit(main())
