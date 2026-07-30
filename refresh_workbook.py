"""Synchronously refresh the FY workbook's Power Query connections.

RefreshAll via COM is async and returns before finishing; this refreshes each
connection with BackgroundQuery=False, feeder queries first, ConsolidatedData
last, then saves. Run after any append, before exporting data JSONs.
"""
import time

import pythoncom
import win32com.client

from inland_workbook import DEFAULT_WORKBOOK, check_workbook_integrity

ORDER = ["Query - Avista", "Query - Inland", "Query - Kintec", "Query - ConsolidatedData"]


def main() -> int:
    pythoncom.CoInitialize()
    xl = win32com.client.DispatchEx("Excel.Application")
    xl.Visible = True   # PQ credential prompts hang headless; visible lets the user see them
    xl.DisplayAlerts = False
    xl.AskToUpdateLinks = False
    xl.EnableEvents = False
    xl.AutomationSecurity = 3
    wb = xl.Workbooks.Open(str(DEFAULT_WORKBOOK), UpdateLinks=0, ReadOnly=False,
                           IgnoreReadOnlyRecommended=True, Notify=False)
    try:
        for name in ORDER:
            conn = wb.Connections(name)
            try:
                conn.OLEDBConnection.BackgroundQuery = False
            except Exception:
                pass
            t0 = time.time()
            conn.Refresh()
            print(f"  {name}: {time.time() - t0:.1f}s")
        wb.Save()
        n = wb.Sheets("Consolidated Data").ListObjects("ConsolidatedData").ListRows.Count
        print(f"ConsolidatedData: {n} rows after refresh")
    finally:
        wb.Close(SaveChanges=False)
        xl.Quit()
    print("Integrity:", check_workbook_integrity(DEFAULT_WORKBOOK))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
