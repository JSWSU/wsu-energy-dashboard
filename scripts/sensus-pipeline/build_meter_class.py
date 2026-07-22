"""Build data/meter_class.json: per-meter collection-class, cross-validated.

Classes: BACnet, Calsense, AMR (Sensus radio), Manual (route technician),
Conflict (sources disagree or a CSV meter has no workbook match).

Sources (no assumptions; disagreement => Conflict, never a guess):
  1. ByMeter Altura report CSVs: Meter + Data Source columns.
     (CS3000) in the meter name  -> Calsense
     Data Source == SkySpark     -> BACnet-connected
     Data Source == CSV          -> CSV-imported (split by source 2)
  2. Meter reads workbook v5 REPAIRED: Route column per meter.
     Route == Sensus                          -> AMR
     Route in {BACnet, Skyspark, CalSense}    -> Connected
     Route is a letter route (A-T, B-D, ...)  -> Manual
     Reference number family corroborates (200xxx Sensus, 5xx000 BACnet).

Usage:
  py build_meter_class.py
  (paths are fixed below; re-run any time inputs change; output is replaced)
"""
import csv
import json
import re
from pathlib import Path

DL = Path(r"C:\Users\john.slagboom\Downloads")
BYMETER = [DL / f"ByMeter_2yr_AlturaMeterReports{n}.csv"
           for n in ("DomesticWater", "IrrigationWater", "WellWater")]
V5 = DL / "Meter Reads since Jan 2026 - REPAIRED-v5.csv"
OUT = Path(r"C:\Users\john.slagboom\Desktop\Git\data\meter_class.json")

CONNECTED_ROUTES = {"BACNET", "SKYSPARK", "CALSENSE"}


def norm_key(name):
    """Normalize a meter name across sources: strip W/, markers, suffix text,
    uppercase, and zero-pad the leading building number to 4 digits."""
    if not name:
        return None
    s = name.strip().upper()
    if s.startswith("W/"):
        s = s[2:]
    s = s.replace("(CSV)", "").replace("(CS3000)", "").strip()
    s = s.split()[0] if s.split() else s
    m = re.match(r"^(\d{1,3})(?=[A-Z_])(.*)$", s)
    if m and len(m.group(1)) < 4:
        s = m.group(1).zfill(4) + m.group(2)
    return s or None


def main():
    # Source 1: SkySpark side (ByMeter exports)
    sky = {}  # key -> {cls, bldg, name, svc, src}
    for p in BYMETER:
        if not p.exists():
            print(f"MISSING input: {p}")
            continue
        with open(p, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                meter = r.get("Meter") or ""
                k = norm_key(meter)
                if not k:
                    continue
                if "(CS3000)" in meter:
                    cls = "Calsense"
                elif (r.get("Data Source") or "").strip() == "CSV":
                    cls = "CSV"
                else:
                    cls = "BACnet"
                prev = sky.get(k)
                if prev and prev["cls"] != cls:
                    prev["cls"] = "MIXED:" + prev["cls"] + "/" + cls
                    continue
                sky[k] = {"cls": cls, "bldg": r.get("Building Number") or "",
                          "name": r.get("Building Name") or "",
                          "svc": (r.get("Service") or "").strip()}

    # Source 2: meter reads workbook v5 (positional; duplicate Month headers)
    v5 = {}  # key -> {routes: set, refs: set}
    if V5.exists():
        with open(V5, encoding="utf-8-sig", newline="") as f:
            rd = csv.reader(f)
            header = next(rd, None)
            for row in rd:
                if len(row) < 25:
                    continue
                ref, route, name = row[3].strip(), row[4].strip(), row[24].strip()
                k = norm_key(name)
                if not k:
                    continue
                e = v5.setdefault(k, {"routes": set(), "refs": set()})
                if route:
                    e["routes"].add(route.upper())
                if ref:
                    e["refs"].add(ref)
    else:
        print(f"MISSING input: {V5}")

    def v5_class(e):
        routes = e["routes"]
        kinds = set()
        for rt in routes:
            if rt == "SENSUS":
                kinds.add("AMR")
            elif rt in CONNECTED_ROUTES:
                kinds.add("Connected")
            else:
                kinds.add("Manual")
        return kinds, routes

    out = {}
    stats = {}
    conflicts = []
    for k in sorted(set(sky) | set(v5)):
        s = sky.get(k)
        e = v5.get(k)
        entry = {"bldg": s["bldg"] if s else "", "svc": s["svc"] if s else "",
                 "route": ", ".join(sorted(e["routes"])) if e else "",
                 "refs": ", ".join(sorted(e["refs"])) if e else ""}
        if s and s["cls"].startswith("MIXED:"):
            entry.update(cls="Conflict", note="SkySpark sources disagree: " + s["cls"][6:])
        elif s and s["cls"] in ("BACnet", "Calsense"):
            # A connected meter can legitimately ALSO sit on a manual billing
            # route (technician records the same register monthly). That is a
            # dual-path fact, not a source disagreement.
            entry.update(cls=s["cls"])
            if e:
                kinds, routes = v5_class(e)
                if "AMR" in kinds:
                    entry.update(cls="Conflict",
                                 note=f"SkySpark says {s['cls']} but workbook route includes Sensus")
                elif "Manual" in kinds:
                    entry["note"] = "also recorded on manual route " + entry["route"]
        elif s and s["cls"] == "CSV":
            if not e:
                entry.update(cls="Conflict", note="CSV-imported in SkySpark but no match in meter reads workbook")
            else:
                kinds, routes = v5_class(e)
                if kinds == {"AMR"}:
                    entry.update(cls="AMR")
                elif kinds == {"Manual"}:
                    entry.update(cls="Manual")
                else:
                    entry.update(cls="Conflict",
                                 note=f"workbook routes ambiguous for a CSV meter: {entry['route']}")
        elif e:  # v5 only
            kinds, routes = v5_class(e)
            if len(kinds) == 1:
                entry.update(cls={"Connected": "BACnet"}.get(next(iter(kinds)), next(iter(kinds))),
                             note="no SkySpark point (v5 only)")
            else:
                entry.update(cls="Conflict", note=f"multiple route kinds in workbook: {entry['route']}")
        else:
            continue
        out[k] = entry
        stats[entry["cls"]] = stats.get(entry["cls"], 0) + 1
        if entry["cls"] == "Conflict":
            conflicts.append((k, entry.get("note", "")))

    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8", newline="\n")
    print(f"wrote {OUT} with {len(out)} meters")
    print("class counts:", dict(sorted(stats.items())))
    print(f"conflicts ({len(conflicts)}):")
    for k, note in conflicts[:40]:
        print("  ", k, "|", note)
    if len(conflicts) > 40:
        print(f"   ... and {len(conflicts) - 40} more")


if __name__ == "__main__":
    main()
