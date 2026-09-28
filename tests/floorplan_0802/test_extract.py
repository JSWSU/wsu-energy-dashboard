import copy
import pytest
from floorplan_0802 import extract


def test_five_sheets_in_order(sheets):
    assert [s.sheet for s in sheets] == ["R-1", "R-2", "R-3", "R-4", "R-5"]
    assert [s.system for s in sheets] == ["Ground Floor", "Mezzanine", "Floor-01", "Floor-02", "Penthouse"]
    assert sum(extract.GSF.values()) == 67805


def test_walls_and_labels_present(sheets):
    first = sheets[2]
    assert len(first.walls) > 100
    names = {n for n, _, _ in first.labels}
    assert {"105", "128", "130", "100"} <= names
    assert not names & {"0", "5", "10", "20"}


def test_display_lines_exclude_doors(sheets):
    # every display segment must come from a wall or glazing layer; seal has more lines
    for s in sheets[:4]:
        assert len(s.seal) > len(s.walls) + len(s.glazing)


def test_to_feet_room_105_is_east_of_room_130(sheets):
    first = sheets[2]
    pos = {n: extract.to_feet(first, x, y) for n, x, y in first.labels}
    assert pos["105"][0] > pos["130"][0]          # 105 east of 130 (R-3)
    assert pos["101"][1] > pos["120B"][1]         # 101 north of 120B (R-3)


def test_alignment_passes_on_real_sheets(sheets):
    extract.check_alignment(sheets)


def test_alignment_fails_when_a_sheet_moves(sheets):
    moved = copy.deepcopy(sheets)
    moved[1].walls = [(a + 30, b, c + 30, d) for a, b, c, d in moved[1].walls]  # 30 pt = 8.3 ft
    with pytest.raises(extract.AlignmentError, match="R-2"):
        extract.check_alignment(moved)


def test_alignment_fails_when_the_penthouse_moves_outside(sheets):
    # Final review Important 2: R-5 must sit inside the R-3 footprint
    moved = copy.deepcopy(sheets)
    moved[4].walls = [(a + 400, b, c + 400, d) for a, b, c, d in moved[4].walls]
    with pytest.raises(extract.AlignmentError, match="R-5"):
        extract.check_alignment(moved)


def test_alignment_fails_when_a_sheet_is_rotated_differently(sheets):
    moved = copy.deepcopy(sheets)
    moved[3].rotation = 90
    with pytest.raises(extract.AlignmentError, match="R-4"):
        extract.check_alignment(moved)
