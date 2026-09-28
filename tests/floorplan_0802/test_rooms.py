import numpy as np
import pytest
from floorplan_0802 import rooms
from floorplan_0802.extract import Sheet
import fitz


def _box_sheet(labels, extra=()):
    # two 40 x 40 pt rooms side by side, shared wall with a 10 pt gap
    w = [(10, 10, 90, 10), (90, 10, 90, 50), (90, 50, 10, 50), (10, 50, 10, 10),
         (50, 10, 50, 25), (50, 35, 50, 50)] + list(extra)
    return Sheet("R-3", "Floor-01", 1, w, [], w, labels, (100, 60), fitz.Identity)


def test_geodesic_split_two_seeds():
    mask = np.ones((5, 9), bool)
    mask[:, 4] = False
    mask[2, 4] = True            # one-pixel doorway
    own = rooms.geodesic_split(mask, [(2, 1), (2, 7)])
    assert own[0, 0] == 0 and own[0, 8] == 1
    assert (own[~mask] == -1).all()


def test_leaky_rooms_are_split_by_walking_distance():
    got = rooms.find_rooms(_box_sheet([("A", 30, 30), ("B", 70, 30)]))
    assert set(got) == {"A", "B"}
    a, b = got["A"]["area_ft2"], got["B"]["area_ft2"]
    assert abs(a - b) / max(a, b) < 0.2
    assert max(x for x, _ in got["A"]["poly_pt"]) < 56


def test_label_outside_the_building_is_rejected():
    got = rooms.find_rooms(_box_sheet([("A", 30, 30), ("OUT", 95, 55)]))
    assert "OUT" not in got


def test_real_room_105_shape(sheets):
    got = rooms.find_rooms(sheets[2])
    assert "105" in got
    # Room 105 measures about 44 ft x 58 ft on R-3 (about 2,550 sq ft)
    assert 1800 < got["105"]["area_ft2"] < 3200
    assert 100 < got["128"]["area_ft2"] < 1200


def _area_ft2(poly_pt):
    from floorplan_0802.extract import FT_PER_PT
    a = 0.0
    for (x1, y1), (x2, y2) in zip(poly_pt, poly_pt[1:] + poly_pt[:1]):
        a += x1 * y2 - x2 * y1
    return abs(a) / 2 * FT_PER_PT ** 2


def test_mezzanine_floor_excludes_open_to_below(sheets):
    mezz = sum(_area_ft2(p) for p in rooms.floor_polygons(sheets[1]))
    first = sum(_area_ft2(p) for p in rooms.floor_polygons(sheets[2]))
    assert 3000 < mezz < 8000          # R-2 gross 4,935 sq ft; most of the level is open to below
    assert 17000 < first < 23500       # R-3 gross 20,679 sq ft


def test_penthouse_enclosure_is_room_301(sheets):
    enc = rooms.enclosure_polygon(sheets[4], "301")
    assert enc is not None
    assert 2000 < _area_ft2(enc) < 4500   # R-5 gross 3,368 sq ft


def test_second_floor_open_area_is_outlined_on_its_own(sheets):
    second = sum(_area_ft2(p) for p in rooms.floor_polygons(sheets[3]))
    assert 17000 < second < 23500      # R-4 gross 21,387 sq ft; A-SPAC-OTBW outlines its open area
