import os
import sys
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
PDF = os.path.join(ROOT, "private", "0802_r-sheets.pdf")
POINTS = os.path.join(ROOT, "data", "0802", "points.json")


@pytest.fixture(scope="session")
def sheets():
    if not os.path.exists(PDF):
        pytest.skip("private R-sheets PDF not present")
    from floorplan_0802 import extract
    return extract.load_sheets(PDF)
