# WSU Design Standards Compliance Review — Excel Report Template

**For Claude agents:** Use openpyxl to generate `report.xlsx` following this structure exactly. The Summary sheet MUST print to one 8.5x11" landscape page.

---

## Workbook Structure

5 sheets in this order: Summary, Findings, Checklist, Variances, Notes

---

## Sheet 1: "Summary" (EXECUTIVE SUMMARY — PRINTS TO ONE PAGE)

### Page Setup (REQUIRED)
```python
from openpyxl.worksheet.page import PageMargins
ws.page_setup.orientation = 'landscape'
ws.page_setup.paperSize = ws.PAPERSIZE_LETTER  # 8.5 x 11
ws.page_setup.fitToPage = True
ws.page_setup.fitToWidth = 1
ws.page_setup.fitToHeight = 1
ws.sheet_properties.pageSetUpPr.fitToPage = True
ws.page_margins = PageMargins(left=0.5, right=0.5, top=0.5, bottom=0.5, header=0.3, footer=0.3)
ws.oddFooter.center.text = "WSU Facilities Services — Design Standards Compliance Review"
ws.oddFooter.right.text = "Page &P"
```

### Column Widths
- A: 3 (spacer)
- B: 18 (labels)
- C: 14
- D: 14
- E: 14
- F: 14
- G: 14
- H: 14
- I: 14

### Layout (top to bottom)

**Row 1-2: Header**
- B1: "WASHINGTON STATE UNIVERSITY" (bold, 14pt, WSU crimson #981E32)
- B2: "Design Standards Compliance Review" (bold, 11pt)

**Row 3-4: Project Info (two columns)**
- B3: "Project:" (bold) | C3: _[project name]_
- D3: "Phase:" (bold) | E3: _[review phase]_
- B4: "Review Date:" (bold) | C4: _[date]_
- D4: "Construction Type:" (bold) | E4: _[type]_

**Row 5: Separator line** (thin bottom border on row 4)

**Row 6-8: Executive Summary**
- B6: "EXECUTIVE SUMMARY" (bold, 11pt, WSU crimson)
- B7-B8: Merged B7:I8 — 2-3 sentence summary paragraph:
  "This review evaluated [N] requirements across [N] divisions. [N]% of requirements are compliant. [N] critical findings require immediate attention. Key areas: [top 2-3 themes]."

**Row 9: Blank spacer**

**Row 10-14: Findings by Severity**
- B10: "FINDINGS BY SEVERITY" (bold, 11pt, WSU crimson)
- Table at B11:D14:

| Severity | Count | % of Findings |
|----------|-------|--------------|
| Critical | N | N% |
| Major | N | N% |
| Minor | N | N% |
| **Total Non-Compliant** | **N** | **100%** |

- "Count" = number of non-compliant findings at that severity level
- "% of Findings" = Count / Total Non-Compliant * 100
- "Total Non-Compliant" MUST equal Critical + Major + Minor (simple addition)
- Critical row: red fill (#FEE2E2)
- Major row: orange fill (#FEF3C7)
- Minor row: yellow fill (#FEF9C3)

**Row 15: Blank spacer**

**Row 16-24: Findings by Discipline**
- B16: "FINDINGS BY DISCIPLINE" (bold, 11pt, WSU crimson)
- Table at B17:I24 (or however many divisions):

| Division | Description | Total Req. | Compliant | Deviations | Omissions | Concerns | Compliance % |
|----------|------------|-----------|-----------|------------|-----------|----------|-------------|
| 26 | Electrical | N | N | N | N | N | N% |
| 23 | HVAC | N | N | N | N | N | N% |
| ... | | | | | | | |
| **TOTAL** | | **N** | **N** | **N** | **N** | **N** | **N%** |

- "Total Req." = total requirements evaluated for that division
- Per-row validation: Compliant + Deviations + Omissions + Concerns = Total Req.
- Compliance % = Compliant / Total Req. * 100
- TOTAL row sums each column
- Total row: bold, light blue fill (#EFF6FF)
- Header row: dark gray fill (#374151), white text

### CRITICAL MATH VALIDATION

These numbers MUST be consistent across tables:

1. Severity table "Total Non-Compliant" = Discipline table (TOTAL Deviations + TOTAL Omissions + TOTAL Concerns)
2. Executive Summary "[N]% of requirements are compliant" = Discipline table TOTAL Compliance %
3. Executive Summary "[N] critical findings" = Severity table Critical count
4. Discipline table TOTAL row = sum of each column above it
5. Per discipline row: Total Req. = Compliant + Deviations + Omissions + Concerns
6. Severity percentages sum to 100%
7. The Findings sheet row count (data rows only) = Severity table "Total Non-Compliant"
8. Priority Actions finding counts: Immediate = Critical count, CD Phase = Major count, 100% CD = Minor count

**Row 26-33: Top Critical Findings**
- B26: "TOP CRITICAL FINDINGS" (bold, 11pt, WSU crimson)
- B27:I33 — Numbered list of 3-6 most critical findings, one per row:
  "#  |  F-NNN  |  Division  |  Brief description  |  Required action"
- If no critical findings: "No critical findings identified."

**Row 35-39: Priority Action Items**
- B35: "PRIORITY ACTIONS" (bold, 11pt, WSU crimson)
- Table at B36:D39:

| Priority | Timeline | Finding Count |
|----------|----------|--------------|
| Immediate (Critical) | Before next submission | N |
| CD Phase (Major) | Resolve during CD | N |
| 100% CD (Minor) | Address by final CD | N |

### Styling Notes
- All text: Calibri font
- Section headers: 11pt bold, WSU crimson (#981E32)
- Body text: 9pt (to fit on one page)
- Table headers: 9pt bold, dark background, white text
- Table body: 9pt
- Gridlines: thin borders on all table cells
- Print area: set to cover all content rows/columns

---

## Sheet 2: "Findings"

### Setup
- Freeze row 1 (header row)
- Auto-filter on all columns
- Column widths: A=6, B=10, C=12, D=10, E=8, F=12, G=16, H=40, I=40

### Header Row (bold, dark gray fill, white text)
| A | B | C | D | E | F | G | H | I |
|---|---|---|---|---|---|---|---|---|
| F-# | Division | CSI Code | Severity | Status | PDF Sheet | Standard Ref | Issue | Required Action |

### Data Rows
- One row per finding, sorted by severity (Critical > Major > Minor) then division
- F-# format: F-001, F-002, F-003, ...
- Status values: [D] Deviation, [O] Omission, [X] Concern

### Conditional Formatting
- Severity = "Critical": entire row light red fill (#FEE2E2)
- Severity = "Major": entire row light orange fill (#FEF3C7)
- Severity = "Minor": entire row light yellow fill (#FEF9C3)

---

## Sheet 3: "Checklist"

### Setup
- Freeze row 1
- Auto-filter on all columns
- Column widths: A=5, B=10, C=12, D=50, E=8, F=8, G=12, H=30

### Header Row (bold, dark gray fill, white text)
| A | B | C | D | E | F | G | H |
|---|---|---|---|---|---|---|---|
| # | Division | CSI Code | Requirement | Status | Finding Ref | Drawing Sheet | Notes |

### Data Rows
- One row per requirement evaluated (ALL requirements, not just findings)
- Status values: [C], [D], [O], [X]
- Sequential numbering in column A
- Finding Ref (column F): blank for [C] items, contains F-### for [D]/[O]/[X] items — links to Findings sheet

### Conditional Formatting
- Status = [D]: light red fill
- Status = [O]: light orange fill
- Status = [X]: light yellow fill
- Status = [C]: light green fill (#DCFCE7)

---

## Sheet 4: "Variances"

### Setup
- Freeze row 1
- Auto-filter on all columns

### Header Row (bold, dark gray fill, white text)
| A | B | C | D | E | F | G |
|---|---|---|---|---|---|---|
| V-# | Finding Ref | Division | CSI Code | Description | Justification | Approval Status |

### Data Rows
- One row per variance request
- V-# format: V-01, V-02, ...
- Finding Ref: link to F-# from Findings sheet
- Approval Status: "Pending" (default for new reviews)
- If no variances needed: single row in B2: "No variance requests identified for this project."

---

## Sheet 5: "Notes"

### Layout (free-form text, merged cells for readability)

**Row 1:** "REVIEW NOTES" (bold, 14pt)

**Row 3:** "Methodology" (bold, 11pt)
**Row 4+:** Description of how the review was conducted (merged A4:H4+)

**After methodology:** "Drawing Inventory" (bold, 11pt)
- Table of drawing sheets reviewed: Sheet # | Description | Discipline

**After inventory:** "Standards Applicability" (bold, 11pt)
- Table of requirements determined N/A: Division | CSI Code | Requirement | Rationale for N/A

**After applicability:** "Review Limitations" (bold, 11pt)
- Bullet list of exclusions or limitations

---

## Python Package

```python
# pip install openpyxl
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.page import PageMargins
```

---

## Cross-Reference with Word Report

The F-### index is the master key for cross-document traceability. If you look up F-042 in ANY output file, you find the same finding.

- Finding numbers (F-001, F-002, ...) MUST match exactly between Word and Excel
- Severity counts in Word Section 4 must match Excel Summary sheet totals
- Every finding in Excel Findings sheet must appear in Word Section 6 (detailed findings)
- Variance items (V-##) must match between Excel Variances sheet and Word Section 7
- Checklist sheet "Finding Ref" column links non-compliant items to their F-###
- checklist.txt non-compliant items include F-### in Notes column (for traceability)
- The Word report provides narrative context; the Excel workbook provides sortable/filterable data
