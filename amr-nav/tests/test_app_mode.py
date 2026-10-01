"""App-mode checks for the AMR Route Guide: the page inside the Android app (window.AMRNative), with the stand-in for
the app's bridge (fake_native.js); and the same page in a browser, unchanged.
Run (repository root served on 127.0.0.1, port from AMR_TEST_PORT):  py amr-nav\\tests\\test_app_mode.py
Never put an email address in this file: the repository is public."""
import json
import os
import re

from playwright.sync_api import sync_playwright

import apptest as A


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
    line = A.text(pg, "#offlineLine")
    A.check("app: the offline line names the app's built-in copy", line == "Offline ready. Web copy 2026.10.01-1, built into the app.", line)
    v = pg.evaluate("() => APP_VERSION")
    A.check("app: the page tells the app it loaded, with its version", A.native(pg)["ready"] == [v], json.dumps(A.native(pg)["ready"]))
    ctx.close()
    ctx, pg = A.open_app(br, mode="app", start=False, query="?reset=1", init=A.QUIET_GPS,
                         native_cfg={"app": "1.0", "web": "2026.10.02-1", "source": "downloaded", "pending": "2026.10.03-1", "check": "staged 2026.10.03-1"})
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
def t_app_old_calls_safe(br):
    """A bridge that throws, or lacks a call, never stops the page."""
    broken = "window.AMRNative = {bridgeVersion() { return '1'; }, info() { throw new Error('boom'); }};"
    ctx, pg = A.open_app(br, mode="browser", start=False, query="?reset=1", init=[A.QUIET_GPS, broken])
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


with sync_playwright() as p:
    br = p.chromium.launch()
    A.run_cases(br)
    br.close()
A.finish()
