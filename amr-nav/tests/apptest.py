"""Shared helpers for the AMR Route Guide browser tests beside test_app.py (test_app_mode.py, test_manual_reads.py).
Plain scripts, not pytest: each check prints PASS or FAIL; finish() checks the console, prints the summary and exits.
Server: serve the repository root on 127.0.0.1 (py -m http.server PORT --bind 127.0.0.1). PORT comes from
AMR_TEST_PORT (default 41999; never 8765). mode "app" injects fake_native.js, the stand-in for the Android app's bridge.
Never put an email address in a test file: the repository is public."""
import json
import os
import sys
import time
from urllib.parse import urlparse

PORT = int(os.environ.get("AMR_TEST_PORT", "41999"))
BASE = f"http://127.0.0.1:{PORT}/amr-nav/"
HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(HERE, "..")
SHOTS = os.path.join(os.environ.get("TEMP", "."), "amr-cycle", "app-test-shots")
os.makedirs(SHOTS, exist_ok=True)
DEPOT = {"latitude": 46.728993, "longitude": -117.144701, "accuracy": 6}
TZ = "America/Los_Angeles"
T1 = 1790890320000          # 10/01/2026 14:32 Pacific (PDT)
T0 = 1767625440000          # 01/05/2026 07:04 Pacific (PST)
ROUTE = json.load(open(os.path.join(APP, "route.json"), encoding="utf-8"))
STOPS = {s["o"]: s for s in ROUTE["stops"]}
FAKE_NATIVE = open(os.path.join(HERE, "fake_native.js"), encoding="utf-8").read()
CAPTURE_SPEECH = """window.__spoken = [];
try { speechSynthesis.speak = (u) => { window.__spoken.push(u.text); }; speechSynthesis.cancel = () => {}; } catch (e) {}"""
QUIET_GPS = "Geolocation.prototype.watchPosition = function () { return 1; }; Geolocation.prototype.clearWatch = function () {};"
RECORD_OPEN = "window.__opened = []; window.open = function (u) { window.__opened.push(String(u)); return null; };"
results, errors, EXTERNAL, CASES = [], [], [], []


def check(name, ok, detail=""):
    detail = " ".join(str(detail).split())
    results.append((name, bool(ok), detail))
    print(("PASS " if ok else "FAIL ") + name + (" | " + detail[:400] if detail else ""))
    return bool(ok)


def attach(page):
    page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type in ("error", "warning") else None)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))


def text(page, sel):
    return page.locator(sel).inner_text().strip()


def dom(pg, sel, what="e.textContent.trim()"):
    """A value read from the first element that matches sel, or None when there is none."""
    return pg.evaluate("(s) => { const e = document.querySelector(s); return e ? " + what + " : null; }", sel)


def wait_for(page, fn, timeout=60, step=0.5):
    t0 = time.time()
    while time.time() - t0 < timeout:
        v = fn()
        if v:
            return v
        time.sleep(step)
    return None


def pump_until(page, fn, timeout=15, step=0.25):
    """Like wait_for, but lets Playwright deliver events and route handlers while it waits."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        if fn():
            return True
        page.wait_for_timeout(int(step * 1000))
    return False


def feed(pg, ll, acc=5, speed=0, heading=None, t=None):
    """Hand one fix to the app's own onFix (the geolocation mock cannot set speed or the time)."""
    return pg.evaluate("""(a) => { onFix({lat: a[0], lon: a[1], acc: a[2], speed: a[3], heading: a[4], t: a[5] == null ? Date.now() : a[5]});
        return S.nav ? S.nav.along : null; }""", [ll[0], ll[1], acc, speed, heading, t])


def is_local(url):
    u = urlparse(url)
    return u.scheme not in ("http", "https", "ws", "wss") or u.hostname == "127.0.0.1"


def block_external(ctx):
    """Abort and record every request to a host other than 127.0.0.1 (finish() checks there were none)."""
    def handler(route):
        EXTERNAL.append(route.request.url)
        route.abort()
    ctx.route(lambda url: not is_local(url), handler)


def new_context(br, viewport=(800, 1280), geolocation=True, **kw):
    """A context that records speech instead of playing it (no test plays speech on the laptop speakers) and asks no
    host other than 127.0.0.1."""
    opts = dict(viewport={"width": viewport[0], "height": viewport[1]}, timezone_id=TZ, accept_downloads=True)
    if geolocation:
        opts.update(geolocation=DEPOT, permissions=["geolocation"])
    opts.update(kw)
    ctx = br.new_context(**opts)
    ctx.add_init_script(CAPTURE_SPEECH)
    block_external(ctx)
    return ctx


def open_app(br, mode="browser", init=None, viewport=(800, 1280), start=True, query="?sim=1&reset=1", ctx=None,
             native_cfg=None, geolocation=True, **kw):
    """The app in a fresh context (or in ctx). mode "app": the page runs with the bridge stand-in (fake_native.js),
    configured by native_cfg. ?sim=1 has no GPS watch, so only fixes a test feeds arrive. start: tap the first start
    button. init: a script, or a list of scripts, run before the page. The scripts are set on the context, so a new page
    in the same context (an app close and open) gets them too. Returns (ctx, pg)."""
    ctx = ctx or new_context(br, viewport, geolocation, **kw)
    if mode == "app":
        ctx.add_init_script("window.__nativeCfg = " + json.dumps(native_cfg or {}) + ";")
        ctx.add_init_script(FAKE_NATIVE)
    ctx.add_init_script(CAPTURE_SPEECH)
    for s in ([init] if isinstance(init, str) else (init or [])):
        ctx.add_init_script(s)
    pg = ctx.new_page()
    attach(pg)
    pg.goto(BASE + query)
    pg.wait_for_selector("#startBtns button", timeout=20000)
    if start:
        pg.click("#startBtns button")
        pg.wait_for_timeout(600)
    return ctx, pg


def native(pg):
    """What the bridge stand-in recorded: calls, spoken, opened, ready, drive (and later parts' records)."""
    return pg.evaluate("() => JSON.parse(JSON.stringify(Object.assign({}, window.__native, {cfg: undefined, st: undefined, save: undefined})))")


def case(fn):
    CASES.append(fn)
    return fn


def run_cases(br):
    only = os.environ.get("AMR_TEST_CASE")             # run one case by name while working on it
    if only and only not in [fn.__name__ for fn in CASES]:
        check("AMR_TEST_CASE names a case of this file (" + only + ")", False, "known: " + " ".join(fn.__name__ for fn in CASES)[:300])
        return
    for fn in CASES:
        if only and fn.__name__ != only:
            continue
        try:
            fn(br)
        except Exception as e:                           # one broken case must not hide the others
            check(fn.__name__ + ": ran to the end", False, repr(e)[:300])


def finish():
    errs = [e for e in errors if "favicon" not in e]
    check("no console errors or page errors", not errs, " || ".join(errs[:6]))
    check("no page asked a host other than 127.0.0.1", not EXTERNAL, " ".join(EXTERNAL[:5]))
    print("SUMMARY", sum(1 for r in results if r[1]), "of", len(results), "passed")
    sys.exit(0 if all(r[1] for r in results) else 1)
