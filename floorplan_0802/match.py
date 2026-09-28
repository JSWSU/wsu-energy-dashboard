"""Match SkySpark zones in points.json to R-sheet room labels."""
import re

FLOOR_SYSTEMS = ("Ground Floor", "Mezzanine", "Floor-01", "Floor-02", "Penthouse")
ZONE_POINT_NAMES = {"zone temp", "TMP", "ZN TMP"}
ROOM_RE = re.compile(r"RM([GM]?\d+[A-Z]*)")
UNLOCATED_ALIASES = {"FPB.STAIRS"}


def zone_equips(points_json):
    have = {p["equip"] for p in points_json["points"] if p["name"] in ZONE_POINT_NAMES}
    return [e for e in points_json["equips"] if e.get("system") in FLOOR_SYSTEMS and e["name"] in have]


def room_key(equip):
    alias = equip.get("alias") or ""
    if alias in UNLOCATED_ALIASES:
        return None
    for src in (alias, equip["name"]):
        m = ROOM_RE.search(src)
        if m:
            return re.sub(r"^([GM]?)0+(?=\d)", r"\1", m.group(1))
    return None


def match_zones(zones, labels_by_system):
    located, unlocated = {}, []
    for e in zones:
        key = room_key(e)
        if key and key in labels_by_system.get(e["system"], set()):
            located.setdefault((e["system"], key), []).append(e["name"])
        else:
            unlocated.append({"equip": e["name"], "system": e["system"], "key": key})
    return located, unlocated
