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
