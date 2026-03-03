# Energy Group Folder Cleanup — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a new standardized folder tree inside `\\fais007\ENERGY GROUP` and write a team guide, leaving all existing files untouched as archive.

**Architecture:** Create a top-level folder `_CURRENT` inside the existing share (underscore prefix sorts it to the very top in Explorer, above the numbered function folders and everything else). Build the 8-function folder skeleton inside it with README and templates. Then identify and copy actively-used files from the archive into the new structure.

**Tech Stack:** Bash (mkdir, cp), plain text files. No code, no dependencies.

**Root path:** `//fais007/ENERGY GROUP/_CURRENT`

---

### Task 1: Create the Folder Skeleton

**Step 1: Create the top-level structure**

Run from any directory:

```bash
ROOT="//fais007/ENERGY GROUP/_CURRENT"

# Top level
mkdir -p "$ROOT"

# 8 function folders
mkdir -p "$ROOT/01 - Metering & Data"
mkdir -p "$ROOT/02 - Billing & Rates"
mkdir -p "$ROOT/03 - SCADA & Controls"
mkdir -p "$ROOT/04 - Conservation & Sustainability"
mkdir -p "$ROOT/05 - Capital Projects"
mkdir -p "$ROOT/06 - Reporting & Compliance"
mkdir -p "$ROOT/07 - Steam Plant Operations"
mkdir -p "$ROOT/08 - Admin & Reference"
mkdir -p "$ROOT/_Templates"
```

**Step 2: Create second-level subfolders**

```bash
# 01 - Metering & Data
mkdir -p "$ROOT/01 - Metering & Data/Meter Reads"
mkdir -p "$ROOT/01 - Metering & Data/Meter Inventory"
mkdir -p "$ROOT/01 - Metering & Data/SkySpark"
mkdir -p "$ROOT/01 - Metering & Data/Data Exports"
mkdir -p "$ROOT/01 - Metering & Data/Network Meters"

# 02 - Billing & Rates
mkdir -p "$ROOT/02 - Billing & Rates/Recharge Rates"
mkdir -p "$ROOT/02 - Billing & Rates/Avista Invoices"
mkdir -p "$ROOT/02 - Billing & Rates/Cost Allocation"
mkdir -p "$ROOT/02 - Billing & Rates/Housing & Dining MOU"

# 03 - SCADA & Controls
mkdir -p "$ROOT/03 - SCADA & Controls/ECS Enercon"
mkdir -p "$ROOT/03 - SCADA & Controls/SEL Devices"
mkdir -p "$ROOT/03 - SCADA & Controls/BACnet Config"
mkdir -p "$ROOT/03 - SCADA & Controls/Modbus Config"

# 04 - Conservation & Sustainability
mkdir -p "$ROOT/04 - Conservation & Sustainability/Water Conservation"
mkdir -p "$ROOT/04 - Conservation & Sustainability/Energy Audits"
mkdir -p "$ROOT/04 - Conservation & Sustainability/Sustainability Programs"

# 05 - Capital Projects
mkdir -p "$ROOT/05 - Capital Projects/Active"
mkdir -p "$ROOT/05 - Capital Projects/Completed"
mkdir -p "$ROOT/05 - Capital Projects/RFPs"

# 06 - Reporting & Compliance
mkdir -p "$ROOT/06 - Reporting & Compliance/Emissions"
mkdir -p "$ROOT/06 - Reporting & Compliance/AASHE STARS"
mkdir -p "$ROOT/06 - Reporting & Compliance/Energy Benchmarking"
mkdir -p "$ROOT/06 - Reporting & Compliance/Annual Reports"

# 07 - Steam Plant Operations
mkdir -p "$ROOT/07 - Steam Plant Operations/Daily Logs"
mkdir -p "$ROOT/07 - Steam Plant Operations/Equipment"
mkdir -p "$ROOT/07 - Steam Plant Operations/Diesel Delivery"
mkdir -p "$ROOT/07 - Steam Plant Operations/Steam Trap Reports"

# 08 - Admin & Reference
mkdir -p "$ROOT/08 - Admin & Reference/Avista Agreements"
mkdir -p "$ROOT/08 - Admin & Reference/Building Ownership"
mkdir -p "$ROOT/08 - Admin & Reference/Standards & Specs"
mkdir -p "$ROOT/08 - Admin & Reference/Training Materials"
mkdir -p "$ROOT/08 - Admin & Reference/Process Documentation"
```

**Step 3: Create fiscal year subfolders**

```bash
# Time-series folders get FY subfolders
mkdir -p "$ROOT/01 - Metering & Data/Meter Reads/FY2025"
mkdir -p "$ROOT/01 - Metering & Data/Meter Reads/FY2026"
mkdir -p "$ROOT/02 - Billing & Rates/Recharge Rates/FY2025"
mkdir -p "$ROOT/02 - Billing & Rates/Recharge Rates/FY2026"
mkdir -p "$ROOT/02 - Billing & Rates/Avista Invoices/FY2025"
mkdir -p "$ROOT/02 - Billing & Rates/Avista Invoices/FY2026"
mkdir -p "$ROOT/06 - Reporting & Compliance/Annual Reports/FY2025"
mkdir -p "$ROOT/06 - Reporting & Compliance/Annual Reports/FY2026"
mkdir -p "$ROOT/07 - Steam Plant Operations/Daily Logs/FY2025"
mkdir -p "$ROOT/07 - Steam Plant Operations/Daily Logs/FY2026"
```

**Step 4: Verify the skeleton**

```bash
find "$ROOT" -type d | sort
```

Expected: ~45 directories, max 3 levels deep, all in the correct structure.

---

### Task 2: Write the README

**Step 1: Create `_README.txt`**

Write the following file to `//fais007/ENERGY GROUP/_CURRENT/_README.txt`:

```
ENERGY GROUP — FOLDER STRUCTURE GUIDE
======================================
Last Updated: 2026-03-02

This is the standardized folder tree for the WSU Energy Group.
All NEW files go here. The old folder structure (everything outside
_CURRENT) is the read-only archive.


WHERE TO SAVE FILES
-------------------

  01 - Metering & Data     Meter reads, SkySpark, data exports, meter inventory
  02 - Billing & Rates     Recharge rates, Avista invoices, cost allocation
  03 - SCADA & Controls    ECS Enercon, SEL devices, BACnet/Modbus configs
  04 - Conservation        Water conservation, energy audits, sustainability
  05 - Capital Projects    Active projects, completed projects, RFPs
  06 - Reporting           Emissions, AASHE STARS, benchmarking, annual reports
  07 - Steam Plant Ops     Daily logs, equipment, diesel delivery, steam traps
  08 - Admin & Reference   Avista agreements, building ownership, standards


RULES
-----

  1. MAX 3 LEVELS DEEP.  Function > Topic > Fiscal Year.  Never deeper.
  2. NO PERSONAL FOLDERS.  Files belong to functions, not people.
  3. NO SOFTWARE INSTALLERS.  Those go on IT's distribution share.
  4. USE FISCAL YEAR FOLDERS (FY2025, FY2026) for time-series data.
     Folders without time-series data hold files directly.


FILE NAMING CONVENTION
----------------------

  Format:   [Category] - [Description] - [Date].ext
  Date:     YYYY-MM-DD  (sorts chronologically)

  Examples:
    Meter Read - Electric Campus Total - 2026-02-15.xlsx
    Recharge Rate - FY2027 Proposal - 2026-03-01.pdf
    Avista Invoice - Electric - 2026-02.pdf
    Steam Log - Daily Reading - 2026-03-02.xlsx

  Do NOT use:
    - Personal initials (JS_Rate_FY27.xlsx)
    - Unclear abbreviations
    - Spaces before file extensions


TEMPLATES
---------

  Check the _Templates folder for starter files with correct naming.


ARCHIVE
-------

  Everything outside _CURRENT is the archive of files from 1983-2026.
  It is NOT organized — that is intentional.  Do not reorganize it.
  If you need an old file, search the archive.
  Do NOT save new files outside _CURRENT.


QUESTIONS?
----------

  Contact: John Slagboom, Energy Group
```

**Step 2: Verify the README is readable**

```bash
cat "//fais007/ENERGY GROUP/_CURRENT/_README.txt"
```

Expected: Clean, readable text with correct formatting.

---

### Task 3: Create Template Files

**Step 1: Create template naming guide files**

These are zero-byte placeholder files that show the correct naming format. Create them in `_Templates`:

```bash
TMPL="//fais007/ENERGY GROUP/_CURRENT/_Templates"

touch "$TMPL/Meter Read - [Type] - [YYYY-MM-DD].xlsx.txt"
touch "$TMPL/Avista Invoice - [Utility] - [YYYY-MM].pdf.txt"
touch "$TMPL/Recharge Rate - [FY20XX] - [Description].xlsx.txt"
touch "$TMPL/Report - [Topic] - [FY20XX].docx.txt"
touch "$TMPL/Steam Log - Daily Reading - [YYYY-MM-DD].xlsx.txt"
touch "$TMPL/Project Brief - [Project Name] - [YYYY-MM-DD].docx.txt"
```

Note: The `.txt` extension is appended so they don't try to open in Excel/Word. The filename itself IS the template showing the naming format.

**Step 2: Create project folder template**

```bash
mkdir -p "$TMPL/Project Folder Template/Scope"
mkdir -p "$TMPL/Project Folder Template/Budget"
mkdir -p "$TMPL/Project Folder Template/Closeout"
```

**Step 3: Verify templates**

```bash
ls -la "$TMPL"
ls -la "$TMPL/Project Folder Template"
```

Expected: 6 template files + 1 project folder template with 3 subfolders.

---

### Task 4: Identify and Copy Active Files

This is the most judgment-intensive task. It requires the user to confirm which files are actively used before copying.

**Step 1: Identify candidate active files**

Search the archive for recently-modified files (last 6 months) that are likely operational:

```bash
find "//fais007/ENERGY GROUP" -maxdepth 4 -name "*.xlsx" -o -name "*.xlsm" -o -name "*.pdf" -o -name "*.docx" | while read f; do
  # Only files modified in 2025 or 2026
  mod=$(stat -c %Y "$f" 2>/dev/null)
  if [ "$mod" -gt 1719792000 ]; then  # July 1, 2025
    echo "$f"
  fi
done 2>/dev/null | head -50
```

**Step 2: Present the list to the user for approval**

Show the user each candidate file and ask:
- Should this be copied to the new structure?
- If yes, which function folder does it belong in?

**Known active files from the scan:**
| File | Current Location | Suggested New Location |
|------|-----------------|----------------------|
| Meter Reads since FY2011.xlsx | Meter Data work files/ | 01 - Metering & Data/Meter Reads/ |
| (Avista reports from Dec 2025) | Avista Energy reports/ | 02 - Billing & Rates/Avista Invoices/FY2026/ |
| (Building ownership files from Mar 2025) | Building Ownership/ | 08 - Admin & Reference/Building Ownership/ |

**Step 3: Copy approved files**

For each approved file, copy (not move) to the new location using the naming convention:

```bash
cp "//fais007/ENERGY GROUP/Meter Data work files/Meter Reads since FY2011.xlsx" \
   "//fais007/ENERGY GROUP/_CURRENT/01 - Metering & Data/Meter Reads/Meter Reads since FY2011.xlsx"
```

IMPORTANT: COPY, never move. The archive must remain intact.

**Step 4: Verify copied files**

```bash
find "//fais007/ENERGY GROUP/_CURRENT" -type f -not -name "_README.txt" -not -name "*.txt" | sort
```

Expected: Only the files the user approved, in the correct locations.

---

### Task 5: Write Team Communication Guide

**Step 1: Create a one-page team guide**

Write to `//fais007/ENERGY GROUP/_CURRENT/08 - Admin & Reference/Process Documentation/Folder Structure Guide - 2026-03-02.txt`:

```
ENERGY GROUP FOLDER STRUCTURE — TEAM GUIDE
============================================
Effective: March 2026

WHAT CHANGED
------------

We have a new organized folder structure for all Energy Group files.

  OLD (archive):  \\fais007\ENERGY GROUP\  (everything outside _CURRENT)
  NEW (use this): \\fais007\ENERGY GROUP\_CURRENT\

The old files are still there and always will be.  Nothing was deleted.
Going forward, save all new files in _CURRENT.


THE NEW STRUCTURE
-----------------

  _CURRENT\
    01 - Metering & Data        Meter reads, SkySpark, data exports
    02 - Billing & Rates        Recharge rates, Avista invoices
    03 - SCADA & Controls       ECS Enercon, SEL, BACnet/Modbus
    04 - Conservation           Water conservation, energy audits
    05 - Capital Projects       Active/completed projects, RFPs
    06 - Reporting              Emissions, AASHE, benchmarking
    07 - Steam Plant Ops        Daily logs, equipment, diesel
    08 - Admin & Reference      Agreements, standards, training


HOW TO NAME FILES
-----------------

  [Category] - [Description] - [Date].ext

  Examples:
    Meter Read - Electric Campus Total - 2026-02-15.xlsx
    Avista Invoice - Electric - 2026-02.pdf

  Use YYYY-MM-DD dates so files sort chronologically.


3 SIMPLE RULES
--------------

  1. Save new files in _CURRENT, not in the old folders
  2. Use the naming convention (see examples above)
  3. Never go more than 3 folders deep


NEED AN OLD FILE?
-----------------

  Search \\fais007\ENERGY GROUP\ (outside _CURRENT).
  Everything from 1983-2026 is still there.

  Tip: Use the Folder Map dashboard to find what you need:
  https://jswsu.github.io/wsu-energy-dashboard/folder-map.html


QUESTIONS?
----------

  Contact: John Slagboom
```

**Step 2: Verify the guide**

```bash
cat "//fais007/ENERGY GROUP/_CURRENT/08 - Admin & Reference/Process Documentation/Folder Structure Guide - 2026-03-02.txt"
```

---

### Task 6: Update Folder Map Dashboard

**Files:**
- Modify: `C:/Users/john.slagboom/Desktop/Git/scan-energy-share.sh`

**Step 1: Run a fresh scan that includes the new _CURRENT folder**

The existing Folder Map dashboard at `folder-map.html` will automatically show the `_CURRENT` folder in the treemap once re-scanned. Run the scan script:

```bash
cd "C:/Users/john.slagboom/Desktop/Git"
bash scan-energy-share.sh "//fais007/ENERGY GROUP"
```

**Step 2: Embed the updated scan data**

Use the same Python replacement approach from the original build to update folder-map.html with the new scan data that includes `_CURRENT`.

**Step 3: Commit and push**

```bash
cd "C:/Users/john.slagboom/Desktop/Git"
git add folder-map.html
git commit -m "feat: update folder map with new _CURRENT structure

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
git push origin main
```

**Step 4: Verify the live dashboard**

Open https://jswsu.github.io/wsu-energy-dashboard/folder-map.html and confirm:
- `_CURRENT` appears in the treemap
- Drilling into `_CURRENT` shows the 8 function folders
- The audit table still shows findings from the archive
