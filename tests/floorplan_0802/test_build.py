import json
import os
import subprocess
import sys
import pytest
from conftest import ROOT, PDF, POINTS


@pytest.fixture(scope="module")
def built():
    if not os.path.exists(PDF):
        pytest.skip("private R-sheets PDF not present")
    sys.path.insert(0, ROOT)
    import build_0802_floorplan as b
    return b.build(PDF, POINTS)


def test_counts(built):
    fp, rep = built
    assert rep["zones"] >= 71
    assert rep["located"] >= 54
    assert [f["system"] for f in fp["floors"]] == ["Ground Floor", "Mezzanine", "Floor-01", "Floor-02", "Penthouse"]
    assert fp["gsfTotal"] == 67805
    assert all(len(f["walls"]) > 20 for f in fp["floors"])


def test_room_105(built):
    fp, _ = built
    first = next(f for f in fp["floors"] if f["system"] == "Floor-01")
    r = next(r for r in first["rooms"] if r["label"] == "105")
    assert sorted(r["zones"]) == ["FPB.L1-16A", "FPB.L1-16B"]
    assert r["traced"] is True
    xs = [x for f in [first] for w in f["walls"] for x in (w[0], w[2])]
    assert r["center"][0] > (min(xs) + max(xs)) / 2        # east half


def test_every_located_zone_is_in_a_room_or_unlocated(built):
    fp, rep = built
    in_rooms = [z for f in fp["floors"] for r in f["rooms"] for z in r["zones"]]
    assert len(in_rooms) == len(set(in_rooms)) == rep["located"]
    assert len(fp["unlocated"]) == rep["unlocated"]
    assert rep["located"] + rep["unlocated"] == rep["zones"]


def test_cli_writes_file_and_passes_privacy(tmp_path):
    if not os.path.exists(PDF):
        pytest.skip("private R-sheets PDF not present")
    out = tmp_path / "fp.json"
    res = subprocess.run([sys.executable, os.path.join(ROOT, "build_0802_floorplan.py"), "--out", str(out)],
                         capture_output=True, text=True, cwd=ROOT)
    assert res.returncode == 0, res.stderr
    assert "located" in res.stdout
    txt = out.read_text(encoding="utf-8")
    assert "A-DOOR" not in txt and ".pdf" not in txt


def test_floors_carry_floor_outlines_and_penthouse_enclosure(built):
    fp, _ = built
    for f in fp["floors"]:
        assert f["floor"], f["system"]
    pent = next(f for f in fp["floors"] if f["system"] == "Penthouse")
    assert len(pent["enclosure"]) >= 4
    assert "label" not in json.dumps(pent["enclosure"])
