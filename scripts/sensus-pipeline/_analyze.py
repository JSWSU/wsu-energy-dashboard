"""
Sensus AMR data/config anomaly scanner.

Scope: DATA + CONFIGURATION anomalies only. Physical problems (leaks, continuous flow)
are explicitly out of scope.

Columns (0-indexed, 27 fields per row):
   0 Account           5 Building #        10 Last Month (MRR-dyn.)  15 (spare)
   1 Key1              6 Service Address   11 Current (MRR-dyn.)    16 MXU ID
   2 Key2              7 Loc Description   12 Raw current reading   17 Meter ID
   3 Key3              8 Meter Number      13 Error Check           18 Meter Type (B/P/M)
   4 (spare)           9 Service Type      14 Billing End Date      19 MXU Type
                                                                    20 Read Date (MMDDYYYY)
                                                                    21 Read Time
                                                                    22 High
                                                                    23 Low
                                                                    24 System (DW)
                                                                    25 Multiplier
                                                                    26 (Notes/trailing)
"""

import csv
from pathlib import Path
from collections import defaultdict
from datetime import date

OUT_DIR = Path(r"C:\Users\john.slagboom\Downloads\Sensus Testbed\Output")

FILES = [
    ("2026-02-09", OUT_DIR / "AMRoutput20260209_copy.csv"),
    ("2026-04-03", OUT_DIR / "AMRoutput20260403.csv"),
    ("2026-04-21", OUT_DIR / "AMRoutput20260421.csv"),
]

C = {
    "account":   0,
    "bldg":      5,
    "svc_addr":  6,
    "loc":       7,
    "meter_num": 8,
    "svc_type":  9,
    "last_mo":   10,
    "current":   11,
    "raw_read":  12,
    "err_chk":   13,
    "bill_end":  14,
    "mxu_id":    16,
    "meter_id":  17,
    "mtr_type":  18,
    "mxu_type":  19,
    "read_date": 20,
    "read_time": 21,
    "high":      22,
    "low":       23,
    "system":    24,
    "mult":      25,
}

EXPECTED_MULT = {"1", "10", "100", "1000"}


def load(path):
    rows = {}
    with open(path, "r", newline="", encoding="utf-8-sig", errors="replace") as f:
        rdr = csv.reader(f)
        for lineno, r in enumerate(rdr, 1):
            if len(r) < 26 or not r[0].strip():
                continue
            acct = r[C["account"]].strip()
            rows[acct] = {
                "line": lineno,
                "bldg": r[C["bldg"]].strip(),
                "svc_addr": r[C["svc_addr"]].strip(),
                "loc": r[C["loc"]].strip(),
                "meter_num": r[C["meter_num"]].strip(),
                "svc_type": r[C["svc_type"]].strip(),
                "raw_read": r[C["raw_read"]].strip(),
                "mxu_id": r[C["mxu_id"]].strip(),
                "meter_id": r[C["meter_id"]].strip(),
                "mtr_type": r[C["mtr_type"]].strip(),
                "mxu_type": r[C["mxu_type"]].strip(),
                "read_date": r[C["read_date"]].strip(),
                "read_time": r[C["read_time"]].strip(),
                "high": r[C["high"]].strip(),
                "low": r[C["low"]].strip(),
                "system": r[C["system"]].strip(),
                "mult": r[C["mult"]].strip(),
            }
    return rows


def to_int(s):
    if s is None:
        return None
    s = s.strip().lstrip("0") or "0"
    try:
        return int(s)
    except ValueError:
        # tolerate decimal strings: truncate to int for sequence math, but original raw still flagged elsewhere
        try:
            return int(float(s))
        except Exception:
            return None


datasets = [(label, load(path)) for label, path in FILES]
all_accts = set()
for _, ds in datasets:
    all_accts.update(ds.keys())

findings = []  # (severity, category, acct, bldg, detail)


def add(sev, cat, acct, bldg, detail):
    findings.append((sev, cat, acct, bldg, detail))


# ---- Per-file single-row checks ----
for label, ds in datasets:
    for acct, row in ds.items():
        mult = row["mult"]
        rd = row["raw_read"]

        if not mult:
            add("HIGH", "Multiplier blank", acct, row["bldg"],
                f"[{label}] line {row['line']}: Multiplier field is empty")
        elif mult not in EXPECTED_MULT:
            add("MED", "Multiplier atypical value", acct, row["bldg"],
                f"[{label}] line {row['line']}: Multiplier={mult} (expected one of {sorted(EXPECTED_MULT, key=int)})")

        if not rd:
            add("HIGH", "Raw reading blank", acct, row["bldg"],
                f"[{label}] line {row['line']}: raw reading column empty (Meter#={row['meter_num'] or '—'}, MeterID={row['meter_id'] or '—'})")
        else:
            if "." in rd:
                add("HIGH", "Raw reading contains decimal", acct, row["bldg"],
                    f"[{label}] line {row['line']}: raw reading '{rd}' contains a decimal point (other runs are integer); "
                    f"Usage calc will be wildly wrong when integer/decimal runs are differenced (Multiplier={mult})")
            rv = to_int(rd)
            if rv is not None and rv == 0:
                add("HIGH", "Raw reading is zero", acct, row["bldg"],
                    f"[{label}] line {row['line']}: raw reading=0 literally (Multiplier={mult})")
            # Stuck at or near 9-digit rollover max (999,999,xxx with mult=1) is a register/export anomaly
            if rv is not None and rv >= 999_990_000:
                add("HIGH", "Raw reading pinned near 9-digit max", acct, row["bldg"],
                    f"[{label}] line {row['line']}: raw reading={rd} ≥ 999,990,000 "
                    f"(System={row['system']}, Multiplier={mult}) — likely rolled over but AMR still reports pre-rollover value")

        if not row["mxu_id"] and not row["meter_id"]:
            add("HIGH", "MXU ID and Meter ID both blank", acct, row["bldg"],
                f"[{label}] line {row['line']}: meter not identifiable by MXU or Meter ID")

        if not row["mtr_type"]:
            add("LOW", "Meter Type blank", acct, row["bldg"],
                f"[{label}] line {row['line']}: Meter Type (B/P/M) blank")

        if not row["read_date"]:
            add("HIGH", "Read Date blank", acct, row["bldg"],
                f"[{label}] line {row['line']}: Read Date column empty")
        else:
            rdate = row["read_date"].zfill(8)
            try:
                mm = int(rdate[0:2]); dd = int(rdate[2:4]); yy = int(rdate[4:8])
                d = date(yy, mm, dd)
                export_anchor = {"2026-02-09": date(2026, 2, 9),
                                 "2026-04-03": date(2026, 4, 3),
                                 "2026-04-21": date(2026, 4, 21)}[label]
                days = (export_anchor - d).days
                if days > 45:
                    add("MED", "Stale Read Date (>45d before export)", acct, row["bldg"],
                        f"[{label}] line {row['line']}: Read Date {rdate} is {days} days before export date")
                elif days < 0:
                    add("HIGH", "Read Date in future", acct, row["bldg"],
                        f"[{label}] line {row['line']}: Read Date {rdate} is AFTER export date {export_anchor}")
            except Exception:
                add("MED", "Read Date unparseable", acct, row["bldg"],
                    f"[{label}] line {row['line']}: Read Date '{row['read_date']}' cannot be parsed MMDDYYYY")


# ---- Cross-file checks per Account ----
for acct in sorted(all_accts):
    versions = [(lbl, ds[acct]) for lbl, ds in datasets if acct in ds]

    # Flag any account NOT present in all 3 files
    if len(versions) < 3:
        present = [l for l, _ in versions]
        missing = [l for l, ds in datasets if acct not in ds]
        bldg = versions[0][1]["bldg"] if versions else ""
        # HIGH if missing from the latest run (meter dropped), MED if only new
        severity = "HIGH" if "2026-04-21" in missing else "MED"
        add(severity, "Account missing in some runs", acct, bldg,
            f"present in {present}; missing from {missing}")
        if len(versions) < 2:
            continue

    bldg = versions[-1][1]["bldg"]

    mults = {lbl: r["mult"] for lbl, r in versions}
    if len(set(v for v in mults.values() if v)) > 1:
        add("HIGH", "Multiplier changed between runs", acct, bldg,
            "Multipliers over time: " + "; ".join(f"{l}={m or '∅'}" for l, m in mults.items()))

    meter_ids = {lbl: r["meter_id"] for lbl, r in versions if r["meter_id"]}
    if len(set(meter_ids.values())) > 1:
        add("HIGH", "Meter ID changed between runs", acct, bldg,
            "Meter IDs: " + "; ".join(f"{l}={m}" for l, m in meter_ids.items()))

    mxu_ids = {lbl: r["mxu_id"] for lbl, r in versions if r["mxu_id"]}
    if len(set(mxu_ids.values())) > 1:
        add("HIGH", "MXU ID changed between runs", acct, bldg,
            "MXU IDs: " + "; ".join(f"{l}={m}" for l, m in mxu_ids.items()))

    mtypes = {lbl: r["mtr_type"] for lbl, r in versions if r["mtr_type"]}
    if len(set(mtypes.values())) > 1:
        add("MED", "Meter Type flipped between runs", acct, bldg,
            "Meter Types: " + "; ".join(f"{l}={m}" for l, m in mtypes.items()))

    # Reading analysis
    reads = [(lbl, to_int(r["raw_read"]), r["raw_read"]) for lbl, r in versions]
    seq = [(l, v, raw) for (l, v, raw) in reads if v is not None]

    # Stuck across 3 runs
    if len(seq) == 3:
        vals = [v for _, v, _ in seq]
        raws = [raw for _, _, raw in seq]
        latest = versions[-1][1]
        latest_mult = latest["mult"]
        latest_sys = latest["system"]
        if len(set(vals)) == 1 and vals[0] > 0:
            if latest_mult not in {"", "1"}:
                add("MED", "Raw reading stuck across all 3 runs", acct, bldg,
                    f"raw={vals[0]} unchanged across {[l for l,_,_ in seq]}; Mult={latest_mult}, System={latest_sys}")
            elif latest_sys == "DW":
                # DW meter with Mult=1 stuck across Feb-Apr is a data concern (residential/lab usage expected)
                add("MED", "DW meter raw reading stuck across all 3 runs", acct, bldg,
                    f"raw={vals[0]} unchanged across {[l for l,_,_ in seq]}; Mult=1, System=DW "
                    f"(ongoing DW usage would normally cause the register to advance)")

    # Backwards reading (decrease, flag unless plausible rollover near 99999999)
    for i in range(1, len(seq)):
        pl, pv, praw = seq[i-1]
        cl, cv, craw = seq[i]
        if cv < pv:
            drop = pv - cv
            near_rollover = pv >= 90_000_000 and cv < 10_000_000
            if not near_rollover:
                add("HIGH", "Raw reading decreased (non-rollover)", acct, bldg,
                    f"{pl} read={praw} ({pv}) → {cl} read={craw} ({cv}); drop={drop}")

    # Digit-count / field-width shift
    raw_strs = [raw for _, _, raw in seq]
    widths = set(len(raw) for raw in raw_strs)
    if len(widths) > 1:
        add("LOW", "Raw reading digit-count changed", acct, bldg,
            "widths over time: " + "; ".join(f"{l}={len(raw)}" for l, _, raw in seq) +
            " (raws: " + " / ".join(raw_strs) + ")")

    # Implausible usage (Feb→Apr03 > 100M gallons on a single meter is suspicious)
    for i in range(1, len(seq)):
        pl, pv, _ = seq[i-1]
        cl, cv, _ = seq[i]
        mult = versions[-1][1]["mult"]
        try:
            mi = int(mult)
        except Exception:
            continue
        if cv >= pv:
            usage = (cv - pv) * mi
            if usage > 100_000_000:
                add("HIGH", "Computed usage implausibly large (data/mult error?)",
                    acct, bldg,
                    f"{pl}→{cl}: delta={cv-pv} × Mult={mi} = {usage:,} units")

# ---- Duplicate IDs within a file ----
for label, ds in datasets:
    for kind, key in (("MXU ID", "mxu_id"), ("Meter ID", "meter_id")):
        by_id = defaultdict(list)
        for acct, row in ds.items():
            v = row[key]
            if v:
                by_id[v].append(acct)
        for v, accts in by_id.items():
            if len(accts) > 1:
                add("HIGH", f"Duplicate {kind} within a single file", ",".join(accts),
                    ds[accts[0]]["bldg"],
                    f"[{label}] {kind} {v} assigned to accounts {accts}")

# ---- Sanity: unusual Service Type / System values ----
# Known valid System codes in Pullman dataset: DW (Domestic Water), IR (Irrigation)
# Known valid Meter Types: B (BCT/SmartPoint), P (Pit), M (Manual)
for label, ds in datasets:
    for acct, row in ds.items():
        if row["svc_type"] and row["svc_type"] not in {"W"}:
            add("LOW", "Unexpected Service Type", acct, row["bldg"],
                f"[{label}] line {row['line']}: Service Type={row['svc_type']!r} (expected 'W')")
        if row["system"] and row["system"] not in {"DW", "IR"}:
            add("LOW", "Unexpected System code", acct, row["bldg"],
                f"[{label}] line {row['line']}: System={row['system']!r} (expected 'DW' or 'IR')")
        if row["mtr_type"] and row["mtr_type"] not in {"B", "P", "M"}:
            add("LOW", "Unexpected Meter Type", acct, row["bldg"],
                f"[{label}] line {row['line']}: Meter Type={row['mtr_type']!r} (expected 'B', 'P', or 'M')")


# ---- Report ----
SEV = {"HIGH": 0, "MED": 1, "LOW": 2}
findings.sort(key=lambda f: (SEV.get(f[0], 9), f[1], f[2]))

by_cat = defaultdict(list)
for sev, cat, acct, bldg, detail in findings:
    by_cat[(sev, cat)].append((acct, bldg, detail))

# Annotations keyed by Account for HIGH findings (investigative notes)
ANNOTATIONS = {
    "200051": ("ENTOM GREENHOUSE 0111 is a manual meter (Meter Type = M, no MXU ID, Meter ID 1852844682). "
               "The 02/09 file records raw='118811.49' (with decimal), while 04/03 = '11891937' and 04/21 = '11931225' (integer). "
               "This is almost certainly a **unit/format change** — e.g., 02/09 recorded as ccf × 100 with decimals, "
               "later exports recorded as raw pulses without decimals. Differencing these runs for usage = 11,891,937 − 118,811.49 = "
               "+11.77M fake units. **Reconcile the format before computing any cross-run usage for 200051.**"),
    "200083": ("Valley Crest Apts Main IR (0675, Meter ID 95260687) raw = **999999768 in all 3 runs**, Mult=1, System=IR. "
               "This is pinned within 232 units of the 9-digit (999,999,999) rollover boundary. "
               "Either the register has rolled over and the MXU is still reporting the pre-rollover snapshot, "
               "or the register is physically stuck at near-max. Either way the Usage calc will be wrong until it's resolved."),
    "200148": ("Steptoe Village Bldg P (0665_DW_014, Meter ID 95260680) raw = **999992946 in all 3 runs**, Mult=1, System=DW. "
               "DW meter pinned near 9-digit rollover. Residential DW should have daily usage; this is a register or "
               "export-identity problem, not a real zero-use condition."),
    "200105": ("Nez Perce Bldgs ABU (0677_DW_001, Meter ID 95260674) was present in 02/09 and 04/03 files but "
               "**DROPPED FROM 04/21**. Either the route was edited, MXU is offline, or the meter was removed. "
               "Verify — a DW meter vanishing mid-cycle is a data continuity issue."),
    "200045": ("ENTOM SHOP (0111A, Meter ID 89124877) reads **exactly 0000** in all 3 runs with Multiplier=1000. "
               "An active building reading literally 0 across 2+ months is almost certainly a configuration or register problem: "
               "newly installed but uncommissioned, stalled register, bad MXU → meter coupling, or an export column misalignment. "
               "Verify with an on-site read before trusting usage billed on this account."),
    "200104": ("McEachern All Sites (0805, Meter ID 95236516) shows **9-digit readings that continuously DECREASE** "
               "(992,485,723 → 992,259,351 → 991,851,628) while Multiplier=1. Total drop = 634,095 units over ~2 months. "
               "Physical meters do not run backwards. Likely causes: (a) Multiplier should be 10 or 100 and the raw register wrapped, "
               "(b) wrong Meter ID is being read (identity crossed with a nearby meter), or (c) an encoder/BCT reversed on swap. "
               "THIS IS THE HIGHEST-VALUE DATA FINDING — it invalidates any usage calc on 200104."),
    "200020": ("STEF CENTER small orchard (0180_DW_001) is a **manual-read meter (Meter Type = M)**, no MXU/Meter ID. "
               "Reading dropped by 1 unit (1,924,147 → 1,924,146) between 04/03 and 04/21 runs. "
               "Most likely a transcription error on manual entry, not an automated data issue. "
               "Note: the 04/03 file shows Read Date 02/27/2026 — the 04/03 export re-published a Feb manual value."),
    "200031": ("ALBRK LAB (0071, Meter ID 91248976) raw=23 unchanged across all 3 runs, Multiplier=1000. "
               "Tablet IS physically polling (read dates 02/04, 02/25, 04/08) but register value is frozen. "
               "Either (a) meter truly registering 0 usage for 60+ days (physical), or (b) register/MXU stuck (data/config). "
               "Classify after walking meter — if flow is visible, this is a config issue."),
    "200112": ("Marriot Residence Inn IR (0865_IR_001) irrigation raw=5540 unchanged across 3 runs, Mult=1000. "
               "For Pullman irrigation in Feb–Apr this is plausibly *legitimate* (winter shut-off). "
               "Flagged only because the multiplier of 1000 × zero delta means Usage is being reported as 0 consistently; "
               "confirm irrigation is physically off before dismissing."),
    "200095": ("Terrace Apts IR Bldg A (0650A) **appears only in 04/21** — either newly commissioned, newly added to route, "
               "or previously dropped from the export. Raw reading = 294,620 with 9-digit leading-zero width ('000294620')."),
    "200131": ("USDA Machine Shop West (0195) **appears only in 04/21** — new to the route or newly commissioned. "
               "Raw = 00033 × Mult 100; verify historical baseline exists before billing."),
}

report = OUT_DIR / "anomaly-report.md"
with open(report, "w", encoding="utf-8") as f:
    f.write("# Sensus AMR Data/Config Anomaly Report\n\n")
    f.write("Generated: 2026-04-21\n\n")
    f.write("Source files:\n")
    for lbl, p in FILES:
        f.write(f"- **{lbl}**: `{p}`\n")
    f.write(f"\nUnique accounts across all 3 runs: **{len(all_accts)}**\n\n")
    f.write("Scope: **data + configuration anomalies only**. Physical issues (leaks, continuous use) are out of scope.\n\n")
    f.write("Column mapping used (27 fields, 0-indexed): Account=0, Bldg#=5, SvcAddr=6, LocDesc=7, Meter#=8, "
            "SvcType=9, LastMo(dyn)=10, Current(dyn)=11, **RawRead=12**, ErrChk=13, BillEnd=14, MXU_ID=16, "
            "MeterID=17, MtrType=18, MXUType=19, ReadDate=20, ReadTime=21, High=22, Low=23, System=24, **Multiplier=25**.\n\n")
    f.write("Known valid codes — System: DW, IR.  Meter Type: B (SmartPoint), P (Pit), M (Manual).  Expected Multipliers: 1/10/100/1000.\n\n")
    f.write("**Findings summary:**\n\n")
    f.write(f"| Severity | Count |\n|---|---|\n")
    for sev in ("HIGH", "MED", "LOW"):
        n = sum(1 for s, *_ in findings if s == sev)
        f.write(f"| {sev} | {n} |\n")
    f.write(f"| **Total** | **{len(findings)}** |\n\n")

    # Top-of-report executive summary for HIGH findings
    f.write("## Executive Summary — HIGH severity data/config issues\n\n")
    high_accts = sorted({acct for sev, cat, acct, *_ in findings if sev == "HIGH"})
    for acct in high_accts:
        note = ANNOTATIONS.get(acct)
        if note:
            f.write(f"### Acct {acct}\n\n{note}\n\n")
    # also list MED-stuck + missing accts
    for acct in ("200031", "200112", "200095", "200131"):
        note = ANNOTATIONS.get(acct)
        if note and acct not in high_accts:
            f.write(f"### Acct {acct} (MED)\n\n{note}\n\n")

    f.write("---\n\n## All findings by category\n\n")

    for (sev, cat), items in by_cat.items():
        f.write(f"### [{sev}] {cat} — {len(items)}\n\n")
        for acct, bldg, detail in items:
            bldg_str = f" (bldg {bldg})" if bldg else ""
            f.write(f"- **Acct {acct}**{bldg_str}: {detail}\n")
        f.write("\n")

print(f"Wrote: {report}")
for sev in ("HIGH", "MED", "LOW"):
    n = sum(1 for s, *_ in findings if s == sev)
    print(f"  {sev}: {n}")
print(f"  Total: {len(findings)}")
