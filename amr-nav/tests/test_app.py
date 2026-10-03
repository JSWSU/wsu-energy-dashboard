"""Browser test for the AMR Route Guide (Playwright, headless Chromium).

Run from the repository root while a static server serves the repository root:
    py -m http.server 41999 --bind 127.0.0.1   (another port: set AMR_TEST_PORT to it)
    py amr-nav\\tests\\test_app.py
No check calls a server other than 127.0.0.1: rerouting runs on the page, on graph.json (the road map). Section 26
drives offline with every other host blocked and recorded, and checks the router, its words and its speed. It also runs
the reference router, Graph.route() in build_graph.py of the sensus-amr-read-cycle skill (folder scripts/route-guide, or
the folder in the environment variable AMR_ROUTE_GUIDE): the app's router must give the same costs, and each new leg that
sections 4 and 26 put in place must be the reference route from the same fix, drawn on the road map (leg_problems()).
Interception of route.json, graph.json and the page uses ctx.route (context level), because page.route does not see
the requests that the service worker makes. A request that a handler lets through ignores set_offline, so the
offline steps remove the handler first, or route only the hosts they block. An offline step that reloads or opens a page
also aborts every request to 127.0.0.1 (Offline below): Playwright 1.58 lets the service worker reach the server after an
offline reload, so set_offline alone does not prove that the page came from the worker's cache.
"""
import base64
import json
import math
import os
import random
import re
import subprocess
import sys
import time
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright
from playwright.sync_api._generated import Browser

# Every context records speech instead of playing it: headless Chromium sends speechSynthesis to the Windows voice,
# which plays on the laptop speakers. Pages that read the words still add CAPTURE_SPEECH (it keeps this list).
SILENCE = "window.__spoken=window.__spoken||[];try{speechSynthesis.speak=u=>window.__spoken.push(u.text);speechSynthesis.cancel=()=>{}}catch(e){}"
_new_context = Browser.new_context


def _silent_context(self, *a, **k):
    ctx = _new_context(self, *a, **k)
    ctx.add_init_script(SILENCE)
    return ctx


Browser.new_context = _silent_context

PORT = int(os.environ.get("AMR_TEST_PORT", "41999"))     # the port of the static server (8765 is blocked on this PC)
BASE = f"http://127.0.0.1:{PORT}/amr-nav/"
RG_DIR = os.environ.get("AMR_ROUTE_GUIDE") or os.path.join(os.path.expanduser("~"), ".claude", "skills", "sensus-amr-read-cycle",
                                                           "scripts", "route-guide")
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


ROUTE_URL = re.compile(r"/amr-nav/route\.json(\?.*)?$")
GRAPH_URL = re.compile(r"/amr-nav/graph\.json(\?.*)?$")
PAGE_URL = re.compile(r"/amr-nav/(index\.html)?(\?.*)?$")
TILE_URL = re.compile(r"https://tile\.openstreetmap\.org/")
PNG_1PX = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
# counts the app's reroute() calls (window.__reroutes) and keeps whether the guide was off route at each one. Run it after
# the page has loaded: onFix calls reroute() through the global object, so the wrapper sees every call.
COUNT_REROUTES = """() => { window.__reroutes = 0; window.__rerouteOff = [];
    const f = window.reroute;
    window.reroute = function () { window.__reroutes++; window.__rerouteOff.push(S.offRoute); return f.apply(this, arguments); }; }"""
# keeps every planLeg() call: its from point, the end of the leg, the heading, the mode, what routeG() gave (window.__plans), and
# the new leg (window.__planLegs, to find the plan behind S.override). Run it after the page has loaded, like COUNT_REROUTES.
RECORD_PLANS = """() => { window.__plans = []; window.__planLegs = [];
    const f = window.planLeg;
    window.planLeg = function (from, base, hd) { const out = f.apply(this, arguments), r = out.route;
      window.__plans.push({from: [from[0], from[1]], end: base.geom[base.geom.length - 1], hd: hd == null ? null : hd, mode: base.mode,
        lead: CFG.lead[base.mode], snapMax: CFG.snapMax,
        route: r ? {cost: r.cost, net: r.net, gapStart: r.gapStart, gapEnd: r.gapEnd, s: r.s.e, t: r.t.e, against: r.against} : null});
      window.__planLegs.push(out.leg || null);
      return out; }; }"""
# the plan behind the new leg in place (S.override), with that leg's points and length; null when there is none
APPLIED_PLAN = """() => { const k = S.override && window.__planLegs ? window.__planLegs.indexOf(S.override) : -1;
    return k < 0 ? null : Object.assign({geom: S.override.geom, dist: S.override.dist}, window.__plans[k]); }"""


def is_local(url):
    """A request to the test server, or no network request at all (data:, blob:, about:)."""
    u = urlparse(url)
    return u.scheme not in ("http", "https", "ws", "wss") or u.hostname == "127.0.0.1"


EXTERNAL = []        # every request to another host, from the pages that block them (guidance_page and section 26)


def block_external(ctx, log=None):
    """Abort and record every request whose host is not 127.0.0.1. Local requests are not routed, so set_offline still
    applies to them."""
    log = EXTERNAL if log is None else log

    def handler(route):
        log.append(route.request.url)
        route.abort()
    ctx.route(lambda url: not is_local(url), handler)


class Offline:
    """No network for ctx: set_offline(True), and every request to the test server (127.0.0.1) aborted as well. Playwright
    1.58 lets the service worker reach the server after an offline reload, so set_offline alone cannot prove that a page
    came from the worker's cache. aborted lists the local requests stopped; back_online() removes the route, then sets the
    context online."""

    def __init__(self, ctx):
        self.ctx, self.aborted = ctx, []
        ctx.route(self.local, self.abort)
        ctx.set_offline(True)

    @staticmethod
    def local(url):
        return urlparse(url).hostname == "127.0.0.1"

    def abort(self, route):
        self.aborted.append(route.request.url)
        route.abort("internetdisconnected")

    def back_online(self):
        self.ctx.unroute(self.local, self.abort)
        self.ctx.set_offline(False)


ROUTE_TEXT = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "route.json"), "rb").read().decode("utf-8")
ROUTE_BUILT = json.loads(ROUTE_TEXT)["built"]
GRAPH_TEXT = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "graph.json"), encoding="utf-8").read()
GRAPH_HEAD = json.loads(GRAPH_TEXT)


def load_reference():
    """The reference router, Graph in build_graph.py, on graph.json: (the graph, '') or (None, why it did not load)."""
    try:
        if RG_DIR not in sys.path:
            sys.path.insert(0, RG_DIR)
        import build_graph as BG
        return BG.Graph(json.loads(GRAPH_TEXT)), ""
    except Exception as ex:                              # a missing reference is a failed check, never a skipped one
        return None, "%s: %s. Set AMR_ROUTE_GUIDE to the scripts\\route-guide folder of the sensus-amr-read-cycle skill." % (RG_DIR, ex)


REF, REF_ERR = load_reference()


def micro(x):
    """degrees -> integer micro-degrees, half away from zero (build_graph.micro and the app's micro)"""
    v = x * 1e6
    return int(math.floor(v + 0.5)) if v >= 0 else -int(math.floor(-v + 0.5))


def leg_problems(plan):
    """What makes a new leg the app planned (APPLIED_PLAN) differ from the reference road route: Graph.route() in build_graph.py
    from the same point to the same end, with the same heading. The leg must be that route's pieces on the road map, with a
    straight lead line from the position when the road is more than CFG.lead m away, and a straight tail line to the end when the
    end is 0.5 m or more off the road. Checked: the cost and both snap gaps of the app's route (1e-6), the leg's length (1 m), where
    the lead and tail lines start and end (1 m), and every point of the road part (each vertex, and points at most 5 m apart
    between them) within 1 m of an edge the mode may use. Returns (problems, a short summary); no problems: the same route."""
    if plan is None:
        return ["no new leg in place, or no plan recorded for it"], ""
    if REF is None:
        return ["no reference router: " + REF_ERR], ""
    mode = "car" if plan["mode"] == "drive" else "foot"
    hd = plan["hd"] if mode == "car" else None
    ref, main_only = None, False
    for main_only in ((False, True) if mode == "car" else (False,)):   # planLeg snaps again to the main car network when it must
        ref = REF.route(plan["from"], plan["end"], mode, heading=hd, max_m=plan["snapMax"], main_only=main_only)
        if ref is not None:
            break
    if ref is None or plan["route"] is None:
        return ["the reference finds no route" if ref is None else "the app's plan has no route"], ""
    out, r, geom = [], plan["route"], plan["geom"]
    for k, rk in (("cost", "cost"), ("gapStart", "gap_start"), ("gapEnd", "gap_end")):
        if abs(r[k] - ref[rk]) > 1e-6 * max(1.0, abs(ref[rk])):
            out.append("route %s %.6f, reference %.6f" % (k, r[k], ref[rk]))
    lead, tail = ref["gap_start"] > plan["lead"], ref["gap_end"] >= 0.5
    # the reference route drawn as the app draws a leg, and measured as the app measures one (the el sum runs long: each edge's
    # el is rounded up to the next 0.1 m)
    want_geom = [[q[0] * 1e-6, q[1] * 1e-6] for q in REF.path_points(ref)]
    if lead:
        want_geom.insert(0, list(plan["from"]))
    if tail:
        want_geom.append(list(plan["end"]))
    elif want_geom:
        want_geom[-1] = list(plan["end"])
    want = Path(want_geom).total if len(want_geom) >= 2 else 0.0
    if abs(plan["dist"] - want) > 1.0:
        out.append("the leg is %.1f m, the reference route %.1f m" % (plan["dist"], want))
    sp = REF.snap(micro(plan["from"][0]), micro(plan["from"][1]), mode, hd=hd, max_m=plan["snapMax"], main_only=main_only)[3]
    tp = REF.snap(micro(plan["end"][0]), micro(plan["end"][1]), mode, max_m=plan["snapMax"], main_only=main_only)[3]
    sp, tp = [sp[0] * 1e-6, sp[1] * 1e-6], [tp[0] * 1e-6, tp[1] * 1e-6]
    if len(geom) < 2 or geom[-1] != plan["end"]:
        out.append("the leg does not end at the end of the leg it replaces")
    else:
        if lead and (geom[0] != plan["from"] or hav_m(geom[1], sp) > 1.0):
            out.append("no straight line from the position %s to the road at %s: the leg starts %s, %s" % (plan["from"], sp, geom[0], geom[1]))
        if not lead and hav_m(geom[0], sp) > 1.0:
            out.append("the leg starts at %s, %.1f m from the road at %s" % (geom[0], hav_m(geom[0], sp), sp))
        if tail and hav_m(geom[-2], tp) > 1.0:
            out.append("no straight line from the road at %s to the end: it starts at %s" % (tp, geom[-2]))
    road = geom[1 if lead else 0:len(geom) - 1 if tail else len(geom)]
    ok = lambda e: REF.allowed(e, mode)
    off, n = [], 0
    for a, b in zip(road, road[1:]):
        parts = max(1, math.ceil(hav_m(a, b) / 5.0))
        for j in range(parts + 1):
            q = (a[0] + (b[0] - a[0]) * j / parts, a[1] + (b[1] - a[1]) * j / parts)
            n += 1
            if REF.grid.nearest(micro(q[0]), micro(q[1]), ok=ok, start_m=1.0, max_m=1.0) is None:
                off.append([round(q[0], 6), round(q[1], 6)])
    if off:
        out.append("%d of %d points on the road part are more than 1 m from any %s edge, first %s" % (len(off), n, mode, off[0]))
    summary = "%d points, %.1f m; the reference route %.1f m (road el sum %.1f, lead line %.1f, tail line %.1f), cost %.1f; %d road points checked" % (
        len(geom), plan["dist"], want, ref["net_m"], ref["gap_start"] if lead else 0.0, ref["gap_end"] if tail else 0.0, ref["cost"], n)
    return out, summary


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


def release_all(held):
    """Let every held request go on to the server, so no handler is left waiting when the context closes."""
    for h in held:
        try:
            h.continue_()
        except Exception:
            pass                                       # already answered, or the page went away
    held.clear()


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

    def xy_of(self, ll):
        """A (lat, lon) point in this path's local metres."""
        return (math.radians(ll[1]) * EARTH * self.k, math.radians(ll[0]) * EARTH)

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
    block_external(ctx)                                                          # no other host may be asked; EXTERNAL is checked at the end
    pg = ctx.new_page()
    attach(pg)
    pg.add_init_script(CAPTURE_SPEECH)
    if not sim:
        pg.add_init_script(QUIET_GPS)
    if init:
        pg.add_init_script(init)
    pg.goto(BASE + ("?sim=1&reset=1" if sim else "?reset=1"))
    pg.wait_for_selector("#startBtns button", timeout=20000)
    pg.evaluate(COUNT_REROUTES)                                                  # window.__reroutes counts reroute() calls
    pump_until(pg, lambda: pg.evaluate("() => !!GR || graphErr !== ''"), timeout=10)   # the road map is ready before any fix
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


NO_ROAD_POINT = """() => {   // the first point on rings around the depot (300 m to 3 km out) with no car road within CFG.snapMax
    const d = S.route.depot, k = Math.cos(d.lat * D2R);
    for (let r = 300; r <= 3000; r += 100) for (let a = 0; a < 360; a += 15) {
      const lat = d.lat + r * Math.cos(a * D2R) / (D2R * R), lon = d.lon + r * Math.sin(a * D2R) / (D2R * R * k);
      if (!snapG(GR, micro(lat), micro(lon), 'car', CFG.snapMax)) return [+lat.toFixed(6), +lon.toFixed(6)];
    }
    return null; }"""


def reroute_case(br, mode):
    """Drive off route on leg 0 (real geolocation feed); the app plans a new leg on the device, from graph.json.
    mode 'apply': the new leg is put in place at once.
    mode 'stale': graph.json is held, so the plan waits for it; the app moves to leg 1 (its own setLeg), then graph.json is
    let through and the waiting plan must be dropped; then a fix at the start of leg 1.
    mode 'nosnap': the off-route point has no road within CFG.snapMax: nothing changes and the banner says why."""
    ctx = br.new_context(viewport={"width": 800, "height": 1280}, geolocation=DEPOT, permissions=["geolocation"])
    block_external(ctx)
    held = []
    if mode == "stale":
        ctx.route(GRAPH_URL, lambda route: held.append(route))
    pg = ctx.new_page()
    attach(pg)
    pg.goto(BASE + "?reset=1")
    pg.wait_for_selector("#startBtns button", timeout=20000)
    if mode != "stale":
        pump_until(pg, lambda: pg.evaluate("() => !!GR"), timeout=10)
    pg.evaluate(COUNT_REROUTES)
    pg.evaluate(RECORD_PLANS)
    pg.click("#startBtns button")
    pg.wait_for_timeout(1500)
    out = {"cfg": pg.evaluate("() => ({osrm: 'osrm' in CFG, timeout: 'rerouteTimeoutMs' in CFG, snapMax: CFG.snapMax})")}
    geom0 = pg.evaluate("() => S.legs[0].geom")
    far = pg.evaluate(NO_ROAD_POINT) if mode == "nosnap" else far_point(geom0)
    out["far"] = far
    if far is None:
        ctx.close()
        return out
    out["min_m"] = round(min(hav_m(far, q) for q in geom0))
    fix = {"latitude": far[0], "longitude": far[1], "accuracy": 5}
    for k in range(4):
        fix["longitude"] += 0.00001
        ctx.set_geolocation(fix)
        pg.wait_for_timeout(450)
    out["asked"] = pump_until(pg, lambda: pg.evaluate("() => window.__reroutes > 0"), timeout=10)
    out["off"] = pg.evaluate("() => window.__rerouteOff.length > 0 && window.__rerouteOff.every(Boolean)")   # off route at every call
    if not out["asked"]:
        release_all(held)
        ctx.close()
        return out
    if mode == "apply":
        pump_until(pg, lambda: pg.evaluate("() => !!S.override"), timeout=5)
        out["ends"] = pg.evaluate("() => !!S.override && JSON.stringify(S.override.geom[S.override.geom.length - 1]) === JSON.stringify(S.legs[0].geom[S.legs[0].geom.length - 1])")
        out["plan"] = pg.evaluate(APPLIED_PLAN)          # the plan behind the new leg, for leg_problems()
    elif mode == "stale":
        out["waits"] = pg.evaluate("() => GR === null && document.getElementById('bThen').textContent")
        pg.evaluate("() => setLeg(1)")
        release_all(held)                              # graph.json goes through now: the plan that waited for it runs
        out["graph"] = pump_until(pg, lambda: pg.evaluate("() => !!GR"), timeout=10)
        pg.wait_for_timeout(1000)                      # time for a wrongly accepted plan to land
        leg1 = pg.evaluate("() => S.legs[1].geom[0]")
        ctx.set_geolocation({"latitude": leg1[0], "longitude": leg1[1], "accuracy": 5})
        pg.wait_for_timeout(1500)
    else:
        out["banner"] = pg.evaluate("() => ({cls: document.getElementById('banner').className, instr: document.getElementById('bInstr').textContent, then: document.getElementById('bThen').textContent})")
        out["snapped"] = pg.evaluate("(p) => !!snapG(GR, micro(p[0]), micro(p[1]), 'car', CFG.snapMax)", far)
    out.update(pg.evaluate("() => ({override: !!S.override, legIdx: S.legIdx, done: Object.keys(S.done), waiting: S.waiting})"))
    out["leg0_to"] = pg.evaluate("() => S.legs.slice(0, 1).filter(l => l.to.kind === 'stop').map(l => String(l.to.o))")
    release_all(held)
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
    net_off = Offline(ctx)
    pg.reload()
    ok = wait_for(pg, lambda: "43 stops" in (pg.locator("#startBody").inner_text() or ""), timeout=20)
    check("app loads offline from cache (every request to the server aborted)", ok and net_off.aborted,
          "%d local requests aborted: %s" % (len(net_off.aborted), " ".join(net_off.aborted[:3])))
    pg.screenshot(path=os.path.join(SHOTS, "07-offline-reload.png"))
    net_off.back_online()
    ctx.close()

    # ---------- 2. real geolocation feed (no sim): progress + off route, rerouted on the device ----------
    ctx = br.new_context(viewport={"width": 800, "height": 1280}, geolocation=DEPOT, permissions=["geolocation"])
    block_external(ctx)
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
    check("reroute builds a new leg on the device (graph.json, no routing server)", rer,
          json.dumps(pg.evaluate("() => ({graph: !!GR, note: S.rerouteNote, steps: S.override ? S.override.steps.length : 0})")))
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

    # ---------- 4. reroute guards (the plan is made on the device; graph.json is held to make a plan wait) ----------
    APP_TEXT = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "index.html"), encoding="utf-8").read()
    r = reroute_case(br, "apply")
    plan = r.pop("plan", None)
    check("reroute test setup: off-route point is 250 m+ from leg 0, app plans a new route while off route",
          r.get("asked") and r.get("off") and r.get("min_m", 0) >= 250, json.dumps(r))
    check("the app names no routing server and has no request timeout (CFG.osrm and CFG.rerouteTimeoutMs are gone)",
          r["cfg"]["osrm"] is False and r["cfg"]["timeout"] is False and "routing.openstreetmap.de" not in APP_TEXT, json.dumps(r["cfg"]))
    check("an offline reroute for the current leg is applied, and the new leg ends where leg 0 ends", r.get("override") and r.get("ends"), json.dumps(r))
    probs, summ = leg_problems(plan)
    check("... the new leg is the reference road route from the off-route fix (build_graph.py Graph.route(): the same cost and snap gaps, the length "
          "within 1 m, the lead and tail lines in place, every road point within 1 m of a car edge)",
          plan is not None and r.get("far") and abs(plan["from"][0] - r["far"][0]) < 1e-9 and abs(plan["from"][1] - r["far"][1]) < 0.0001 and not probs,
          "%s; %s" % (summ, "; ".join(probs[:3]) or "the same route"))
    r = reroute_case(br, "stale")
    check("a reroute that waited for graph.json is dropped when the leg changed meanwhile",
          r.get("asked") and r.get("graph") and r.get("waits") == "Loading the road map" and r.get("override") is False, json.dumps(r))
    check("the dropped plan leaves the new leg in place", r.get("legIdx") == 1 and r.get("waiting") is None, json.dumps(r))
    check("the dropped plan marks no stop reached", set(r.get("done", ["?"])) <= set(r.get("leg0_to", [])), json.dumps(r))
    r = reroute_case(br, "nosnap")
    check("nosnap test setup: a point 300 m+ from the depot with no car road within CFG.snapMax (150 m)",
          r.get("far") is not None and r.get("snapped") is False and r["cfg"]["snapMax"] == 150, json.dumps(r))
    check("off route with no road within 490 ft: the reroute is tried, no new leg, leg 0 stays",
          r.get("asked") and r.get("off") and r.get("override") is False and r.get("legIdx") == 0, json.dumps(r))
    check("... the arrow stays and the banner says why in plain words",
          "off" in r.get("banner", {}).get("cls", "").split() and r["banner"]["then"] == "No road within 490 ft. Follow the arrow."
          and r["banner"]["instr"].startswith("Off route. Head "), json.dumps(r.get("banner")))

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
    net_off = Offline(ctx)
    pg.reload()
    pg.wait_for_selector("#startBtns button", timeout=20000)
    st = pg.evaluate("() => ({base: map.hasLayer(baseGroup), tiles: map.hasLayer(tileLayer), saved: S.tiles, online: navigator.onLine})")
    check("offline with the street map saved: offline base map shows, street tiles do not",
          st["base"] is True and st["tiles"] is False and st["saved"] is True and st["online"] is False, json.dumps(st))
    net_off.back_online()
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
    net_off = Offline(ctx)
    pg.goto("about:blank")
    pg.goto(BASE + "?sim=1")
    ok = wait_for(pg, lambda: "43 stops" in (pg.locator("#startBody").inner_text() or ""), timeout=20)
    check("offline, a query address opens from the one saved page", ok)
    check("that offline open still asked the network for the page, and the worker's own request failed",
          any(sw and "?sim=1" in u for u, sw in net_failed), json.dumps(net_failed[:3]))
    net_off.back_online()
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
    # No ctx.route that lets requests through here; offline, Offline aborts the worker's own requests to the server.
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
    net_off = Offline(ctx)
    pg.goto("about:blank")
    pg.goto(BASE)
    ok = wait_for(pg, lambda: "43 stops" in (pg.locator("#startBody").inner_text() or ""), timeout=20)
    check("offline, the app still opens and its start card shows 43 stops", ok, text(pg, "body")[:60])
    check("that offline open still asked the network for the page, and the worker's own request failed (other-file test)",
          any(sw and u.rstrip("?").endswith("/amr-nav/") for u, sw in net_failed), json.dumps(net_failed[:3]))
    net_off.back_online()
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
    # off route sets S.offRoute and calls reroute(); where a road is near, the new leg is in place at once and S.offRoute is
    # false again, so "was off route" is S.offRoute or a reroute() call made while off route
    r = pg.evaluate("() => ({off: S.offRoute, cnt: S.offCnt, rerouted: window.__rerouteOff.some(Boolean), override: !!S.override})")
    check("50 m from the route with a 10 m fix is off route", r["off"] is True or (r["rerouted"] and r["override"]), json.dumps(r))
    ctx.close()

    # ---------- 19. the off-route arrow keeps its frame when the heading drops out ----------
    # The fixes are where no road is within CFG.snapMax: the reroute finds none, so the off-route arrow stays.

    def arrow(pg):
        return pg.evaluate("""() => { const a = document.getElementById('bArrow'), g = a.querySelector('g'), t = a.querySelector('text');
            const m = g ? /rotate\\((-?\\d+) 24 24\\)/.exec(g.getAttribute('transform')) : null;
            return {rot: m ? Number(m[1]) : null, label: t ? t.textContent : null, off: S.offRoute}; }""")

    ctx, pg = guidance_page(br)
    far = pg.evaluate(NO_ROAD_POINT)
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
    r = pg.evaluate("() => ({off: S.offRoute, cnt: S.offCnt, waiting: S.waiting, spoken: window.__spoken.filter(x => x === 'Off route.').length, calls: window.__reroutes})")
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
        r = pg.evaluate("() => ({waiting: S.waiting, leg: S.legIdx, passed: Object.keys(S.passed), off: S.offRoute, spoken: window.__spoken, calls: window.__reroutes})")
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
    r = pg.evaluate("() => ({waiting: S.waiting, off: S.offRoute, cnt: S.offCnt, calls: window.__reroutes, spoken: window.__spoken.filter(x => x === 'Off route.').length})")
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

    # f. the app page opens at once from the saved copy (stale while revalidate); version 2026.10.02-3; every save inside e.waitUntil
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
    check("app version 2026.10.02-3 and one worker cache, amr-nav-2026.10.02-3", v["app"] == "2026.10.02-3" and v["caches"] == ["amr-nav-2026.10.02-3"], json.dumps(v))
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

    # l. a reroute that waited for the road map (graph.json held) is dropped when the driver is back on the route by then
    ctx = br.new_context(viewport={"width": 800, "height": 1280}, geolocation=DEPOT, permissions=["geolocation"])
    block_external(ctx)
    held = []
    ctx.route(GRAPH_URL, lambda route: held.append(route))
    pg = ctx.new_page()
    attach(pg)
    pg.add_init_script(CAPTURE_SPEECH)
    pg.goto(BASE + "?sim=1&reset=1")
    pg.wait_for_selector("#startBtns button", timeout=20000)
    pg.evaluate(COUNT_REROUTES)
    pg.click("#startBtns button")
    pg.wait_for_timeout(800)
    P0 = Path(legs[0]["geom"])
    far0 = far_point(legs[0]["geom"])
    feed(pg, P0.ll(0))
    for k in range(3):
        feed(pg, [far0[0], far0[1] + 0.00001 * k], speed=8)
    asked = pg.evaluate("() => window.__reroutes > 0 && GR === null && S.rerouteNote === 'Loading the road map'")
    was_off = pg.evaluate("() => S.offRoute")
    feed(pg, P0.ll(100), speed=8)                        # back on the route before the road map is ready
    back = pg.evaluate("() => !S.offRoute")
    pg.evaluate("() => { window.__spoken = []; }")
    release_all(held)
    loaded = pump_until(pg, lambda: pg.evaluate("() => !!GR"), timeout=10)
    pg.wait_for_timeout(1000)
    r = pg.evaluate("() => ({override: !!S.override, spoken: window.__spoken})")
    check("a reroute that waited for the road map is dropped when the driver is back on the route by then: no new leg, no Route updated.",
          asked and was_off and back and loaded and r["override"] is False and "Route updated." not in r["spoken"], json.dumps([asked, was_off, back, loaded, r]))
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

    # ---------- 26. rerouting with no network at all: a drive on the installed app, the router, and its speed ----------
    STEP_TYPES = {"depart", "turn", "new name", "continue", "end of road", "offpath", "arrive", "roundabout", "exit roundabout"}
    STEP_MODS = {"", "straight", "slight left", "slight right", "left", "right", "sharp left", "sharp right", "uturn"}
    legs = ROUTE["legs"]

    def off_route_point(i, lo, hi, end_min, modes):
        """A vertex of another leg of the given modes (so it lies on a road or path), lo to hi m from leg i and end_min m or
        more from the end of leg i: the one nearest the middle of that band. Returns (point, distance, the direction of travel
        of that other leg there) or (None, None, None)."""
        P = Path(legs[i]["geom"])
        end = legs[i]["geom"][-1]
        best = None
        for j, l in enumerate(legs):
            if j == i or l["mode"] not in modes:
                continue
            for k, q in enumerate(l["geom"]):
                d = P.nearest(P.xy_of(q))[0]
                if lo <= d <= hi and hav_m(q, end) >= end_min and 0 < k < len(l["geom"]) - 1:
                    key = (abs(d - (lo + hi) / 2), j, q[0], q[1])
                    if best is None or key < best[0]:
                        Q = Path(l["geom"])
                        best = (key, q, d, Q.bearing(Q.cum[k]))
        return (best[1], best[2], best[3]) if best else (None, None, None)

    def fix_state(pg, ll, speed, heading=None):
        """Hand one good fix to onFix and return what the guide made of it."""
        return pg.evaluate("""(a) => { onFix({lat: a[0], lon: a[1], acc: 5, speed: a[2], heading: a[3], t: Date.now()});
            return {off: S.offRoute, d: S.nav ? S.nav.off : null, leg: S.legIdx, waiting: S.waiting}; }""", [ll[0], ll[1], speed, heading])

    ctx = br.new_context(viewport={"width": 800, "height": 1280}, geolocation=DEPOT, permissions=["geolocation"])
    pg = ctx.new_page()
    attach(pg)
    pg.add_init_script(CAPTURE_SPEECH)
    pg.add_init_script(QUIET_GPS)
    pg.goto(BASE + "?reset=1")                           # online once: the worker installs and saves the app, the route and graph.json
    pg.wait_for_selector("#startBtns button", timeout=20000)
    sw = sw_controls(pg)
    ready = wait_for(pg, lambda: "Offline ready." in text(pg, "#startBody"), timeout=20)
    cached = pg.evaluate("async () => { const r = await caches.match('graph.json'); return r ? (await r.text()).length : 0; }")
    check("offline drive setup: the worker controls the page, the start screen says Offline ready., and the worker holds all of graph.json",
          sw and ready and cached == len(GRAPH_TEXT), "saved %s of %d characters" % (cached, len(GRAPH_TEXT)))
    ext = []                                             # every request to a host other than 127.0.0.1 from here on
    ctx.on("request", lambda req: ext.append(req.url) if not is_local(req.url) else None)
    block_external(ctx, ext)
    net_off = Offline(ctx)                               # and no network at all for the test server either
    pg.reload()
    pg.wait_for_selector("#startBtns button", timeout=20000)
    got = pump_until(pg, lambda: pg.evaluate("() => !!GR || graphErr !== ''"), timeout=10)
    st = pg.evaluate("() => ({online: navigator.onLine, n: GR && GR.n, m: GR && GR.m, ms: GR && GR.ms, err: graphErr, start: document.getElementById('startBody').textContent})")
    check("offline: the app opens from the worker's cache and decodes the road map with no network (every request to the server aborted)",
          got and st["online"] is False and st["n"] == GRAPH_HEAD["n"] and st["m"] == GRAPH_HEAD["m"] and "43 stops" in st["start"] and net_off.aborted,
          json.dumps(st)[:300] + " | %d local requests aborted" % len(net_off.aborted))
    pg.evaluate(COUNT_REROUTES)
    pg.evaluate(RECORD_PLANS)
    pg.click("#startBtns button")
    pg.wait_for_timeout(500)

    # a. off route on two drive legs and one walk leg; each time a new leg to the same end, then drive or walk it to the end
    for i, mode in ((0, "drive"), (21, "drive"), (12, "walk")):
        leg = legs[i]
        lo, hi, end_min, v, step, modes = (80, 250, 200, 10, 25, ("drive",)) if mode == "drive" else (40, 120, 80, 1.4, 5, ("drive", "walk"))
        off, d_off, hd_off = off_route_point(i, lo, hi, end_min, modes)
        check("offline drive, leg %d: a %s leg (to %s %s), and an off-route point on another leg's road %d to %d m from it" % (i, mode, leg["to"]["kind"], leg["to"].get("o", ""), lo, hi),
              leg["mode"] == mode and off is not None, "point %s, %s m from the leg" % (off, d_off and round(d_off)))
        if off is None:
            continue
        P = Path(leg["geom"])
        # S.lastReroute = 0: more than CFG.rerouteGapMs (20 s) has passed since the reroute on the leg before
        pg.evaluate("(i) => { S.fix = null; setLeg(i); S.lastReroute = 0; window.__spoken = []; }", i)
        s0 = min(30.0, P.total / 3)
        fix_state(pg, P.ll(s0), v, P.bearing(s0))
        for k in range(4):                               # CFG.offFixes (3) fixes off the leg make it off route; a car on the other
            fix_state(pg, [off[0], off[1] + 0.000004 * k], v, hd_off if mode == "drive" else None)   # road drives along it
        r = pg.evaluate("""(i) => { const o = S.override, base = S.legs[i];
            if (!o) return {override: false, note: S.rerouteNote, off: S.offRoute};
            const rt = prepLeg(o);
            return {override: true, geom: o.geom, baseEnd: base.geom[base.geom.length - 1], sameTo: o.to === base.to, mode: o.mode, dist: o.dist,
              types: o.steps.map(s => s.type), mods: o.steps.map(s => s.mod), words: o.steps.map(s => s.type === 'arrive' ? 'arrive' : instr(s, o.mode)), atStart: o.steps.map(s => !!s.atStart),
              along: rt.steps.map(s => s.along), onLine: Math.max(...rt.steps.map(s => project(rt, s.loc).d)), offRoute: S.offRoute,
              cls: document.getElementById('banner').className, instr: document.getElementById('bInstr').textContent, spoken: window.__spoken}; }""", i)
        if not r["override"]:
            check("offline drive, leg %d: off route, a new leg is planned on the device" % i, False, json.dumps(r))
            continue
        end_ok = r["geom"][-1] == r["baseEnd"] == leg["geom"][-1]
        check("offline drive, leg %d: off route %.0f m from the leg, the device plans a new %s leg that ends at the leg's own end" % (i, d_off, mode),
              end_ok and r["sameTo"] and r["mode"] == mode, "%d points, %.0f m, %d steps" % (len(r["geom"]), r["dist"], len(r["types"])))
        plan = pg.evaluate(APPLIED_PLAN)
        fed = [[off[0], off[1] + 0.000004 * k] for k in range(4)]
        probs, summ = leg_problems(plan)
        check("offline drive, leg %d: the new leg is the reference %s route from the off-route fix (build_graph.py Graph.route(): the same cost and "
              "snap gaps, the length within 1 m, the lead and tail lines in place, every road point within 1 m of a %s edge)"
              % (i, "road" if mode == "drive" else "path", "car" if mode == "drive" else "foot"),
              plan is not None and plan["from"] in fed and not probs, "%s; %s" % (summ, "; ".join(probs[:3]) or "the same route"))
        moves = [(a, m, t) for t, a, m, st in zip(r["types"], r["along"], r["mods"], r["atStart"]) if t not in ("depart", "arrive", "offpath") and not st]
        close = [(x, y) for x, y in zip(moves, moves[1:]) if y[0] - x[0] < 14.9]      # kept apart only when both turn (a jog)
        sided = lambda m: "left" in m or "right" in m or m == "uturn"
        bad_words = [w for w in r["words"] if not w or "undefined" in w or "null" in w or "  " in w]
        check("offline drive, leg %d: sensible steps: depart first, arrive last, known types and turns, plain words, maneuvers under 15 m apart only when both are turns, every step on the line" % i,
              r["types"][0] == "depart" and r["types"][-1] == "arrive" and r["types"].count("arrive") == 1 and set(r["types"]) <= STEP_TYPES
              and set(r["mods"]) <= STEP_MODS and not bad_words and all(sided(x[1]) and sided(y[1]) for x, y in close) and r["onLine"] <= 1.0,
              " | ".join(r["words"]))
        pg.wait_for_timeout(700)                         # the map pans to the position in 0.5 s
        pg.screenshot(path=os.path.join(SHOTS, "26-offline-reroute-leg%02d.png" % i))
        check("offline drive, leg %d: the banner leaves the off-route display and the guide says Route updated." % i,
              not r["offRoute"] and "off" not in r["cls"].split() and "Off route" not in r["instr"] and "Route updated." in r["spoken"],
              "%s | %s" % (r["instr"], json.dumps(r["spoken"][-3:])))
        Q = Path(r["geom"])
        s, worst, offs, last = 0.0, 0.0, 0, None
        while s <= Q.total + step:
            last = fix_state(pg, Q.ll(min(s, Q.total)), v, Q.bearing(min(s, Q.total)))
            if last["leg"] != i or last["waiting"]:
                break
            worst = max(worst, last["d"] or 0)
            offs += 1 if last["off"] else 0
            s += step
        check("offline drive, leg %d: following the new leg stays on it (never off route) and arrives at its end" % i,
              offs == 0 and worst <= 5 and last is not None and (last["leg"] != i or last["waiting"] is not None),
              "largest distance from the line %.1f m, end state %s" % (worst, json.dumps(last)))
    check("offline drive: no request to any host but 127.0.0.1, and the browser was offline", not ext and pg.evaluate("() => !navigator.onLine"),
          " ".join(ext[:5]))

    # b. the router on its own: every pair of consecutive park points, a one-way street, a footway
    PP = [("depot", [ROUTE["depot"]["lat"], ROUTE["depot"]["lon"]])] + [(s["o"], s.get("park") or [s["lat"], s["lon"]]) for s in ROUTE["stops"]]
    PP.append(PP[0])
    pairs = []
    for k in range(len(PP) - 1):
        o = PP[k + 1][0]
        li_ = len(legs) - 1 if o == "depot" else next(j for j, l in enumerate(legs) if l["mode"] == "drive" and l["to"].get("o") == o)
        pairs.append([PP[k][1], PP[k + 1][1], li_])
    res = pg.evaluate("""(pairs) => pairs.map(([a, b, i]) => { const r = routeG(GR, a, b, 'car');
        if (r.fail) return {i, fail: r.fail};
        const wrong = r.pieces.filter(([e, x, y]) => Math.abs(y - x) > 1e-6 && !(GR.fl[e] & (y > x ? F_FWD : F_BWD))).length;
        return {i, length: r.length, wrong}; })""", pairs)
    # keyed by (leg index, stop): after a route rebuild that moves this leg, the key no longer matches and the check fails
    EXPLAINED = {(38, 31): "leg 38: the stop 31 park point is on a footpath (highway=path, access=permissive) that OSRM drove; "
                           "the car route ends on Southeast Forest Way 45.8 m away (offline-graph-validation.txt)"}
    bad, ratios = [], []
    for (ei, eo), why in EXPLAINED.items():
        if not (ei < len(legs) and legs[ei]["mode"] == "drive" and legs[ei]["to"].get("o") == eo):
            bad.append("EXPLAINED (%d, %d) no longer matches route.json: review the note" % (ei, eo))
    for x in res:
        dist = legs[x["i"]]["dist"]
        if "fail" in x or x["wrong"]:
            bad.append(json.dumps(x))
            continue
        if dist >= 1:
            ratio = x["length"] / dist
            ratios.append(ratio)
            if ratio > 1.35 or (ratio < 0.75 and (x["i"], legs[x["i"]]["to"].get("o")) not in EXPLAINED):
                bad.append("leg %d ratio %.2f" % (x["i"], ratio))
        elif x["length"] > 10:
            bad.append("leg %d: %.1f m for a 0 m leg" % (x["i"], x["length"]))
    check("router: a car route joins every pair of consecutive park points (depot, stops 1 to 43, depot), never drives an edge against its one-way flag, "
          "and is at most 1.35 times the route.json leg (and 0.75 or more, except the leg the validation report explains)",
          len(res) == 44 and not bad, "%d routes, ratio %.2f to %.2f; %s; explained: %s" % (len(res), min(ratios or [0]), max(ratios or [0]), "; ".join(bad[:4]) or "none bad",
                                                                                             "; ".join("%s (%.2f)" % (EXPLAINED[(x["i"], legs[x["i"]]["to"].get("o"))], x["length"] / legs[x["i"]]["dist"])
                                                                                                       for x in res if (x["i"], legs[x["i"]]["to"].get("o")) in EXPLAINED and "length" in x)))
    one = pg.evaluate("""() => {
        const cand = [];
        for (let e = 0; e < GR.m; e++) { const f = GR.fl[e]; if (((f & 3) === F_FWD || (f & 3) === F_BWD) && !(f & (F_RESTRICT | F_NOSNAP)) && GR.names[GR.en[e]] && GR.el[e] >= 80) cand.push(e); }
        cand.sort((a, b) => GR.el[b] - GR.el[a] || a - b);
        const at = (e, frac) => { const p = piecePts(GR, e, 0, GR.el[e] * frac).pop(); return [+(p[0] * 1e-6).toFixed(6), +(p[1] * 1e-6).toFixed(6)]; };
        const wrong = r => r.pieces.filter(([e, x, y]) => Math.abs(y - x) > 1e-6 && !(GR.fl[e] & (y > x ? F_FWD : F_BWD))).length;
        for (const e of cand) {
          const a = at(e, 0.2), b = at(e, 0.8), fwd = (GR.fl[e] & 3) === F_FWD;
          const w = fwd ? routeG(GR, a, b, 'car') : routeG(GR, b, a, 'car'), x = fwd ? routeG(GR, b, a, 'car') : routeG(GR, a, b, 'car');
          if (w.fail || x.fail) continue;
          return {e, name: GR.names[GR.en[e]], el: GR.el[e], withPieces: w.pieces.length, withEdge: w.pieces[0][0], withLen: w.length,
                  againstLen: x.length, againstOnIt: x.pieces.filter(([i, p, q]) => i === e && (fwd ? q < p : q > p)).length, wrongAgainst: wrong(x), wrongWith: wrong(w)};
        }
        return null; }""")
    check("router: a one-way street (the longest named one-way edge in graph.json) is driven with its flow and never against it",
          one is not None and one["withPieces"] == 1 and one["withEdge"] == one["e"] and one["againstOnIt"] == 0 and one["wrongAgainst"] == 0
          and one["wrongWith"] == 0 and one["againstLen"] > one["withLen"] + 50, json.dumps(one))
    walk_legs = [i for i, l in enumerate(legs) if l["mode"] == "walk" and l["dist"] > 50]
    foot = pg.evaluate("""(idx) => idx.map(i => { const l = S.legs[i], a = l.geom[0], b = l.geom[l.geom.length - 1];
        const f = routeG(GR, a, b, 'foot'), c = routeG(GR, a, b, 'car');
        if (f.fail) return {i, fail: f.fail};
        const only = f.pieces.filter(([e, x, y]) => Math.abs(y - x) > 1e-6 && !(GR.fl[e] & 3));
        return {i, to: l.to.o, foot: f.length, car: c.fail ? null : c.length, onlyM: only.reduce((s, [e, x, y]) => s + Math.abs(y - x), 0),
                kinds: [...new Set(only.map(([e]) => GR.cl[e]))],
                footBad: f.pieces.filter(([e, x, y]) => Math.abs(y - x) > 1e-6 && !(GR.fl[e] & F_FOOT)).length,
                carBad: c.fail ? 0 : c.pieces.filter(([e, x, y]) => Math.abs(y - x) > 1e-6 && !(GR.fl[e] & 3)).length}; })""", walk_legs)
    classes = GRAPH_HEAD["classes"]
    uses = [x for x in foot if "fail" not in x and x["onlyM"] >= 20 and (x["car"] is None or x["car"] > 1.1 * x["foot"])]
    check("router: every walk leg routes on foot over walkable edges only, and no car route uses an edge that cars may not use",
          all("fail" not in x and x["footBad"] == 0 and x["carBad"] == 0 for x in foot), json.dumps(foot)[:400])
    check("router: on foot the route takes footways where a car cannot go (the car has no route between the same points, or one over 1.1 times longer)",
          bool(uses), "; ".join("walk leg %d to stop %s: %.0f m of %s, foot %.0f m, car %s m" % (x["i"], x["to"], x["onlyM"], "/".join(classes[k] for k in x["kinds"]), x["foot"],
                                                                                                 "none" if x["car"] is None else "%.0f" % x["car"]) for x in uses))

    # d. the router against its reference, Graph.route() in build_graph.py (the rules in its docstring): the same cost, the same
    #    snapped edges and the same start direction for the 44 park-point pairs, every leg in its own profile, and 360 seeded
    #    random trips (car with and without a heading, car snapped to the main network only, foot). Every routed trip is legal.
    snap_max = pg.evaluate("() => CFG.snapMax")
    check("parity setup: the reference router (build_graph.py) loads and reads graph.json", REF is not None, REF_ERR)
    # problems(r, car): what makes a routed trip illegal (an edge against its flags, pieces that do not meet, a barrier passed,
    # a banned turn), from the decoded graph
    PROBLEMS = """(r, car) => { const out = [], P = r.pieces;
        P.forEach(([e, x, y]) => { if (Math.abs(y - x) > 1e-6 && !(GR.fl[e] & (car ? (y > x ? F_FWD : F_BWD) : F_FOOT))) out.push('edge ' + e + ' against its flags'); });
        for (let k = 0; k + 1 < P.length; k++) {
          const e = P[k][0], v = P[k][2] === 0 ? GR.ea[e] : GR.eb[e], e2 = P[k + 1][0];
          if ((P[k + 1][1] === 0 ? GR.ea[e2] : GR.eb[e2]) !== v) out.push('pieces ' + k + ' and ' + (k + 1) + ' do not meet');
          if (!car) continue;
          if (GR.blk[v]) out.push('through barrier node ' + v);
          const rule = GR.xbase[v] >= 0 ? GR.xto[GR.slotOf(v, e)] : null;
          if (rule && (rule.only ? !rule.to.includes(e2) : rule.to.includes(e2))) out.push('banned turn ' + e + ' -> ' + e2 + ' at node ' + v);
        }
        return out; }"""
    prng = random.Random(20261002)

    def near_route(rng, spread):
        """a random point within spread m of a random point of a random leg"""
        i = rng.choice([j for j, l in enumerate(legs) if l["dist"] > 0])
        Pn = Path(legs[i]["geom"])
        ang, dd = rng.random() * 2 * math.pi, rng.random() * spread
        return Pn.ll(rng.random() * Pn.total, dd * math.sin(ang), dd * math.cos(ang))

    cases = [[a, b, "car", None, False] for a, b, _ in pairs]
    cases += [[l["geom"][0], l["geom"][-1], "car" if l["mode"] == "drive" else "foot", None, False] for l in legs if l["dist"] > 0]
    for k in range(360):
        mode = "foot" if k % 4 == 0 else "car"
        cases.append([near_route(prng, 200), near_route(prng, 200), mode, prng.random() * 360 if k % 4 in (1, 2) else None, k % 8 == 3])
    js = pg.evaluate("""(cs) => { const problems = """ + PROBLEMS + """;
        return cs.map(([a, b, m, h, mo]) => { const r = routeG(GR, a, b, m, h, mo);
          return r.fail ? {fail: r.fail} : {cost: r.cost, s: r.s.e, t: r.t.e, sg: r.s.gap, tg: r.t.gap, against: r.against, bad: problems(r, m === 'car')}; }); }""", cases)
    mism, bad_routes, n_ok, n_hd, n_against = [], [], 0, 0, 0
    for (a, b, m, h, mo), j in zip(cases, js):
        py = REF.route(a, b, m, heading=h, max_m=snap_max, main_only=mo) if REF else None
        if "fail" in j or py is None:
            if not ("fail" in j and py is None):
                mism.append("%s %s %s h=%s: app %s, reference %s" % (a, b, m, h, j.get("fail") or round(j["cost"], 3), py and round(py["cost"], 3)))
            continue
        n_ok += 1
        n_hd += h is not None
        n_against += bool(j["against"])
        if j["bad"]:
            bad_routes.append("%s -> %s %s: %s" % (a, b, m, "; ".join(j["bad"][:2])))
        same_s = py["start_edge"] == j["s"] or abs(py["gap_start"] - j["sg"]) < 1e-9      # an exact tie in distance may go either way
        same_t = py["end_edge"] == j["t"] or abs(py["gap_end"] - j["tg"]) < 1e-9
        if abs(py["cost"] - j["cost"]) > 1e-6 * max(1.0, py["cost"]) or not same_s or not same_t or py["start_against"] != j["against"]:
            mism.append("%s %s %s h=%s: app %.6f e%d->e%d %s, reference %.6f e%d->e%d %s" % (a, b, m, h, j["cost"], j["s"], j["t"], j["against"],
                                                                                         py["cost"], py["start_edge"], py["end_edge"], py["start_against"]))
    check("router parity with build_graph.py Graph.route(): %d trips (44 park-point pairs, every leg, 360 random: car with and without a heading, car on the main network only, foot), "
          "the same cost (1e-6), snapped edges and start direction" % len(cases),
          REF is not None and n_ok >= 300 and n_hd >= 100 and n_against >= 5 and not mism,
          "%d routed (%d with a heading, %d planned against it), %d differ: %s" % (n_ok, n_hd, n_against, len(mism), " || ".join(mism[:3])))
    check("every routed trip is legal: no edge against its one-way or mode flag, pieces that meet, no pass through a barrier node, no banned turn",
          n_ok >= 300 and not bad_routes, "%d routed; %s" % (n_ok, " || ".join(bad_routes[:3])))
    rules_js = pg.evaluate("""() => { const out = []; GR.xto.forEach((r, sl) => { if (r) out.push([GR.xnode[sl], GR.xedge[sl], r.only ? 'only' : 'no', [...r.to].sort((a, b) => a - b)]); });
        return out; }""")
    rules_py = sorted([v, f, k, sorted(t)] for (v, f), (k, t) in REF.rule.items()) if REF else None
    check("the app reads the same turn restrictions as the reference (via node, from edge, only or no, to edges)",
          REF is not None and sorted(rules_js) == rules_py, "%d rules in the app, %s in the reference" % (len(rules_js), rules_py and len(rules_py)))

    # e. barriers and turn restrictions on their own: from the middle of one car edge at a barrier node to the middle of another,
    #    and over every banned turn; the route never takes them. A route that must go around (or finds none) shows the rule acts.
    br_r = pg.evaluate("""() => { const out = {blk: [], turns: []};
        const mid = e => { const p = piecePts(GR, e, 0, GR.el[e] / 2).pop(); return [p[0] * 1e-6, p[1] * 1e-6]; };
        const carAt = v => { const o = []; for (let j = GR.ao[v]; j < GR.ao[v + 1]; j++) { const e = GR.adj[j]; if ((GR.fl[e] & 3) && !(GR.fl[e] & F_NOSNAP) && GR.el[e] >= 4) o.push(e); } return o; };
        const arrives = (e, v) => (GR.eb[e] === v && (GR.fl[e] & F_FWD)) || (GR.ea[e] === v && (GR.fl[e] & F_BWD));
        const leaves = (e, v) => (GR.ea[e] === v && (GR.fl[e] & F_FWD)) || (GR.eb[e] === v && (GR.fl[e] & F_BWD));
        const direct = (e1, e2) => GR.cpm[GR.cl[e1]] * GR.el[e1] / 2 + GR.cpm[GR.cl[e2]] * GR.el[e2] / 2;
        const passed = r => r.pieces.slice(0, -1).map(pc => pc[2] === 0 ? GR.ea[pc[0]] : GR.eb[pc[0]]);
        const turned = (r, v, e1, e2) => r.pieces.some((pc, k) => k + 1 < r.pieces.length && pc[0] === e1 && r.pieces[k + 1][0] === e2 && passed(r)[k] === v);
        const run = (e1, e2) => { const r = routeG(GR, mid(e1), mid(e2), 'car', null, false);
          return !r.s || !r.t || r.s.e !== e1 || r.t.e !== e2 ? null : r; };     // null: the test points did not snap to these edges
        for (let v = 0; v < GR.n; v++) if (GR.blk[v]) {
          const es = carAt(v);
          es.forEach(e1 => es.forEach(e2 => { if (e1 === e2 || !arrives(e1, v) || !leaves(e2, v)) return;
            const r = run(e1, e2); if (!r) return;
            out.blk.push({v, e1, e2, through: !r.fail && passed(r).includes(v), around: !!r.fail || r.cost > direct(e1, e2) + 1e-6}); })); }
        GR.xto.forEach((rule, sl) => { if (!rule) return; const v = GR.xnode[sl], f = GR.xedge[sl];
          const tos = rule.only ? carAt(v).filter(e => e !== f && leaves(e, v) && !rule.to.includes(e)) : rule.to.filter(e => leaves(e, v));
          tos.forEach(t => { const r = run(f, t); if (!r) return;
            out.turns.push({v, f, t, only: rule.only, banned: !r.fail && turned(r, v, f, t), around: !!r.fail || r.cost > direct(f, t) + 1e-6}); }); });
        const problems = """ + PROBLEMS + """;
        out.leg40 = [[46.7268228, -117.1658191], [46.7266166, -117.1672591], [46.7261526, -117.1671955]].map(p => {
          const r = routeG(GR, p, S.legs[40].geom[S.legs[40].geom.length - 1], 'car', null, false); return r.fail ? ['no route: ' + r.fail] : problems(r, true); });
        return out; }""")
    check("barriers: a car route between two roads that meet at a barrier node never passes it (%d trips; the ones that must go around show it acts)" % len(br_r["blk"]),
          br_r["blk"] and not [x for x in br_r["blk"] if x["through"]] and any(x["around"] for x in br_r["blk"]),
          "%d trips, %d through, %d go around" % (len(br_r["blk"]), sum(x["through"] for x in br_r["blk"]), sum(x["around"] for x in br_r["blk"])))
    check("turn restrictions: a car route over a banned turn never takes it (%d trips: no_* turns and the turns an only_* rule leaves out)" % len(br_r["turns"]),
          br_r["turns"] and not [x for x in br_r["turns"] if x["banned"]] and any(x["around"] for x in br_r["turns"]),
          "%d trips, %d banned turns taken, %d go around" % (len(br_r["turns"]), sum(x["banned"] for x in br_r["turns"]), sum(x["around"] for x in br_r["turns"])))
    check("the three review probe starts near the end of leg 40 route without the bollard on Southeast Nevada Street or a banned turn at Stadium Way and Main Street",
          all(x == [] for x in br_r["leg40"]), json.dumps(br_r["leg40"]))

    # f. the heading: on a divided road the new route starts on the carriageway the car drives; a missed turn gives a U-turn or a
    #    way ahead; the U-turn is said at once
    hdr = pg.evaluate("""(p) => { const out = {};
        [[41, 58], [24, 58], [41, 238], [24, 238]].forEach(([i, h]) => { const pl = planLeg(p, S.legs[i], h);
          if (!pl.leg) { out[i + '/' + h] = {fail: pl.fail}; return; }
          const g = pl.leg.geom, q = g.find(z => hav(z, g[0]) >= 10) || g[g.length - 1];
          pl.leg.to = S.legs[i].to;
          out[i + '/' + h] = {brg: Math.round(bearing(g[0], q)), uturn: !!pl.leg.steps[1] && !!pl.leg.steps[1].atStart,
            words: prepLeg(pl.leg).steps.slice(0, 3).map(s => s.type === 'depart' ? 'depart' : s.type === 'arrive' ? 'arrive' : instr(s, 'drive'))}; });
        const s0 = snapG(GR, micro(p[0]), micro(p[1]), 'car', CFG.snapMax, null, false);
        out.plainFits58 = s0 ? fitsHeading(GR.fl[s0.e], s0.brg, 58) : null;
        return out; }""", [46.7278038, -117.1637859])
    ang_deg = lambda a, b: abs(((a - b + 540) % 360) - 180)       # degrees between two bearings
    check("divided road (Northeast Stadium Way): from one point, heading 58 starts on the northeast carriageway and heading 238 on the southwest one, with no U-turn, to legs 24 and 41",
          hdr["plainFits58"] is False and all("fail" not in hdr[k] and ang_deg(hdr[k]["brg"], int(k.split("/")[1])) <= 45 and not hdr[k]["uturn"] for k in ("41/58", "24/58", "41/238", "24/238")),
          json.dumps(hdr))
    snaps = pg.evaluate("""(seed) => { let x = seed; const rnd = () => { x = (x * 1103515245 + 12345) % 2147483648; return x / 2147483648; };
        const cand = []; for (let e = 0; e < GR.m; e++) { const f = GR.fl[e]; if (((f & 3) === F_FWD || (f & 3) === F_BWD) && !(f & F_NOSNAP) && GR.el[e] > 20) cand.push(e); }
        let n = 0, against = 0, plain = 0;
        for (let k = 0; k < 600; k++) {
          const e = cand[Math.floor(rnd() * cand.length)], pts = piecePts(GR, e, 0, GR.el[e] * (0.1 + 0.8 * rnd())), p = pts[pts.length - 1], q = pts[pts.length - 2];
          const b = segBearing((p[1] - q[1]) * Math.cos(p[0] * 1e-6 * D2R), p[0] - q[0]), hd = (GR.fl[e] & 3) === F_FWD ? b : (b + 180) % 360;
          const r = 8 * rnd(), a = rnd() * 2 * Math.PI, lat = Math.round(p[0] + r * Math.cos(a) / (1e-6 * KM)), lon = Math.round(p[1] + r * Math.sin(a) / (1e-6 * KM * Math.cos(p[0] * 1e-6 * D2R)));
          const s = snapG(GR, lat, lon, 'car', CFG.snapMax, hd, false), s0 = snapG(GR, lat, lon, 'car', CFG.snapMax, null, false);
          if (!s) continue; n++;
          if (!fitsHeading(GR.fl[s.e], s.brg, hd)) against++;
          if (!fitsHeading(GR.fl[s0.e], s0.brg, hd)) plain++; }
        return {n, against, plain}; }""", 20261001)
    check("one-way roads: of 600 positions with up to 8 m GPS error and the legal heading, none snaps to a road it cannot drive that way (without the heading some do)",
          snaps["n"] >= 590 and snaps["against"] == 0 and snaps["plain"] > 0, json.dumps(snaps))
    missed = pg.evaluate("""() => { const side = m => /left/.test(m || '') ? 'L' : /right/.test(m || '') ? 'R' : '';
        let n = 0, uturn = 0, ahead = 0, words = ''; const bad = [];
        S.legs.forEach((leg, i) => { if (leg.mode !== 'drive') return; const rt = prepLeg(leg), xy = rt.xy, k0 = Math.cos(rt.lat0 * D2R);
          const at = d => { let j = 0; while (j < rt.cum.length - 2 && rt.cum[j + 1] < d) j++; const t = Math.max(0, Math.min(1, (d - rt.cum[j]) / ((rt.cum[j + 1] - rt.cum[j]) || 1)));
            return [xy[j][0] + t * (xy[j + 1][0] - xy[j][0]), xy[j][1] + t * (xy[j + 1][1] - xy[j][1])]; };
          rt.steps.forEach(s => { if (!side(s.mod) || /slight/.test(s.mod) || s.type === 'depart' || s.type === 'arrive' || s.along < 20) return;
            const p1 = at(s.along - 15), p2 = at(s.along), hd = (Math.atan2(p2[0] - p1[0], p2[1] - p1[1]) / D2R + 360) % 360;
            const X = [p2[0] + 70 * Math.sin(hd * D2R), p2[1] + 70 * Math.cos(hd * D2R)], ll = [X[1] / (D2R * R), X[0] / (D2R * R * k0)];
            const sn = snapG(GR, micro(ll[0]), micro(ll[1]), 'car', CFG.snapMax, null, false); if (!sn || sn.gap > 10) return;   // the road goes on straight
            const pl = planLeg(ll, leg, hd); if (!pl.leg) return; n++;
            const st = pl.leg.steps[1];
            if (st && st.atStart) { uturn++; words = words || instr(st, 'drive'); return; }
            const g = pl.leg.geom, q = g.find(z => hav(z, g[0]) >= 4) || g[g.length - 1];
            if (angDiff(bearing(g[0], q), hd) <= 90) ahead++; else bad.push([i, s.mod, Math.round(s.along)]); }); });
        return {n, uturn, ahead, bad, words}; }""")
    check("missed turns: on every drive leg the car misses each left or right turn and goes straight on 70 m; the new route starts with Make a U-turn or goes ahead, never back without a word",
          missed["n"] >= 20 and not missed["bad"] and missed["uturn"] >= 1 and missed["ahead"] >= 1 and missed["words"].startswith("Make a U-turn"), json.dumps(missed))

    # g. words against OSRM: every leg over 50 m planned offline from its first point
    W = pg.evaluate("""() => { const side = m => /left/.test(m || '') ? 'L' : /right/.test(m || '') ? 'R' : '';
        const say = (s, mode) => s.type === 'arrive' ? 'arrive' : s.type === 'depart' ? 'depart' : instr(s, mode);
        const res = {agree: 0, sideBad: [], realBad: [], keepExtra: [], turnsOn: {}, words: {}};
        S.legs.forEach((leg, i) => { if (!(leg.dist > 50)) return;
          const p = planLeg(leg.geom[0], leg, null); if (!p.leg) { res.sideBad.push([i, p.fail]); return; }
          p.leg.to = leg.to;
          const mv = a => a.filter(s => s.type !== 'depart' && s.type !== 'arrive'), off = mv(prepLeg(p.leg).steps), osrm = mv(prepLeg(leg).steps);
          res.words[i] = prepLeg(p.leg).steps.map(s => say(s, leg.mode));
          res.turnsOn[i] = off.filter(s => side(s.mod) && s.mod !== 'uturn').length;
          off.forEach(s => { const sd = side(s.mod); if (!sd || s.mod === 'uturn') return;          // 1. left and right as OSRM has them
            let o = null, od = 20; osrm.forEach(t => { if (!side(t.mod) || t.mod === 'uturn') return; const d = hav(t.loc, s.loc); if (d <= od) { od = d; o = t; } });
            if (!o) return; if (side(o.mod) === sd) res.agree++; else res.sideBad.push([i, say(s, leg.mode), say(o, leg.mode), +od.toFixed(1)]); });
          if (leg.mode !== 'drive') return;
          osrm.forEach(t => { if (!/^(sharp )?(left|right)$/.test(t.mod || '') || /roundabout|rotary/.test(t.type)) return;   // 2. a real turn is never Continue or Keep
            const near = off.filter(s => hav(s.loc, t.loc) <= 20); if (!near.length) return;
            if (!near.some(s => side(s.mod) === side(t.mod) && ['turn', 'end of road', 'roundabout'].includes(s.type))) res.realBad.push([i, say(t, 'drive'), near.map(s => say(s, 'drive'))]); });
          off.forEach(s => { if (s.type === 'continue' && side(s.mod) && !osrm.some(t => hav(t.loc, s.loc) <= 30)) res.keepExtra.push([i, say(s, 'drive'), Math.round(s.along)]); });   // 3. no extra Keep
        });
        return res; }""")
    words_of = lambda i: W["words"].get(str(i), [])
    check("offline turns keep their side: every left or right step of every leg over 50 m planned offline has the side of the nearest OSRM maneuver within 20 m",
          W["agree"] >= 80 and not W["sideBad"], "%d agree; %s" % (W["agree"], json.dumps(W["sideBad"][:4])))
    check("legs 0 and 21 planned offline have left or right turn steps, and leg 0 reads as OSRM: end of the road, left onto East Grimes Way; left onto Southeast Dairy Road",
          W["turnsOn"].get("0", 0) >= 1 and W["turnsOn"].get("21", 0) >= 1 and words_of(0)[1:3] == ["At the end of the road, turn left onto East Grimes Way", "Turn left onto Southeast Dairy Road"],
          json.dumps([W["turnsOn"].get("0"), W["turnsOn"].get("21"), words_of(0)]))
    check("a real left or right turn (OSRM) is never said as Continue or Keep; the right-then-left jogs of legs 48 and 49 give both turns",
          not W["realBad"] and words_of(48).count("Turn right") >= 1 and "Turn left" in words_of(48)
          and "At the end of the road, turn right" in words_of(49) and "At the end of the road, turn left onto Northeast TerreView Drive" in words_of(49),
          json.dumps([W["realBad"][:3], words_of(48), words_of(49)]))
    check("no Keep left or Keep right on a drive leg where OSRM has no maneuver within 30 m (a driveway or parking aisle beside the road is no fork)",
          not W["keepExtra"], json.dumps(W["keepExtra"][:6]))
    check("street names: a turn names the road it leads to, not a short stub (leg 21: Thatuna Street, then Colorado Street), and a change of quadrant word is not a new road (leg 43)",
          "Turn right onto Northeast Thatuna Street" in words_of(21) and "At the end of the road, turn left onto Northeast Colorado Street" in words_of(21)
          and not [w for w in words_of(21) if "Campus Street" in w or "Cougar Way" in w] and not [w for w in words_of(43) if w.startswith("Continue onto")],
          json.dumps([words_of(21), words_of(43)]))
    check("U-turns: the U-turn where the two halves of Northeast Stadium Way meet reads Make a U-turn (leg 34); a sharp bend of the two-way Antelope Trail does not (leg 45)",
          "Make a U-turn onto Northeast Stadium Way" in words_of(34) and not [w for w in words_of(45) if "U-turn" in w], json.dumps([words_of(34), words_of(45)]))
    ra = pg.evaluate("""() => { const out = [];
        S.legs.forEach((leg, i) => { if (leg.mode !== 'drive') return; const rt = prepLeg(leg);
          rt.steps.forEach((s, k) => { if (s.type !== 'roundabout' || !s.exit) return;
            const ex = rt.steps.slice(k + 1).find(t => t.type === 'exit roundabout'), a0 = s.along - 60, a1 = (ex ? ex.along : s.along) + 60;
            if (a0 < 0 || a1 > rt.total) return;
            const at = d => { let j = 0; while (j < rt.cum.length - 2 && rt.cum[j + 1] < d) j++; const t = (d - rt.cum[j]) / ((rt.cum[j + 1] - rt.cum[j]) || 1);
              const A = leg.geom[j], B = leg.geom[j + 1]; return [A[0] + t * (B[0] - A[0]), A[1] + t * (B[1] - A[1])]; };
            const p = at(a0), q = at(a1), pl = planLeg(p, {mode: 'drive', geom: [p, q], to: leg.to, dist: 0}, null);
            out.push({i, want: instr(s, 'drive'), words: pl.leg ? prepLeg(Object.assign(pl.leg, {to: leg.to})).steps.map(t => t.type === 'arrive' ? 'arrive' : t.type === 'depart' ? 'depart' : instr(t, 'drive')) : [pl.fail]}); }); });
        return out; }""")
    check("roundabouts: through every roundabout of a drive leg, from 60 m before it to 60 m after, the one step is OSRM's At the roundabout, take the Nth exit onto ... (the 3rd exit on leg 27)",
          len(ra) >= 3 and all(x["words"][1:-1] == [x["want"]] for x in ra) and any("3rd exit" in x["want"] for x in ra), json.dumps(ra))

    # h. a start on a small piece of road with no way into the main car network: the route snaps again to the main network
    isl = pg.evaluate("""(i) => { const leg = S.legs[i], end = leg.geom[leg.geom.length - 1], out = {tested: 0, planned: 0, bad: []};
        for (let e = 0; e < GR.m; e++) { if (!GR.isl[e] || !(GR.fl[e] & 3) || (GR.fl[e] & F_NOSNAP)) continue;
          const p = piecePts(GR, e, 0, GR.el[e] / 2).pop(), ll = [p[0] * 1e-6, p[1] * 1e-6];
          const s0 = snapG(GR, p[0], p[1], 'car', CFG.snapMax, null, false); if (!s0 || s0.e !== e) continue;
          if (routeG(GR, ll, end, 'car', null, false).fail !== 'route' || !snapG(GR, p[0], p[1], 'car', CFG.snapMax, null, true)) continue;
          out.tested++; const pl = planLeg(ll, leg, null); if (pl.leg) out.planned++; else out.bad.push([e, pl.fail]); }
        return out; }""", 31)
    check("car islands: from every off-network piece of road (car_island) with the main network within 490 ft, the plain route to the end of leg 31 fails, and planLeg snaps again and plans one",
          isl["tested"] >= 5 and isl["planned"] == isl["tested"], json.dumps(isl))

    # i. the straight line from the position to the road: a drive fix 40 to 100 m from any road
    lead = pg.evaluate("""() => { const d = S.route.depot, k = Math.cos(d.lat * D2R);
        for (let r = 60; r <= 2500; r += 20) for (let a = 0; a < 360; a += 10) {
          const lat = d.lat + r * Math.cos(a * D2R) / (D2R * R), lon = d.lon + r * Math.sin(a * D2R) / (D2R * R * k), p = [+lat.toFixed(6), +lon.toFixed(6)];
          const s = snapG(GR, micro(p[0]), micro(p[1]), 'car', CFG.snapMax, null, false);
          if (!s || s.gap < 40 || s.gap > 100) continue;
          const pl = planLeg(p, S.legs[0], null); if (!pl.leg) continue;
          pl.leg.to = S.legs[0].to;
          return {p, gap: pl.route.gapStart, first: pl.leg.geom[0], toRoad: hav(pl.leg.geom[0], pl.leg.geom[1]),
            words: prepLeg(pl.leg).steps.slice(0, 2).map(t => t.type === 'depart' ? 'depart' : instr(t, 'drive'))}; }
        return null; }""")
    check("off the road map (a fix 40 to 100 m from any road): the new route starts with a straight line to the road, and its first words name the road",
          lead is not None and lead["first"] == lead["p"] and 40 <= lead["gap"] <= 100 and abs(lead["toRoad"] - lead["gap"]) < 2
          and re.match(r"^(Continue|Turn|At the end of the road, turn|Keep|Make a U-turn) ", lead["words"][1] or "") and "undefined" not in lead["words"][1],
          json.dumps(lead))

    # c. speed: 50 reroutes from random points within 300 m of random legs; the graph decode. Measured with the CPU slowed 4 times
    #    (CDP), a stand-in for the Galaxy Tab A9+ (an estimate, not a measurement on the tablet); the page is opened again so the
    #    decode at app start runs slowed too.
    cdp = ctx.new_cdp_session(pg)
    cdp.send("Emulation.setCPUThrottlingRate", {"rate": 4})
    pg.reload()
    pg.wait_for_selector("#startBtns button", timeout=30000)
    pump_until(pg, lambda: pg.evaluate("() => (!!GR && GR.gridMs !== null) || graphErr !== ''"), timeout=20)
    rng = random.Random(20261001)
    trips = []
    for _ in range(50):
        i = rng.choice([j for j, l in enumerate(legs) if l["dist"] > 0])
        Pr = Path(legs[i]["geom"])
        ang, dd = rng.random() * 2 * math.pi, rng.random() * 300
        trips.append([i, Pr.ll(rng.random() * Pr.total, dd * math.sin(ang), dd * math.cos(ang))])
    perf = pg.evaluate("""(trips) => trips.map(([i, p]) => { const t0 = performance.now(), r = planLeg(p, S.legs[i]);
        if (r.leg) prepLeg(r.leg);
        return {ms: performance.now() - t0, ok: !!r.leg, fail: r.fail || ''}; })""", trips)
    ms = sorted(x["ms"] for x in perf)
    p95 = ms[math.ceil(0.95 * len(ms)) - 1]
    n_ok = sum(1 for x in perf if x["ok"])
    check("speed, CPU slowed 4 times: 50 reroutes (snap, A*, steps, prepLeg) from random points within 300 m of random legs, 40 or more planned, p95 under 150 ms",
          len(ms) == 50 and n_ok >= 40 and p95 < 150, "p95 %.1f ms, median %.1f ms, max %.1f ms; %d planned, %d not (%s)" % (
              p95, ms[len(ms) // 2], ms[-1], n_ok, 50 - n_ok, "; ".join(sorted({x["fail"] for x in perf if not x["ok"]}))))
    dec = pg.evaluate("""async () => { const txt = await (await caches.match('graph.json')).text(), out = [];
        for (let k = 0; k < 5; k++) { const t0 = performance.now(); ensureGrid(decodeGraph(JSON.parse(txt))); out.push(performance.now() - t0); }
        return {load: GR.ms, grid: GR.gridMs, again: out}; }""")
    check("speed, CPU slowed 4 times: at app start graph.json parse and decode, and then the segment grid (a task of its own), each under 150 ms; "
          "all three together 5 more times, each under 150 ms",
          dec["load"] < 150 and dec["grid"] is not None and dec["grid"] < 150 and max(dec["again"]) < 150,
          "at start %.1f ms, then the grid %s ms; again %s ms" % (dec["load"], dec["grid"] is not None and round(dec["grid"], 1), ", ".join("%.1f" % x for x in dec["again"])))
    PERF = {"p95": p95, "decode": dec["load"], "grid": dec["grid"]}
    cdp.send("Emulation.setCPUThrottlingRate", {"rate": 1})
    net_off.back_online()
    ctx.close()

    # ---------- 27. a damaged graph.json is never saved; with no road map the banner says rerouting cannot run ----------
    ctx = br.new_context(viewport={"width": 800, "height": 1280}, geolocation=DEPOT, permissions=["geolocation"])
    block_external(ctx)
    gstate = {"cut": False, "seen": 0}

    def graph_handler(route):
        if not gstate["cut"]:
            route.continue_()
            return
        gstate["seen"] += 1
        route.fulfill(status=200, content_type="application/json", body=route.fetch().text()[:20000])

    ctx.route(GRAPH_URL, graph_handler)
    pg = ctx.new_page()
    attach(pg)
    pg.add_init_script(QUIET_GPS)
    pg.goto(BASE + "?reset=1")
    pg.wait_for_selector("#startBtns button", timeout=20000)
    sw_controls(pg)
    wait_for(pg, lambda: "Offline ready." in text(pg, "#startBody"), timeout=20)
    gstate["cut"] = True                                 # from now on the server sends the first 20000 characters of graph.json
    pg.reload()
    pg.wait_for_selector("#startBtns button", timeout=20000)
    pump_until(pg, lambda: gstate["seen"] > 0, timeout=8)
    pg.wait_for_timeout(1000)                            # time for a wrongly saved copy to land
    r = pg.evaluate("async () => { const c = await caches.match('graph.json'); return {cached: c ? (await c.text()).length : 0, graph: !!GR}; }")
    check("a damaged graph.json reply is not saved: the worker keeps the whole graph, and the page runs on it",
          gstate["seen"] > 0 and r["cached"] == len(GRAPH_TEXT) and r["graph"], json.dumps(r))
    pg.evaluate("async () => { for (const k of await caches.keys()) { const c = await caches.open(k); await c.delete('graph.json'); } }")
    pg.reload()
    pg.wait_for_selector("#startBtns button", timeout=20000)
    pump_until(pg, lambda: pg.evaluate("() => graphErr !== ''"), timeout=8)
    pump_until(pg, lambda: "Not offline ready" in text(pg, "#startBody"), timeout=8)
    st = pg.evaluate("async () => ({graph: !!GR, err: graphErr, cached: !!(await caches.match('graph.json')), line: document.getElementById('offlineLine').textContent})")
    check("no saved graph and a damaged reply: no road map on the page, nothing saved, and the start screen is not Offline ready.",
          st["graph"] is False and st["err"] != "" and st["cached"] is False and st["line"] == "Not offline ready yet. Keep this page open online for a minute.", json.dumps(st))
    pg.evaluate(COUNT_REROUTES)
    pg.click("#startBtns button")
    pg.wait_for_timeout(500)
    feed(pg, legs[0]["geom"][0])
    far = far_point(legs[0]["geom"])
    for k in range(3):
        feed(pg, [far[0], far[1] + 0.00001 * k], speed=8)
    pump_until(pg, lambda: pg.evaluate("() => !graphLoading"), timeout=8)    # a road map asked for again has failed again by now
    b = pg.evaluate("() => ({cls: document.getElementById('banner').className, then: document.getElementById('bThen').textContent, override: !!S.override, calls: window.__reroutes})")
    check("off route with no road map: the reroute is tried, no new leg, the arrow stays, and the banner says The road map did not load. Follow the arrow.",
          b["calls"] >= 1 and "off" in b["cls"].split() and b["then"] == "The road map did not load. Follow the arrow." and b["override"] is False, json.dumps(b))
    ctx.close()
    # b. a graph.json that is whole JSON but does not decode (one interior point pair short; a turn row whose node is not on its
    #    edges): never saved, a good saved copy is neither replaced nor passed over, and with no good copy no Offline ready.
    good_graph = json.loads(GRAPH_TEXT)
    short = dict(good_graph, ec=good_graph["ec"][:-2])
    badturn = dict(good_graph, turns=good_graph["turns"] + [[0, good_graph["n"] - 1, 1, 0]])
    CACHED_GRAPH = """async () => { const c = await caches.match('graph.json');
        return {cached: c ? (await c.text()).length : 0, graph: !!GR, err: graphErr, line: document.getElementById('offlineLine').textContent}; }"""
    for label, doc in (("one interior point pair short", short), ("a turn row whose node is not on its edges", badturn)):
        ctx = br.new_context(viewport={"width": 800, "height": 1280}, geolocation=DEPOT, permissions=["geolocation"])
        block_external(ctx)
        gs = {"bad": False, "seen": 0}

        def bad_graph_handler(gs, body):
            def handler(route):
                if not gs["bad"]:
                    route.continue_()
                    return
                gs["seen"] += 1
                route.fulfill(status=200, content_type="application/json", body=body)
            return handler

        ctx.route(GRAPH_URL, bad_graph_handler(gs, json.dumps(doc, separators=(",", ":"))))
        pg = ctx.new_page()
        attach(pg)
        pg.add_init_script(QUIET_GPS)
        pg.goto(BASE + "?reset=1")
        pg.wait_for_selector("#startBtns button", timeout=20000)
        sw_controls(pg)
        wait_for(pg, lambda: "Offline ready." in text(pg, "#startBody"), timeout=20)
        gs["bad"] = True
        pg.reload()
        pg.wait_for_selector("#startBtns button", timeout=20000)
        pump_until(pg, lambda: gs["seen"] > 0 and pg.evaluate("() => !graphLoading"), timeout=10)
        pump_until(pg, lambda: "Offline ready." in text(pg, "#startBody"), timeout=8)
        pg.wait_for_timeout(1000)                        # time for a wrongly saved copy to land
        r = pg.evaluate(CACHED_GRAPH)
        check("graph.json with %s (whole JSON): the worker keeps the good saved copy and serves it, the page decodes it, and the start screen says Offline ready." % label,
              gs["seen"] > 0 and r["cached"] == len(GRAPH_TEXT) and r["graph"] and r["line"].startswith("Offline ready."), json.dumps(r))
        pg.evaluate("async () => { for (const k of await caches.keys()) { const c = await caches.open(k); await c.delete('graph.json'); } }")
        pg.reload()
        pg.wait_for_selector("#startBtns button", timeout=20000)
        pump_until(pg, lambda: pg.evaluate("() => !graphLoading && graphErr !== ''"), timeout=10)
        pump_until(pg, lambda: "Not offline ready" in text(pg, "#startBody"), timeout=8)
        pg.wait_for_timeout(1000)
        r = pg.evaluate(CACHED_GRAPH)
        check("... and with no saved copy: it is not saved, the page has no road map, and the start screen is not Offline ready.",
              r["cached"] == 0 and not r["graph"] and r["err"] != "" and r["line"].startswith("Not offline ready yet."), json.dumps(r))
        ctx.close()

    # ---------- 28. graph.json from the network first and asked for again, a road map older than the route, the reroute timing and
    #            banner notes, the U-turn said at once, arrival at a stop off the road, the walker's last stretch, car islands ----------
    # a. the first open after a deploy reads the new graph.json at once (route.json and graph.json both come network first)
    ctx = br.new_context(viewport={"width": 800, "height": 1280}, geolocation=DEPOT, permissions=["geolocation"])
    block_external(ctx)
    gst = {"edit": None}

    def graph_edit(route):
        if gst["edit"] is None:
            route.continue_()
            return
        route.fulfill(status=200, content_type="application/json", body=gst["edit"](route.fetch().text()))

    ctx.route(GRAPH_URL, graph_edit)
    pg = ctx.new_page()
    attach(pg)
    pg.add_init_script(QUIET_GPS)
    pg.goto(BASE + "?reset=1")
    pg.wait_for_selector("#startBtns button", timeout=20000)
    sw_controls(pg)
    wait_for(pg, lambda: "Offline ready." in text(pg, "#startBody"), timeout=20)
    gst["edit"] = lambda t: t.replace('"built":"' + GRAPH_HEAD["built"] + '"', '"built":"12/31/2026"', 1)
    pg.reload()
    pg.wait_for_selector("#startBtns button", timeout=20000)
    pump_until(pg, lambda: pg.evaluate("() => !graphLoading && !!GR"), timeout=10)
    pg.wait_for_timeout(500)
    r = pg.evaluate("""async () => { const c = await caches.match('graph.json');
        return {built: GR && GR.built, cached: c ? JSON.parse(await c.text()).built : null}; }""")
    check("first open after a deploy: the page reads the new graph.json at once (network first, not the copy saved before), and the worker saves the new one",
          r["built"] == "12/31/2026" and r["cached"] == "12/31/2026", json.dumps(r))

    # b. a road map that did not load is asked for again: by the next reroute, and when the device comes back online
    gst["edit"] = None
    ctx.unroute(GRAPH_URL, graph_edit)
    aborting = {"on": True}                              # on: the server sends a damaged graph.json (it does not load); off: the real one
    ctx.route(GRAPH_URL, lambda route: route.fulfill(status=200, content_type="application/json", body=GRAPH_TEXT[:20000])
              if aborting["on"] else route.continue_())
    DROP_GRAPH = "async () => { for (const k of await caches.keys()) { const c = await caches.open(k); await c.delete('graph.json'); } }"
    pg.evaluate(DROP_GRAPH)
    pg.reload()
    pg.wait_for_selector("#startBtns button", timeout=20000)
    pump_until(pg, lambda: pg.evaluate("() => !graphLoading && graphErr !== ''"), timeout=10)
    r0 = pg.evaluate("() => ({graph: !!GR, err: graphErr})")
    aborting["on"] = False
    pg.evaluate(COUNT_REROUTES)
    pg.click("#startBtns button")
    pg.wait_for_timeout(500)
    pg.evaluate("() => { graphTriedAt = Date.now() - CFG.graphRetryMs - 1; }")     # the last try was CFG.graphRetryMs ago
    off0, _, hd0 = off_route_point(0, 80, 250, 200, ("drive",))
    feed(pg, legs[0]["geom"][0], speed=8)
    for k in range(4):
        feed(pg, [off0[0], off0[1] + 0.000004 * k], speed=8, heading=hd0)
    got = pump_until(pg, lambda: pg.evaluate("() => !!GR && !!S.override"), timeout=10)
    check("a road map that did not load (graph.json damaged, none saved) is asked for again by the next reroute, which then plans the new route",
          r0["graph"] is False and r0["err"] != "" and got, json.dumps([r0, pg.evaluate("() => ({graph: !!GR, err: graphErr, note: S.rerouteNote, override: !!S.override})")]))
    aborting["on"] = True
    pg.evaluate(DROP_GRAPH)
    pg.reload()
    pg.wait_for_selector("#startBtns button", timeout=20000)
    pump_until(pg, lambda: pg.evaluate("() => !graphLoading && graphErr !== ''"), timeout=10)
    r0 = pg.evaluate("() => ({graph: !!GR, line: document.getElementById('offlineLine').textContent})")
    aborting["on"] = False
    pg.evaluate("() => window.dispatchEvent(new Event('online'))")
    got = pump_until(pg, lambda: pg.evaluate("() => !!GR"), timeout=10)
    ready = wait_for(pg, lambda: "Offline ready." in text(pg, "#startBody"), timeout=10)
    check("... and when the device comes back online; the start screen then changes from Not offline ready yet. to Offline ready.",
          r0["graph"] is False and r0["line"].startswith("Not offline ready yet.") and got and ready, json.dumps([r0, text(pg, "#startBody")[-80:]]))
    ctx.close()

    # c. a road map older than the route: graph.json carries the signature of its route.json, and the page knows its box
    check("graph.json was built for this route.json (its route_sig is the FNV-1a hash of route.json); if not, run build_graph.py (route-guide README step 5)",
          GRAPH_HEAD.get("route_sig") == fnv1a_py(ROUTE_TEXT), "graph %s, route.json %s" % (GRAPH_HEAD.get("route_sig"), fnv1a_py(ROUTE_TEXT)))
    ctx = br.new_context(viewport={"width": 800, "height": 1280}, geolocation=DEPOT, permissions=["geolocation"])
    block_external(ctx)
    rstate = {"edit": None, "served": None}
    ctx.route(ROUTE_URL, route_editor(rstate))

    def move_stop_33(t):                                 # the end of leg 40 (stop 33) 5.5 km south, outside the road map's box
        r = json.loads(t)
        g = r["legs"][40]["geom"]
        g[-1] = [round(g[-1][0] - 0.05, 6), g[-1][1]]
        return json.dumps(r, separators=(",", ":"))

    rstate["edit"] = move_stop_33
    pg = ctx.new_page()
    attach(pg)
    pg.add_init_script(QUIET_GPS)
    pg.goto(BASE + "?reset=1")
    pg.wait_for_selector("#startBtns button", timeout=20000)
    pump_until(pg, lambda: pg.evaluate("() => !!GR") and "does not reach" in text(pg, "#startBody"), timeout=10)
    r = pg.evaluate("""() => ({line: document.getElementById('offlineLine').textContent, to: S.legs[40].to,
        fail: planLeg(S.legs[39].geom[0], S.legs[40], null).fail || '', ok41: !!planLeg(S.legs[40].geom[0], S.legs[41], null).leg, sameSig: GR.routeSig === S.routeSig})""")
    check("a stop outside the road map's box (graph.json older than route.json): the start screen says so, a reroute to it says why, and reroutes to other stops still work",
          "The road map does not reach 1 stop: no new route to it." in r["line"] and r["to"]["kind"] == "stop"
          and r["fail"] == "The road map does not reach the stop. Follow the arrow." and r["ok41"] and r["sameSig"] is False, json.dumps(r))
    ctx.close()

    # d. a missed turn on leg 9 (Northeast Ellis Way): the new route says Make a U-turn at once, or turns ahead; the car keeps going
    #    straight and leaves that route too: a new plan comes within a few fixes (no 20 s wait), Route updated. is said once, and the
    #    banner never claims a plan runs when none does
    def along_of(P, ll):
        q = P.xy_of(ll)
        best = (1e18, 0.0)
        for k in range(len(P.xy) - 1):
            a, b = P.xy[k], P.xy[k + 1]
            dx, dy = b[0] - a[0], b[1] - a[1]
            l2 = dx * dx + dy * dy
            t = max(0.0, min(1.0, ((q[0] - a[0]) * dx + (q[1] - a[1]) * dy) / l2)) if l2 else 0.0
            d = math.hypot(q[0] - (a[0] + t * dx), q[1] - (a[1] + t * dy))
            if d < best[0]:
                best = (d, P.cum[k] + t * math.sqrt(l2))
        return best[1]

    i9 = 9
    turn9 = next((s for s in legs[i9]["steps"] if s.get("name") == "Northeast Ellis Way" and "right" in (s.get("mod") or "")), None)
    check("missed-turn test setup: leg 9 turns right onto Northeast Ellis Way", turn9 is not None and legs[i9]["mode"] == "drive")
    P9 = Path(legs[i9]["geom"])
    s9 = along_of(P9, turn9["loc"])
    h9 = P9.bearing(s9 - 8)
    ctx, pg = guidance_page(br)
    pg.evaluate("(i) => setLeg(i)", i9)
    for s in range(max(0, int(s9) - 100), int(s9), 10):
        feed(pg, P9.ll(s), speed=11, heading=P9.bearing(s))
    pg.evaluate("() => { window.__spoken = []; }")
    base_xy = P9.at(s9)
    ahead = lambda m: P9.to_ll((base_xy[0] + m * math.sin(math.radians(h9)), base_xy[1] + m * math.cos(math.radians(h9))))
    first, k = None, 0
    while k < 14 and not first:
        k += 1
        feed(pg, ahead(11 * k), speed=11, heading=h9)
        first = pg.evaluate("""() => S.override ? {steps: S.override.steps.slice(0, 2), dist: document.getElementById('bDist').textContent,
            instr: document.getElementById('bInstr').textContent, spoken: window.__spoken.slice(), calls: window.__reroutes,
            next: S.nav && S.nav.step ? S.nav.step.loc : null, fix: [S.fix.lat, S.fix.lon]} : null""")
    ok_first = False
    if first:
        if first["steps"][1].get("atStart"):
            ok_first = first["instr"].startswith("Make a U-turn") and first["dist"] == "Now" and any(x.startswith("Make a U-turn") for x in first["spoken"])
        elif first["next"]:
            fq, nq = P9.xy_of(first["fix"]), P9.xy_of(first["next"])
            ok_first = ang_deg((math.degrees(math.atan2(nq[0] - fq[0], nq[1] - fq[1])) + 360) % 360, h9) <= 90
    check("missed turn onto Northeast Ellis Way (leg 9), the car goes straight on: the new route's first words are Make a U-turn (now, and spoken) or a maneuver ahead of the car",
          ok_first, json.dumps(first)[:500])
    plans, then_off = [], []
    o1 = pg.evaluate("() => { window.__o1 = S.override; return window.__reroutes; }")
    for k2 in range(k + 1, k + 13):
        feed(pg, ahead(11 * k2), speed=11, heading=h9)
        st = pg.evaluate("() => ({calls: window.__reroutes, changed: S.override !== window.__o1, cls: document.getElementById('banner').className, then: document.getElementById('bThen').textContent})")
        if "off" in st["cls"].split():
            then_off.append(st["then"])
        if st["changed"]:
            plans.append(k2)
            break
    said = pg.evaluate("() => window.__spoken.filter(x => x === 'Route updated.').length")
    check("... the car keeps going straight and leaves the new route too: a second plan comes within 12 fixes (11 m apart), with no 20 s wait",
          bool(first) and bool(plans), "second plan at fix %s; banner notes while off: %s" % (plans, json.dumps(then_off)))
    check("... Route updated. is said once for the two plans, and the banner never says Finding a new route while no plan runs",
          said == 1 and "Finding a new route" not in then_off, "said %d times; notes %s" % (said, json.dumps(then_off)))
    ctx.close()

    # e. banner notes: a failed plan says why; back on the line the note is cleared; a one-fix GPS jump later shows the arrow only
    ctx, pg = guidance_page(br)
    far = pg.evaluate(NO_ROAD_POINT)
    pg.evaluate("() => setLeg(0)")
    P0 = Path(legs[0]["geom"])
    feed(pg, P0.ll(10), speed=8)
    for k in range(4):
        feed(pg, [far[0], far[1] + 0.00001 * k], speed=8)
    t1 = text(pg, "#bThen")
    feed(pg, P0.ll(20), speed=8)
    note = pg.evaluate("() => S.rerouteNote")
    feed(pg, far, speed=8)
    r = pg.evaluate("() => ({then: document.getElementById('bThen').textContent, cls: document.getElementById('banner').className, off: S.offRoute})")
    check("banner notes: no road near says why; back on the route the note is cleared; one fix far off again shows Follow the arrow, not the old note or Finding a new route",
          t1 == "No road within 490 ft. Follow the arrow." and note == "" and r["then"] == "Follow the arrow" and "off" in r["cls"].split() and r["off"] is False,
          json.dumps([t1, note, r]))
    ctx.close()

    # f. a drive leg whose end lies 45.8 m off the car network (leg 38, stop 31): after a reroute the car arrives at the end of the road
    i38 = next(i for i, l in enumerate(legs) if l["mode"] == "drive" and l["to"].get("o") == 31 and l["to"]["kind"] == "stop")
    P38 = Path(legs[i38]["geom"])
    ctx, pg = guidance_page(br)
    pg.evaluate("(i) => setLeg(i)", i38)
    feed(pg, P38.ll(0))
    east = P38.ll(0, 120, 0)
    for k in range(4):
        feed(pg, [east[0], east[1] + 0.000004 * k])
    o = pg.evaluate("() => S.override ? {geom: S.override.geom, tail: S.override.tail} : null")
    check("off-road stop test setup: the new leg to stop 31 ends with a straight line over 45 m (no car drives it) at the stop",
          o is not None and (o["tail"] or 0) > 45 and o["geom"][-1] == legs[i38]["geom"][-1], json.dumps(o and {"tail": o["tail"], "end": o["geom"][-1]}))
    arrived_at, before = None, pg.evaluate("() => [S.legIdx, S.waiting]")
    if o and o["tail"]:
        Q = Path(o["geom"])
        road_end = Q.total - o["tail"]
        for s in [float(x) for x in range(0, int(road_end), 10)] + [road_end]:
            feed(pg, Q.ll(s), speed=5, heading=Q.bearing(s))
            if pg.evaluate("() => [S.legIdx, S.waiting]") != before:
                arrived_at = s
                break
    check("... the car that drives the new leg arrives at stop 31 by the end of the road, without driving the straight line", arrived_at is not None,
          "arrived %s m along the new leg (the road ends at %s m)" % (arrived_at, o and round(Path(o["geom"]).total - (o["tail"] or 0))))
    ctx.close()

    # g. the walker's last stretch: off walk leg 1, the new leg leaves the path straight to the meter, and the walker arrives there
    i1 = 1
    W1 = Path(legs[i1]["geom"])
    side60 = None
    for s_try in range(5, int(W1.total) - 5, 5):
        side60 = W1.side_point(s_try, 60)
        if side60:
            break
    ctx, pg = guidance_page(br)
    pg.evaluate("(i) => { S.fix = null; setLeg(i); }", i1)
    feed(pg, W1.ll(0), speed=1.4)
    for k in range(4):
        feed(pg, [side60[0], side60[1] + 0.000004 * k], speed=1.4)
    o = pg.evaluate("() => S.override ? {geom: S.override.geom, words: S.override.steps.map(s => s.type === 'arrive' ? 'arrive' : instr(s, 'walk'))} : null")
    arrived = False
    if o:
        Q = Path(o["geom"])
        s = 0.0
        while s <= Q.total + 3 and not arrived:
            feed(pg, Q.ll(min(s, Q.total)), speed=1.4)
            arrived = pg.evaluate("() => S.waiting === 'stop'")
            s += 3
    check("off walk leg 1 (60 m away): the new leg ends with Leave the path. Walk straight to the meter, and the walker who follows it arrives at the meter",
          side60 is not None and o is not None and "Leave the path. Walk straight to the meter" in o["words"] and o["geom"][-1] == legs[i1]["geom"][-1] and arrived,
          json.dumps(o and o["words"]))
    ctx.close()

    # h. a car island next to leg 31: the fixes snap to a piece of road with no way into the main network; the reroute still plans
    ctx, pg = guidance_page(br)
    pt = pg.evaluate("""(i) => { const leg = S.legs[i], rt = prepLeg(leg), end = leg.geom[leg.geom.length - 1];
        for (let e = 0; e < GR.m; e++) { if (!GR.isl[e] || !(GR.fl[e] & 3) || (GR.fl[e] & F_NOSNAP)) continue;
          const p = piecePts(GR, e, 0, GR.el[e] / 2).pop(), ll = [+(p[0] * 1e-6).toFixed(6), +(p[1] * 1e-6).toFixed(6)];
          const s0 = snapG(GR, micro(ll[0]), micro(ll[1]), 'car', CFG.snapMax, null, false); if (!s0 || s0.e !== e) continue;
          if (project(rt, ll).d < 70 || routeG(GR, ll, end, 'car', null, false).fail !== 'route') continue;
          if (!snapG(GR, micro(ll[0]), micro(ll[1]), 'car', CFG.snapMax, null, true)) continue;
          return ll; }
        return null; }""", 31)
    pg.evaluate("(i) => setLeg(i)", 31)
    feed(pg, legs[31]["geom"][0])
    for k in range(4 if pt else 0):                      # no such point: the check below fails
        feed(pg, pt)
    r = pg.evaluate("() => ({override: !!S.override, then: document.getElementById('bThen').textContent, instr: document.getElementById('bInstr').textContent})")
    check("leg 31, the car on a piece of road with no way into the main network (a car island): the reroute snaps to the main network and plans a new leg",
          pt is not None and r["override"] and "No route found" not in r["then"], json.dumps([pt, r]))
    ctx.close()

    check("no guidance page asked a host other than 127.0.0.1", not EXTERNAL, " ".join(EXTERNAL[:5]))
    br.close()

# the file list the Android app updates from must match amr-nav (tests/make_app_manifest.py after every change)
mf = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_app_manifest.py")],
                    capture_output=True, text=True, encoding="utf-8", errors="replace")
check("app-manifest.json is current (tests/test_app_manifest.py; fix: py amr-nav\\tests\\make_app_manifest.py)", mf.returncode == 0,
      " ".join(ln for ln in mf.stdout.splitlines() if ln.startswith("FAIL"))[:300])
errs = [e for e in errors if "favicon" not in e]
check("no console errors or page errors", not errs, " || ".join(errs[:6]))
print("SUMMARY", sum(1 for r in results if r[1]), "of", len(results), "passed")
sys.exit(0 if all(r[1] for r in results) else 1)
