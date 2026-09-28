"""Build data/0802/floorplan.json from the private 0802 R-sheets PDF.

Run by hand when the R-sheets change:  py build_0802_floorplan.py
The PDF stays in private/ (gitignored). Output passes privacy.check before it is written.
"""
import argparse
import datetime
import json
import os

from floorplan_0802 import extract, match, privacy, rooms

HERE = os.path.dirname(os.path.abspath(__file__))
PDF = os.path.join(HERE, "private", "0802_r-sheets.pdf")
POINTS = os.path.join(HERE, "data", "0802", "points.json")
OUT = os.path.join(HERE, "data", "0802", "floorplan.json")
SQUARE_FT = 8.0


def _ft_seg(sheet, seg):
    a = extract.to_feet(sheet, seg[0], seg[1])
    b = extract.to_feet(sheet, seg[2], seg[3])
    return [a[0], a[1], b[0], b[1]]


def build(pdf=PDF, points=POINTS):
    sheets = extract.load_sheets(pdf)
    extract.check_alignment(sheets)
    pj = json.load(open(points, encoding="utf-8"))
    zones = match.zone_equips(pj)
    labels_by_system = {s.system: {n for n, _, _ in s.labels} for s in sheets}
    located, unlocated = match.match_zones(zones, labels_by_system)

    floors, traced, squares, per_floor = [], 0, 0, {}
    for s in sheets:
        if not s.walls:
            raise RuntimeError(f"{s.sheet}: zero wall segments")
        shapes = rooms.find_rooms(s)
        label_pt = {}
        for n, x, y in s.labels:
            label_pt.setdefault(n, (x, y))
        out_rooms = []
        for (system, label), names in sorted(located.items()):
            if system != s.system:
                continue
            cx, cy = extract.to_feet(s, *label_pt[label])
            if label in shapes:
                poly = [list(extract.to_feet(s, x, y)) for x, y in shapes[label]["poly_pt"]]
                traced += 1
                ok = True
            else:
                h = SQUARE_FT / 2
                poly = [[cx - h, cy - h], [cx + h, cy - h], [cx + h, cy + h], [cx - h, cy + h]]
                squares += 1
                ok = False
            out_rooms.append({"label": label, "poly": poly, "center": [cx, cy], "zones": sorted(names), "traced": ok})
        per_floor[s.system] = len(out_rooms)
        floors.append({"system": s.system, "sheet": s.sheet, "gsf": s.gsf,
                       "walls": [_ft_seg(s, g) for g in s.walls],
                       "glazing": [_ft_seg(s, g) for g in s.glazing],
                       "rooms": out_rooms})

    fp = {"generated": datetime.datetime.now().astimezone().isoformat(timespec="minutes"),
          "source": "WSU Facilities R-sheets 0802, plotted 11/20/2025 and 11/21/2025",
          "units": "ft", "gsfTotal": sum(extract.GSF.values()), "floors": floors,
          "unlocated": [{"equip": u["equip"], "system": u["system"]} for u in unlocated]}
    privacy.check(fp)
    report = {"zones": len(zones), "located": sum(len(v) for v in located.values()),
              "unlocated": len(unlocated), "rooms_traced": traced, "rooms_square": squares,
              "per_floor": per_floor, "unlocated_list": unlocated}
    return fp, report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", default=PDF)
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    fp, rep = build(a.pdf)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(fp, f, separators=(",", ":"))
    print(f"zones {rep['zones']}, located {rep['located']}, unlocated {rep['unlocated']}")
    print(f"rooms traced {rep['rooms_traced']}, rooms shown as 8 ft squares {rep['rooms_square']}")
    print("rooms per floor:", rep["per_floor"])
    for u in rep["unlocated_list"]:
        print(f"  unlocated: {u['equip']} ({u['system']}, key {u['key']})")
    print("wrote", a.out, os.path.getsize(a.out) // 1024, "KB")


if __name__ == "__main__":
    main()
