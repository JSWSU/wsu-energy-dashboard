"""Browser test for the AMR Route Guide (Playwright, headless Chromium).

Run from the repository root while a static server serves the repository root:
    py -m http.server 41999 --bind 127.0.0.1
    py amr-nav\\tests\\test_app.py
Only the original reroute check (section 2) calls the real OSRM server. New checks intercept it.
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
TILE_URL = re.compile(r"https://tile\.openstreetmap\.org/")
PNG_1PX = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
# remembers the AbortSignal of every reroute request, so a test can see whether the app ended it
RECORD_OSRM_SIGNALS = """
window.__osrmSignals = [];
const __f = window.fetch.bind(window);
window.fetch = (u, o) => { if (String(u).includes('routing.openstreetmap.de')) window.__osrmSignals.push(o && o.signal); return __f(u, o); };
"""


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
    br.close()

errs = [e for e in errors if "favicon" not in e]
check("no console errors or page errors", not errs, " || ".join(errs[:6]))
print("SUMMARY", sum(1 for r in results if r[1]), "of", len(results), "passed")
sys.exit(0 if all(r[1] for r in results) else 1)
