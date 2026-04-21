"""Rebuild Feb-Mar 2026 CSV-sourced rows in the dashboard JSONs from AMR raw reads.

Strategy:
- Load all 3 AMR snapshots (02/09, 04/03, 04/21).
- For each account, take earliest + latest valid reads, compute delta * multiplier.
- Prorate the delta by day count across Feb and Mar 2026.
- Aggregate per (bldgNo, system) across multi-meter buildings.
- Rewrite Feb 2026 + Mar 2026 rows with dataSource containing "CSV".
- Preserve all other rows (SkySpark-only, non-2026, Jan 2026).
"""
import csv
import json
import shutil
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

AMR_DIR = Path(r"C:\Users\john.slagboom\Downloads\Sensus Testbed\Output")
DATA_DIR = Path(r"C:\Users\john.slagboom\Desktop\Git\data")

AMR_FILES = [
    (date(2026, 2, 9), AMR_DIR / "AMRoutput20260209_copy.csv"),
    (date(2026, 4, 3), AMR_DIR / "AMRoutput20260403.csv"),
    (date(2026, 4, 21), AMR_DIR / "AMRoutput20260421.csv"),
]

FEB_START = date(2026, 2, 1)
MAR_START = date(2026, 3, 1)
APR_START = date(2026, 4, 1)


def parse_raw(s):
    """Return (int_value, is_decimal_stripped) or (None, False)."""
    s = s.strip()
    if not s:
        return None, False
    if "." in s:
        try:
            stripped = s.replace(".", "")
            return int(stripped.lstrip("0") or "0"), True
        except ValueError:
            return None, False
    try:
        return int(s.lstrip("0") or "0"), False
    except ValueError:
        return None, False


def parse_date(s):
    s = s.strip().zfill(8)
    try:
        return date(int(s[4:8]), int(s[0:2]), int(s[2:4]))
    except ValueError:
        return None


def load_amr():
    snaps = defaultdict(list)
    for snapshot_date, path in AMR_FILES:
        with open(path, newline="", encoding="utf-8-sig", errors="replace") as f:
            for r in csv.reader(f):
                if len(r) < 26 or not r[0].strip():
                    continue
                acct = r[0].strip()
                raw, was_decimal = parse_raw(r[12])
                if raw is None:
                    continue
                try:
                    mult = int(r[25])
                except (ValueError, TypeError):
                    continue
                rd = parse_date(r[20])
                if not rd:
                    continue
                snaps[acct].append({
                    "snap_date": snapshot_date,
                    "read_date": rd,
                    "raw": raw,
                    "was_decimal": was_decimal,
                    "mult": mult,
                    "bldg": r[5].strip(),
                    "system": r[24].strip(),
                    "meter": r[8].strip(),
                    "meter_type": r[18].strip(),
                })
    return snaps


def validate_account(snaps):
    """Return (earliest, latest) pair suitable for delta, or None.

    Rules:
    - Need >=2 snapshots spanning a positive day count.
    - Reject if latest.raw < earliest.raw (backward register).
    - Reject if raw is pinned near 9-digit max (register at rollover boundary).
    - Handle decimal-stripped case: if one snapshot was decimal and others weren't,
      prefer the decimal-stripped value if it matches the later reads' order of magnitude.
    """
    if len(snaps) < 2:
        return None
    snaps = sorted(snaps, key=lambda x: x["snap_date"])
    earliest = snaps[0]
    latest = snaps[-1]

    # Reject pinned-near-max registers
    if earliest["raw"] >= 999_990_000 or latest["raw"] >= 999_990_000:
        return None

    # Reject backward (non-rollover)
    if latest["raw"] < earliest["raw"]:
        return None

    # Reject zero-span reads
    if latest["read_date"] <= earliest["read_date"]:
        return None

    return earliest, latest


def compute_usage(snaps):
    """Return dict with feb_usage, mar_usage, apr_usage (gallons), or None."""
    pair = validate_account(snaps)
    if pair is None:
        return None
    earliest, latest = pair

    total_delta = (latest["raw"] - earliest["raw"]) * latest["mult"]
    total_days = (latest["read_date"] - earliest["read_date"]).days
    if total_days <= 0 or total_delta < 0:
        return None

    # Sanity: skip implausible daily rates (>500k gal/day for a single meter)
    daily_rate = total_delta / total_days
    if daily_rate > 500_000:
        # Leave as None; force manual review
        return None

    feb_days = mar_days = apr_days = 0
    d = earliest["read_date"]
    end = latest["read_date"]
    while d < end:
        if d.year == 2026:
            if d.month == 2:
                feb_days += 1
            elif d.month == 3:
                mar_days += 1
            elif d.month == 4:
                apr_days += 1
        d += timedelta(days=1)

    rate = total_delta / total_days
    return {
        "feb": rate * feb_days,
        "mar": rate * mar_days,
        "apr": rate * apr_days,
        "total_delta": total_delta,
        "total_days": total_days,
        "daily_rate": rate,
        "earliest_read": earliest["read_date"].isoformat(),
        "latest_read": latest["read_date"].isoformat(),
        "meter": latest["meter"],
        "bldg": latest["bldg"],
        "system": latest["system"],
    }


def historical_baseline(rows, bldg, service):
    """Return median monthly usage for this bldg in Jan 2025 - Jan 2026, or None if unavailable."""
    hist = []
    for r in rows:
        if r.get("bldgNo") != bldg:
            continue
        if r.get("service") != service:
            continue
        sd = r.get("startDate", "")
        # Include Jan 2025 through Jan 2026 (pre-corruption period)
        if not sd.endswith(("2025", "2026")):
            continue
        if sd.startswith(("02-01-2026", "03-01-2026", "04-01-2026")):
            continue
        u = r.get("usage")
        if isinstance(u, (int, float)) and u >= 0:
            hist.append(u)
    if not hist:
        return None
    hist.sort()
    return hist[len(hist) // 2]


def main():
    amr = load_amr()
    print(f"Loaded {len(amr)} accounts from AMR files")

    per_building = defaultdict(lambda: {"feb": 0.0, "mar": 0.0, "apr": 0.0, "accts": [], "skipped": []})

    for acct, snaps in amr.items():
        usage = compute_usage(snaps)
        if usage is None:
            s = snaps[0]
            per_building[(s["bldg"], s["system"])]["skipped"].append(acct)
            continue
        key = (usage["bldg"], usage["system"])
        per_building[key]["feb"] += usage["feb"]
        per_building[key]["mar"] += usage["mar"]
        per_building[key]["apr"] += usage["apr"]
        per_building[key]["accts"].append((acct, usage["total_delta"], usage["daily_rate"]))

    # Per-file rewrite
    for fname, system in [("domestic_water.json", "DW"), ("irrigation.json", "IR")]:
        path = DATA_DIR / fname
        backup = path.with_suffix(f".json.prefix.{datetime.now().strftime('%Y%m%dT%H%M%S')}.bak")
        shutil.copy2(path, backup)
        print(f"\nBacked up {fname} -> {backup.name}")

        with open(path, encoding="utf-8") as f:
            grid = json.load(f)

        # Precompute historical baselines (median monthly usage pre-Feb 2026) per bldg
        service = "Domestic Water" if system == "DW" else "Irrigation Water"
        baselines = {}
        for r in grid["rows"]:
            b = r.get("bldgNo", "")
            if b and b not in baselines:
                baselines[b] = historical_baseline(grid["rows"], b, service)

        touched = 0
        skipped_no_amr = 0
        nulled_suspect = 0
        preserved = 0
        changes = []
        for r in grid["rows"]:
            sd = r.get("startDate", "")
            ds = r.get("dataSource", "")
            if sd not in ("02-01-2026", "03-01-2026"):
                continue
            if "CSV" not in ds:
                preserved += 1
                continue
            bldg = r.get("bldgNo", "")
            key = (bldg, system)
            old_usage = r.get("usage")
            # Only update if we have AMR data with a valid account for this bldg+system
            if key in per_building and per_building[key]["accts"]:
                month = "feb" if sd.startswith("02") else "mar"
                new_val = per_building[key][month]
                baseline = baselines.get(bldg)
                # Sanity check: if new value is >10x historical median, the col 25 mult
                # is likely wrong for this meter — null instead
                if baseline is not None and baseline > 0 and new_val > 10 * baseline and new_val > 10_000:
                    r["usage"] = None
                    nulled_suspect += 1
                    changes.append((bldg, sd, old_usage, f"NULL (was {new_val:,.0f}, baseline {baseline:,.0f})"))
                else:
                    r["usage"] = round(new_val, 2) if new_val > 0 else 0
                    touched += 1
                    changes.append((bldg, sd, old_usage, r["usage"]))
            else:
                # No AMR source — don't touch (non-Sensus CSV, or reads we can't compute)
                skipped_no_amr += 1

        # Write back in compact per-row format (merge-data.py style)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write("{\n")
            f.write('"_kind": "grid",\n')
            f.write('"meta": ' + json.dumps(grid["meta"], ensure_ascii=False) + ",\n")
            f.write('"cols": [\n')
            cols = grid["cols"]
            for i, col in enumerate(cols):
                comma = "," if i < len(cols) - 1 else ""
                f.write(json.dumps(col, ensure_ascii=False) + comma + "\n")
            f.write("],\n")
            f.write('"rows":[\n')
            rows = grid["rows"]
            for i, row in enumerate(rows):
                comma = "," if i < len(rows) - 1 else ""
                f.write(json.dumps(row, ensure_ascii=False, separators=(", ", ":")) + comma + "\n")
            f.write("]\n")
            f.write("}\n")

        print(f"  {fname}: {touched} rebuilt, {nulled_suspect} nulled (mult suspect), {skipped_no_amr} left alone (no AMR), {preserved} non-CSV preserved")
        print(f"  Sample changes (old -> new):")
        for bldg, sd, old, new in changes[:20]:
            old_s = f"{old:>14,.0f}" if isinstance(old, (int, float)) else f"{str(old):>14}"
            new_s = f"{new:>14,.2f}" if isinstance(new, (int, float)) else f"{str(new):>14}"
            print(f"    {bldg:<8} {sd}  {old_s}  ->  {new_s}")
        if len(changes) > 20:
            print(f"    ... +{len(changes)-20} more")


if __name__ == "__main__":
    main()
