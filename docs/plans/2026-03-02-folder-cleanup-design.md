# Energy Group Folder Cleanup — Design Document

**Date:** 2026-03-02
**Purpose:** Design a new standardized folder tree for the Energy Group, turning the current `\\fais007\ENERGY GROUP` into a read-only archive
**Audience:** WSU Energy Group team (5+ daily users)

---

## Overview

The current `\\fais007\ENERGY GROUP` share contains ~58K files across 34.5 GB spanning 43 years (1983–2026). The structure has accumulated duplicate folders (nested 14–18 levels deep), orphaned personal files, legacy formats, and large installers with no naming convention.

Rather than reorganize the existing mess, a new standardized folder tree will be created alongside it. The old share becomes the archive. All new work goes in the new structure going forward.

## Strategy

1. **Leave the old share untouched** — it becomes the archive
2. **Create a new folder tree** with a clean, standardized structure
3. **Copy only actively-used files** from the archive to the new tree
4. **Communicate the change** to the team with a one-page guide

## New Folder Tree Architecture

### Top-Level Structure

```
\\fais007\ENERGY\                    (or ENERGY GROUP\ENERGY (Current)\)
  01 - Metering & Data\
  02 - Billing & Rates\
  03 - SCADA & Controls\
  04 - Conservation & Sustainability\
  05 - Capital Projects\
  06 - Reporting & Compliance\
  07 - Steam Plant Operations\
  08 - Admin & Reference\
  _Templates\
  _README.txt
```

**Rules:**
- Numbered prefixes (`01`–`08`) lock display order in Explorer
- `_Templates` and `_README.txt` sort to top (underscore before numbers)
- No personal-name folders — files belong to functions, not people
- No software installers — those belong on IT's software distribution share

### Internal Structure (3-Level Max)

Each function folder uses a consistent pattern: function → topic → fiscal year (where applicable).

```
01 - Metering & Data\
  Meter Reads\
    FY2025\
    FY2026\
  Meter Inventory\
  SkySpark\
  Data Exports\
  Network Meters\

02 - Billing & Rates\
  Recharge Rates\
    FY2025\
    FY2026\
  Avista Invoices\
    FY2025\
    FY2026\
  Cost Allocation\
  Housing & Dining MOU\

03 - SCADA & Controls\
  ECS Enercon\
  SEL Devices\
  BACnet Config\
  Modbus Config\

04 - Conservation & Sustainability\
  Water Conservation\
  Energy Audits\
  Sustainability Programs\

05 - Capital Projects\
  Active\
  Completed\
  RFPs\

06 - Reporting & Compliance\
  Emissions\
  AASHE STARS\
  Energy Benchmarking\
  Annual Reports\
    FY2025\
    FY2026\

07 - Steam Plant Operations\
  Daily Logs\
    FY2025\
    FY2026\
  Equipment\
  Diesel Delivery\
  Steam Trap Reports\

08 - Admin & Reference\
  Avista Agreements\
  Building Ownership\
  Standards & Specs\
  Training Materials\
  Process Documentation\
```

**Key rules:**
- Max 3 levels deep — function → topic → year (never deeper)
- Fiscal year folders (`FY2025`, `FY2026`) only for time-series data
- Active/Completed split only for Capital Projects
- Folders without time-series data hold files directly

## Naming Conventions

### Folder Names
- Title Case with spaces: `Meter Reads`, not `meter_reads`
- No special characters (except `&` in top-level names)
- Year format: `FY2026` for fiscal year, `2026` for calendar year

### File Names
- Format: `[Category] - [Description] - [Date].ext`
- Date format: `YYYY-MM-DD` (sorts chronologically)
- Examples:
  - `Meter Read - Electric Campus Total - 2026-02-15.xlsx`
  - `Recharge Rate - FY2027 Proposal - 2026-03-01.pdf`
  - `Avista Invoice - Electric - 2026-02.pdf`
- No version numbers in names — use `_v2`, `_DRAFT`, `_FINAL` only when necessary
- No personal initials in file names

### Templates
```
_Templates\
  Meter Read - [Type] - [YYYY-MM-DD].xlsx
  Invoice - [Vendor] - [YYYY-MM].pdf
  Report - [Topic] - [FY20XX].docx
  Project Folder Template\
    Scope\
    Budget\
    Closeout\
```

## Transition Plan

### Phase 1: Create the New Tree
- Create the full folder skeleton (~40 folders) on the new share
- Write `_README.txt` with structure guide and naming conventions
- Place template files in `_Templates\`

### Phase 2: Archive the Old Share
- Rename or label the old share as archive (e.g., `ENERGY GROUP (Archive)`)
- Old share remains read-only accessible indefinitely
- No files moved or deleted from the archive

### Phase 3: Copy Active Files
- Selectively copy only actively-used files to the new structure:
  - Current meter reads workbook
  - Active rate development files
  - Current SkySpark configs
  - Active capital project files
  - Current process documentation
- Do NOT bulk-migrate historical files — they stay in the archive

### Phase 4: Team Communication
- One-page guide: new share location, naming convention, where to save things
- Set a go-live date (e.g., start of next month) — all new files in the new share
- Old share remains for reference

## What the Current Share Contains (for reference)

| Issue | Scale | Impact |
|-------|-------|--------|
| Energy Services Admin domination | 27 GB / 47K files (89% of share) | Everything buried under one folder |
| Deep nesting | 14–18 levels deep | Files impossible to navigate |
| Duplicate folder structures | "Energy Files" appears 7 times nested in itself | Confusion about which copy is current |
| Orphaned personal folders | Loc Vo (430 MB), Croyle, Terry Ryan | Former employees' files with no owner |
| Large installers | 2.7 GB (RTACSetup.exe + AcSELerator) | Storage waste |
| Legacy formats | ~2,200 files (KVA, WKS, WK1, WPS, EU) | Unopenable without specialized software |
| Duplicate working files | 5+ copies of "Meter Reads since FY2011.xlsx" | Confusion about which is current |
| Empty folders | 86 empty folders | Clutter |
| No naming convention | Mixed styles across all folders | Inconsistent, hard to search |

## What This Does NOT Include

- No deletion of anything from the archive
- No conversion of legacy file formats
- No reorganization of the old share
- No changes to file permissions beyond matching the existing share
