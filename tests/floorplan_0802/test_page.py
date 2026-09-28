import json
import os
import socket
import subprocess
import sys
import time
import pytest
from playwright.sync_api import sync_playwright
from conftest import ROOT


def _free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


@pytest.fixture(scope="session")
def base_url():
    port = _free_port()
    proc = subprocess.Popen([sys.executable, "-m", "http.server", str(port)], cwd=ROOT,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.5)
    yield f"http://127.0.0.1:{port}/seh-energy.html"
    proc.terminate()


@pytest.fixture()
def page(base_url):
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-gl=angle", "--enable-webgl", "--ignore-gpu-blocklist"])
        pg = b.new_page(viewport={"width": 1440, "height": 1000})
        pg.errors = []
        pg.on("pageerror", lambda e: pg.errors.append(str(e)))
        pg.on("console", lambda m: m.type == "error" and pg.errors.append(m.text))
        pg.base_url = base_url
        yield pg
        b.close()


def _open(page, route_floorplan=None):
    if route_floorplan is not None:
        page.route("**/data/0802/floorplan.json", route_floorplan)
    page.goto(page.base_url, wait_until="networkidle")
    page.wait_for_function("window.SEH !== undefined", timeout=20000)


def test_floorplan_mode_and_no_errors_on_every_tab(page):
    _open(page)
    assert page.evaluate("SEH.mode") == "floorplan"
    for tab in ["energy", "meters", "points", "learn", "about", "explore"]:
        page.click(f'.nav-tab[data-tab="{tab}"]')
        page.wait_for_timeout(600)
    assert page.errors == []
    assert "67,805" in page.inner_text("header")


def test_room_105_is_in_east_half(page):
    _open(page)
    w = page.evaluate("SEH.roomWorld('105')")
    f = page.evaluate("SEH.footprint()")
    assert w is not None
    assert w["x"] > (f["minX"] + f["maxX"]) / 2


def test_fallback_to_schematic_when_file_missing(page):
    _open(page, lambda route: route.fulfill(status=404, body="not found"))
    assert page.evaluate("SEH.mode") == "schematic"
    assert "floor plan could not load" in page.inner_text("#sec-explore").lower()
    assert [e for e in page.errors if "404" not in e] == []


def test_room_with_no_data_renders_gray_without_errors(page):
    # Review Focus 2: move the slider to hour 0 where some zones have no data, hover every room
    _open(page)
    page.evaluate("document.getElementById('timeSlider').value = 0; document.getElementById('timeSlider').dispatchEvent(new Event('input'))")
    page.wait_for_timeout(400)
    for label in page.evaluate("SEH.labels()"):
        pos = page.evaluate(f"SEH.roomScreen('{label}')")
        if pos:
            page.mouse.move(pos["x"], pos["y"])
    assert page.errors == []


def test_first_floor_button_top_down_and_click_room_105(page):
    _open(page)
    page.click('.floor-btn[data-floor="Floor-01"]')
    page.wait_for_timeout(800)
    pos = page.evaluate("SEH.roomScreen('105')")
    assert pos is not None
    page.mouse.click(pos["x"], pos["y"])
    page.wait_for_timeout(500)
    assert page.inner_text("#detailTitle") == "Room 105"
    assert page.locator("#detailBody [data-zone]").count() == 2
    assert page.evaluate("SEH.roomScreen('230J')") is None      # second floor hidden
    assert page.errors == []


def test_slider_updates_colors_on_focused_floor(page):
    # Review Focus 3
    _open(page)
    page.evaluate("SEH.focusFloor('Floor-01')")
    a = page.evaluate("SEH.roomColor('105')")
    page.evaluate("const s=document.getElementById('timeSlider'); s.value=Math.floor(s.max/2); s.dispatchEvent(new Event('input'))")
    b = page.evaluate("SEH.roomColor('105')")
    assert a != b


def test_new_zone_missing_from_floorplan_still_shows(page):
    # Review Focus 1: drop FPB.L1-16B from the file; the page must put it in the First Floor strip
    def route(r):
        fp = json.load(open(os.path.join(ROOT, "data", "0802", "floorplan.json"), encoding="utf-8"))
        for f in fp["floors"]:
            for room in f["rooms"]:
                room["zones"] = [z for z in room["zones"] if z != "FPB.L1-16B"]
        r.fulfill(status=200, content_type="application/json", body=json.dumps(fp))
    _open(page, route)
    assert "FPB.L1-16B" in page.evaluate("SEH.stripNames('Floor-01')")


def test_dark_mode_walls_visible(page):
    # Review Focus 5: wall pixels must differ from the dark scene background
    _open(page)
    page.click("#darkToggle")
    page.evaluate("SEH.focusFloor('Floor-01')")
    page.wait_for_timeout(800)
    assert page.evaluate("SEH.wallContrast()") > 40


def test_room_whose_zone_left_points_json_does_not_break_the_page(page):
    # Final review Important 1: rename TF.RM107 in points.json; click Room 107, then move the slider
    def route(r):
        pj = json.load(open(os.path.join(ROOT, "data", "0802", "points.json"), encoding="utf-8"))
        for e in pj["equips"]:
            if e["name"] == "TF.RM107":
                e["name"] = "TF.RM107X"
        for p in pj["points"]:
            if p["equip"] == "TF.RM107":
                p["equip"] = "TF.RM107X"
        r.fulfill(status=200, content_type="application/json", body=json.dumps(pj))
    page.route("**/data/0802/points.json", route)
    _open(page)
    page.evaluate("SEH.focusFloor('Floor-01')")
    page.wait_for_timeout(600)
    pos = page.evaluate("SEH.roomScreen('107')")
    assert pos is not None
    page.mouse.click(pos["x"], pos["y"])
    page.evaluate("const s=document.getElementById('timeSlider'); s.value=3; s.dispatchEvent(new Event('input'))")
    page.click("#darkToggle")
    assert page.errors == []


def test_mezzanine_slab_follows_the_sheet_not_the_footprint(page):
    # R-2: most of the level is OPEN TO BELOW, so its slab must be far smaller than the First Floor's
    _open(page)
    mezz, first = page.evaluate("[SEH.slabArea('Mezzanine'), SEH.slabArea('Floor-01')]")
    assert 3000 < mezz < 0.35 * first


def test_penthouse_is_named_roof_and_has_its_own_enclosure(page):
    _open(page)
    assert page.evaluate("SEH.floorName('Penthouse')") == "Roof and mechanical penthouse"
    assert 2000 < page.evaluate("SEH.enclosureArea()") < 4500


def test_walls_cast_no_shadows_on_the_ground(page):
    _open(page)
    assert page.evaluate("SEH.wallShadows()") is False


def test_time_steps_with_a_room_selected_do_not_rebuild_the_chart(page):
    # stutter: every slider or Play step used to destroy and rebuild the room chart (12.9 ms vs 1.0 ms)
    _open(page)
    page.evaluate("SEH.focusFloor('Floor-01')")
    page.wait_for_timeout(500)
    pos = page.evaluate("SEH.roomScreen('105')")
    page.mouse.click(pos["x"], pos["y"])
    page.wait_for_timeout(300)
    before = page.evaluate("SEH.chartBuilds()")
    page.evaluate("const s=document.getElementById('timeSlider'); for (let i=0;i<20;i++){ s.value=i; s.dispatchEvent(new Event('input')); }")
    assert page.evaluate("SEH.chartBuilds()") == before
    assert page.inner_text("#detailTitle") == "Room 105"


def test_no_coplanar_or_see_through_depth_writing_surfaces(page):
    # flicker: grass and Ground Floor slab were both at y = -0.05; transparent slabs wrote depth
    _open(page)
    d = page.evaluate("SEH.depthLayout()")
    assert d["groundY"] < d["lowestSlabY"] - 0.2
    assert d["roomGap"] >= 0.1
    assert d["transparentDepthWriters"] == []


def test_play_blends_colors_between_hours(page):
    # Play jumps: a half-hour position must give a color between the two hourly colors
    _open(page)
    r = page.evaluate("SEH.blendCheck('105')")
    assert r is not None, "no hour pair with different colors found"
    lo, mid, hi = r
    for a, m, b in zip(lo, mid, hi):
        assert min(a, b) - 1 <= m <= max(a, b) + 1
    assert mid != lo and mid != hi


def test_equipment_sits_against_the_building(page):
    _open(page)
    e = page.evaluate("SEH.equipLayout()")
    f = page.evaluate("SEH.footprint()")
    assert f["maxX"] <= e["riserX"] <= f["maxX"] + 4          # risers on the east face
    assert e["doasY"] >= e["roofY"]                             # DOAS-01 on the roof
    assert f["minX"] <= e["doasX"] <= f["maxX"]
    assert f["maxX"] < e["pumpsMinX"] and e["pumpsMaxX"] < f["maxX"] + 25
