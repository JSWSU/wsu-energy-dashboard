"""Rank accounts by computed usage between runs, flag the highest."""
import csv
from pathlib import Path
from datetime import date

OUT = Path(r"C:\Users\john.slagboom\Downloads\Sensus Testbed\Output")
FILES = [
    ("2026-02-09", OUT / "AMRoutput20260209_copy.csv"),
    ("2026-04-03", OUT / "AMRoutput20260403.csv"),
    ("2026-04-21", OUT / "AMRoutput20260421.csv"),
]


def parse_int(s):
    s = s.strip()
    if not s:
        return None
    s_int = s.lstrip("0") or "0"
    try:
        return int(s_int)
    except ValueError:
        try:
            return int(float(s))  # tolerate '118811.49'
        except Exception:
            return None


def parse_date(s):
    s = s.strip().zfill(8)
    try:
        return date(int(s[4:8]), int(s[0:2]), int(s[2:4]))
    except Exception:
        return None


def load(path):
    rows = {}
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as f:
        for r in csv.reader(f):
            if len(r) < 26 or not r[0].strip():
                continue
            rows[r[0].strip()] = {
                "bldg": r[5].strip(),
                "svc_addr": r[6].strip(),
                "meter_num": r[8].strip(),
                "raw": r[12].strip(),
                "mxu": r[16].strip(),
                "meter_id": r[17].strip(),
                "mtr_type": r[18].strip(),
                "rdate": r[20].strip(),
                "system": r[24].strip(),
                "mult": r[25].strip(),
            }
    return rows


datasets = {lbl: load(p) for lbl, p in FILES}

# Compute usage between consecutive runs
pairs = [("2026-02-09", "2026-04-03"), ("2026-04-03", "2026-04-21"),
         ("2026-02-09", "2026-04-21")]

results = []  # (usage, period, acct, bldg, svc, system, mult, prev_raw, cur_raw, prev_date, cur_date, days)

for prev_lbl, cur_lbl in pairs:
    prev_ds, cur_ds = datasets[prev_lbl], datasets[cur_lbl]
    common = set(prev_ds) & set(cur_ds)
    for acct in common:
        p = prev_ds[acct]
        c = cur_ds[acct]
        pv = parse_int(p["raw"])
        cv = parse_int(c["raw"])
        if pv is None or cv is None:
            continue
        try:
            mi = int(c["mult"])
        except (ValueError, TypeError):
            continue
        if cv < pv:
            continue  # backwards = already flagged
        usage = (cv - pv) * mi
        pdate = parse_date(p["rdate"])
        cdate = parse_date(c["rdate"])
        days = (cdate - pdate).days if pdate and cdate else None
        results.append((
            usage, f"{prev_lbl} ->{cur_lbl}",
            acct, c["bldg"], c["svc_addr"], c["system"], c["mult"],
            p["raw"], c["raw"], p["rdate"], c["rdate"], days, c["meter_id"], c["mtr_type"]
        ))

# Sort descending
results.sort(key=lambda x: -x[0])

print(f"{'Usage':>15}  {'Period':<25}  {'Acct':<7}  {'Bldg':<8}  {'Sys':<3}  {'Mult':<5}  "
      f"{'PrevRead':<12}  {'CurRead':<12}  {'PrevDate':<10}  {'CurDate':<10}  {'Days':<5}  Svc")
print("-" * 170)
for row in results[:50]:
    usage, period, acct, bldg, svc, system, mult, praw, craw, pd, cd, days, mid, mt = row
    pds = f"{pd[:2]}/{pd[2:4]}/{pd[4:]}" if len(pd) == 8 else pd
    cds = f"{cd[:2]}/{cd[2:4]}/{cd[4:]}" if len(cd) == 8 else cd
    print(f"{usage:>15,}  {period:<25}  {acct:<7}  {bldg:<8}  {system:<3}  {mult:<5}  "
          f"{praw:<12}  {craw:<12}  {pds:<10}  {cds:<10}  {str(days):<5}  {svc}")

print("\nTotal pair-rows evaluated:", len(results))
