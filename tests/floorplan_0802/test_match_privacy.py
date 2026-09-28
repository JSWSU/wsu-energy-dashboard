import json
import pytest
from floorplan_0802 import match, privacy
from conftest import POINTS


def E(name, alias=None, system="Floor-01"):
    return {"name": name, "alias": alias, "system": system}


def test_room_key_rules():
    assert match.room_key(E("FPB.L1-16A", "FPB.RM105")) == "105"
    assert match.room_key(E("FPB.G1A", "FPB.RMG05", "Ground Floor")) == "G5"
    assert match.room_key(E("WFCU.RMG19", None, "Ground Floor")) == "G19"
    assert match.room_key(E("FPB.G2", "FPB.STAIRS", "Ground Floor")) is None
    assert match.room_key(E("L2 RAD ZN1", None, "Floor-02")) is None


def test_match_uses_the_equipment_floor_only():
    zones = [E("A", "FPB.RM105"), E("B", "FPB.RM105", "Floor-02")]
    located, unlocated = match.match_zones(zones, {"Floor-01": {"105"}, "Floor-02": {"205"}})
    assert located == {("Floor-01", "105"): ["A"]}
    assert [u["equip"] for u in unlocated] == ["B"]


def test_real_points_file_counts():
    pj = json.load(open(POINTS, encoding="utf-8"))
    zones = match.zone_equips(pj)
    assert len(zones) >= 71
    names = {z["name"] for z in zones}
    assert {"FPB.L1-16A", "FPB.L1-16B"} <= names
    assert "GF RAD PMP01" not in names          # pumps are not zones


def _fp(rooms, extra=None):
    fp = {"floors": [{"system": "Floor-01", "walls": [], "glazing": [], "rooms": rooms}], "unlocated": []}
    fp.update(extra or {})
    return fp


def test_privacy_passes_zoned_rooms():
    privacy.check(_fp([{"label": "105", "zones": ["FPB.L1-16A"], "poly": [], "center": [0, 0]}]))
    privacy.check(_fp([{"label": "G1VS", "zones": ["EUH.RMG1VS"], "poly": [], "center": [0, 0]}]))


def test_privacy_blocks_unzoned_sensitive_label():
    with pytest.raises(privacy.PrivacyError, match="101EL"):
        privacy.check(_fp([{"label": "101EL", "zones": [], "poly": [], "center": [0, 0]}]))


def test_privacy_blocks_any_unzoned_room():
    with pytest.raises(privacy.PrivacyError, match="130"):
        privacy.check(_fp([{"label": "130", "zones": [], "poly": [], "center": [0, 0]}]))


def test_privacy_blocks_layer_names_and_pdf_path():
    with pytest.raises(privacy.PrivacyError, match="A-DOOR"):
        privacy.check(_fp([], {"note": "A-DOOR-SWNG"}))
    with pytest.raises(privacy.PrivacyError, match="pdf"):
        privacy.check(_fp([], {"source": "private/0802_r-sheets.pdf"}))
