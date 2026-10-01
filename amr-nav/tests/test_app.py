"""Browser test for the AMR Route Guide (Playwright, headless Chromium).

Run from the repository root while a static server serves the repository root:
    py -m http.server 41999 --bind 127.0.0.1
    py amr-nav\\tests\\test_app.py
Only the original reroute check (section 2) calls the real OSRM server. New checks intercept it.
Interception of route.json and the page uses ctx.route (context level), because page.route does not see the
requests that the service worker makes. A request that a handler lets through ignores set_offline, so the
offline steps remove the handler first.
"""
import base64
import json
import math
import os
import re
import sys
import time

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:41999/amr-nav/"
SHOTS = os.path.join(os.environ.get("TEMP", "."), "amr-cycle", "app-test-shots")
os.makedirs(SHOTS, exist_ok=True)
DEPOT = {"latitude": 46.728993, "longitude": -117.144701, "accuracy": 6}
errors = []
results = []


def check(name, ok, detail=""):
    detail = " ".join(str(detail).split())          # one line per check
    results.append((name, bool(ok), detail))
    print(("PASS " if ok else "FAIL ") + name + (" | " + detail if detail else ""))


def attach(page):
    page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type in ("error", "warning") else None)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))


def text(page, sel):
    return page.locator(sel).inner_text().strip()


def wait_for(page, fn, timeout=60, step=0.5):
    t0 = time.time()
    while time.time() - t0 < timeout:
        v = fn()
        if v:
            return v
        time.sleep(step)
    return None


def pump_until(page, fn, timeout=15, step=0.25):
    """Like wait_for, but lets Playwright deliver route handlers and events while it waits."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        if fn():
            return True
        page.wait_for_timeout(int(step * 1000))
    return False


def hav_m(a, b):
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(b[1] - a[1]) / 2) ** 2
    return 2 * 6371008.8 * math.asin(math.sqrt(h))


def far_point(geom, min_m=250):
    """A point at least min_m from every vertex of geom (north of its northernmost vertex)."""
    top = max(geom, key=lambda q: q[0])
    far = [top[0] + 0.0030, top[1]]
    while min(hav_m(far, q) for q in geom) < min_m:
        far[0] += 0.0005
    return far


OSRM_URL = re.compile(r"https://routing\.openstreetmap\.de/")
ROUTE_URL = re.compile(r"/amr-nav/route\.json(\?.*)?$")
PAGE_URL = re.compile(r"/amr-nav/(index\.html)?(\?.*)?$")
TILE_URL = re.compile(r"https://tile\.openstreetmap\.org/")
PNG_1PX = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
# remembers the AbortSignal of every reroute request, so a test can see whether the app ended it
RECORD_OSRM_SIGNALS = """
window.__osrmSignals = [];
const __f = window.fetch.bind(window);
window.fetch = (u, o) => { if (String(u).includes('routing.openstreetmap.de')) window.__osrmSignals.push(o && o.signal); return __f(u, o); };
"""


ROUTE_TEXT = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "route.json"), "rb").read().decode("utf-8")
ROUTE_BUILT = json.loads(ROUTE_TEXT)["built"]


def fnv1a_py(s):
    """32-bit FNV-1a over the UTF-16 code units of s, as 8 hex digits (the same as the page's fnv1a)."""
    b = s.encode("utf-16-le")
    h = 0x811C9DC5
    for i in range(0, len(b), 2):
        h = ((h ^ (b[i] | (b[i + 1] << 8))) * 0x01000193) & 0xFFFFFFFF
    return "%08x" % h


def route_editor(state):
    """Handler for ctx.route(ROUTE_URL, ...). state['edit'] is None (pass the request on) or a function that
    rewrites the route.json text. The rewritten text is kept in state['served']. The service worker's own
    requests reach this handler too, because the route is set on the context."""
    def handler(route):
        edit = state["edit"]
        if edit is None:
            route.continue_()
            return
        body = edit(route.fetch().text())
        state["served"] = body
        route.fulfill(status=200, content_type="application/json", body=body)
    return handler


def sw_controls(pg, timeout=20):
    return wait_for(pg, lambda: pg.evaluate("() => navigator.serviceWorker && navigator.serviceWorker.controller ? 1 : 0"), timeout=timeout)


def osrm_reply(geom):
    """A valid OSRM route reply that follows geom (lat, lon pairs)."""
    coords = [[p[1], p[0]] for p in geom]
    steps = [
        {"geometry": {"coordinates": coords}, "maneuver": {"type": "depart", "modifier": "", "location": coords[0], "bearing_after": 0},
         "name": "Test Road", "ref": "", "distance": 100, "duration": 20},
        {"geometry": {"coordinates": [coords[-1]]}, "maneuver": {"type": "arrive", "modifier": "", "location": coords[-1], "bearing_after": 0},
         "name": "", "ref": "", "distance": 0, "duration": 0},
    ]
    return {"code": "Ok", "routes": [{"legs": [{"distance": 100, "duration": 20, "steps": steps}]}]}


def release(route, body):
    route.fulfill(status=200, content_type="application/json", headers={"access-control-allow-origin": "*"}, body=json.dumps(body))


ROUTE = json.loads(ROUTE_TEXT)
EARTH = 6371008.8
# keeps what the app speaks, so a test can read it (the real speech engine is not needed)
CAPTURE_SPEECH = """
window.__spoken = [];
try { speechSynthesis.speak = (u) => { window.__spoken.push(u.text); }; speechSynthesis.cancel = () => {}; } catch (e) {}
"""


class Path:
    """A leg geometry in the app's local metres (flat map around its first point), to place test fixes along it."""

    def __init__(self, geom):
        self.geom = geom
        self.k = math.cos(math.radians(geom[0][0]))
        self.xy = [(math.radians(p[1]) * EARTH * self.k, math.radians(p[0]) * EARTH) for p in geom]
        self.cum = [0.0]
        for i in range(1, len(self.xy)):
            self.cum.append(self.cum[-1] + math.hypot(self.xy[i][0] - self.xy[i - 1][0], self.xy[i][1] - self.xy[i - 1][1]))
        self.total = self.cum[-1]

    def to_ll(self, q):
        return [math.degrees(q[1] / EARTH), math.degrees(q[0] / (EARTH * self.k))]

    def at(self, s):
        """The point (x, y) at distance s along the path."""
        s = max(0.0, min(self.total, s))
        i = 0
        while i < len(self.cum) - 2 and self.cum[i + 1] < s:
            i += 1
        t = (s - self.cum[i]) / ((self.cum[i + 1] - self.cum[i]) or 1.0)
        a, b = self.xy[i], self.xy[i + 1]
        return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)

    def ll(self, s, dx=0.0, dy=0.0):
        """The point at s along the path, moved dx metres east and dy metres north (to place a fix off the line)."""
        q = self.at(s)
        return self.to_ll((q[0] + dx, q[1] + dy))

    def bearing(self, s):
        """The direction of travel at s in degrees (0 north, 90 east)."""
        a, b = self.at(s - 1), self.at(s + 1)
        return (math.degrees(math.atan2(b[0] - a[0], b[1] - a[1])) + 360) % 360

    def nearest(self, q, s_min=0.0, s_max=None):
        """(distance, point) of the point of the path nearest to q, looking only at the part from s_min to s_max."""
        best = (1e18, None)
        for i in range(len(self.xy) - 1):
            if self.cum[i + 1] < s_min or (s_max is not None and self.cum[i] > s_max):
                continue
            a, b = self.xy[i], self.xy[i + 1]
            dx, dy = b[0] - a[0], b[1] - a[1]
            l2 = dx * dx + dy * dy
            t = max(0.0, min(1.0, ((q[0] - a[0]) * dx + (q[1] - a[1]) * dy) / l2)) if l2 else 0.0
            pt = (a[0] + t * dx, a[1] + t * dy)
            d = math.hypot(q[0] - pt[0], q[1] - pt[1])
            if d < best[0]:
                best = (d, pt)
        return best

    def side_point(self, s, dist):
        """A point dist metres (plus or minus 2) to the side of the path at s, with no other part of the path nearer. None if not found."""
        a, b, q = self.at(s - 1), self.at(s + 1), self.at(s)
        n = math.hypot(b[0] - a[0], b[1] - a[1])
        nx, ny = -(b[1] - a[1]) / n, (b[0] - a[0]) / n
        for sign in (1, -1):
            c = (q[0] + sign * dist * nx, q[1] + sign * dist * ny)
            if abs(self.nearest(c)[0] - dist) <= 2:
                return self.to_ll(c)
        return None


def toward(P, s, s_min, s_max, frac):
    """The path point at s moved frac of the way to the nearest point of the same path between s_min and s_max
    (the other lane of an out-and-back road). Returns (lat/lon, distance between the lanes here)."""
    q = P.at(s)
    d, pt = P.nearest(q, s_min, s_max)
    return P.to_ll((q[0] + frac * (pt[0] - q[0]), q[1] + frac * (pt[1] - q[1]))), d


def feed(pg, ll, acc=5, speed=0, heading=None, t=None):
    """Hand one fix to the app's own onFix (the geolocation mock cannot set speed or the time) and return S.nav.along.
    speed None is a device that sends no speed; t is the fix time in ms (now, when not given)."""
    return pg.evaluate("""(a) => { onFix({lat: a[0], lon: a[1], acc: a[2], speed: a[3], heading: a[4], t: a[5] == null ? Date.now() : a[5]});
        return S.nav ? S.nav.along : null; }""", [ll[0], ll[1], acc, speed, heading, t])


# a GPS that never sends a fix: the app's own GPS code runs (no simulator), and only the fixes a test feeds arrive
QUIET_GPS = "Geolocation.prototype.watchPosition = function () { return 1; }; Geolocation.prototype.clearWatch = function () {};"


def guidance_page(br, sim=True, init=None):
    """A started app. sim: the simulator page (?sim=1 has no GPS watch). Otherwise the app's real GPS code runs with a GPS that
    never sends a fix. Either way only the fixes a test feeds arrive. init: one more script that runs before the page."""
    ctx = br.new_context(viewport={"width": 800, "height": 1280}, geolocation=DEPOT, permissions=["geolocation"])
    ctx.route(OSRM_URL, lambda route: release(route, {"code": "NoRoute"}))      # a reroute must never reach the real server
    pg = ctx.new_page()
    attach(pg)
    pg.add_init_script(CAPTURE_SPEECH)
    pg.add_init_script(RECORD_OSRM_SIGNALS)                                      # window.__osrmSignals has one entry per reroute request
    if not sim:
        pg.add_init_script(QUIET_GPS)
    if init:
        pg.add_init_script(init)
    pg.goto(BASE + ("?sim=1&reset=1" if sim else "?reset=1"))
    pg.wait_for_selector("#startBtns button", timeout=20000)
    pg.click("#startBtns button")
    pg.wait_for_timeout(800)
    return ctx, pg


def tap(pg, sel):
    """Click the first visible element that matches sel. Returns False at once when there is none, so a check fails
    instead of the run stopping on a wait."""
    loc = pg.locator(sel)
    for i in range(loc.count()):
        if loc.nth(i).is_visible():
            loc.nth(i).click()
            return True
    return False


def start_btns(pg):
    return pg.evaluate("() => [...document.querySelectorAll('#startBtns button')].map(b => b.textContent)")


def opened(pg, timeout=12000):
    """True when the start screen buttons appear (the route loaded), False when they do not."""
    try:
        pg.wait_for_selector("#startBtns button", timeout=timeout)
        return True
    except Exception:
        return False


def state_of(pg):
    return pg.evaluate("() => ({waiting: S.waiting, leg: S.legIdx, passed: Object.keys(S.passed || {}), done: Object.keys(S.done), skipped: Object.keys(S.skipped)})")


def dom(pg, sel, what="e.textContent.trim()"):
    """A value read from the first element that matches sel, or None when there is none."""
    return pg.evaluate("(s) => { const e = document.querySelector(s); return e ? " + what + " : null; }", sel)


def reroute_case(br, mode):
    """Drive off route on leg 0 with routing.openstreetmap.de held, then finish the scenario.
    mode 'apply': release the reply with the leg unchanged.
    mode 'stale': move to leg 1 with the app's own setLeg, release the reply, feed a fix at the start of leg 1.
    mode 'timeout': shorten the timeout, never reply, see whether the app ends the request."""
    ctx = br.new_context(viewport={"width": 800, "height": 1280}, geolocation=DEPOT, permissions=["geolocation"])
    held = []
    ctx.route(OSRM_URL, lambda route: held.append(route))
    pg = ctx.new_page()
    attach(pg)
    pg.add_init_script(RECORD_OSRM_SIGNALS)
    pg.goto(BASE + "?reset=1")
    pg.wait_for_selector("#startBtns button", timeout=20000)
    pg.click("#startBtns button")
    pg.wait_for_timeout(1500)
    out = {"timeout_cfg": pg.evaluate("() => CFG.rerouteTimeoutMs")}
    if mode == "timeout":
        pg.evaluate("() => { CFG.rerouteTimeoutMs = 1500; }")
    geom0 = pg.evaluate("() => S.legs[0].geom")
    far = far_point(geom0)
    out["min_m"] = round(min(hav_m(far, q) for q in geom0))
    fix = {"latitude": far[0], "longitude": far[1], "accuracy": 5}
    for k in range(4):
        fix["longitude"] += 0.00001
        ctx.set_geolocation(fix)
        pg.wait_for_timeout(450)
    out["asked"] = pump_until(pg, lambda: len(held) > 0, timeout=10)
    out["off"] = pg.evaluate("() => S.offRoute")
    if not out["asked"]:
        ctx.close()
        return out
    if mode == "apply":
        release(held[0], osrm_reply(geom0))
        pump_until(pg, lambda: pg.evaluate("() => !!S.override"), timeout=5)
    elif mode == "stale":
        pg.evaluate("() => setLeg(1)")
        release(held[0], osrm_reply(geom0))
        pg.wait_for_timeout(1500)                      # time for a wrongly accepted reply to land
        leg1 = pg.evaluate("() => S.legs[1].geom[0]")
        ctx.set_geolocation({"latitude": leg1[0], "longitude": leg1[1], "accuracy": 5})
        pg.wait_for_timeout(1500)
    else:
        out["aborted"] = pump_until(pg, lambda: pg.evaluate("() => !!(__osrmSignals[0] && __osrmSignals[0].aborted)"), timeout=8)
    out.update(pg.evaluate("() => ({override: !!S.override, legIdx: S.legIdx, done: Object.keys(S.done), waiting: S.waiting})"))
    out["leg0_to"] = pg.evaluate("() => S.legs.slice(0, 1).filter(l => l.to.kind === 'stop').map(l => String(l.to.o))")
    for h in held:                                     # answer every held request, so no handler is left waiting when the context closes
        try:
            release(h, {"code": "NoRoute"})
        except Exception:
            pass                                       # already answered, or the app ended the request
    ctx.close()
    return out


with sync_playwright() as p:
    br = p.chromium.launch()

    # ---------- 1. tablet landscape, simulated drive ----------
    ctx = br.new_context(viewport={"width": 1280, "height": 800}, device_scale_factor=1.5,
                         geolocation=DEPOT, permissions=["geolocation"])
    pg = ctx.new_page()
    attach(pg)
    pg.goto(BASE + "?sim=1&reset=1")
    pg.wait_for_selector("#startBtns button", timeout=20000)
    check("start screen shows route stats", "43 stops" in text(pg, "#startBody"), text(pg, "#startBody")[:120])
    pg.screenshot(path=os.path.join(SHOTS, "01-start-tablet.png"))
    pg.click("#startBtns button")
    time.sleep(1)
    check("banner after start", len(text(pg, "#bInstr")) > 0, text(pg, "#banner"))
    pg.click("#sSpeed")  # 5x -> 20x
    pg.click("#sPlay")
    # stop 1 is a walk-in stop: expect the park prompt
    got = wait_for(pg, lambda: "Park here" in text(pg, "#bDist"), timeout=90)
    check("arrives at the parking spot of walk-in stop 1", got, text(pg, "#banner"))
    pg.screenshot(path=os.path.join(SHOTS, "02-park-prompt.png"))
    check("park prompt offers Walk to meter", text(pg, "#aNext") == "Walk to meter", text(pg, "#actions"))
    pg.click("#aNext")
    time.sleep(1.5)
    check("walk leg banner is blue", "walk" in (pg.get_attribute("#banner", "class") or ""), pg.get_attribute("#banner", "class"))
    pg.screenshot(path=os.path.join(SHOTS, "03-walk-leg.png"))
    got = wait_for(pg, lambda: text(pg, "#bDist").startswith("Stop 1"), timeout=90)
    check("arrives at stop 1 on foot", got, text(pg, "#banner"))
    pg.screenshot(path=os.path.join(SHOTS, "04-at-stop.png"))
    pg.click("#aNext")  # Done, walk back
    got = wait_for(pg, lambda: "Stop 2" in text(pg, "#cSub") or "stop 2" in text(pg, "#cSub").lower() or text(pg, "#cNo") == "2", timeout=120)
    check("walks back to the car and moves on to stop 2", got, text(pg, "#cSub"))
    st = pg.evaluate("() => ({done: Object.keys(S.done), leg: S.legIdx})")
    check("stop 1 recorded as reached", "1" in st["done"], json.dumps(st))
    # let it drive a while at 20x and capture a maneuver banner
    time.sleep(6)
    pg.screenshot(path=os.path.join(SHOTS, "05-driving.png"))
    ban = text(pg, "#banner")
    check("driving banner shows a distance and an instruction", any(u in ban for u in (" ft", " mi")), ban.replace("\n", " | "))
    # auto advance through a drive-by stop
    leg_before = pg.evaluate("() => S.legIdx")
    got = wait_for(pg, lambda: pg.evaluate("() => S.legIdx") > leg_before or pg.evaluate("() => !!S.waiting"), timeout=120)
    check("reaches the next stop (auto advance or attention pause)", got,
          json.dumps(pg.evaluate("() => ({leg: S.legIdx, waiting: S.waiting, done: Object.keys(S.done)})")))
    # instruction words sanity
    words = pg.evaluate("""() => { const out = new Set(); S.legs.forEach(l => l.steps.forEach(s => out.add(instr(s, l.mode)))); return [...out]; }""")
    bad = [w for w in words if "undefined" in w or "null" in w or "  " in w]
    check("instructions have no undefined/null text", not bad, "; ".join(bad[:5]))
    json.dump(sorted(words), open(os.path.join(SHOTS, "instructions.json"), "w"), indent=1)
    # list panel
    pg.click("#fList")
    time.sleep(0.6)
    pg.screenshot(path=os.path.join(SHOTS, "06-list-panel.png"))
    check("list panel lists 43 stops", pg.locator("#pBody .row").count() == 43, str(pg.locator("#pBody .row").count()))
    check("list panel shows the 2 unmapped airport meters", "200059" in text(pg, "#pBody") and "200060" in text(pg, "#pBody"))
    pg.click("#pClose")
    # jump to a stop from the list: stop 12 (walk-in, on the ped mall)
    pg.click("#fList")
    pg.locator("#row12 button").click()
    time.sleep(1)
    check("Go on stop 12 targets stop 12", text(pg, "#cNo") == "12", text(pg, "#cSub"))
    # resume after reload keeps progress
    pg.click("#sPlay")  # pause
    pg.reload()
    pg.wait_for_selector("#startBtns button", timeout=20000)
    check("resume offers the current stop", "Resume at stop 12" in text(pg, "#startBtns"), text(pg, "#startBtns"))
    sw = wait_for(pg, lambda: pg.evaluate("() => navigator.serviceWorker && navigator.serviceWorker.controller ? 1 : 0"), timeout=20)
    check("service worker controls the page", sw)
    ready = wait_for(pg, lambda: "Offline ready." in text(pg, "#startBody"), timeout=20)
    check("start screen says Offline ready. once the worker holds route.json and basemap.json", ready, text(pg, "#startBody")[-80:])
    ctx.set_offline(True)
    pg.reload()
    ok = wait_for(pg, lambda: "43 stops" in (pg.locator("#startBody").inner_text() or ""), timeout=20)
    check("app loads offline from cache", ok)
    pg.screenshot(path=os.path.join(SHOTS, "07-offline-reload.png"))
    ctx.set_offline(False)
    ctx.close()

    # ---------- 2. real geolocation feed (no sim): progress + off route ----------
    ctx = br.new_context(viewport={"width": 800, "height": 1280}, geolocation=DEPOT, permissions=["geolocation"])
    pg = ctx.new_page()
    attach(pg)
    pg.goto(BASE + "?reset=1")
    pg.wait_for_selector("#startBtns button", timeout=20000)
    pg.click("#startBtns button")
    time.sleep(1.5)
    geom = pg.evaluate("() => S.legs[0].geom")
    # walk the first half of leg 0 by setting positions
    for i in range(0, max(2, len(geom) // 2), max(1, len(geom) // 12)):
        ctx.set_geolocation({"latitude": geom[i][0], "longitude": geom[i][1], "accuracy": 5})
        time.sleep(0.4)
    along = pg.evaluate("() => S.nav ? S.nav.along : -1")
    check("real GPS feed advances along leg 0", along > 20, f"along={along:.0f} m")
    pg.screenshot(path=os.path.join(SHOTS, "08-portrait-gps.png"))
    # pick a point at least 250 m from every vertex of leg 0 (north of its northernmost vertex)
    import math
    def hav(a, b):
        p1, p2 = math.radians(a[0]), math.radians(b[0])
        h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(b[1] - a[1]) / 2) ** 2
        return 2 * 6371008.8 * math.asin(math.sqrt(h))
    top = max(geom, key=lambda q: q[0])
    far = [top[0] + 0.0030, top[1]]
    while min(hav(far, q) for q in geom) < 250:
        far[0] += 0.0005
    print("off-route test point", far, "min distance to leg", round(min(hav(far, q) for q in geom)), "m")
    off = {"latitude": far[0], "longitude": far[1], "accuracy": 5}
    for k in range(5):
        off["longitude"] += 0.00001
        ctx.set_geolocation(off)
        time.sleep(0.5)
    t_off = text(pg, "#banner")
    check("off route is detected", "Off route" in t_off or pg.evaluate("() => !!S.override"), t_off.replace("\n", " | "))
    rer = wait_for(pg, lambda: pg.evaluate("() => !!S.override"), timeout=25)
    check("online reroute builds a new leg", rer)
    pg.screenshot(path=os.path.join(SHOTS, "09-off-route.png"))
    ctx.close()

    # ---------- 3. phone ----------
    ctx = br.new_context(viewport={"width": 412, "height": 915}, device_scale_factor=2.6, geolocation=DEPOT,
                         permissions=["geolocation"], is_mobile=True, has_touch=True)
    pg = ctx.new_page()
    attach(pg)
    pg.goto(BASE + "?reset=1")
    pg.wait_for_selector("#startBtns button", timeout=20000)
    pg.screenshot(path=os.path.join(SHOTS, "10-phone-start.png"))
    pg.click("#startBtns button")  # immediately, while the first-load view may still be settling
    time.sleep(1.5)
    z = pg.evaluate("() => map.getZoom()")
    check("map zooms to the car after Start (phone)", z >= 16, f"zoom={z}")
    pg.click("#cToggle")
    time.sleep(0.5)
    pg.screenshot(path=os.path.join(SHOTS, "11-phone-guidance.png"))
    ow = pg.evaluate("() => document.documentElement.scrollWidth > window.innerWidth || window.innerHeight > 915")
    check("no horizontal overflow or layout growth on a phone", not ow)
    lift = pg.evaluate("() => document.querySelector('.leaflet-control-zoom').getBoundingClientRect().bottom <= document.getElementById('card').getBoundingClientRect().top")
    check("zoom buttons sit above the card on a phone", lift)
    ctx.close()

    # ---------- 4. reroute guard (routing.openstreetmap.de is intercepted, never called) ----------
    r = reroute_case(br, "apply")
    check("reroute test setup: off-route point is 250 m+ from leg 0, app asks for a new route",
          r["asked"] and r["off"] and r["min_m"] >= 250, json.dumps(r))
    check("reroute timeout is 8000 ms", r["timeout_cfg"] == 8000, str(r["timeout_cfg"]))
    check("a reroute reply for the current leg is applied", r.get("override"), json.dumps(r))
    r = reroute_case(br, "stale")
    check("a late reroute reply is dropped after the leg changed", r["asked"] and r["override"] is False, json.dumps(r))
    check("late reply leaves the new leg in place", r["legIdx"] == 1 and r["waiting"] is None, json.dumps(r))
    check("late reply marks no stop reached", set(r["done"]) <= set(r["leg0_to"]), json.dumps(r))
    r = reroute_case(br, "timeout")
    check("a reroute request that gets no reply is aborted by the app", r["asked"] and r.get("aborted"), json.dumps(r))
    check("an aborted reroute changes nothing", r["override"] is False and r["legIdx"] == 0, json.dumps(r))

    # ---------- 5. U-turn words, Finish button, damaged saved leg ----------
    ctx = br.new_context(viewport={"width": 800, "height": 1280}, geolocation=DEPOT, permissions=["geolocation"])
    pg = ctx.new_page()
    attach(pg)
    pg.goto(BASE + "?reset=1")
    pg.wait_for_selector("#startBtns button", timeout=20000)
    w = pg.evaluate("() => instr({type: 'continue', mod: 'uturn', name: 'X'}, 'drive')")
    check("a continue step with a U-turn reads Make a U-turn", w == "Make a U-turn onto X", w)
    w = pg.evaluate("() => instr({type: 'turn', mod: 'uturn', name: ''}, 'drive')")
    check("a U-turn with no road name reads Make a U-turn", w == "Make a U-turn", w)
    words = pg.evaluate("() => { const out = new Set(); S.legs.forEach(l => l.steps.forEach(s => out.add(instr(s, l.mode)))); return [...out]; }")
    bad = [x for x in words if "uturn" in x.lower()]
    check("no instruction in route.json says uturn", not bad, "; ".join(bad[:5]))
    # Finish button: last leg, far from the depot
    pg.click("#startBtns button")
    pg.wait_for_timeout(1000)
    far_north = {"latitude": DEPOT["latitude"] + 0.02, "longitude": DEPOT["longitude"], "accuracy": 5}
    ctx.set_geolocation(far_north)
    pump_until(pg, lambda: pg.evaluate("() => !!S.fix && S.fix.lat > 46.74"), timeout=8)
    pg.evaluate("() => setLeg(S.legs.length - 1)")
    pg.wait_for_timeout(500)
    check("last leg offers the Finish button", text(pg, "#aNext") == "Finish", text(pg, "#actions"))
    check("Finish is not pressed yet (2 km from the depot)", pg.evaluate("() => S.waiting") is None)
    pg.click("#aNext")
    pg.wait_for_timeout(500)
    check("Finish button ends the route away from the depot", pg.evaluate("() => S.waiting") == "finish",
          json.dumps(pg.evaluate("() => ({waiting: S.waiting, leg: S.legIdx})")))
    check("banner shows Route complete", "Route complete" in text(pg, "#banner"), text(pg, "#banner").replace("\n", " | "))
    # damaged saved leg
    n_legs = pg.evaluate("() => S.legs.length")
    for raw, want, label in (('"abc"', 0, "text"), ("-5", 0, "negative number"), ("1.5", 0, "fraction"), ("9999", n_legs - 1, "too large")):
        pg.evaluate("(v) => localStorage.setItem('amrNav.v1.leg', v)", raw)
        pg.reload()
        try:
            shown = pg.wait_for_selector("#startBtns button", timeout=8000) is not None
        except Exception:
            shown = False      # the route did not load: report it as a failed check
        got = pg.evaluate("() => S.legIdx")
        check("saved leg " + label + " (" + raw + ") still starts the app", shown and got == want and "43 stops" in text(pg, "#startBody"),
              "legIdx=" + str(got) + " want " + str(want))
    ctx.close()

    # ---------- 6. saved street-map choice while offline ----------
    ctx = br.new_context(viewport={"width": 800, "height": 1280}, geolocation=DEPOT, permissions=["geolocation"])
    ctx.route(TILE_URL, lambda route: route.fulfill(status=200, content_type="image/png", body=PNG_1PX))
    pg = ctx.new_page()
    attach(pg)
    pg.goto(BASE + "?reset=1")
    pg.wait_for_selector("#startBtns button", timeout=20000)
    sw = wait_for(pg, lambda: pg.evaluate("() => navigator.serviceWorker && navigator.serviceWorker.controller ? 1 : 0"), timeout=20)
    check("service worker controls the page (map test)", sw)
    pg.evaluate("() => localStorage.setItem('amrNav.v1.tiles', 'true')")
    ctx.set_offline(True)
    pg.reload()
    pg.wait_for_selector("#startBtns button", timeout=20000)
    st = pg.evaluate("() => ({base: map.hasLayer(baseGroup), tiles: map.hasLayer(tileLayer), saved: S.tiles, online: navigator.onLine})")
    check("offline with the street map saved: offline base map shows, street tiles do not",
          st["base"] is True and st["tiles"] is False and st["saved"] is True and st["online"] is False, json.dumps(st))
    ctx.set_offline(False)
    ok = pump_until(pg, lambda: pg.evaluate("() => map.hasLayer(tileLayer) && !map.hasLayer(baseGroup)"), timeout=8)
    check("back online: street tiles replace the offline map", ok,
          json.dumps(pg.evaluate("() => ({base: map.hasLayer(baseGroup), tiles: map.hasLayer(tileLayer)})")))
    ctx.set_offline(True)
    ok = pump_until(pg, lambda: pg.evaluate("() => !map.hasLayer(tileLayer) && map.hasLayer(baseGroup)"), timeout=8)
    check("connection lost: offline map returns", ok,
          json.dumps(pg.evaluate("() => ({base: map.hasLayer(baseGroup), tiles: map.hasLayer(tileLayer)})")))
    ctx.set_offline(False)
    ctx.close()

    # ---------- 7. location denied, then allowed ----------
    ctx = br.new_context(viewport={"width": 800, "height": 1280})     # no geolocation permission
    pg = ctx.new_page()
    attach(pg)
    pg.goto(BASE + "?reset=1")
    pg.wait_for_selector("#startBtns button", timeout=20000)
    pg.click("#startBtns button")
    pg.wait_for_timeout(1500)
    check("without permission the GPS chip says GPS blocked", text(pg, "#gps") == "GPS blocked", text(pg, "#gps"))
    check("no fix while blocked", pg.evaluate("() => S.fix === null"))
    ctx.grant_permissions(["geolocation"])
    ctx.set_geolocation(DEPOT)
    pg.evaluate("() => document.dispatchEvent(new Event('visibilitychange'))")
    got = pump_until(pg, lambda: pg.evaluate("() => S.fix !== null"), timeout=5)
    check("after permission is granted the app gets a fix without a reload", got, text(pg, "#gps"))
    ctx.close()

    # ---------- 8. a redeploy in the middle of a drive ----------
    # Every request for route.json, including the service worker's own, goes through ctx.route (set on the context,
    # so the worker's traffic is seen). The worker is on, so this also proves it asks the network first.
    NEW_BUILT = "10/01/2026"
    ctx = br.new_context(viewport={"width": 800, "height": 1280}, geolocation=DEPOT, permissions=["geolocation"])
    rstate = {"edit": None, "served": None}
    ctx.route(ROUTE_URL, route_editor(rstate))
    pg = ctx.new_page()
    attach(pg)
    pg.goto(BASE + "?reset=1")
    pg.wait_for_selector("#startBtns button", timeout=20000)
    check("service worker controls the page (redeploy test)", sw_controls(pg))
    vec = pg.evaluate("() => [fnv1a(''), fnv1a('a'), fnv1a('foobar')]")
    check("fnv1a gives the published FNV-1a test values", vec == ["811c9dc5", "e40c292c", "bf9cf968"], json.dumps(vec))
    sig0 = pg.evaluate("() => S.routeSig")
    check("the route signature is the FNV-1a hash of route.json", sig0 == fnv1a_py(ROUTE_TEXT), sig0 + " vs " + fnv1a_py(ROUTE_TEXT))
    pg.click("#startBtns button")
    pg.wait_for_timeout(1000)
    pin = pg.evaluate("() => ({route: lsGet('activeRoute', null), sig: lsGet('activeSig', null)})")
    check("Start pins the route text and its hash", pin["route"] == ROUTE_TEXT and pin["sig"] == sig0, str(pin["sig"]))
    # reach two stops by GPS: legs 3 and 4 end at stops 2 and 3, which have no ATTENTION meters
    pg.evaluate("() => setLeg(3)")
    for _ in range(2):
        before = pg.evaluate("() => S.legIdx")
        end = pg.evaluate("() => { const g = S.legs[S.legIdx].geom; return g[g.length - 1]; }")
        ctx.set_geolocation({"latitude": end[0], "longitude": end[1], "accuracy": 5})
        pump_until(pg, lambda: pg.evaluate("() => S.legIdx") != before, timeout=8)
    prog = pg.evaluate("() => ({leg: S.legIdx, done: Object.keys(S.done).sort(), next: currentTargetStop().o})")
    check("redeploy test setup: two stops reached", len(prog["done"]) == 2 and prog["leg"] == 5 and prog["next"] == 4, json.dumps(prog))

    def reload_with(edit):
        rstate["edit"] = edit
        pg.reload()
        pg.wait_for_selector("#startBtns button", timeout=20000)
        return pg.evaluate("""() => ({leg: S.legIdx, done: Object.keys(S.done).sort(), built: S.route.built,
            line: document.getElementById('newRouteLine') ? document.getElementById('newRouteLine').textContent : null,
            btns: [...document.querySelectorAll('#startBtns button')].map(b => b.textContent)})""")

    # same built date, other content: the hash (not the date) decides
    r = reload_with(lambda t: t.replace('"source":"', '"source":"Revised. ', 1))
    check("redeploy test: the served route.json really differs", rstate["served"] != ROUTE_TEXT and ROUTE_BUILT in rstate["served"])
    check("new content with the same built date still shows the new-route line",
          r["line"] == "A new route is ready (built " + ROUTE_BUILT + "). It loads when you start a new drive.", str(r["line"]))
    check("a new route keeps the saved progress", r["leg"] == prog["leg"] and r["done"] == prog["done"], json.dumps(r))
    check("the primary button resumes at the same stop", r["btns"][0] == "Resume at stop 4", json.dumps(r["btns"]))
    check("the second button starts a new drive with the new route", r["btns"][1:] == ["Start a new drive with the new route"], json.dumps(r["btns"]))
    # the old route comes back: no new-route line, same progress (the worker must not serve the revised copy it saved)
    r = reload_with(None)
    check("route.json back to the pinned one: no new-route line, progress kept",
          r["line"] is None and r["leg"] == prog["leg"] and r["done"] == prog["done"] and r["btns"][0] == "Resume at stop 4", json.dumps(r))
    # the brief's case: the built date changes
    r = reload_with(lambda t: t.replace('"built":"' + ROUTE_BUILT + '"', '"built":"' + NEW_BUILT + '"', 1))
    check("redeploy mid-drive: the new-route line shows the new built date",
          r["line"] == "A new route is ready (built " + NEW_BUILT + "). It loads when you start a new drive.", str(r["line"]))
    check("redeploy mid-drive: progress is kept (same leg, same stops)", r["leg"] == prog["leg"] and r["done"] == prog["done"], json.dumps(r))
    check("redeploy mid-drive: primary button reads Resume at stop 4 and the session runs the pinned route",
          r["btns"][0] == "Resume at stop 4" and r["built"] == ROUTE_BUILT, json.dumps(r))
    pg.click('#startBtns button:has-text("Start a new drive with the new route")')
    one = pg.evaluate("() => ({leg: S.legIdx, done: Object.keys(S.done).sort(), built: S.route.built, started: S.started})")
    one["btns"] = start_btns(pg)
    check("one tap on Start a new drive with the new route clears nothing and asks for a second tap",
          one["leg"] == prog["leg"] and one["done"] == prog["done"] and one["built"] == ROUTE_BUILT and not one["started"]
          and one["btns"][1:] == ["Tap again to clear progress"], json.dumps(one))
    tap(pg, '#startBtns button:has-text("Tap again to clear progress")')      # the second tap confirms
    pg.wait_for_timeout(800)
    st = pg.evaluate("""() => ({leg: S.legIdx, done: Object.keys(S.done), skipped: Object.keys(S.skipped), built: S.route.built,
        started: S.started, sig: lsGet('activeSig', null), saved: lsGet('leg', null), shown: getComputedStyle(document.getElementById('start')).display})""")
    check("new drive with the new route: leg 0, nothing reached", st["leg"] == 0 and st["done"] == [] and st["skipped"] == [] and st["saved"] == 0, json.dumps(st))
    check("new drive with the new route: the page now uses the new route", st["built"] == NEW_BUILT and st["started"] and st["shown"] == "none", json.dumps(st))
    check("the new route is pinned", st["sig"] == fnv1a_py(rstate["served"]), json.dumps(st))
    r = reload_with(rstate["edit"])
    check("after the switch the new route is the pinned one: no new-route line", r["line"] is None and r["built"] == NEW_BUILT, json.dumps(r))
    check("after the switch the start button starts at stop 1", r["btns"] == ["Start guidance"], json.dumps(r["btns"]))
    # a panel reset with a newer route waiting also switches to it
    pg.click("#startBtns button")
    pg.wait_for_timeout(500)
    pg.evaluate("() => setLeg(3)")
    rstate["edit"] = lambda t: t.replace('"built":"' + ROUTE_BUILT + '"', '"built":"11/01/2026"', 1)
    pg.reload()
    pg.wait_for_selector("#startBtns button", timeout=20000)
    check("a newer route waits while the drive has progress",
          pg.evaluate("() => !!S.pending && S.pending.route.built === '11/01/2026' && S.route.built === '10/01/2026'"))
    pg.click("#startBtns button")
    pg.wait_for_timeout(500)
    pg.click("#fList")
    pg.click("#bReset")
    pg.click("#bReset")      # the second tap confirms
    pg.wait_for_timeout(500)
    st = pg.evaluate("() => ({leg: S.legIdx, built: S.route.built, pending: S.pending, sig: lsGet('activeSig', null)})")
    check("Start a new drive in the stop list switches to the waiting route", st["leg"] == 0 and st["built"] == "11/01/2026" and st["pending"] is None
          and st["sig"] == fnv1a_py(rstate["served"]), json.dumps(st))
    ctx.close()

    # ---------- 9. a query address does not pin an old page; the saved page is one entry ----------
    # The app page is stale while revalidate: a visit opens the saved page at once and saves the server's page for the next open.
    ctx = br.new_context(viewport={"width": 800, "height": 1280}, geolocation=DEPOT, permissions=["geolocation"])
    pstate = {"marker": None}

    def page_handler(route):
        if not pstate["marker"]:
            route.continue_()
            return
        body = route.fetch().text().replace("<head>", "<head><!-- " + pstate["marker"] + " -->", 1)
        route.fulfill(status=200, content_type="text/html; charset=utf-8", body=body)

    ctx.route(PAGE_URL, page_handler)
    pg = ctx.new_page()
    attach(pg)
    pg.goto(BASE)
    pg.wait_for_selector("#startBtns button", timeout=20000)
    check("service worker controls the page (query test)", sw_controls(pg))
    pg.goto(BASE + "?reset=1")                     # a query visit while the worker runs: the old worker saved a second page entry
    pg.wait_for_selector("#startBtns button", timeout=20000)
    saved_page = "async () => { const r = await caches.match(new URL('./', location.href).href); return r ? await r.text() : ''; }"
    pstate["marker"] = "AMR-TEST-MARKER-1"
    pg.goto("about:blank")
    pg.goto(BASE)                                  # plain address, online, the server now sends a changed page
    pg.wait_for_selector("#startBtns button", timeout=20000)
    has = pg.evaluate("() => document.head.innerHTML.includes('AMR-TEST-MARKER-1')")
    saved = pump_until(pg, lambda: "AMR-TEST-MARKER-1" in pg.evaluate(saved_page), timeout=8)
    check("a plain visit after a ?reset=1 visit opens the saved page at once and saves the page the server sends now",
          not has and saved, "shown now: %s, saved: %s" % (has, saved))
    pg.goto("about:blank")
    pg.goto(BASE + "?sim=1")
    pg.wait_for_selector("#startBtns button", timeout=20000)
    check("the next visit, on ?sim=1, opens that one saved page, now the server's new page",
          pg.evaluate("() => document.head.innerHTML.includes('AMR-TEST-MARKER-1')"))
    keys = pg.evaluate("""async () => { const out = []; for (const k of await caches.keys()) { const c = await caches.open(k);
        (await c.keys()).forEach(r => out.push(r.url)); } return out; }""")
    check("no saved page or file has a query string", not [u for u in keys if "?" in u], " ".join(u for u in keys if "?" in u))
    pstate["marker"] = None
    # A request that a ctx.route handler lets through is not stopped by set_offline, so drop the handler first:
    # the offline steps below must reach the worker's real (failing) network request.
    ctx.unroute(PAGE_URL, page_handler)
    net_failed = []
    ctx.on("requestfailed", lambda r: net_failed.append((r.url, bool(r.service_worker))))
    ctx.set_offline(True)
    pg.goto("about:blank")
    pg.goto(BASE + "?sim=1")
    ok = wait_for(pg, lambda: "43 stops" in (pg.locator("#startBody").inner_text() or ""), timeout=20)
    check("offline, a query address opens from the one saved page", ok)
    check("that offline open still asked the network for the page, and the worker's own request failed",
          any(sw and "?sim=1" in u for u, sw in net_failed), json.dumps(net_failed[:3]))
    ctx.set_offline(False)
    pg.goto("about:blank")
    pg.goto(BASE)
    pg.wait_for_selector("#startBtns button", timeout=20000)
    ready = wait_for(pg, lambda: "Offline ready." in text(pg, "#startBody"), timeout=20)
    check("Offline ready. shows while the worker holds route.json and basemap.json", ready, text(pg, "#startBody")[-80:])
    txt = pg.evaluate("""async () => { for (const k of await caches.keys()) { const c = await caches.open(k); await c.delete('basemap.json'); }
        await updateOfflineLine(); return document.getElementById('offlineLine').textContent; }""")
    check("without basemap.json in the cache the line asks the driver to wait online",
          txt == "Not offline ready yet. Keep this page open online for a minute.", txt)
    ctx.close()

    # a browser without service workers (insecure address, old browser): never claim offline readiness
    ctx = br.new_context(viewport={"width": 800, "height": 1280})
    pg = ctx.new_page()
    attach(pg)
    pg.add_init_script("delete Navigator.prototype.serviceWorker;")
    pg.goto(BASE + "?reset=1")
    pg.wait_for_selector("#startBtns button", timeout=20000)
    ok = wait_for(pg, lambda: "Not offline ready yet. Keep this page open online for a minute." in text(pg, "#startBody"), timeout=10)
    check("with no service worker the start screen says Not offline ready yet.", ok, text(pg, "#startBody")[-90:])
    ctx.close()

    # ---------- 10. a slow network: wait 3 s, then use the saved route; the late reply still refreshes the save ----------
    ctx = br.new_context(viewport={"width": 800, "height": 1280}, geolocation=DEPOT, permissions=["geolocation"])
    held = []
    hold = {"on": False}

    def slow_handler(route):
        if hold["on"]:
            held.append(route)
        else:
            route.continue_()

    ctx.route(ROUTE_URL, slow_handler)
    pg = ctx.new_page()
    attach(pg)
    pg.goto(BASE + "?reset=1")
    pg.wait_for_selector("#startBtns button", timeout=20000)
    sw_controls(pg)
    wait_for(pg, lambda: "Offline ready." in text(pg, "#startBody"), timeout=20)
    hold["on"] = True
    t0 = time.time()
    pg.reload()
    pg.wait_for_selector("#startBtns button", timeout=20000)
    dt = time.time() - t0
    check("route.json that never answers: the page waits about 3 s, then opens with the saved route",
          2.5 <= dt <= 9 and len(held) >= 1 and "43 stops" in text(pg, "#startBody"), "%.1f s, held=%d" % (dt, len(held)))
    late = json.loads(ROUTE_TEXT)
    late["built"] = "12/31/2026"
    for h in held:
        h.fulfill(status=200, content_type="application/json", body=json.dumps(late, separators=(",", ":")))
    hold["on"] = False
    saved = wait_for(pg, lambda: '"built":"12/31/2026"' in pg.evaluate("async () => { const r = await caches.match('route.json'); return r ? await r.text() : ''; }"), timeout=8)
    check("the late reply was saved in the worker's cache", saved)
    ctx.close()

    # ---------- 11. a failed store does not stop the drive from starting ----------
    ctx = br.new_context(viewport={"width": 800, "height": 1280}, geolocation=DEPOT, permissions=["geolocation"])
    pg = ctx.new_page()
    attach(pg)
    pg.add_init_script("""
      const __set = Storage.prototype.setItem;
      Storage.prototype.setItem = function (k, v) {
        if (String(k).endsWith('.activeRoute')) throw new DOMException('full', 'QuotaExceededError');
        return __set.call(this, k, v);
      };
    """)
    pg.goto(BASE + "?reset=1")
    pg.wait_for_selector("#startBtns button", timeout=20000)
    pg.click("#startBtns button")
    pg.wait_for_timeout(1000)
    st = pg.evaluate("() => ({started: S.started, shown: getComputedStyle(document.getElementById('start')).display, pinned: localStorage.getItem('amrNav.v1.activeRoute'), leg: lsGet('leg', null)})")
    check("Start works when the route pin cannot be stored", st["started"] and st["shown"] == "none" and st["pinned"] is None and st["leg"] == 0, json.dumps(st))
    pg.reload()
    pg.wait_for_selector("#startBtns button", timeout=20000)
    check("the app still opens after a failed pin", "43 stops" in text(pg, "#startBody"))
    ctx.close()

    # ---------- 12. street tiles showing: no offline buildings and paths on top; the layer button offline ----------
    ctx = br.new_context(viewport={"width": 800, "height": 1280}, geolocation=DEPOT, permissions=["geolocation"])
    ctx.route(TILE_URL, lambda route: route.fulfill(status=200, content_type="image/png", body=PNG_1PX))
    pg = ctx.new_page()
    attach(pg)
    pg.goto(BASE + "?reset=1")
    pg.wait_for_selector("#startBtns button", timeout=20000)
    pg.evaluate("() => localStorage.setItem('amrNav.v1.tiles', 'true')")
    pg.reload()
    pg.wait_for_selector("#startBtns button", timeout=20000)
    pg.evaluate("() => { map.setZoom(16, {animate: false}); }")
    pg.wait_for_timeout(500)
    lay = "() => ({z: map.getZoom(), tiles: map.hasLayer(tileLayer), base: map.hasLayer(baseGroup), bldg: map.hasLayer(bldgGroup), path: map.hasLayer(pathGroup)})"
    st = pg.evaluate(lay)
    check("street tiles at zoom 16: buildings and paths of the offline map are not added",
          st["z"] == 16 and st["tiles"] is True and st["bldg"] is False and st["path"] is False, json.dumps(st))
    pg.evaluate("() => { map.setZoom(14, {animate: false}); map.setZoom(17, {animate: false}); }")
    pg.wait_for_timeout(300)
    st = pg.evaluate(lay)
    check("street tiles after more zooming: still no offline buildings or paths",
          st["tiles"] is True and st["bldg"] is False and st["path"] is False, json.dumps(st))
    ctx.set_offline(True)
    ok = pump_until(pg, lambda: pg.evaluate("() => map.hasLayer(bldgGroup) && map.hasLayer(pathGroup) && !map.hasLayer(tileLayer)"), timeout=8)
    check("offline map showing: buildings and paths are added", ok, json.dumps(pg.evaluate(lay)))
    pg.click("#startBtns button")
    pg.wait_for_timeout(800)
    pg.click("#fLayer")
    st = pg.evaluate("() => ({saved: S.tiles, stored: lsGet('tiles', null), base: map.hasLayer(baseGroup), tiles: map.hasLayer(tileLayer)})")
    toast_txt = pg.locator("#toast").inner_text().strip() if pg.locator("#toast").is_visible() else ""
    check("layer button offline with street map saved: the saved choice stays on", st["saved"] is True and st["stored"] is True, json.dumps(st))
    check("layer button offline: the data connection toast shows and the map does not change",
          toast_txt == "Street map needs a data connection" and st["base"] is True and st["tiles"] is False, toast_txt + " " + json.dumps(st))
    ctx.set_offline(False)
    pump_until(pg, lambda: pg.evaluate("() => map.hasLayer(tileLayer)"), timeout=8)
    pg.click("#fLayer")                              # online: the button still switches the street map off
    st = pg.evaluate("() => ({saved: S.tiles, base: map.hasLayer(baseGroup), tiles: map.hasLayer(tileLayer)})")
    check("layer button online: a tap switches the street map off", st["saved"] is False and st["base"] is True and st["tiles"] is False, json.dumps(st))
    pg.click("#fLayer")
    st = pg.evaluate("() => ({saved: S.tiles, base: map.hasLayer(baseGroup), tiles: map.hasLayer(tileLayer)})")
    check("layer button online: a second tap switches it on again", st["saved"] is True and st["tiles"] is True and st["base"] is False, json.dumps(st))
    ctx.close()

    # ---------- 13. a tab opened on another file in the scope must not replace the saved app page ----------
    # No ctx.route here, so set_offline reaches the worker's own requests.
    ctx = br.new_context(viewport={"width": 800, "height": 1280}, geolocation=DEPOT, permissions=["geolocation"])
    pg = ctx.new_page()
    attach(pg)
    pg.goto(BASE + "?reset=1")
    pg.wait_for_selector("#startBtns button", timeout=20000)
    check("service worker controls the page (other-file test)", sw_controls(pg))
    check("Offline ready. shows before the other files are opened",
          wait_for(pg, lambda: "Offline ready." in text(pg, "#startBody"), timeout=20))
    for other in ("route.json", "manifest.webmanifest", "sw.js"):
        pg.goto("about:blank")
        try:
            pg.goto(BASE + other)
        except Exception:
            pass                       # a file type the browser downloads instead of showing still went through the worker
        pg.wait_for_timeout(300)
    # stay on that last file (no online visit to the app page, which would save a good copy again) and read the cache from here
    kind = pg.evaluate("""async () => { const r = await caches.match(new URL('./', location.href).href);
        return r ? (r.headers.get('content-type') || '') : null; }""")
    check("the saved app page is still text/html after other files were opened in the tab", bool(kind) and kind.lower().startswith("text/html"), str(kind))
    net_failed = []
    ctx.on("requestfailed", lambda r: net_failed.append((r.url, bool(r.service_worker))))
    ctx.set_offline(True)
    pg.goto("about:blank")
    pg.goto(BASE)
    ok = wait_for(pg, lambda: "43 stops" in (pg.locator("#startBody").inner_text() or ""), timeout=20)
    check("offline, the app still opens and its start card shows 43 stops", ok, text(pg, "body")[:60])
    check("that offline open still asked the network for the page, and the worker's own request failed (other-file test)",
          any(sw and u.rstrip("?").endswith("/amr-nav/") for u, sw in net_failed), json.dumps(net_failed[:3]))
    ctx.set_offline(False)
    ctx.close()

    # ---------- 14. a stop that waits for a tap is left behind when the vehicle drives away ----------
    legs = ROUTE["legs"]
    attn_stops = {s["o"] for s in ROUTE["stops"] if any(m.get("attn") for m in s["meters"])}
    i7 = next(i for i, l in enumerate(legs) if l["to"].get("o") == 7 and l["to"]["kind"] == "stop")
    nxt = legs[i7 + 1]
    end7 = legs[i7]["geom"][-1]
    P7 = Path(nxt["geom"])

    def away(m):
        """The first point along the next leg that is at least m metres (straight line) from stop 7."""
        s = 0.0
        while s < P7.total and hav_m(P7.ll(s), end7) < m:
            s += 5
        return P7.ll(s)

    ctx, pg = guidance_page(br)
    check("stop 7 test setup: an ATTENTION stop reached by driving, and the next leg drives on to stop 8",
          7 in attn_stops and legs[i7]["mode"] == "drive" and nxt["mode"] == "drive" and nxt["to"].get("o") == 8 and hav_m(away(95), end7) > 80,
          "leg %d -> leg %d" % (i7, i7 + 1))

    def state():
        return pg.evaluate("() => ({waiting: S.waiting, leg: S.legIdx, passed: Object.keys(S.passed || {}), done: Object.keys(S.done), skipped: Object.keys(S.skipped)})")

    pg.evaluate("(i) => setLeg(i)", i7)
    feed(pg, end7)
    check("arriving at ATTENTION stop 7 waits for a tap", state()["waiting"] == "stop", json.dumps(state()))
    feed(pg, away(40), speed=5)
    check("moving at 5 m/s but only 40 m from stop 7: still waiting", state()["waiting"] == "stop", json.dumps(state()))
    feed(pg, away(95), speed=1)
    check("95 m from stop 7 but slower than 3 m/s: still waiting", state()["waiting"] == "stop", json.dumps(state()))
    feed(pg, away(95), acc=100, speed=5)
    check("95 m from stop 7 at 5 m/s with a weak fix (100 m): still waiting", state()["waiting"] == "stop", json.dumps(state()))
    feed(pg, away(95), speed=5)
    check("one fast fix more than 80 m from stop 7 is not enough: still waiting", state()["waiting"] == "stop", json.dumps(state()))
    feed(pg, away(95), speed=1)
    feed(pg, away(95), speed=5)
    check("fast, slow, fast: the slow fix starts the count again, still waiting", state()["waiting"] == "stop", json.dumps(state()))
    feed(pg, away(95), acc=100, speed=5)
    feed(pg, away(95), speed=5)
    check("fast, weak-GPS fix, fast: the weak fix starts the count again, still waiting", state()["waiting"] == "stop", json.dumps(state()))
    feed(pg, away(100), speed=5)
    r = state()
    check("two fast fixes in a row more than 80 m from stop 7: the guide goes on without a tap",
          r["waiting"] is None and r["leg"] == i7 + 1, json.dumps(r))
    check("stop 7 is put in Passed, not in reached or skipped", r["passed"] == ["7"] and "7" not in r["done"] and "7" not in r["skipped"], json.dumps(r))
    check("the passed stop is saved", pg.evaluate("() => Object.keys(lsGet('passed', {}))") == ["7"])
    spoken = pg.evaluate("() => window.__spoken")
    check("the guide says which stop comes next", "Continuing to stop 8." in spoken, json.dumps(spoken[-3:]))
    mk = pg.evaluate("""() => { const m = stopMarkers[7], e = m && m.getElement() ? m.getElement().querySelector('.sm') : null;
        return e ? {c: e.className, bg: getComputedStyle(e).backgroundColor, fg: getComputedStyle(e).color} : null; }""")
    check("the map marker of stop 7 shows it as Passed: amber (#f59e0b) with white text",
          bool(mk) and "pass" in mk["c"].split() and mk["bg"] == "rgb(245, 158, 11)" and mk["fg"] == "rgb(255, 255, 255)", json.dumps(mk))
    pg.click("#fList")
    chip = dom(pg, "#row7 .chip", "({t: e.textContent, c: e.className, bg: getComputedStyle(e).backgroundColor, fg: getComputedStyle(e).color})")
    check("the stop list shows a Passed chip for stop 7", bool(chip) and chip["t"] == "Passed" and "pass" in chip["c"].split(), json.dumps(chip))
    check("the Passed chip is pale amber with brown text", bool(chip) and chip["bg"] == "rgb(254, 243, 199)" and chip["fg"] == "rgb(146, 64, 14)", json.dumps(chip))
    summ = dom(pg, "#pBody .sum")
    check("the list summary counts the passed stop", summ is not None and "1 passed" in summ, str(summ))
    pg.click("#pClose")
    pg.reload()
    pg.wait_for_selector("#startBtns button", timeout=20000)
    check("a passed stop is still Passed after a reload", pg.evaluate("() => Object.keys(S.passed || {})") == ["7"])
    pg.click('#startBtns button:has-text("Start a new drive at stop 1")')
    tap(pg, '#startBtns button:has-text("Tap again to clear progress")')      # the second tap confirms
    pg.wait_for_timeout(500)
    r = pg.evaluate("() => ({passed: Object.keys(S.passed || {}), stored: lsGet('passed', null)})")
    check("Start a new drive at stop 1 (start screen) clears Passed", r["passed"] == [] and r["stored"] == {}, json.dumps(r))
    pg.evaluate("() => { S.passed = S.passed || {}; S.passed[7] = 1; S.passed[9] = 1; }")
    pg.evaluate("() => { markStop(7, 'done'); markStop(9, 'skip'); }")
    r = pg.evaluate("() => ({passed: Object.keys(S.passed || {}), stored: lsGet('passed', null), done: Object.keys(S.done), skipped: Object.keys(S.skipped)})")
    check("marking a passed stop done or skipped takes it out of Passed",
          r["passed"] == [] and r["stored"] == {} and r["done"] == ["7"] and r["skipped"] == ["9"], json.dumps(r))
    pg.evaluate("() => { S.passed = S.passed || {}; S.passed[7] = 1; lsSet('passed', S.passed); }")
    pg.click("#fList")
    pg.click("#bReset")
    pg.click("#bReset")                                  # the second tap confirms
    pg.wait_for_timeout(400)
    r = pg.evaluate("() => ({passed: Object.keys(S.passed || {}), stored: lsGet('passed', null), leg: S.legIdx})")
    check("Start a new drive in the stop list clears Passed", r["passed"] == [] and r["stored"] == {} and r["leg"] == 0, json.dumps(r))
    pg.evaluate("() => { S.passed = S.passed || {}; S.passed[7] = 1; }")
    pg.click("#fList")
    pg.locator("#row7 button").click()                   # Go: the driver returns to stop 7
    pg.wait_for_timeout(400)
    r = pg.evaluate("() => ({passed: Object.keys(S.passed || {}), leg: S.legIdx})")
    check("Go to a passed stop from the list takes it out of Passed", r["passed"] == [] and r["leg"] == i7, json.dumps(r))
    ctx.close()

    # ---------- 15. a fix with poor accuracy does not steer the guide ----------
    i_u = next(i for i, l in enumerate(legs) if l["mode"] == "drive" and any(s.get("mod") == "uturn" for s in l["steps"]))
    uturn = next(s for s in legs[i_u]["steps"] if s.get("mod") == "uturn")
    nxt_step = legs[i_u]["steps"][legs[i_u]["steps"].index(uturn) + 1]
    PU = Path(legs[i_u]["geom"])
    turn_j = min(range(len(PU.geom)), key=lambda j: hav_m(PU.geom[j], uturn["loc"]))
    s_turn = PU.cum[turn_j]                              # where the out-and-back turns around

    ctx, pg = guidance_page(br)
    pg.evaluate("(i) => setLeg(i)", i_u)
    a0 = feed(pg, PU.ll(200))
    keys0 = pg.evaluate("() => Object.keys(S.announced).sort()")
    check("accuracy test setup: a good fix 200 m along leg %d matches near 200 m" % i_u, a0 is not None and abs(a0 - 200) < 10, "along=%s" % a0)
    weak_at = nxt_step["loc"]                            # the next maneuver: a voice prompt would be spoken here
    a1 = feed(pg, weak_at, acc=150)
    keys1 = pg.evaluate("() => Object.keys(S.announced).sort()")
    check("a fix with 150 m accuracy does not change S.nav.along", a1 == a0, "%s -> %s" % (a0, a1))
    check("a fix with 150 m accuracy adds no key to S.announced", keys1 == keys0, json.dumps([keys0, keys1]))
    r = pg.evaluate("""() => ({then: document.getElementById('bThen').textContent, chip: document.getElementById('gps').textContent,
        cls: document.getElementById('gps').className, lat: meMarker.getLatLng().lat, rad: accCircle.getRadius()})""")
    check("a weak fix still moves the marker and the accuracy circle, and shows the GPS chip",
          abs(r["lat"] - weak_at[0]) < 1e-6 and r["rad"] == 150 and r["chip"].startswith("GPS ±") and r["cls"] == "none", json.dumps(r))
    check("a weak fix says Weak GPS. Waiting for a better fix.", r["then"] == "Weak GPS. Waiting for a better fix.", r["then"])
    a2 = feed(pg, PU.ll(220))
    then = text(pg, "#bThen")
    check("the next good fix is matched again and the banner recovers", a2 is not None and abs(a2 - 220) < 10 and "Weak GPS" not in then, "along=%s then=%r" % (a2, then))
    ctx.close()

    # ---------- 16. a fix with no news for 10 s shows GPS lost (real GPS code: the simulator has no GPS-lost check) ----------
    ctx, pg = guidance_page(br, sim=False)
    t0 = time.time()
    feed(pg, [DEPOT["latitude"], DEPOT["longitude"]], acc=5)
    check("a good fix: the GPS chip shows the accuracy", text(pg, "#gps").startswith("GPS ±"), text(pg, "#gps"))
    pg.wait_for_timeout(8000)
    check("8 s after the last fix the chip still shows the accuracy", text(pg, "#gps").startswith("GPS ±"), text(pg, "#gps"))
    lost_at = None
    while time.time() - t0 < 16:
        pg.wait_for_timeout(250)
        if text(pg, "#gps") == "GPS lost":
            lost_at = time.time() - t0
            break
    check("with no fix for 11 s or more the GPS chip text is GPS lost (shown 10 to 13 s after the last fix)",
          lost_at is not None and 9.9 <= lost_at <= 13, "after %s s" % (round(lost_at, 1) if lost_at else None))
    r = pg.evaluate("() => ({then: document.getElementById('bThen').textContent, cls: document.getElementById('gps').className})")
    check("the banner says GPS lost and how old the last fix is, and the chip is red",
          re.fullmatch(r"GPS lost\. Last fix 1\d s ago\.", r["then"]) is not None and r["cls"] == "none", json.dumps(r))
    feed(pg, [DEPOT["latitude"], DEPOT["longitude"]], acc=5)
    check("a new fix takes GPS lost away", text(pg, "#gps").startswith("GPS ±") and "GPS lost" not in text(pg, "#bThen"), text(pg, "#gps") + " | " + text(pg, "#bThen"))
    ctx.close()

    # ---------- 17. an out-and-back road: the guide stays on the pass the vehicle is on ----------
    ctx, pg = guidance_page(br)
    gaps, errs_out, jumps_out = [], [], []
    pg.evaluate("(i) => setLeg(i)", i_u)
    prev = None
    for k, s in enumerate(range(100, int(s_turn) - 70, 20)):
        if k % 2:                                        # every second fix drifts 70% of the way to the other lane
            ll, gap = toward(PU, s, s_turn + 15, None, 0.7)
            gaps.append(gap)
        else:
            ll = PU.ll(s)
        along = feed(pg, ll, acc=5, speed=10)
        errs_out.append(abs(along - s))
        if prev is not None:
            jumps_out.append(along - prev)
        prev = along
    check("out-and-back setup: the return lane is 4 to 15 m from the outbound fixes", gaps and 4 <= min(gaps) and max(gaps) <= 15, "%.1f to %.1f m" % (min(gaps), max(gaps)))
    check("outbound fixes never match the return part: no forward jump over 60 m between fixes 20 m apart",
          max(jumps_out) <= 60, "largest forward step %.0f m" % max(jumps_out))
    check("outbound fixes stay within 25 m of their true distance along the leg", max(errs_out) <= 25, "largest error %.0f m" % max(errs_out))
    jumps_back, errs_back = [], []
    pg.evaluate("(i) => setLeg(i)", i_u)
    prev = None
    for k, s in enumerate(range(int(s_turn) + 60, int(s_turn) + 300, 20)):
        ll = toward(PU, s, 0.0, s_turn - 15, 0.7)[0] if k % 2 else PU.ll(s)
        along = feed(pg, ll, acc=5, speed=10)
        errs_back.append(abs(along - s))
        if prev is not None:
            jumps_back.append(prev - along)
        prev = along
    check("return fixes never match the outbound part: no backward jump over 60 m between fixes 20 m apart",
          max(jumps_back) <= 60, "largest backward step %.0f m" % max(jumps_back))
    check("return fixes stay within 25 m of their true distance along the leg", max(errs_back) <= 25, "largest error %.0f m" % max(errs_back))
    ctx.close()

    # ---------- 18. off-route distance grows with the fix's own error ----------
    P0 = Path(legs[0]["geom"])
    side, s_side = None, None
    for s_try in range(150, int(P0.total) - 100, 25):
        side = P0.side_point(s_try, 50)
        if side:
            s_side = s_try
            break
    ctx, pg = guidance_page(br)
    check("off-route test setup: a point 48 to 52 m from leg 0 and no nearer part of it", side is not None, "at %s m" % s_side)
    feed(pg, P0.ll(s_side))
    for _ in range(4):
        feed(pg, side, acc=55, speed=5)
    r = pg.evaluate("() => ({off: S.offRoute, cnt: S.offCnt})")
    check("50 m from the route with a 55 m fix is not off route", r["off"] is False and r["cnt"] == 0, json.dumps(r))
    for _ in range(4):
        feed(pg, side, acc=10, speed=5)
    r = pg.evaluate("() => ({off: S.offRoute, cnt: S.offCnt})")
    check("50 m from the route with a 10 m fix is off route", r["off"] is True, json.dumps(r))
    ctx.close()

    # ---------- 19. the off-route arrow keeps its frame when the heading drops out ----------
    far = far_point(legs[0]["geom"])

    def arrow(pg):
        return pg.evaluate("""() => { const a = document.getElementById('bArrow'), g = a.querySelector('g'), t = a.querySelector('text');
            const m = g ? /rotate\\((-?\\d+) 24 24\\)/.exec(g.getAttribute('transform')) : null;
            return {rot: m ? Number(m[1]) : null, label: t ? t.textContent : null, off: S.offRoute}; }""")

    ctx, pg = guidance_page(br)
    pg.evaluate("() => setLeg(0)")
    feed(pg, legs[0]["geom"][0])
    for k in range(4):
        feed(pg, [far[0], far[1] + 0.00001 * k], acc=5, speed=0, heading=None)
    a_none = arrow(pg)
    brg = pg.evaluate("() => { const l = S.legs[0], e = l.geom[l.geom.length - 1]; return bearing([S.fix.lat, S.fix.lon], e); }")
    check("off route with no heading: the arrow points on a north-up map and carries an N",
          a_none["off"] and a_none["label"] == "N" and a_none["rot"] == round(brg), json.dumps(a_none) + " bearing=%.1f" % brg)
    feed(pg, [far[0], far[1] + 0.00005], acc=5, speed=8, heading=90)
    a_head = arrow(pg)
    brg = pg.evaluate("() => { const l = S.legs[0], e = l.geom[l.geom.length - 1]; return bearing([S.fix.lat, S.fix.lon], e); }")
    check("off route with a heading: the arrow is relative to the direction of travel, no N",
          a_head["label"] is None and a_head["rot"] == round(brg - 90), json.dumps(a_head) + " bearing=%.1f" % brg)
    feed(pg, [far[0], far[1] + 0.00005], acc=5, speed=0, heading=None)
    a_held = arrow(pg)
    check("the heading is held when the next fix has none: same frame, no N",
          a_held["label"] is None and a_held["rot"] == a_head["rot"], json.dumps(a_held))
    pg.evaluate("() => { if (S.lastHeading) S.lastHeading.t -= 31000; }")      # 31 s have passed since the last heading
    feed(pg, [far[0], far[1] + 0.00005], acc=5, speed=0, heading=None)
    a_old = arrow(pg)
    brg = pg.evaluate("() => { const l = S.legs[0], e = l.geom[l.geom.length - 1]; return bearing([S.fix.lat, S.fix.lon], e); }")
    check("the heading is forgotten after 30 s: north-up with an N again",
          a_old["label"] == "N" and a_old["rot"] == round(brg), json.dumps(a_old))
    ctx.close()

    # ---------- 20. a device that sends no speed: a speed worked out over 3 s or more; walkers at walk-in stops ----------
    T0 = 1_700_000_000_000                               # fix times in ms; only the differences matter

    def at_stop7_no_speed():
        ctx, pg = guidance_page(br)
        pg.evaluate("(i) => setLeg(i)", i7)
        feed(pg, end7, speed=None, t=T0)
        return ctx, pg

    ctx, pg = at_stop7_no_speed()
    check("no-speed test setup: arriving at stop 7 waits for a tap", state_of(pg)["waiting"] == "stop", json.dumps(state_of(pg)))
    resumed_at, early = None, []
    for k, s in enumerate(range(20, 241, 20)):           # 20 m every 4 s is 5 m/s
        ll = P7.ll(s)
        feed(pg, ll, speed=None, t=T0 + 4000 * (k + 1))
        if state_of(pg)["waiting"] is None and resumed_at is None:
            resumed_at = s
            if hav_m(ll, end7) <= 80:
                early.append(s)
    r = state_of(pg)
    check("no speed sent, driving away at 5 m/s: the guide goes on without a tap",
          r["waiting"] is None and r["leg"] == i7 + 1 and r["passed"] == ["7"], json.dumps(r))
    check("... and only once the vehicle is more than 80 m from stop 7", resumed_at is not None and not early,
          "resumed at %s m along the next leg" % resumed_at)
    check("... and says which stop comes next", "Continuing to stop 8." in pg.evaluate("() => window.__spoken"))
    ctx.close()

    ctx, pg = at_stop7_no_speed()
    for k, s in enumerate(range(20, 201, 20)):           # 20 m every 20 s is 1 m/s
        feed(pg, P7.ll(s), speed=None, t=T0 + 20000 * (k + 1))
    r = state_of(pg)
    check("no speed sent, creeping away at 1 m/s: still waiting", r["waiting"] == "stop" and r["passed"] == [], json.dumps(r))
    ctx.close()

    ctx, pg = at_stop7_no_speed()
    feed(pg, away(95), speed=None, t=T0 + 2000)          # 2 s after the arrival fix: too short to measure a speed
    feed(pg, away(97), speed=None, t=T0 + 2500)
    feed(pg, away(98), speed=None, t=T0 + 9000)          # 9 s: still too short
    check("no speed sent, fixes less than 10 s after the reference fix give no speed: still waiting", state_of(pg)["waiting"] == "stop", json.dumps(state_of(pg)))
    feed(pg, away(99), speed=None, t=T0 + 10000)         # 10 s after the arrival fix: about 100 m in 10 s
    check("the first speed comes 10 s after the reference fix, and one fast fix is not enough", state_of(pg)["waiting"] == "stop", json.dumps(state_of(pg)))
    feed(pg, away(101), speed=None, t=T0 + 11000)
    check("a second fast fix in a row: the guide goes on", state_of(pg)["waiting"] is None and state_of(pg)["passed"] == ["7"], json.dumps(state_of(pg)))
    ctx.close()

    # driving away with no speed sent, at 5 and 8 m/s, fixes every 1 or 2 s, from a drive stop (7) and from a parking spot (10)
    ip10 = next(i for i, l in enumerate(legs) if l["to"].get("o") == 10 and l["to"]["kind"] == "park")
    dep10 = next(i for i in range(ip10 + 1, len(legs)) if legs[i]["mode"] == "drive")
    for name, o, sl, dl in (("stop 7", 7, i7, i7 + 1), ("parking spot of stop 10", 10, ip10, dep10)):
        leg_end = legs[sl]["geom"][-1]
        Pd = Path(legs[dl]["geom"])
        for v_ms, dt_ms in ((5, 1000), (5, 2000), (8, 1000), (8, 2000)):
            ctx, pg = guidance_page(br)
            pg.evaluate("(i) => setLeg(i)", sl)
            feed(pg, leg_end, speed=None, t=T0)
            w0, t, resumed = state_of(pg)["waiting"], T0, None
            step = v_ms * dt_ms / 1000.0
            for k in range(1, int(min(400, Pd.total) / step)):
                t += dt_ms
                ll = Pd.ll(step * k)
                feed(pg, ll, speed=None, t=t)
                if state_of(pg)["waiting"] is None:
                    resumed = hav_m(ll, leg_end)
                    break
            r = state_of(pg)
            check("no speed sent, driving away from %s at %d m/s with a fix every %d s: the guide goes on, more than 80 m away, stop %d Passed" % (name, v_ms, dt_ms // 1000, o),
                  w0 in ("stop", "park") and resumed is not None and resumed > 80 and r["passed"] == [str(o)], "waiting at start %s, resumed %s m from the stop, %s" % (w0, resumed and round(resumed), json.dumps(r)))
            ctx.close()

    # walk-in stops 10 and 26: the driver parks, then walks to the meter without tapping Walk to meter. The guide must neither
    # jump to the next stop nor say Off route. A device with no speed shows a walker 1.4 m/s; one GPS fix can be 4 m off.
    for o in (10, 26):
        ip = next(i for i, l in enumerate(legs) if l["to"].get("o") == o and l["to"]["kind"] == "park")
        W = Path(legs[ip + 1]["geom"])
        park = legs[ip]["geom"][-1]
        # (label, device speed, kind of GPS error, size in m). blip: one fix 4 m east. step: from the first fix more than 85 m from the
        # parking spot on, the fixes are d m off and stay off: along the walk, sideways, or sideways with accuracy 30 m (a Wi-Fi style jump).
        for label, dev_speed, kind, d in (("device speed 1.4 m/s", 1.4, None, 0), ("no speed", None, None, 0), ("no speed, one fix 4 m off", None, "blip", 4),
                                          ("no speed, a 4 m step that stays", None, "east", 4), ("no speed, a 5 m step along the walk that stays", None, "along", 5),
                                          ("no speed, a 10 m sideways step that stays", None, "side", 10),
                                          ("no speed, a 15 m jump with accuracy 30 m that stays", None, "wifi", 15)):
            ctx, pg = guidance_page(br)
            pg.evaluate("(i) => setLeg(i)", ip)
            feed(pg, park, t=T0)
            waiting0 = state_of(pg)["waiting"]
            pg.evaluate("() => { window.__spoken = []; }")
            t, stepped, ox, oy, acc, max_d = T0, False, 0.0, 0.0, 5, 0.0
            for k in range(1, int(W.total / 1.4)):
                t += 1000
                s_at = 1.4 * k
                b = math.radians(W.bearing(s_at))
                ux, uy = math.sin(b), math.cos(b)                 # the direction of the walk (east, north)
                if kind and not stepped and hav_m(W.ll(s_at), park) > 85:
                    stepped = True
                    ox, oy = {"blip": (d, 0.0), "east": (d, 0.0), "along": (d * ux, d * uy), "side": (d * uy, -d * ux), "wifi": (d * uy, -d * ux)}[kind]
                    acc = 30 if kind == "wifi" else 5
                elif kind == "blip" and stepped:
                    ox = oy = 0.0
                ll = W.ll(s_at, ox, oy)
                max_d = max(max_d, hav_m(ll, park))
                feed(pg, ll, acc=acc, speed=dev_speed, t=t)
            r = pg.evaluate("() => ({waiting: S.waiting, leg: S.legIdx, passed: Object.keys(S.passed), off: S.offRoute, spoken: window.__spoken})")
            check("walk-in stop %d, %s: the walker reaches %.0f m from the parking spot (past the 80 m limit)%s" % (o, label, max_d, ", GPS error made" if kind else ""),
                  waiting0 == "park" and max_d > 85 and (not kind or stepped), "waiting at start: %s" % waiting0)
            check("walk-in stop %d, %s: the guide does not go on to the next stop" % (o, label),
                  r["waiting"] == "park" and r["leg"] == ip and r["passed"] == [], json.dumps(r))
            check("walk-in stop %d, %s: no Off route. is spoken to the walker" % (o, label), not r["off"] and "Off route." not in r["spoken"], json.dumps(r["spoken"]))
            ctx.close()

    # ---------- 21. waiting at a stop: Off route only for a vehicle driving more than 80 m away ----------
    P0 = Path(legs[0]["geom"])                           # leg 0 drives to the parking spot of stop 1
    end0 = legs[0]["geom"][-1]
    near = P0.side_point(P0.total, 60)                   # 60 m from the parking spot, and more than 45 m from the leg line
    farp = P0.side_point(P0.total, 100)
    ctx, pg = guidance_page(br)
    check("park-stop test setup: side points 60 m and 100 m from the parking spot exist",
          near is not None and farp is not None and hav_m(near, end0) <= 80 < hav_m(farp, end0), "")
    feed(pg, end0)
    check("arriving at the parking spot of stop 1 waits for a tap", state_of(pg)["waiting"] == "park", json.dumps(state_of(pg)))
    cue = "() => ({off: S.offRoute, cnt: S.offCnt, waiting: S.waiting, spoken: window.__spoken.filter(x => x === 'Off route.').length})"
    for _ in range(5):
        feed(pg, near, speed=1)
    r = pg.evaluate(cue)
    check("60 m from the parking spot and still waiting: no off-route count", r["off"] is False and r["cnt"] == 0 and r["spoken"] == 0, json.dumps(r))
    for _ in range(5):
        feed(pg, farp, speed=1)
    r = pg.evaluate("() => ({off: S.offRoute, cnt: S.offCnt, waiting: S.waiting, spoken: window.__spoken.filter(x => x === 'Off route.').length, calls: window.__osrmSignals.length})")
    check("100 m from the parking spot at 1 m/s (a walker) and still waiting: no off-route count, no cue, no reroute request",
          r["off"] is False and r["cnt"] == 0 and r["waiting"] == "park" and r["spoken"] == 0 and r["calls"] == 0, json.dumps(r))
    ctx.close()

    # walk-in stops 1 and 10: the reader reaches the meter, does not tap Done, walks back to the car and drives away. The meter
    # wait ends like a drive stop (2 fixes, over 3 m/s, over 80 m from the meter): Passed, past the walk back, to the next drive.
    for o in (1, 10):
        iw = next(i for i, l in enumerate(legs) if l["to"].get("o") == o and l["to"]["kind"] == "stop")
        idr = next(i for i in range(iw + 2, len(legs)) if legs[i]["mode"] == "drive")
        meter, nxt_o = legs[iw]["geom"][-1], legs[idr]["to"]["o"]
        Pc, Pn = Path(legs[iw + 1]["geom"]), Path(legs[idr]["geom"])    # the walk back to the car, the drive after it
        ctx, pg = guidance_page(br)
        pg.evaluate("(i) => { S.fix = null; setLeg(i); }", iw)
        feed(pg, meter)
        w0 = state_of(pg)
        pg.evaluate("() => { window.__spoken = []; }")
        s = 0.0
        while s < Pc.total:
            feed(pg, Pc.ll(s), speed=1.4)
            s += 5
        feed(pg, Pc.ll(Pc.total), speed=0)
        r_walk = pg.evaluate("() => ({waiting: S.waiting, leg: S.legIdx, off: S.offRoute})")
        resumed, s = None, 0.0
        while s <= Pn.total:
            ll = Pn.ll(s)
            feed(pg, ll, speed=8, heading=Pn.bearing(s))
            if state_of(pg)["waiting"] is None:
                resumed = hav_m(ll, meter)
                break
            s += 8
        r = pg.evaluate("() => ({waiting: S.waiting, leg: S.legIdx, passed: Object.keys(S.passed), off: S.offRoute, spoken: window.__spoken, calls: window.__osrmSignals.length})")
        check("walk-in stop %d test setup: the meter is reached on a walk leg and waits for Done; the car leg, then the drive to stop %d follow" % (o, nxt_o),
              legs[iw]["mode"] == "walk" and legs[iw + 1]["to"]["kind"] == "car" and w0["waiting"] == "stop" and w0["leg"] == iw, json.dumps(w0))
        check("walk-in stop %d: walking back to the car at 1.4 m/s without Done keeps the wait at the meter" % o,
              r_walk["waiting"] == "stop" and r_walk["leg"] == iw and r_walk["off"] is False, json.dumps(r_walk))
        check("walk-in stop %d: driving away at 8 m/s, the guide goes on without Done, more than 80 m from the meter, past the walk back to the drive to stop %d" % (o, nxt_o),
              r["waiting"] is None and r["leg"] == idr and resumed is not None and resumed > 80,
              "resumed %s m from the meter, leg %s, waiting %s" % (resumed and round(resumed), r["leg"], r["waiting"]))
        check("walk-in stop %d: the stop is Passed and the guide says Continuing to stop %d." % (o, nxt_o),
              r["passed"] == [str(o)] and ("Continuing to stop %d." % nxt_o) in r["spoken"], json.dumps(r))
        check("walk-in stop %d: no Off route. and no reroute request before or during this" % o,
              "Off route." not in r["spoken"] and r["calls"] == 0 and r["off"] is False, json.dumps(r))
        ctx.close()

    # ---------- 22. after the route is complete there is no route to be off ----------
    il = len(legs) - 1
    end_d = legs[il]["geom"][-1]
    Qf = Path([end_d, [end_d[0] + 0.0020, end_d[1] + 0.0020]])      # a straight line about 280 m long, away from the depot
    ctx, pg = guidance_page(br)
    pg.evaluate("(i) => setLeg(i)", il)
    feed(pg, end_d, speed=0)
    check("finish test setup: arriving at the depot ends the route", state_of(pg)["waiting"] == "finish" and Qf.total > 250, json.dumps(state_of(pg)))
    pg.evaluate("() => { window.__spoken = []; }")
    for d in range(10, int(Qf.total), 20):
        feed(pg, Qf.ll(d), speed=8)
    r = pg.evaluate("() => ({waiting: S.waiting, off: S.offRoute, cnt: S.offCnt, calls: window.__osrmSignals.length, spoken: window.__spoken.filter(x => x === 'Off route.').length})")
    far_end = hav_m(Qf.ll(Qf.total - 10), end_d)
    check("after Finish, driving %.0f m away at 8 m/s: no Off route. and no reroute request" % far_end,
          far_end > 200 and r["waiting"] == "finish" and r["off"] is False and r["cnt"] == 0 and r["calls"] == 0 and r["spoken"] == 0, json.dumps(r))
    ctx.close()

    # ---------- 23. a gap in the fixes across the U-turn must not send the guide back down the outbound lane ----------
    # (last good fix before the gap, first fix after it on the return lane); the U-turn is at 446 m. The first pair is the main case.
    gap_cases = [(int(s_turn) - 200, int(s_turn) + 150), (int(s_turn) - 300, int(s_turn) + 250), (int(s_turn) - 140, int(s_turn) + 100)]
    for g_from, g_resume in gap_cases:
        ctx, pg = guidance_page(br)
        pg.evaluate("(i) => setLeg(i)", i_u)
        top = 0.0
        for s in range(0, g_from + 1, 20):
            top = max(top, feed(pg, PU.ll(s), speed=10))
        pg.evaluate("() => { window.__spoken = []; }")
        worst_back, wrong, trace = 0.0, [], []
        for k, s in enumerate(range(g_resume, int(PU.total) - 50, 15)):
            a = feed(pg, PU.ll(s), speed=10)
            top = max(top, a)
            worst_back = max(worst_back, top - a)
            trace.append((s, round(a)))
            if abs(a - s) > 25:
                wrong.append(k)
        spoken = pg.evaluate("() => window.__spoken")
        label = "gap from %d m to %d m" % (g_from, g_resume)
        check("%s: no match goes back more than 30 m from the highest one so far" % label, worst_back <= 30.5,
              "largest step back %.0f m; %s" % (worst_back, trace[:6]))
        check("%s: back on the return lane within a few fixes (every fix from the fifth is within 25 m)" % label,
              not [k for k in wrong if k >= 4], "wrong fixes %s" % wrong)
        if (g_from, g_resume) == gap_cases[0]:
            check("%s: no U-turn prompt is spoken after the U-turn point" % label, not [x for x in spoken if "U-turn" in x], json.dumps(spoken))
        ctx.close()

    for g_from, g_resume in gap_cases:                   # the same gaps when the fixes carry a heading
        ctx, pg = guidance_page(br)
        pg.evaluate("(i) => setLeg(i)", i_u)
        for s in range(0, g_from + 1, 20):
            feed(pg, PU.ll(s), speed=10, heading=PU.bearing(s))
        pg.evaluate("() => { window.__spoken = []; }")
        errs = [abs(feed(pg, PU.ll(s), speed=10, heading=PU.bearing(s)) - s) for s in range(g_resume, int(PU.total) - 50, 15)]
        spoken = pg.evaluate("() => window.__spoken")
        label = "gap from %d m to %d m with headings" % (g_from, g_resume)
        check("%s: the first fix after the gap is already on the return lane, and so are all the rest" % label,
              max(errs) <= 25, "largest error %.0f m, first %.0f m" % (max(errs), errs[0]))
        check("%s: no U-turn prompt is spoken after the U-turn point" % label, not [x for x in spoken if "U-turn" in x], json.dumps(spoken))
        ctx.close()

    ctx, pg = guidance_page(br)
    pg.evaluate("(i) => setLeg(i)", i_u)
    errs = [abs(feed(pg, PU.ll(s), speed=10, heading=PU.bearing(s)) - s) for s in range(0, int(PU.total) - 60, 20)]
    check("with headings, driving the whole out-and-back leg (through the U-turn) stays within 25 m of the true distance",
          max(errs) <= 25, "largest error %.0f m" % max(errs))
    ctx.close()

    # ---------- 24. stuck states: a second tap to skip, no guidance to stops already closed, a start screen after the last leg ----------
    def li(o, kind):
        """Index of the leg that ends at stop o with the given kind (stop, park or car)."""
        return next(i for i, l in enumerate(legs) if l["to"].get("o") == o and l["to"]["kind"] == kind)

    def nums(pg, what):
        return pg.evaluate("() => Object.keys(S.%s).map(Number).sort((a, b) => a - b)" % what)

    def at(pg):
        return pg.evaluate("() => ({leg: S.legIdx, waiting: S.waiting})")

    # a. Skip needs a second tap within 4 s
    i2 = li(2, "stop")
    ctx, pg = guidance_page(br)
    pg.evaluate("(i) => setLeg(i)", i2)
    check("skip test setup: the drive to stop 2 is leg %d and the button reads Skip stop" % i2,
          legs[i2]["mode"] == "drive" and text(pg, "#aSkip") == "Skip stop", text(pg, "#aSkip"))
    pg.click("#aSkip")
    r = at(pg)
    check("one tap on Skip does not skip: nothing is skipped or reached, and the leg stays",
          r["leg"] == i2 and nums(pg, "skipped") == [] and nums(pg, "done") == [], json.dumps(r))
    check("after one tap the button reads Tap again to skip", text(pg, "#aSkip") == "Tap again to skip", text(pg, "#aSkip"))
    feed(pg, legs[i2]["geom"][0])                        # a GPS fix redraws the card
    check("a GPS fix does not take the Tap again to skip text away", text(pg, "#aSkip") == "Tap again to skip", text(pg, "#aSkip"))
    pg.click("#aSkip")
    r = at(pg)
    check("a second tap within 4 s skips stop 2 and moves to the next leg", nums(pg, "skipped") == [2] and r["leg"] == i2 + 1, json.dumps(r))
    check("on the next leg the button reads Skip stop again", text(pg, "#aSkip") == "Skip stop", text(pg, "#aSkip"))
    pg.click("#aSkip")                                   # arms the button on the drive to stop 3
    pg.evaluate("(i) => setLeg(i)", i2 + 2)
    check("moving to another leg takes the armed state away", text(pg, "#aSkip") == "Skip stop" and nums(pg, "skipped") == [2], text(pg, "#aSkip"))
    pg.click("#aSkip")                                   # arms the button on the drive to stop 4
    pg.wait_for_timeout(4400)
    check("4 s after the first tap the button reads Skip stop again", text(pg, "#aSkip") == "Skip stop", text(pg, "#aSkip"))
    pg.click("#aSkip")
    r = at(pg)
    check("a tap after the 4 s are over only arms the button again: stop 4 is not skipped",
          nums(pg, "skipped") == [2] and r["leg"] == i2 + 2 and text(pg, "#aSkip") == "Tap again to skip", json.dumps(r))
    ctx.close()

    # b. Skip on the walk-in leg of stop 12 goes to the walk back to the car, not to the next drive
    ip12, iw12, ic12 = li(12, "park"), li(12, "stop"), li(12, "car")
    ctx, pg = guidance_page(br)
    pg.evaluate("(i) => setLeg(i)", iw12)
    check("walk-in skip test setup: the walk to stop 12 is leg %d and the car leg of stop 12 follows it" % iw12,
          legs[iw12]["mode"] == "walk" and ic12 == iw12 + 1 and legs[ic12]["mode"] == "walk", "")
    pg.click("#aSkip")
    pg.click("#aSkip")
    r = at(pg)
    check("a confirmed skip on the walk-in leg of stop 12 goes to the car leg of stop 12",
          nums(pg, "skipped") == [12] and r["leg"] == ic12 and r["waiting"] is None, json.dumps(r))
    check("... and the card says Walk back to the car", text(pg, "#cSub").startswith("Walk back to the car"), text(pg, "#cSub"))
    pg.evaluate("(i) => setLeg(i)", ip12)                # still driving to the parking spot: nobody is on foot, so skip drives on
    pg.click("#aSkip")
    pg.click("#aSkip")
    r = at(pg)
    check("a confirmed skip on the drive to the parking spot of stop 12 goes to the next drive leg (stop 13)",
          r["leg"] == li(13, "stop") and legs[r["leg"]]["mode"] == "drive", json.dumps(r))
    ctx.close()

    # c. Go to stop 12 with stops 13, 14 and 15 closed: after its walk the guide drives on to stop 16
    ctx, pg = guidance_page(br)
    pg.evaluate("() => { [13, 14, 15].forEach(o => markStop(o, 'done')); }")
    pg.click("#fList")
    pg.locator("#row12 button").click()
    pg.wait_for_timeout(400)
    check("Go to stop 12 starts at its parking-spot leg", at(pg)["leg"] == ip12, json.dumps(at(pg)))
    feed(pg, legs[ip12]["geom"][-1])
    check("at the parking spot of stop 12 the guide waits", at(pg)["waiting"] == "park", json.dumps(at(pg)))
    pg.click("#aNext")                                   # Walk to meter
    feed(pg, legs[iw12]["geom"][-1])
    check("at stop 12 on foot the guide waits for Done", at(pg)["waiting"] == "stop" and at(pg)["leg"] == iw12, json.dumps(at(pg)))
    pg.click("#aNext")                                   # Done, walk back
    check("Done at stop 12 starts the walk back to the car", at(pg)["leg"] == ic12 and nums(pg, "done") == [12, 13, 14, 15], json.dumps(at(pg)))
    feed(pg, legs[ic12]["geom"][-1])                     # back at the car
    r = at(pg)
    check("back at the car, the guide drives on to stop 16 and not to stops 13, 14 or 15",
          r["leg"] == li(16, "stop") and legs[r["leg"]]["mode"] == "drive" and r["waiting"] is None, json.dumps(r))
    ctx.close()

    def go(pg, i):
        """setLeg(i) with no saved fix: setLeg replays the newest fix, which could arrive at the end of the leg the test just left."""
        pg.evaluate("(i) => { S.fix = null; setLeg(i); }", i)

    # e. every other way to move on after a stop passes over closed stops too
    i3, i4 = li(3, "stop"), li(4, "stop")
    ctx, pg = guidance_page(br)
    pg.evaluate("() => markStop(3, 'done')")
    go(pg, i2)
    feed(pg, legs[i2]["geom"][-1])                       # stop 2 reached by driving (no ATTENTION meter): auto advance
    check("auto advance after stop 2 passes over stop 3, which is closed", at(pg)["leg"] == i4, json.dumps(at(pg)))
    go(pg, i2)
    pg.click("#aNext")                                   # Reached, next
    check("Reached, next after stop 2 passes over stop 3", at(pg)["leg"] == i4, json.dumps(at(pg)))
    go(pg, i2)
    pg.click("#aSkip")
    pg.click("#aSkip")
    check("Skip stop (two taps) at stop 2 passes over stop 3, and skips only stop 2",
          at(pg)["leg"] == i4 and nums(pg, "skipped") == [2], json.dumps([at(pg), nums(pg, "skipped")]))
    ip10 = li(10, "park")
    pg.evaluate("() => markStop(11, 'skip')")
    go(pg, ip10)
    feed(pg, legs[ip10]["geom"][-1])
    pg.click("#aSkip")                                   # Read from car
    check("Read from car at the parking spot of stop 10 passes over stop 11, which was skipped",
          at(pg)["leg"] == ip12 and 10 in nums(pg, "done"), json.dumps(at(pg)))
    pg.evaluate("() => { markStop(8, 'done'); markStop(11, 'done'); }")
    go(pg, i7)
    feed(pg, end7)                                       # stop 7 has an ATTENTION meter: the guide waits
    feed(pg, away(100), speed=5)
    feed(pg, away(100), speed=5)                         # driving away: the guide goes on without a tap
    r = at(pg)
    check("auto-resume from stop 7 passes over stop 8, which is closed, and goes to stop 9",
          r["leg"] == li(9, "stop") and r["waiting"] is None, json.dumps(r))
    check("... and says that stop 9 comes next", "Continuing to stop 9." in pg.evaluate("() => window.__spoken"), "")
    # a closed walk-in stop (10): from the drive before it, the guide goes past its parking, walk and walk-back legs to the drive to stop 11;
    # from its own walk leg, the walk back to the car is the next leg
    pg.evaluate("() => { S.done = {}; S.skipped = {}; S.passed = {}; markStop(10, 'done'); }")
    r = pg.evaluate("(a) => typeof nextOpenLeg === 'function' ? [nextOpenLeg(a[0]), nextOpenLeg(a[1])] : null", [li(9, "stop"), li(10, "stop")])
    check("with walk-in stop 10 closed, the next leg after stop 9 is the drive to stop 11, and after its walk the walk back to the car",
          r == [li(11, "stop"), li(10, "car")], json.dumps(r))
    pg.evaluate("() => { S.passed[10] = Date.now(); delete S.done[10]; }")
    r = pg.evaluate("(a) => typeof nextOpenLeg === 'function' ? [nextOpenLeg(a[0]), nextOpenLeg(a[1])] : null", [li(9, "stop"), len(legs) - 2])
    check("a passed stop is closed too, and the drive back to the depot is always open",
          r == [li(11, "stop"), len(legs) - 1], json.dumps(r))
    ctx.close()

    # d. the last leg saved: the start screen offers a new drive first, and a way to look at the stops
    NEW_BUILT_24 = "12/01/2026"
    ctx = br.new_context(viewport={"width": 800, "height": 1280}, geolocation=DEPOT, permissions=["geolocation"])
    rstate = {"edit": None, "served": None}
    ctx.route(ROUTE_URL, route_editor(rstate))
    pg = ctx.new_page()
    attach(pg)
    pg.goto(BASE + "?reset=1")
    pg.wait_for_selector("#startBtns button", timeout=20000)
    pg.click("#startBtns button")                        # Start pins the route
    pg.wait_for_timeout(600)
    n_legs = pg.evaluate("() => S.legs.length")

    def end_screen(edit=None):
        """The drive is over (last leg, finished at the depot, some stops marked); open the app again. Returns the start screen buttons."""
        pg.evaluate("(n) => { markStop(1, 'done'); markStop(2, 'skip'); setLeg(n - 1); arrived(); }", n_legs)
        rstate["edit"] = edit
        pg.reload()
        pg.wait_for_selector("#startBtns button", timeout=20000)
        return pg.evaluate("() => [...document.querySelectorAll('#startBtns button')].map(b => b.textContent)")

    btns = end_screen()
    check("with the drive finished, the start screen offers Start a new drive at stop 1 first, then Review the last drive",
          btns == ["Start a new drive at stop 1", "Review the last drive"], json.dumps(btns))
    check("... and not Start guidance or Resume", pg.evaluate("() => S.legIdx") == n_legs - 1 and "Resume" not in " ".join(btns), json.dumps(btns))
    pg.click('#startBtns button:has-text("Review the last drive")')
    pg.wait_for_timeout(300)
    r = pg.evaluate("""() => { const b = document.getElementById('pBody').getBoundingClientRect(), e = document.elementFromPoint(b.left + b.width / 2, b.top + 30);
        return {shown: document.getElementById('panel').classList.contains('show'), rows: document.querySelectorAll('#pBody .row').length,
                over: !!e && document.getElementById('panel').contains(e), started: S.started}; }""")
    check("Review the last drive opens the stop list, in front of the start screen, without starting the drive",
          r["shown"] and r["rows"] == 43 and r["over"] and r["started"] is False, json.dumps(r))
    pg.screenshot(path=os.path.join(SHOTS, "24-review-last-drive.png"))
    pg.locator("#row12 button").click()                  # Go from the list while the start screen is up
    pg.wait_for_timeout(300)
    btns2 = pg.evaluate("() => [...document.querySelectorAll('#startBtns button')].map(b => b.textContent)")
    check("Go on a stop in that list makes the start screen offer Resume at stop 12 (the buttons are redrawn)",
          btns2[0] == "Resume at stop 12" and pg.evaluate("() => S.started") is False, json.dumps(btns2))
    btns = end_screen()
    pg.click('#startBtns button:has-text("Start a new drive at stop 1")')
    tap(pg, '#startBtns button:has-text("Tap again to clear progress")')      # the second tap confirms
    pg.wait_for_timeout(500)
    r = pg.evaluate("() => ({leg: S.legIdx, done: Object.keys(S.done), skipped: Object.keys(S.skipped), started: S.started, built: S.route.built})")
    check("Start a new drive at stop 1 after the finished drive (two taps): leg 0, nothing reached, drive started",
          r["leg"] == 0 and r["done"] == [] and r["skipped"] == [] and r["started"] and r["built"] == ROUTE_BUILT, json.dumps(r))
    # a newer route waits too: the same two buttons, and the new drive uses the new route
    btns = end_screen(lambda t: t.replace('"built":"' + ROUTE_BUILT + '"', '"built":"' + NEW_BUILT_24 + '"', 1))
    line = pg.evaluate("() => document.getElementById('newRouteLine') ? document.getElementById('newRouteLine').textContent : null")
    check("drive finished and a new route waiting: the same two buttons, and the new-route line shows",
          btns == ["Start a new drive at stop 1", "Review the last drive"] and line is not None and NEW_BUILT_24 in line, json.dumps([btns, line]))
    pg.click('#startBtns button:has-text("Start a new drive at stop 1")')
    tap(pg, '#startBtns button:has-text("Tap again to clear progress")')      # the second tap confirms
    pg.wait_for_timeout(500)
    r = pg.evaluate("() => ({leg: S.legIdx, done: Object.keys(S.done), built: S.route.built, pending: S.pending, started: S.started, sig: lsGet('activeSig', null)})")
    check("Start a new drive at stop 1 with a new route waiting uses the new route",
          r["leg"] == 0 and r["done"] == [] and r["built"] == NEW_BUILT_24 and r["pending"] is None and r["started"] and r["sig"] == fnv1a_py(rstate["served"]), json.dumps(r))
    ctx.close()

    # ---------- 25. final review fixes ----------
    def snap(pg):
        """Drive state and start screen buttons."""
        r = pg.evaluate("""() => ({leg: S.legIdx, done: Object.keys(S.done).map(Number), started: S.started, finished: S.finished,
            stored: lsGet('finished', null), shown: getComputedStyle(document.getElementById('start')).display !== 'none'})""")
        r["btns"] = start_btns(pg)
        return r

    # a. voice prompts only on the leg: Go to stop 30, then a fix 1 km from its leg, past its end
    i30 = li(30, "stop")
    P30 = Path(legs[i30]["geom"])
    qa, qb = P30.at(P30.total - 20), P30.at(P30.total)
    qn = math.hypot(qb[0] - qa[0], qb[1] - qa[1])
    far_xy = (qb[0] + (qb[0] - qa[0]) / qn * 1000, qb[1] + (qb[1] - qa[1]) / qn * 1000)
    far30, d30 = P30.to_ll(far_xy), P30.nearest(far_xy)[0]
    ctx, pg = guidance_page(br)
    pg.click("#fList")
    pg.locator("#row30 button").click()
    pg.wait_for_timeout(300)
    pg.evaluate("() => { window.__spoken = []; }")
    feed(pg, far30, speed=10)
    r = pg.evaluate("""() => ({leg: S.legIdx, off: S.nav ? S.nav.off : null, offRoute: S.offRoute, spoken: window.__spoken,
        cls: document.getElementById('banner').className, instr: document.getElementById('bInstr').textContent})""")
    check("prompt test setup: Go to stop 30 (leg %d), then a fix %.0f m from its leg, past its end" % (i30, d30),
          r["leg"] == i30 and d30 >= 900 and r["off"] is not None and r["off"] >= 900, json.dumps(r))
    check("a fix 1 km from the leg speaks no maneuver or arrival prompt", r["spoken"] == [], json.dumps(r["spoken"]))
    check("... and the banner shows the direct arrow to the stop (the off-route display)",
          "off" in r["cls"].split() and r["instr"].startswith("Off route. Head ") and r["instr"].endswith(" to stop 30"), json.dumps(r))
    feed(pg, P30.ll(P30.total - 30), speed=10)
    sp = pg.evaluate("() => window.__spoken")
    check("on the leg, 30 m before its end, the arrival prompt is spoken", "Arriving at stop 30" in sp, json.dumps(sp))
    ctx.close()

    # b. two taps for every button that clears progress, with the Skip time (CFG.skipConfirmMs)
    ctx, pg = guidance_page(br)
    pg.evaluate("() => { markStop(2, 'done'); S.fix = null; setLeg(5); }")
    pg.reload()
    pg.wait_for_selector("#startBtns button", timeout=20000)
    pg.evaluate("() => { CFG.skipConfirmMs = 1500; }")
    b0 = start_btns(pg)
    tap(pg, '#startBtns button:has-text("Start a new drive at stop 1")')
    r1 = snap(pg)
    check("start screen: one tap on Start a new drive at stop 1 clears nothing and reads Tap again to clear progress",
          b0 == ["Resume at stop 4", "Start a new drive at stop 1"] and r1["leg"] == 5 and r1["done"] == [2] and r1["shown"]
          and not r1["started"] and r1["btns"] == ["Resume at stop 4", "Tap again to clear progress"], json.dumps([b0, r1]))
    pg.wait_for_timeout(1800)
    r2 = snap(pg)
    check("... after CFG.skipConfirmMs (here 1.5 s) the text goes back and nothing is cleared",
          r2["btns"] == b0 and r2["leg"] == 5 and r2["done"] == [2], json.dumps(r2))
    tap(pg, '#startBtns button:has-text("Start a new drive at stop 1")')
    pg.wait_for_timeout(1800)
    tap(pg, '#startBtns button:has-text("Start a new drive at stop 1")')
    r3 = snap(pg)
    check("a tap after that time only arms the button again: nothing cleared", r3["leg"] == 5 and r3["done"] == [2] and not r3["started"], json.dumps(r3))
    tap(pg, '#startBtns button:has-text("Tap again to clear progress")')
    r4 = snap(pg)
    check("a second tap within the time starts a new drive: leg 0, nothing reached", r4["leg"] == 0 and r4["done"] == [] and r4["started"], json.dumps(r4))
    pg.evaluate("() => { markStop(3, 'done'); }")
    pg.click("#fList")
    pg.click("#bReset")
    t1, d1 = text(pg, "#bReset"), pg.evaluate("() => Object.keys(S.done)")
    pg.wait_for_timeout(1800)
    t2 = text(pg, "#bReset")
    check("stop list: one tap on Start a new drive clears nothing, reads Tap again to clear progress, and goes back after CFG.skipConfirmMs",
          t1 == "Tap again to clear progress" and d1 == ["3"] and t2 == "Start a new drive", json.dumps([t1, d1, t2]))
    pg.click("#pClose")

    # c. newDrive() is the one way to a new drive
    r = pg.evaluate("""() => { if (typeof newDrive !== 'function') return null;
        S.done = {1: 1}; S.skipped = {2: 1}; S.passed = {7: 1}; S.finished = true; S.legIdx = 9;
        lsSet('leg', 9); lsSet('done', S.done); lsSet('skipped', S.skipped); lsSet('passed', S.passed); lsSet('finished', true);
        const swap = newDrive({adopt: true});
        return {swap, leg: S.legIdx, done: S.done, skipped: S.skipped, passed: S.passed, finished: S.finished,
                stored: ['leg', 'done', 'skipped', 'passed', 'finished'].map(k => lsGet(k, null))}; }""")
    check("newDrive clears leg, done, skipped, passed and finished, in memory and in storage (no route waiting: no switch)",
          r is not None and r["swap"] is False and r["leg"] == 0 and r["done"] == {} and r["skipped"] == {} and r["passed"] == {}
          and r["finished"] is False and r["stored"] == [0, {}, {}, {}, False], json.dumps(r))
    ctx.close()

    # d. the finished flag: driving back to the depot resumes in one tap; only a finished drive offers a new one first
    ctx, pg = guidance_page(br)
    pg.evaluate("(n) => { markStop(1, 'done'); S.fix = null; setLeg(n - 1); }", len(legs))
    pg.reload()
    pg.wait_for_selector("#startBtns button", timeout=20000)
    r = snap(pg)
    check("driving back to the depot (last leg, not finished): the start screen offers Resume: return to McCluskey Services first",
          r["btns"] == ["Resume: return to McCluskey Services", "Start a new drive at stop 1"] and r["stored"] is not True, json.dumps(r))
    tap(pg, '#startBtns button:has-text("Resume: return to McCluskey Services")')
    pg.wait_for_timeout(300)
    r = snap(pg)
    check("one tap on Resume: return to McCluskey Services resumes the last leg with the progress kept",
          r["started"] and r["leg"] == len(legs) - 1 and r["done"] == [1], json.dumps(r))
    pg.evaluate("() => arrived()")                      # Finish at the depot
    fin = pg.evaluate("() => lsGet('finished', null)")
    pg.reload()
    pg.wait_for_selector("#startBtns button", timeout=20000)
    r = snap(pg)
    check("finished at the depot: the flag is saved, and the start screen offers Start a new drive at stop 1, then Review the last drive",
          fin is True and r["btns"] == ["Start a new drive at stop 1", "Review the last drive"], json.dumps([fin, r]))
    tap(pg, '#startBtns button:has-text("Start a new drive at stop 1")')
    r = snap(pg)
    check("after a finished drive one tap on Start a new drive at stop 1 clears nothing yet",
          r["leg"] == len(legs) - 1 and r["done"] == [1] and not r["started"] and r["btns"][0] == "Tap again to clear progress", json.dumps(r))
    tap(pg, '#startBtns button:has-text("Tap again to clear progress")')
    pg.wait_for_timeout(300)
    r = snap(pg)
    check("the second tap starts a new drive and clears the finished flag",
          r["started"] and r["leg"] == 0 and r["done"] == [] and r["finished"] is False and r["stored"] is False, json.dumps(r))
    ctx.close()

    # e. a drive with only a passed stop keeps its pinned route when a new route arrives
    ctx = br.new_context(viewport={"width": 800, "height": 1280}, geolocation=DEPOT, permissions=["geolocation"])
    rstate = {"edit": None, "served": None}
    ctx.route(ROUTE_URL, route_editor(rstate))
    pg = ctx.new_page()
    attach(pg)
    pg.goto(BASE + "?reset=1")
    pg.wait_for_selector("#startBtns button", timeout=20000)
    pg.click("#startBtns button")                        # Start pins the route
    pg.wait_for_timeout(600)
    pg.evaluate("() => { S.passed[7] = Date.now(); lsSet('passed', S.passed); }")
    r0 = pg.evaluate("() => ({leg: lsGet('leg', null), done: lsGet('done', null), skipped: lsGet('skipped', null)})")
    rstate["edit"] = lambda t: t.replace('"built":"' + ROUTE_BUILT + '"', '"built":"10/15/2026"', 1)
    pg.reload()
    ok = opened(pg)
    r = pg.evaluate("() => ({passed: Object.keys(S.passed), built: S.route && S.route.built, pending: S.pending ? S.pending.route.built : null})")
    check("a drive with only a passed stop (leg 0, nothing reached or skipped) keeps the pinned route and the passed stop when a new route arrives",
          ok and r0 == {"leg": 0, "done": {}, "skipped": {}} and r["passed"] == ["7"] and r["built"] == ROUTE_BUILT and r["pending"] == "10/15/2026",
          json.dumps([r0, r]))
    ctx.close()

    # f. the app page opens at once from the saved copy (stale while revalidate); version -3; every save inside e.waitUntil
    SW_TEXT = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sw.js"), encoding="utf-8").read()
    puts = [ln.strip() for ln in SW_TEXT.splitlines() if "cache.put(" in ln]
    check("sw.js: every cache.put runs inside e.waitUntil", bool(puts) and all("e.waitUntil(" in ln for ln in puts), " | ".join(puts))
    ctx = br.new_context(viewport={"width": 800, "height": 1280}, geolocation=DEPOT, permissions=["geolocation"])
    hold, held = {"on": False}, []
    ctx.route(PAGE_URL, lambda route: held.append(route) if hold["on"] else route.continue_())
    pg = ctx.new_page()
    attach(pg)
    pg.goto(BASE + "?reset=1")
    pg.wait_for_selector("#startBtns button", timeout=20000)
    sw_controls(pg)
    wait_for(pg, lambda: "Offline ready." in text(pg, "#startBody"), timeout=20)
    v = pg.evaluate("async () => ({app: APP_VERSION, caches: (await caches.keys()).filter(k => k.startsWith('amr-nav-'))})")
    check("app version 2026.09.30-3 and one worker cache, amr-nav-2026.09.30-3", v["app"] == "2026.09.30-3" and v["caches"] == ["amr-nav-2026.09.30-3"], json.dumps(v))
    hold["on"] = True
    pg.goto("about:blank")
    t0 = time.time()
    pg.goto(BASE)
    pg.wait_for_selector("#startBtns button", timeout=20000)
    dt = time.time() - t0
    check("the server holds the app page: the saved page opens at once (under 2 s, no 3 s wait)", dt < 2.0 and len(held) >= 1, "%.1f s, held=%d" % (dt, len(held)))
    hold["on"] = False
    for h in held:
        h.fulfill(status=200, content_type="text/html; charset=utf-8", body=h.fetch().text().replace("<head>", "<head><!-- AMR-SWR-MARK -->", 1))
    held.clear()
    saved = pump_until(pg, lambda: "AMR-SWR-MARK" in pg.evaluate(saved_page), timeout=8)
    check("the page that arrives late is saved for the next open", saved)
    pg.goto("about:blank")
    pg.goto(BASE)
    pg.wait_for_selector("#startBtns button", timeout=20000)
    check("the next open shows that refreshed page", pg.evaluate("() => document.head.innerHTML.includes('AMR-SWR-MARK')"))
    ctx.close()

    # g. a damaged route.json: never saved by the worker; the app runs on the pin, else on the saved copy, else the load error
    ctx = br.new_context(viewport={"width": 800, "height": 1280}, geolocation=DEPOT, permissions=["geolocation"])
    rstate = {"edit": None, "served": None}
    ctx.route(ROUTE_URL, route_editor(rstate))
    pg = ctx.new_page()
    attach(pg)
    pg.goto(BASE + "?reset=1")
    pg.wait_for_selector("#startBtns button", timeout=20000)
    sw_controls(pg)
    wait_for(pg, lambda: "Offline ready." in text(pg, "#startBody"), timeout=20)
    damaged = lambda t: t[:5000]
    rstate["edit"] = damaged
    pg.reload()
    ok = opened(pg)
    good = pg.evaluate("""async () => { const r = await caches.match('route.json'); if (!r) return null;
        try { const j = JSON.parse(await r.text()); return Array.isArray(j.legs) ? j.legs.length : -1; } catch (e) { return -2; } }""")
    check("damaged route.json test setup: the reply is 5000 bytes of %d" % len(ROUTE_TEXT), rstate["served"] is not None and len(rstate["served"]) == 5000)
    check("a damaged route.json reply is not saved: the worker keeps the good copy", good == len(legs), str(good))
    check("damaged reply and no pinned route: the app opens on the copy the worker saved", ok and "43 stops" in text(pg, "#startBody"), text(pg, "#startBody")[:80])
    rstate["edit"] = None
    pg.reload()
    pg.wait_for_selector("#startBtns button", timeout=20000)
    tap(pg, "#startBtns button")                         # Start pins the route
    pg.wait_for_timeout(500)
    pg.evaluate("() => { markStop(2, 'done'); S.fix = null; setLeg(5); }")
    rstate["edit"] = damaged
    pg.reload()
    ok = opened(pg)
    r = pg.evaluate("() => ({leg: S.legIdx, done: Object.keys(S.done), built: S.route && S.route.built, pending: S.pending})")
    r["btns"] = start_btns(pg)
    check("damaged reply with a pinned drive: the app runs on the pinned route, progress kept",
          ok and r["leg"] == 5 and r["done"] == ["2"] and r["built"] == ROUTE_BUILT and r["pending"] is None and r["btns"][:1] == ["Resume at stop 4"], json.dumps(r))
    pg.evaluate("""async () => { localStorage.removeItem('amrNav.v1.activeRoute');
        for (const k of await caches.keys()) { const c = await caches.open(k); await c.delete('route.json'); } }""")
    n_err = len(errors)
    pg.reload()
    msg = wait_for(pg, lambda: (lambda m: m if ("did not load" in m or "43 stops" in m) else None)(text(pg, "#startBody")), timeout=10) or ""
    new_errs = errors[n_err:]
    del errors[n_err:]                                   # the one expected console error of this step
    check("damaged reply, no pin and no saved copy: the app shows the load error",
          "The route did not load." in msg and len(new_errs) == 1 and "route.json is missing or damaged" in new_errs[0], msg + " | " + " || ".join(new_errs))
    ctx.close()

    # h. GPS lost: nothing in the simulator; while the guide waits, only the chip changes
    ctx, pg = guidance_page(br)
    feed(pg, [DEPOT["latitude"], DEPOT["longitude"]])
    r = pg.evaluate("""() => { S.fixAt = Date.now() - 11000; checkFixAge();
        return {chip: document.getElementById('gps').textContent, then: document.getElementById('bThen').textContent}; }""")
    check("simulator (?sim=1): the GPS-lost check does nothing", r["chip"].startswith("GPS ±") and "GPS lost" not in r["then"], json.dumps(r))
    ctx.close()
    ctx, pg = guidance_page(br, sim=False)
    ip10 = li(10, "park")
    for label, li_, pt, want in (("stop 7 (waiting for Done)", i7, end7, "stop"), ("the parking spot of stop 10", ip10, legs[ip10]["geom"][-1], "park"),
                                 ("the finish", len(legs) - 1, legs[-1]["geom"][-1], "finish")):
        pg.evaluate("(i) => { S.fix = null; setLeg(i); }", li_)
        feed(pg, pt)
        before = pg.evaluate("() => ({waiting: S.waiting, then: document.getElementById('bThen').textContent})")
        r = pg.evaluate("""() => { S.fixAt = Date.now() - 11000; checkFixAge();
            return {chip: document.getElementById('gps').textContent, then: document.getElementById('bThen').textContent}; }""")
        check("waiting at %s: GPS lost changes the chip, and the banner keeps its line %r" % (label, before["then"]),
              before["waiting"] == want and r["chip"] == "GPS lost" and r["then"] == before["then"], json.dumps([before, r]))
    ctx.close()

    # i. a return to the app (visibilitychange) starts the GPS only after the route has loaded, and never in the simulator
    for sim in (True, False):
        ctx = br.new_context(viewport={"width": 800, "height": 1280}, geolocation=DEPOT, permissions=["geolocation"])
        hold, held = {"on": True}, []
        ctx.route(ROUTE_URL, lambda route: held.append(route) if hold["on"] else route.continue_())
        pg = ctx.new_page()
        attach(pg)
        pg.goto(BASE + ("?sim=1&reset=1" if sim else "?reset=1"))
        pump_until(pg, lambda: len(held) > 0, timeout=10)
        pg.evaluate("() => document.dispatchEvent(new Event('visibilitychange'))")
        w1 = pg.evaluate("() => watchId")
        hold["on"] = False
        for h in held:
            h.continue_()
        held.clear()
        pg.wait_for_selector("#startBtns button", timeout=20000)
        pg.evaluate("() => document.dispatchEvent(new Event('visibilitychange'))")
        w2 = pg.evaluate("() => watchId")
        if sim:
            check("simulator: a return to the app while the route is still loading does not start the GPS, nor after it loaded",
                  w1 is None and w2 is None, json.dumps([w1, w2]))
        else:
            check("a return to the app while the route is still loading does not start the GPS; the finished load starts it",
                  w1 is None and w2 is not None, json.dumps([w1, w2]))
        ctx.close()

    # j. the screen lock: one at a time; after the system drops it, ask again at most once per CFG.wakeRetryMs
    WAKE_MOCK = """
    window.__wake = {requests: 0, sentinels: []};
    Object.defineProperty(Navigator.prototype, 'wakeLock', {configurable: true, get() { return {request: async () => {
      window.__wake.requests++;
      const s = new EventTarget(); s.released = false;
      s.release = async () => { if (!s.released) { s.released = true; s.dispatchEvent(new Event('release')); } };
      window.__wake.sentinels.push(s); return s; }}; }});
    """
    live = "() => ({requests: __wake.requests, live: __wake.sentinels.filter(s => !s.released).length})"
    ctx, pg = guidance_page(br, init=WAKE_MOCK)
    r0 = pg.evaluate(live)
    for _ in range(3):
        pg.evaluate("() => document.dispatchEvent(new Event('visibilitychange'))")
    pg.wait_for_timeout(200)
    r1 = pg.evaluate(live)
    check("screen lock: Start asks once, and returns to the app while it is held ask no more (one lock)",
          r0 == {"requests": 1, "live": 1} and r1 == {"requests": 1, "live": 1}, json.dumps([r0, r1]))
    pg.evaluate("() => { CFG.wakeRetryMs = 1500; }")
    pg.wait_for_timeout(1600)                            # the last request is now older than CFG.wakeRetryMs
    pg.evaluate("() => __wake.sentinels[0].release()")
    pg.wait_for_timeout(200)
    r2 = pg.evaluate(live)
    check("the system drops the lock: the app asks again at once", r2 == {"requests": 2, "live": 1}, json.dumps(r2))
    pg.evaluate("() => __wake.sentinels[1] && __wake.sentinels[1].release()")
    pg.wait_for_timeout(200)
    r3 = pg.evaluate(live)
    check("dropped again within CFG.wakeRetryMs: no request at once (no loop)", r3 == {"requests": 2, "live": 0}, json.dumps(r3))
    pg.wait_for_timeout(1600)
    r4 = pg.evaluate(live)
    check("... one request when that time is over, and one lock again", r4 == {"requests": 3, "live": 1}, json.dumps(r4))
    ctx.close()

    # k. streetShown() decides the street map for applyTiles, zoomLayers and the layer button
    ctx = br.new_context(viewport={"width": 800, "height": 1280}, geolocation=DEPOT, permissions=["geolocation"])
    ctx.route(TILE_URL, lambda route: route.fulfill(status=200, content_type="image/png", body=PNG_1PX))
    pg = ctx.new_page()
    attach(pg)
    pg.goto(BASE + "?reset=1")
    pg.wait_for_selector("#startBtns button", timeout=20000)
    pg.click("#startBtns button")
    pg.wait_for_timeout(500)
    pg.evaluate("() => { map.setZoom(16, {animate: false}); }")
    r = pg.evaluate("""() => { const out = {}; window.__realStreet = window.streetShown;
        const lay = () => ({tiles: map.hasLayer(tileLayer), base: map.hasLayer(baseGroup), bldg: map.hasLayer(bldgGroup)});
        S.tiles = false; window.streetShown = () => true; applyTiles(); zoomLayers(); out.on = lay();
        S.tiles = true; window.streetShown = () => false; applyTiles(); zoomLayers(); out.off = lay();
        return out; }""")
    check("applyTiles and zoomLayers follow streetShown(): shown, street tiles only; not shown, the offline map with buildings",
          r["on"] == {"tiles": True, "base": False, "bldg": False} and r["off"] == {"tiles": False, "base": True, "bldg": True}, json.dumps(r))
    pg.click("#fLayer")                                  # streetShown() says not shown (saved choice on): the button turns the street map on
    r = pg.evaluate("() => { const t = S.tiles; window.streetShown = window.__realStreet; applyTiles(); return t; }")
    check("the layer button follows streetShown() too", r is True, str(r))
    ctx.close()

    # l. a reroute reply that comes after the driver is back on the route is dropped
    ctx = br.new_context(viewport={"width": 800, "height": 1280}, geolocation=DEPOT, permissions=["geolocation"])
    held = []
    ctx.route(OSRM_URL, lambda route: held.append(route))
    pg = ctx.new_page()
    attach(pg)
    pg.add_init_script(CAPTURE_SPEECH)
    pg.goto(BASE + "?sim=1&reset=1")
    pg.wait_for_selector("#startBtns button", timeout=20000)
    pg.click("#startBtns button")
    pg.wait_for_timeout(800)
    P0 = Path(legs[0]["geom"])
    far0 = far_point(legs[0]["geom"])
    feed(pg, P0.ll(0))
    for k in range(3):
        feed(pg, [far0[0], far0[1] + 0.00001 * k], speed=8)
    asked = pump_until(pg, lambda: len(held) > 0, timeout=8)
    was_off = pg.evaluate("() => S.offRoute")
    feed(pg, P0.ll(100), speed=8)                        # back on the route before the reply comes
    back = pg.evaluate("() => !S.offRoute")
    pg.evaluate("() => { window.__spoken = []; }")
    if held:
        release(held[0], osrm_reply(legs[0]["geom"]))
    pg.wait_for_timeout(1000)
    r = pg.evaluate("() => ({override: !!S.override, spoken: window.__spoken})")
    check("a reroute reply that comes after the driver is back on the route is dropped: no new leg, no Route updated.",
          asked and was_off and back and r["override"] is False and "Route updated." not in r["spoken"], json.dumps([asked, was_off, back, r]))
    for h in held[1:]:
        try:
            release(h, {"code": "NoRoute"})
        except Exception:
            pass
    ctx.close()

    # m. a speed worked out from two fixes counts only when both fixes are 20 m or better
    ctx, pg = at_stop7_no_speed()                        # the arrival fix has accuracy 5 m
    for k, s in enumerate(range(20, 301, 20)):           # 20 m every 2 s is 10 m/s, every fix with accuracy 25 m
        feed(pg, P7.ll(s), acc=25, speed=None, t=T0 + 2000 * (k + 1))
    r = state_of(pg)
    check("no speed sent, driving away at 10 m/s with every fix at accuracy 25 m (over 20 m): no speed, still waiting",
          r["waiting"] == "stop" and r["passed"] == [], json.dumps(r))
    ctx.close()
    ctx, pg = guidance_page(br)
    pg.evaluate("(i) => setLeg(i)", i7)
    feed(pg, end7, acc=30, speed=None, t=T0)             # the arrival fix, later the reference for a speed, has accuracy 30 m
    w0 = state_of(pg)["waiting"]
    feed(pg, away(95), acc=5, speed=None, t=T0 + 10000)
    feed(pg, away(101), acc=5, speed=None, t=T0 + 11000)
    r1 = state_of(pg)
    check("good fixes measured from a reference fix at accuracy 30 m give no speed either: still waiting",
          w0 == "stop" and r1["waiting"] == "stop", json.dumps([w0, r1]))
    feed(pg, away(200), acc=5, speed=None, t=T0 + 21000)
    feed(pg, away(210), acc=5, speed=None, t=T0 + 22000)
    r2 = state_of(pg)
    check("... and two fast fixes measured from good fixes: the guide goes on", r2["waiting"] is None and r2["passed"] == ["7"], json.dumps(r2))
    ctx.close()
    br.close()

errs = [e for e in errors if "favicon" not in e]
check("no console errors or page errors", not errs, " || ".join(errs[:6]))
print("SUMMARY", sum(1 for r in results if r[1]), "of", len(results), "passed")
sys.exit(0 if all(r[1] for r in results) else 1)
