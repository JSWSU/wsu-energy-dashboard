"""Fold the ByMeter Altura report CSV exports into the dashboard data files.

Reads the three ByMeter exports (Domestic Water, Irrigation Water, Well Water;
columns: id, Building Number, Building Name, Data Source, Meter, Service, Unit,
Start Date, End Date, Usage; gallons) and:

- appends one row PER METER-MONTH to data/domestic_water.json and
  data/irrigation.json, tagged "byMeter": true
- writes data/well_water.json (all per-meter, byMeter: true)

Idempotent: existing byMeter rows for the same (bldgNo, meters, service,
startDate) are replaced on re-run. Building-total rows are left untouched;
the dashboard prefers byMeter rows at render time for any building-month
they cover, so no rows are deleted and the weekly merge pipeline is
unaffected.

Usage:  py bymeter_to_dashboard.py <DomesticWater.csv> <IrrigationWater.csv> <WellWater.csv>
        (any subset of files, any order; service comes from the Service column)
"""
import csv
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

DATA = Path(r"C:\Users\john.slagboom\Desktop\Git\data")
FILE_FOR_SERVICE = {
    "Domestic Water": "domestic_water.json",
    "Irrigation Water": "irrigation.json",
    "Well Water": "well_water.json",
}


def write_grid(path, grid):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("{\n")
        f.write('"_kind": "grid",\n')
        f.write('"meta": ' + json.dumps(grid["meta"], ensure_ascii=False) + ",\n")
        f.write('"cols": [\n')
        cols = grid["cols"]
        for i, col in enumerate(cols):
            f.write(json.dumps(col, ensure_ascii=False) + ("," if i < len(cols) - 1 else "") + "\n")
        f.write("],\n")
        f.write('"rows":[\n')
        rows = grid["rows"]
        for i, row in enumerate(rows):
            f.write(json.dumps(row, ensure_ascii=False, separators=(", ", ":")) + ("," if i < len(rows) - 1 else "") + "\n")
        f.write("]\n}\n")


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    new_by_service = {}
    for arg in argv:
        with open(arg, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                if not r.get("Building Number") or not r.get("Start Date") or not r.get("Service"):
                    continue
                unit = (r.get("Unit") or "gal").strip()
                factor = {"gal": 1.0, "ft³": 7.48051948, "kgal": 1000.0}.get(unit)
                if factor is None:
                    print(f"SKIP unknown unit {unit!r} for {r.get('Meter')}")
                    continue
                svc = r["Service"].strip()
                u = r.get("Usage")
                try:
                    usage = float(u) * factor if u not in ("", None) else None
                except ValueError:
                    usage = None
                new_by_service.setdefault(svc, []).append({
                    "bldgNo": r["Building Number"],
                    "bldgName": r.get("Building Name") or "",
                    "dataSource": r.get("Data Source") or "ByMeter",
                    "meters": r.get("Meter") or "",
                    "service": svc,
                    "unit": "gal",
                    "startDate": r["Start Date"],
                    "endDate": r.get("End Date") or r["Start Date"],
                    "usage": usage,
                    "byMeter": True,
                })

    for svc, new_rows in new_by_service.items():
        fname = FILE_FOR_SERVICE.get(svc)
        if not fname:
            print(f"SKIP unknown service {svc!r} ({len(new_rows)} rows)")
            continue
        path = DATA / fname
        if path.exists():
            shutil.copy2(path, path.with_suffix(f".json.bymeter.{ts}.bak"))
            grid = json.load(open(path, encoding="utf-8"))
        else:
            grid = {"_kind": "grid", "meta": {"ver": "3.0"},
                    "cols": [{"name": n} for n in
                             ["bldgNo", "bldgName", "dataSource", "meters", "service",
                              "unit", "startDate", "endDate", "usage", "byMeter"]],
                    "rows": []}
        keys_new = {(r["bldgNo"], r["meters"], r["service"], r["startDate"]) for r in new_rows}
        kept = [r for r in grid["rows"]
                if not (r.get("byMeter") and
                        (r.get("bldgNo"), r.get("meters"), r.get("service"), r.get("startDate")) in keys_new)]
        replaced = len(grid["rows"]) - len(kept)
        grid["rows"] = kept + new_rows
        write_grid(path, grid)
        print(f"{fname}: +{len(new_rows)} byMeter rows ({replaced} replaced), total {len(grid['rows'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
