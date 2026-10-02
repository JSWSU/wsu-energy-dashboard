"""App-mode checks for the AMR Route Guide: the page inside the Android app (window.AMRNative), with the stand-in for
the app's bridge (fake_native.js); and the same page in a browser, unchanged.
Run (repository root served on 127.0.0.1, port from AMR_TEST_PORT):  py amr-nav\\tests\\test_app_mode.py
Never put an email address in this file: the repository is public."""
import json
import os
import re

from playwright.sync_api import sync_playwright

import apptest as A

GRAPH_URL = re.compile(r"/amr-nav/graph\.json(\?.*)?$")
ROUTE_URL = re.compile(r"/amr-nav/route\.json(\?.*)?$")
GRAPH_DONE = "() => !!GR && !graphLoading"           # the road map is decoded and the offline line has been brought up to date


@A.case
def t_browser_unchanged(br):
    ctx, pg = A.open_app(br, mode="browser", start=False, query="?reset=1", init=[A.QUIET_GPS, A.RECORD_OPEN])
    A.check("browser: no bridge, so NATIVE is null", pg.evaluate("() => NATIVE === null"))
    sw = A.wait_for(pg, lambda: pg.evaluate("() => !!(navigator.serviceWorker && navigator.serviceWorker.controller)"), timeout=20)
    A.check("browser: the service worker still runs", sw)
    A.wait_for(pg, lambda: "Offline ready." in A.text(pg, "#startBody"), timeout=20)
    A.check("browser: the offline line is the service worker's", "Offline ready." in A.text(pg, "#startBody") and "Web copy" not in A.text(pg, "#startBody"))
    pg.evaluate("() => openPanel()")                 # the start screen covers the side buttons
    A.check("browser: the help has no installed-app line", pg.evaluate("() => !document.getElementById('appLine')"))
    ctx.close()


@A.case
def t_app_detect(br):
    ctx, pg = A.open_app(br, mode="app", start=False, query="?reset=1", init=A.QUIET_GPS, native_cfg={"web": "2026.10.01-1"})
    A.check("app: NATIVE is the bridge", pg.evaluate("() => NATIVE === window.AMRNative"))
    pg.wait_for_timeout(2500)
    r = pg.evaluate("async () => ({regs: navigator.serviceWorker ? (await navigator.serviceWorker.getRegistrations()).length : 0, "
                    "ctl: !!(navigator.serviceWorker && navigator.serviceWorker.controller)})")
    A.check("app: no service worker is registered", r == {"regs": 0, "ctl": False}, json.dumps(r))
    A.pump_until(pg, lambda: pg.evaluate(GRAPH_DONE), timeout=20)
    line = A.text(pg, "#offlineLine")
    A.check("app: the offline line names the app's built-in copy", line == "Offline ready. Web copy 2026.10.01-1, built into the app.", line)
    v = pg.evaluate("() => APP_VERSION")
    A.check("app: the page tells the app it loaded, with its version", A.native(pg)["ready"] == [v], json.dumps(A.native(pg)["ready"]))
    ctx.close()
    ctx, pg = A.open_app(br, mode="app", start=False, query="?reset=1", init=A.QUIET_GPS,
                         native_cfg={"app": "1.0", "web": "2026.10.02-1", "source": "downloaded", "pending": "2026.10.03-1", "check": "staged 2026.10.03-1"})
    A.pump_until(pg, lambda: pg.evaluate(GRAPH_DONE), timeout=20)
    line = A.text(pg, "#offlineLine")
    A.check("app: a downloaded copy, and a newer one that waits for the next start",
            line == "Offline ready. Web copy 2026.10.02-1, downloaded. Version 2026.10.03-1 loads at the next start.", line)
    pg.evaluate("() => openPanel()")                 # the start screen covers the side buttons
    help_line = A.dom(pg, "#appLine")
    A.check("app: the help names the installed app, the web copy and the last update check",
            help_line == "Installed app 1.0. Web copy 2026.10.02-1, downloaded. Version 2026.10.03-1 loads at the next start. Last update check: staged 2026.10.03-1.",
            help_line)
    ctx.close()


@A.case
def t_app_road_map(br):
    """In the app, Offline ready. waits for the road map (graph.json), as in a browser: while it loads, and when it does
    not decode, the line says Loading the road map.; once it is decoded, the stops it does not reach are named."""
    ctx = A.new_context(br)
    graph = {"hold": True, "held": []}

    def graph_gate(route):                              # holds the page's graph.json request until the test answers it
        if graph["hold"]:
            graph["held"].append(route)
        else:
            route.continue_()

    def far_stop_33(route):                             # the end of leg 40 (stop 33) 5.5 km south, outside the road map's box
        r = json.loads(route.fetch().text())
        g = r["legs"][40]["geom"]
        g[-1] = [round(g[-1][0] - 0.05, 6), g[-1][1]]
        route.fulfill(status=200, content_type="application/json", body=json.dumps(r, separators=(",", ":")))

    ctx.route(GRAPH_URL, graph_gate)
    ctx.route(ROUTE_URL, far_stop_33)
    ctx, pg = A.open_app(br, mode="app", start=False, query="?reset=1", init=A.QUIET_GPS, ctx=ctx, native_cfg={"web": "2026.10.01-1"})
    A.pump_until(pg, lambda: graph["held"], timeout=20)
    line = A.text(pg, "#offlineLine")
    A.check("app: while the road map loads, the line says so, not Offline ready.",
            line == "Loading the road map. Web copy 2026.10.01-1, built into the app.", line)
    graph["hold"] = False
    graph["held"].pop(0).fulfill(status=200, content_type="application/json", body='{"damaged')
    A.pump_until(pg, lambda: pg.evaluate("() => !graphLoading && !!graphErr"), timeout=20)
    r = pg.evaluate("() => ({graph: !!GR, err: graphErr, line: document.getElementById('offlineLine').textContent})")
    A.check("app: a road map that does not decode: no road map, and never Offline ready.",
            not r["graph"] and r["err"] and r["line"] == "Loading the road map. Web copy 2026.10.01-1, built into the app.", json.dumps(r))
    pg.evaluate("() => { startGraphLoad(); return true; }")   # the next try (a reroute or the device back online)
    A.pump_until(pg, lambda: pg.evaluate(GRAPH_DONE), timeout=20)
    line = A.text(pg, "#offlineLine")
    A.check("app: the road map decoded: Offline ready., the stop it does not reach (as in a browser), then the web copy",
            line == "Offline ready. The road map does not reach 1 stop: no new route to it. Web copy 2026.10.01-1, built into the app.", line)
    ctx.close()


@A.case
def t_app_old_calls_safe(br):
    """A bridge that throws, or lacks a call, never stops the page."""
    broken = "window.AMRNative = {bridgeVersion() { return '1'; }, info() { throw new Error('boom'); }};"
    ctx, pg = A.open_app(br, mode="browser", start=False, query="?reset=1", init=[A.QUIET_GPS, broken])
    A.pump_until(pg, lambda: pg.evaluate(GRAPH_DONE), timeout=20)
    A.check("a broken bridge: the route still loads and the offline line still shows",
            "Offline ready." in A.text(pg, "#offlineLine") and pg.evaluate("() => nativeCall('nope') === '' && JSON.stringify(nativeInfo()) === '{}'"))
    ctx.close()


@A.case
def t_csp(br):
    """The page may connect only to itself and the map tiles, and loads no frames (both modes; in the app the native
    side refuses other hosts too)."""
    ctx, pg = A.open_app(br, mode="browser", start=False, query="?reset=1", init=A.QUIET_GPS)
    csp = pg.evaluate("() => (document.querySelector('meta[http-equiv=\"Content-Security-Policy\"]') || {}).content || ''")
    A.check("CSP: connect-src is the page itself and the map tiles; no frames",
            "connect-src 'self' https://tile.openstreetmap.org" in csp and "frame-src 'none'" in csp, csp)
    n = len(A.errors)
    r = pg.evaluate("() => fetch('https://example.com/x').then(() => 'fetched', e => 'blocked')")
    pg.wait_for_timeout(300)
    extra = A.errors[n:]
    A.check("CSP: a fetch to another host is blocked in the page (the only console line is the CSP report)",
            r == "blocked" and all("Content Security Policy" in e for e in extra), json.dumps([r, extra[:2]]))
    del A.errors[n:]
    ctx.close()


@A.case
def t_public_files(br):
    email = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
    hits, dashes = [], []
    names = ["index.html", "sw.js", "manifest.webmanifest"] + ["tests/" + n for n in os.listdir(A.HERE) if n.endswith((".py", ".js"))]
    for n in names:
        p = os.path.join(A.APP, n)
        if not os.path.exists(p):
            continue
        txt = open(p, encoding="utf-8").read()
        hits += [n + ": " + m for m in email.findall(txt)]
        if "\u2014" in txt:
            dashes.append(n)
    A.check("no email address in the app's files or tests (the site is public)", not hits, "; ".join(hits)[:200])
    A.check("no em dash in the app's files or tests", not dashes, ", ".join(dashes))


@A.case
def t_app_speech(br):
    ctx, pg = A.open_app(br, mode="app")
    spoken = A.native(pg)["spoken"]
    A.check("app: the first prompt goes to the app's voice, not speechSynthesis",
            len(spoken) >= 1 and pg.evaluate("() => window.__spoken.length") == 0, json.dumps(spoken[:3]))
    pg.click("#fVoice")
    n = len(A.native(pg)["spoken"])
    pg.evaluate("() => setLeg(2)")
    calls = [c[0] for c in A.native(pg)["calls"]]
    A.check("app: Voice off stops the app's voice and later prompts are not sent",
            "stopSpeech" in calls and len(A.native(pg)["spoken"]) == n, json.dumps(calls[-5:]))
    ctx.close()
    ctx, pg = A.open_app(br, mode="browser")
    # the start button also speaks a blank ' ' to unlock speech: only a prompt with words counts
    A.check("browser: the prompts still use speechSynthesis",
            pg.evaluate("() => window.__spoken.filter(t => String(t).trim()).length") >= 1, json.dumps(pg.evaluate("() => window.__spoken")[:3]))
    ctx.close()


@A.case
def t_app_links(br):
    ctx, pg = A.open_app(br, mode="app", init=A.RECORD_OPEN)
    pg.click("#aGmaps")
    opened = A.native(pg)["opened"]
    A.check("app: Google Maps goes through the app (an https maps link), never window.open",
            len(opened) == 1 and opened[0].startswith("https://www.google.com/maps/dir/?api=1&destination=")
            and pg.evaluate("() => window.__opened.length") == 0, json.dumps(opened))
    pg.click("#fList")
    href0 = pg.evaluate("() => location.href")
    pg.click("#bRoutePage")
    pg.wait_for_timeout(300)
    A.check("app: the printable route page opens through the app at the live site, and the guide stays",
            A.native(pg)["opened"][-1] == "https://jswsu.github.io/wsu-energy-dashboard/route.html" and pg.evaluate("() => location.href") == href0,
            json.dumps(A.native(pg)["opened"]))
    ctx.close()
    ctx, pg = A.open_app(br, mode="app", native_cfg={"open": "no app"})
    pg.click("#aGmaps")
    A.check("app: when no app can open the link, a toast says so", A.dom(pg, "#toast") == "No app on this tablet can open that link.", A.dom(pg, "#toast"))
    ctx.close()
    ctx, pg = A.open_app(br, mode="browser", init=A.RECORD_OPEN)
    pg.click("#aGmaps")
    A.check("browser: Google Maps still opens with window.open", pg.evaluate("() => window.__opened.length") == 1)
    ctx.close()


@A.case
def t_app_drive_flag(br):
    ctx, pg = A.open_app(br, mode="app", start=False)
    A.check("app: at load with no progress the drive is not active", A.native(pg)["drive"][-1:] == [False], json.dumps(A.native(pg)["drive"]))
    pg.click("#startBtns button")
    pg.wait_for_timeout(400)
    pg.evaluate("() => { markStop(S.legs[0].to.o, 'done'); setLeg(nextOpenLeg(0)); }")
    A.check("app: after a stop is reached the drive is active", A.native(pg)["drive"][-1] is True, json.dumps(A.native(pg)["drive"]))
    pg.evaluate("() => { newDrive({adopt: true}); setLeg(0); }")
    A.check("app: a new drive is not active", A.native(pg)["drive"][-1] is False, json.dumps(A.native(pg)["drive"]))
    pg.evaluate("() => { setLeg(S.legs.length - 1); S.arrivedLeg = -1; arrived(); }")
    A.check("app: a finished drive is not active", A.native(pg)["drive"][-1] is False and pg.evaluate("() => S.finished"), json.dumps(A.native(pg)["drive"]))
    ctx.close()


@A.case
def t_location_text(br):
    for mode, want in (("app", "Location is blocked. Allow location for AMR Route Guide in Settings, Apps."),
                       ("browser", "Location is blocked. Allow location for this site in the browser settings.")):
        ctx = A.new_context(br, geolocation=False)
        ctx, pg = A.open_app(br, mode=mode, ctx=ctx, query="?reset=1")
        got = A.pump_until(pg, lambda: A.dom(pg, "#toast") == want, timeout=6)
        A.check(mode + ": location blocked names where to allow it", got, A.dom(pg, "#toast"))
        ctx.close()


with sync_playwright() as p:
    br = p.chromium.launch()
    A.run_cases(br)
    br.close()
A.finish()
