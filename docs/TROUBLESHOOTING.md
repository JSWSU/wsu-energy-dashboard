# Troubleshooting Guide

Quick-reference for common problems with the WSU Energy Dashboard. Organized as **Symptom > Cause > Solution**.

---

## Dashboard Shows "Could not load data"

**Cause:** `data.json` is missing from the GitHub repository, or the file is malformed.

**Solution:**
1. Go to https://github.com/JSWSU/wsu-energy-dashboard and verify `data.json` exists
2. If missing: re-run the export macro in Excel and upload `data.json` to GitHub
3. If present: open `data.json` in a text editor -- check for JSON syntax errors (missing commas, brackets, etc.)
4. Validate the JSON at https://jsonlint.com/

---

## VBA Macro Fails with "Subscript out of range"

**Cause:** One of the required Excel sheets is missing or its name does not match exactly.

**Solution:** Verify all 4 required sheets exist with **exact** names (case-sensitive, no trailing spaces):
- `Executive Summary (Print)`
- `HDD Data`
- `Kintec Data`
- `Consolidated Data`

Right-click each sheet tab to confirm the name. Even a trailing space will cause this error.

---

## VBA Macro Fails with "Permission denied"

**Cause:** The output file (`data.json`) is open in another program, or the workbook folder is read-only.

**Solution:**
1. Close any other editors (Notepad, VS Code, etc.) that have `data.json` open
2. Verify you have write permissions to the workbook's folder
3. If on a network share, check that the share isn't read-only

---

## Verification Shows Large Discrepancies (>5%)

**Cause:** Billing adjustments, credits, data entry timing, or errors between the Executive Summary and Consolidated Data sheets.

**Solution:**
1. Note which specific months are flagged in the message box
2. Compare the flagged month's values in "Executive Summary (Print)" against line items in "Consolidated Data"
3. Common reasons for discrepancies:
   - A bill was entered in Consolidated Data but not yet reflected in Executive Summary (or vice versa)
   - An adjustment or credit was applied to one sheet but not the other
   - A bill was assigned to the wrong month
4. If the discrepancy is <10% and you understand the reason, it's safe to proceed
5. If >10% or unexplained, resolve the data issue before publishing

---

## "Last Updated" Date Is Stale

**Cause:** Either the export macro was not run recently, or the updated `data.json` was not pushed to GitHub.

**Solution:**
1. Re-run the export macro (it stamps the current date automatically)
2. Upload the new `data.json` to GitHub
3. Wait 1-2 minutes for GitHub Pages to deploy
4. Hard-refresh the browser (Ctrl+Shift+R)

---

## Charts Look Wrong in Dark Mode

**Cause:** Known limitation -- Chart.js sets text and grid colors once at page load. Toggling dark mode after the page loads doesn't update chart colors.

**Solution:** Refresh the page after toggling dark mode. The charts will render with the correct colors on the fresh load.

---

## Password Not Working

**Cause:** The password is case-sensitive.

**Solution:** Enter exactly: `Energy@WSU`
- Capital `E` in Energy
- Capital `W`, `S`, `U` in WSU
- `@` symbol between Energy and WSU

**To change the password:**
1. Open `index.html`
2. Find the line: `if (input.value === 'Energy@WSU')`
3. Replace `Energy@WSU` with the new password
4. Commit and push to GitHub
5. Communicate the new password to all authorized users

---

## GitHub Pages Not Updating After Push

**Cause:** GitHub Pages can take 1-5 minutes to rebuild. Occasionally the CDN caches stale content.

**Solution:**
1. Wait 5 minutes
2. Hard-refresh the browser: **Ctrl+Shift+R** (Windows) or **Cmd+Shift+R** (Mac)
3. Check deployment status: go to the GitHub repo > **Settings** > **Pages** -- look for "Your site is live"
4. If using a custom domain (not applicable currently), check DNS propagation

---

## Macros Are Disabled / Trust Center Error

**Cause:** Excel's default security settings block VBA macros.

**Solution:**
1. Go to **File > Options > Trust Center > Trust Center Settings > Macro Settings**
2. Select **"Disable VBA macros with notification"** (recommended) or **"Enable all macros"**
3. Click OK, close and reopen the workbook
4. If using "with notification": click **"Enable Content"** in the yellow security banner when prompted

---

## Export Button Is Missing from Excel

**Cause:** The button was never created, or the sheet was renamed/recreated.

**Solution:**
1. Press **Alt+F8** to open the Macros dialog
2. Select **`ExportDataJSON.AddExportButton`**
3. Click **Run**
4. The crimson "Export data.json" button will appear near cell M2 on the "Executive Summary (Print)" sheet

---

## Chart.js CDN Is Down (Charts Not Loading)

**Cause:** `cdn.jsdelivr.net` is unavailable or blocked by a firewall.

**Solution:**
1. Download `chart.umd.min.js` v4.4.7 from https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js
2. Save it in the repository root as `chart.umd.min.js`
3. Edit `index.html` line 7 -- change:
   ```html
   <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
   ```
   to:
   ```html
   <script src="chart.umd.min.js"></script>
   ```
4. Commit and push both files to GitHub

---

## VBA Macro Module Is Missing from Excel

**Cause:** The VBA module was not imported into the workbook, or was lost when the workbook was saved as `.xlsx` (which strips macros).

**Solution:**
1. Ensure the workbook is saved as `.xlsm` (macro-enabled format)
2. Press **Alt+F11** to open the VBA Editor
3. In the Project Explorer pane, right-click the workbook name
4. Select **Import File...**
5. Browse to `ExportDataJSON.bas` and import it
6. Close the VBA Editor
7. Save the workbook as `.xlsm`

---

## Dashboard Shows Stale Data After Refresh

**Cause:** Browser is serving a cached version of `data.json`.

**Solution:**
1. Hard-refresh: **Ctrl+Shift+R** (clears cache for the current page)
2. If that doesn't work, open browser DevTools (F12) > Network tab > check "Disable cache" > refresh
3. As a last resort, clear the browser cache entirely
