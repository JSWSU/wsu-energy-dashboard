"""Manual reads checks for the AMR Route Guide (manual-reads.js): in a browser (IndexedDB, the share menu) and in the
Android app (fake_native.js stands in for the app's store, camera and Gmail export).
Run (repository root served on 127.0.0.1, port from AMR_TEST_PORT):  py amr-nav\\tests\\test_manual_reads.py
One case only: set AMR_TEST_CASE to its name first.
Never put an email address in this file: the repository is public."""
import io
import base64
import json
import math
import os
import re

from PIL import Image
from playwright.sync_api import sync_playwright

import apptest as A

MODES = ("browser", "app")


@A.case
def t_loaded(br):
    ctx, pg = A.open_app(br, start=False)
    r = pg.evaluate("""() => ({
        fns: ['mrStamp', 'mrCsvField', 'mrSiteName', 'mrCsvText', 'mrPhotoNames', 'mrPartNames', 'mrSplit', 'mrCheck', 'mrMakeEntry']
          .every(n => typeof window[n] === 'function'),
        first: [...document.scripts].findIndex(s => /manual-reads\\.js$/.test(s.src)) < [...document.scripts].findIndex(s => !s.src)})""")
    A.check("manual-reads.js loads before the main script and defines its functions", r == {"fns": True, "first": True}, json.dumps(r))
    sw = open(os.path.join(A.APP, "sw.js"), encoding="utf-8").read()
    A.check("sw.js keeps manual-reads.js for offline use (CORE)", "'./manual-reads.js'" in sw)
    ctx.close()


def quiet_503(n0):
    """Drop the 'Failed to load resource' console lines a refused manual-reads.js leaves (they are the test's own)."""
    A.errors[n0:] = [e for e in A.errors[n0:] if "Failed to load resource" not in e]


@A.case
def t_script_pairing(br):
    """The website, after a deploy: the service worker can serve a new index.html while manual-reads.js is missing
    (503 offline) or an older copy. The Manual read button is hidden in the markup and shows only when manual-reads.js
    is there and has the page's own version (MR_JS_VERSION === APP_VERSION): never a button that does nothing."""
    idx = open(os.path.join(A.APP, "index.html"), encoding="utf-8").read()
    A.check("index.html: the Manual read button is hidden in the markup (only mrInit shows it)",
            re.search(r'<button[^>]*id="aManual"[^>]*\bhidden\b', idx) is not None)
    n0 = len(A.errors)
    ctx = A.new_context(br)
    ctx.route("**/amr-nav/manual-reads.js", lambda r: r.fulfill(status=503, body="Offline"))
    ctx, pg = A.open_app(br, ctx=ctx)
    pg.click("#fList")
    r = pg.evaluate("() => [typeof mrInit, $('aManual').hidden, $('bManual').hidden, document.querySelector('#pBody .help').textContent.includes('Manual read')]")
    A.check("manual-reads.js not served (503): no Manual read button, no Manual reads button, no manual reads help",
            r == ["undefined", True, True, False], json.dumps(r))
    ctx.close()
    quiet_503(n0)
    mr = open(os.path.join(A.APP, "manual-reads.js"), encoding="utf-8").read()
    old = re.sub(r"const MR_JS_VERSION = '[^']+'", "const MR_JS_VERSION = '2000.01.01-1'", mr)
    ctx = A.new_context(br)
    ctx.route("**/amr-nav/manual-reads.js", lambda r: r.fulfill(status=200, body=old, content_type="text/javascript"))
    ctx, pg = A.open_app(br, ctx=ctx)
    pg.click("#fList")
    r = pg.evaluate("() => [typeof mrInit, $('aManual').hidden, $('aManual').onclick === null, $('bManual').hidden, "
                    "document.querySelector('#pBody .help').textContent.includes('Manual read')]")
    A.check("an older manual-reads.js with a newer page: manual reads stay off for this open (no button, no help line)",
            r == ["function", True, True, True, False], json.dumps(r))
    r = pg.evaluate("() => { mrInit(); return [$('aManual').hidden, MR.off, mrHelpLines()]; }")   # as an older page would call it
    A.check("an older page calling this manual-reads.js: mrInit keeps manual reads off and its help line empty",
            r == [True, True, ""], json.dumps(r))
    ctx.close()


@A.case
def t_pure(br):
    ctx, pg = A.open_app(br, start=False)
    r = pg.evaluate("([t0, t1]) => ({a: mrStamp(t0), b: mrStamp(t1)})", [A.T0, A.T1])
    A.check("mrStamp: MM/DD/YYYY, 24 h time, YYYYMMDD-HHMM stamp, local (Pacific) time",
            r == {"a": {"date": "01/05/2026", "time": "07:04", "stamp": "20260105-0704"},
                  "b": {"date": "10/01/2026", "time": "14:32", "stamp": "20261001-1432"}}, json.dumps(r))
    r = pg.evaluate("""() => [mrCsvField('abc'), mrCsvField('a,b'), mrCsvField('say "hi"'), mrCsvField('two\\nlines'),
        mrCsvField(' pad'), mrCsvField(''), mrCsvField(null), mrCsvField('004512')]""")
    A.check("mrCsvField: RFC 4180 quoting; plain text and leading zeros stay as they are",
            r == ["abc", '"a,b"', '"say ""hi"""', '"two\nlines"', '" pad"', "", "", "004512"], json.dumps(r))
    r = pg.evaluate("() => [mrSiteName('CREAM ANNEX \\u00b7 M100'), mrSiteName('ELK RESEARCH off Dairy Rd \\u00b7 Ext Vlt'), mrSiteName(''), mrSiteName(undefined)]")
    A.check("mrSiteName: the building name before the middle dot", r == ["CREAM ANNEX", "ELK RESEARCH off Dairy Rd", "", ""], json.dumps(r))
    r = pg.evaluate("""(t1) => {
        const e = mrMakeEntry({id: 'x1', savedAt: t1, gps: {lat: 46.727212, lon: -117.146276, accFt: 30}, stop: 2, meter: '0353_DW_001',
          ref: '200041', bldg: '0353', site: 'CREAM ANNEX', read: '004512', mult: '10', notes: 'Lid "stuck", used bar\\nsecond line', photoBytes: 1});
        const e2 = mrMakeEntry({id: 'x2', savedAt: t1 + 60000, gps: null, stop: null, other: true, meter: 'AIRPORT-X', read: '7', mult: '1'});
        return mrCsvText([e, e2], new Map([['x1', '200041-20261001-1432.jpg']])); }""", A.T1)
    want = ("\ufeffDate,Time,Meter ID,Route ref,Building number,Site name,Face read,Multiplier,Notes,Photo file name,"
            "GPS latitude,GPS longitude,GPS accuracy (ft),Stop number\r\n"
            '10/01/2026,14:32,0353_DW_001,200041,0353,CREAM ANNEX,004512,10,"Lid ""stuck"", used bar\nsecond line",'
            "200041-20261001-1432.jpg,46.727212,-117.146276,30,2\r\n"
            "10/01/2026,14:33,AIRPORT-X,,,,7,1,,,,,,\r\n")
    A.check("mrCsvText: BOM, 14 columns, CRLF rows, quoting, leading zeros kept, no calculated column, no radio ID", r == want, repr(r)[:400])
    r = pg.evaluate("""(t1) => {
        const mk = (id, ref, meter, ms, pb) => mrMakeEntry({id, savedAt: ms, meter, ref, read: '1', mult: '1', photoBytes: pb});
        const list = [mk('a', '200041', '0353_DW_001', t1, 5), mk('b', '200041', '0353_DW_001', t1 + 20000, 5),
                      mk('c', '', 'AIR/PORT 9', t1, 5), mk('d', '200043', '0357_DW_001', t1, 0)];
        return [...mrPhotoNames(list).entries()]; }""", A.T1)
    A.check("mrPhotoNames: <route ref>-<YYYYMMDD-HHMM>.jpg; -2 for a second photo in the same minute; typed ID cleaned; none without a photo",
            r == [["a", "200041-20261001-1432.jpg"], ["b", "200041-20261001-1432-2.jpg"], ["c", "AIR-PORT-9-20261001-1432.jpg"]], json.dumps(r))
    r = pg.evaluate("""(t1) => {
        const e = mrMakeEntry({id: 'z', savedAt: t1, other: true, meter: '_X1', read: '1', mult: '1', photoBytes: 5});
        return [mrSafeId('_X1'), mrSafeId('--a_b--'), mrSafeId('___'), mrSafeId(''), mrSafeId('AIR/PORT 9'), [...mrPhotoNames([e]).values()][0]]; }""", A.T1)
    A.check("mrSafeId: no leading underscore or dash and no trailing dash (a file name starts with a letter or digit): _X1 gives X1-20261001-1432.jpg",
            r == ["X1", "a_b", "meter", "meter", "AIR-PORT-9", "X1-20261001-1432.jpg"], json.dumps(r))
    r = pg.evaluate("(t1) => [mrPartNames(t1, 0, 1), mrPartNames(t1, 1, 3)]", A.T1)
    A.check("mrPartNames: name from the latest entry, digits and hyphens only, part suffix; plain subject",
            r == [{"csv": "AMR-manual-reads-20261001-1432.csv", "subject": "AMR manual reads 10/01/2026 14:32"},
                  {"csv": "AMR-manual-reads-20261001-1432-part2of3.csv", "subject": "AMR manual reads 10/01/2026 14:32, part 2 of 3"}], json.dumps(r))
    r = pg.evaluate("""() => {
        const mk = (i, pb) => ({id: 'e' + i, photoBytes: pb, savedAt: i});
        const ids = parts => parts.map(p => p.map(e => e.id).join(' '));
        const a = Array.from({length: 20}, (_, i) => mk(i, 500000));
        const b = Array.from({length: 5}, (_, i) => mk(i, 0)).concat(Array.from({length: 10}, (_, i) => mk(10 + i, 500000)));
        const c = [mk(1, 8000000), mk(2, 8000000), mk(3, 8000000)];
        const d = Array.from({length: 40}, (_, i) => mk(i, 0));
        return {a10: mrSplit(a, 10).map(p => p.length), aApp: mrSplit(a, Infinity).map(p => p.length), b: ids(mrSplit(b, 10)),
                c: mrSplit(c, Infinity).map(p => p.length), d: mrSplit(d, 10).map(p => p.length), e: mrSplit([], 10)}; }""")
    A.check("mrSplit: browser parts hold at most 9 photos (10 files with the CSV); app parts split only by size; every part under 18 MB",
            r == {"a10": [9, 9, 2], "aApp": [20], "b": ["e0 e1 e2 e3 e4 e10 e11 e12 e13 e14 e15 e16 e17 e18", "e19"], "c": [2, 1], "d": [40], "e": []},
            json.dumps(r))
    r = pg.evaluate("""() => [
        mrCheck({meterRef: '200041', other: false, otherId: '', read: '004512', mult: '10'}),
        mrCheck({meterRef: null, other: false, otherId: '', read: '', mult: ''}),
        mrCheck({meterRef: null, other: true, otherId: '  ', read: '12a', mult: '0'}),
        mrCheck({meterRef: null, other: true, otherId: 'X1', read: '0012.5', mult: '0.1'})]""")
    A.check("mrCheck: face read and multiplier required, digits only, multiplier above 0, a meter or a typed ID",
            r[0] == {} and sorted(r[1]) == ["meter", "mult", "read"] and sorted(r[2]) == ["meter", "mult", "read"] and r[3] == {}, json.dumps(r))
    r = pg.evaluate("""(t1) => { const e = mrMakeEntry({savedAt: t1, meter: 'M', read: '1', mult: '1'});
        return [e.v, e.status, e.stop, e.lat, e.accFt, e.photoBytes, e.exportName, /^mr-[a-z0-9]+-[a-z0-9]+$/.test(e.id), e.stamp, e.other]; }""", A.T1)
    A.check("mrMakeEntry: schema v1, status new, no stop and no GPS when none given, an id the app store takes",
            r == [1, "new", None, None, None, 0, None, True, "20261001-1432", False], json.dumps(r))
    ctx.close()


@A.case
def t_public_files(br):
    email = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
    hits, dashes = [], []
    for n in ("index.html", "manual-reads.js", "sw.js", "tests/test_manual_reads.py", "tests/fake_native.js"):
        txt = open(os.path.join(A.APP, n), encoding="utf-8").read()
        hits += [n + ": " + m for m in email.findall(txt)]
        if "\u2014" in txt:
            dashes.append(n)
    A.check("no email address in the manual reads files (the site is public)", not hits, "; ".join(hits)[:200])
    A.check("no em dash in the manual reads files", not dashes, ", ".join(dashes))


@A.case
def t_offline_file(br):
    ctx, pg = A.open_app(br, start=False)
    A.wait_for(pg, lambda: pg.evaluate("() => !!(navigator.serviceWorker && navigator.serviceWorker.controller)"), timeout=20)
    A.wait_for(pg, lambda: "Offline ready." in A.text(pg, "#startBody"), timeout=20)
    ctx.set_offline(True)
    pg.reload()
    pg.wait_for_selector("#startBtns button", timeout=20000)
    A.check("browser: manual-reads.js comes from the offline cache after an offline reload",
            pg.evaluate("() => typeof mrCsvText === 'function' && typeof mrSplit === 'function'"))
    ctx.set_offline(False)
    ctx.close()


BLOCK_IDB = ("Object.defineProperty(window, 'indexedDB', {configurable: true, get() { return {open() { "
             "throw new DOMException('The user denied permission to access the database.', 'SecurityError'); }}; }});")


def seed(pg, specs):
    """Store entries through the app's own mrMakeEntry and mrSaveEntry. A spec holds the mrMakeEntry fields (id, savedAt,
    meter, ref, bldg, site, stop, other, read, mult, notes, gps), plus status ('new' or 'exported'), exportedAt (ms; default
    savedAt), photo ([w, h]: a JPEG drawn in the page) and photoBytes (to pretend a larger photo for the part split)."""
    pg.evaluate("""async (specs) => {
      for (const s of specs) {
        let blob;
        if (s.photo) {
          const c = document.createElement('canvas'); c.width = s.photo[0]; c.height = s.photo[1];
          const g = c.getContext('2d'); g.fillStyle = '#4a7a8c'; g.fillRect(0, 0, c.width, c.height);
          g.fillStyle = '#fff'; g.font = '40px sans-serif'; g.fillText(s.meter, 20, 60);
          blob = await new Promise(r => c.toBlob(r, 'image/jpeg', 0.9));
        }
        const e = mrMakeEntry(Object.assign({}, s, {photoBytes: s.photoBytes || (blob ? blob.size : 0)}));
        if (s.status === 'exported') { e.status = 'exported'; e.exportedAt = s.exportedAt || s.savedAt; e.exportName = 'AMR-manual-reads-test.csv'; }
        await mrSaveEntry(e, blob);
      }
      await mrRefreshCounts();
    }""", specs)


def all_entries(pg):
    return pg.evaluate("async () => (await mrAll()).map(e => Object.assign({}, e))")


@A.case
def t_store(br):
    for mode in MODES:
        ctx, pg = A.open_app(br, mode=mode, start=False)
        seed(pg, [dict(id="s1", savedAt=A.T1, meter="0353_DW_001", ref="200041", read="004512", mult="10", photo=[640, 480]),
                  dict(id="s2", savedAt=A.T1 + 60000, meter="0357_DW_001", ref="200043", read="7", mult="1")])
        r = [[e["id"], e["status"], e["read"], e["photoBytes"] > 0] for e in all_entries(pg)]
        A.check(mode + " store: two reads in save order, the photo with the first", r == [["s1", "new", "004512", True], ["s2", "new", "7", False]], json.dumps(r))
        b = pg.evaluate("async () => { const b = await mrPhoto('s1'); return b ? [b.type, b.size > 1000] : null; }")
        A.check(mode + " store: the photo comes back as a JPEG blob", b == ["image/jpeg", True], json.dumps(b))
        A.check(mode + " store: counts of new and exported reads", pg.evaluate("() => mrRefreshCounts()") == {"new": 2, "exported": 0})
        pg.reload()
        pg.wait_for_selector("#startBtns button", timeout=20000)
        n1 = len(all_entries(pg))
        pg2 = ctx.new_page()
        A.attach(pg2)
        pg.close()
        pg2.goto(A.BASE + "?sim=1")
        pg2.wait_for_selector("#startBtns button", timeout=20000)
        n2 = len(all_entries(pg2))
        A.check(mode + " store: reads survive a reload and an app close (a new page, the same profile)", n1 == 2 and n2 == 2, f"{n1} {n2}")
        pg2.evaluate("() => mrSetStatus(['s1'], 'exported', 'AMR-manual-reads-20261001-1432.csv')")
        r = [[e["id"], e["status"], e["exportName"]] for e in all_entries(pg2)]
        A.check(mode + " store: mark exported keeps the read and records the CSV name",
                r == [["s1", "exported", "AMR-manual-reads-20261001-1432.csv"], ["s2", "new", None]], json.dumps(r))
        k0 = pg2.evaluate("async () => [await mrClearExported(), (await mrAll()).map(e => e.id)]")
        A.check(mode + " store: a read exported today is not cleared (K8: exported is not sent)", k0 == [0, ["s1", "s2"]], json.dumps(k0))
        pg2.evaluate("async () => { const e = await mrGet('s1'); e.exportedAt = Date.now() - 8 * 86400000; await mrSaveEntry(e, undefined); }")
        k = pg2.evaluate("async () => { const n = await mrClearExported(); return [n, (await mrAll()).map(e => e.id), await mrPhoto('s1')]; }")
        A.check(mode + " store: clear removes only reads exported more than 7 days ago, with their photos", k == [1, ["s2"], None], json.dumps(k))
        pg2.evaluate("() => { newDrive({adopt: true}); }")
        pg2.goto(A.BASE + "?sim=1&reset=1")
        pg2.wait_for_selector("#startBtns button", timeout=20000)
        A.check(mode + " store: Start a new drive and ?reset=1 leave the reads alone", len(all_entries(pg2)) == 1)
        d = pg2.evaluate("""async () => {
            const c = document.createElement('canvas'); c.width = 64; c.height = 48;
            const blob = await new Promise(r => c.toBlob(r, 'image/jpeg', 0.9));
            await mrDraftPut({form: {read: '12', photo: blob}}); const a = await mrDraftGet(); await mrDraftDel();
            const b = await mrDraftGet(); return [a.k, a.form.read, typeof a.at, a.form.photo instanceof Blob, a.form.photo.type, b === undefined]; }""")
        A.check(mode + " store: a draft with its photo is put, read back and deleted", d == ["current", "12", "number", True, "image/jpeg", True], json.dumps(d))
        pg2.evaluate("() => mrDelete('s2')")
        A.check(mode + " store: delete removes the read", len(all_entries(pg2)) == 0)
        ctx.close()


@A.case
def t_store_app_files(br):
    ctx, pg = A.open_app(br, mode="app", start=False)
    seed(pg, [dict(id="f1", savedAt=A.T1, meter="M1", ref="200041", read="1", mult="1", photo=[320, 240])])
    r = pg.evaluate("async () => ({dbs: (await indexedDB.databases()).map(d => d.name), st: Object.keys(window.__native.st.entries), "
                    "ph: Object.keys(window.__native.st.photos), persisted: await mrPersist(true)})")
    A.check("app: reads and photos go to the app's own store; IndexedDB is never opened; the app keeps them (protected)",
            r == {"dbs": [], "st": ["f1"], "ph": ["f1"], "persisted": True}, json.dumps(r))
    ctx.close()


@A.case
def t_store_app_flaky(br):
    """In the app, a store call that answers '' for a moment (the page did not count as the app's own page) never sends a
    read to IndexedDB: the save fails and says so. The mode is fixed when the page loads."""
    ctx, pg = A.open_app(br, mode="app", start=False)
    pg.evaluate("() => { window.__native.cfg.bridge = ''; window.__native.cfg.notApp = true; }")
    r = pg.evaluate("""async () => {
        let saved = 'saved', listed = 'listed';
        try { await mrSaveEntry(mrMakeEntry({savedAt: Date.now(), meter: 'M', read: '1', mult: '1'}), undefined); } catch (e) { saved = 'refused'; }
        try { await mrAll(); } catch (e) { listed = 'refused'; }
        return {saved, listed, app: mrStore() === MR_APP && !!mrBridge(), dbs: (await indexedDB.databases()).map(d => d.name)}; }""")
    A.check("app: a store call that answers nothing fails the save and the list; IndexedDB is never used in the app",
            r == {"saved": "refused", "listed": "refused", "app": True, "dbs": []}, json.dumps(r))
    pg.evaluate("() => { window.__native.cfg.bridge = '2'; window.__native.cfg.notApp = false; }")
    seed(pg, [dict(id="f2", savedAt=A.T1, meter="M2", read="1", mult="1")])
    A.check("app: once the bridge answers again, the read saves in the app's store",
            pg.evaluate("() => Object.keys(window.__native.st.entries)") == ["f2"])
    ctx.close()


@A.case
def t_fake_bridge(br):
    """Ruling C1: the bridge stand-in answers as the app does (Bridge.java and ReadStore.java): ids and the draft photo,
    '' for a missing photo or draft, 'ok' for a delete, size limits, and one JSON list that leaves out a damaged entry."""
    ctx, pg = A.open_app(br, mode="app", start=False)
    r = pg.evaluate("""() => { const N = window.AMRNative, st = window.__native.st, jpg = '/9j/4AAQ', out = {};
        out.draftId = [N.storePut('draft', '{"id":"draft"}').startsWith('error'), N.photoPut('draft', jpg), N.photoGet('draft') === jpg];
        out.missing = [N.photoGet('mr-none'), N.draftGet(), N.photoDelete('mr-none'), N.storeDelete('mr-none')];
        out.draft = [N.draftPut('[1]').startsWith('error'), N.draftPut(' {"form":{}} '), N.draftGet()];
        out.put = [N.storePut('mr-a', '{"id":"mr-a"}'), N.storePut('mr-b', 'x').startsWith('error'),
                   N.storePut('mr-c', '{"x":"' + 'a'.repeat(70000) + '"}').startsWith('error')];
        out.photo = [N.photoPut('mr-a', '/9j/').startsWith('error'), N.photoPut('mr-a', '/9j/' + 'A'.repeat(11200000)).startsWith('error'),
                     N.photoPut('mr-a', 'AAAA').startsWith('error'), N.photoPut('mr-a', jpg)];
        out.delDraft = [N.storeDelete('draft'), N.photoGet('draft') === jpg, N.photoGet('mr-a') === jpg];
        st.entries['mr-d'] = '{"id":"mr-d",}';
        try { out.all = JSON.parse(N.storeAll()).map(e => e.id); } catch (e) { out.all = 'not one JSON list'; }
        window.__native.cfg.storeError = 'error: disk full';
        out.full = [N.storeAll(), N.storePut('mr-e', '{}'), N.photoDelete('mr-a'), N.draftDelete(), N.storeDelete('mr-a')];
        return out; }""")
    A.check("fake bridge (C1): storePut refuses id draft; photoPut and photoGet take it",
            r["draftId"] == [True, "ok", True], json.dumps(r["draftId"]))
    A.check("fake bridge (C1): a missing photo or draft answers ''; photoDelete and storeDelete of a missing one answer ok",
            r["missing"] == ["", "", "ok", "ok"], json.dumps(r["missing"]))
    A.check("fake bridge (C1): draftPut refuses text that is not an object and keeps the trimmed text",
            r["draft"] == [True, "ok", '{"form":{}}'], json.dumps(r["draft"]))
    A.check("fake bridge (C1): storePut refuses text that is not an object and an entry over 64 KB",
            r["put"] == ["ok", True, True], json.dumps(r["put"]))
    A.check("fake bridge (C1): photoPut refuses under 4 bytes, over 8 MB and a file that is not a JPEG",
            r["photo"] == [True, True, True, "ok"], json.dumps(r["photo"]))
    A.check("fake bridge (C1): storeDelete('draft') deletes nothing (the form's photo and the saved read's photo stay)",
            r["delDraft"] == ["ok", True, True], json.dumps(r["delDraft"]))
    A.check("fake bridge (C1): storeAll is one JSON list that leaves out a damaged entry", r["all"] == ["mr-a"], json.dumps(r["all"]))
    A.check("fake bridge (C1): a full store fails the reads and writes; the deletes still answer ok (the app's never fail)",
            r["full"] == ["error: disk full", "error: disk full", "ok", "ok", "ok"], json.dumps(r["full"]))
    ctx.close()


@A.case
def t_store_blocked(br):
    for mode, kw in (("browser", {"init": BLOCK_IDB}), ("app", {"native_cfg": {"storeError": "error: disk full"}})):
        ctx, pg = A.open_app(br, mode=mode, start=False, **kw)
        r = pg.evaluate("async () => { try { await mrAll(); return 'opened'; } catch (e) { return 'refused'; } }")
        c = pg.evaluate("async () => [await mrRefreshCounts(), MR.storeOk]")
        A.check(mode + " store: a blocked or full store is refused cleanly; counts are 0 and storeOk is false (no page error)",
                r == "refused" and c == [{"new": 0, "exported": 0}, False], json.dumps([r, c]))
        ctx.close()


@A.case
def t_store_versions(br):
    ctx, pg = A.open_app(br, start=False)
    seed(pg, [dict(id="v1", savedAt=A.T1, meter="0353_DW_001", ref="200041", read="1", mult="1")])
    r = pg.evaluate("""() => new Promise(res => { const q = indexedDB.open('amrNav-manualReads', 2);
        q.onupgradeneeded = () => { q.result.createObjectStore('later', {keyPath: 'k'}); };
        q.onblocked = () => res('blocked');
        q.onsuccess = () => { const names = [...q.result.objectStoreNames]; q.result.close(); res(names); }; })""")
    A.check("browser store: the page closes its connection when a newer version opens (no blocked upgrade); its stores are kept",
            r == ["drafts", "entries", "later", "photos"], json.dumps(r))
    pg.reload()
    pg.wait_for_selector("#startBtns button", timeout=20000)
    k = pg.evaluate("async () => { try { await mrAll(); return 'opened'; } catch (e) { return e.name; } }")
    A.check("browser store: a database from a newer app version is refused with VersionError, not a page error", k == "VersionError", k)
    ctx.close()


def open_form(pg):
    pg.click("#aManual")
    pg.wait_for_selector("#mrForm:not([hidden])", timeout=5000)
    pg.wait_for_timeout(200)


def save_form(pg):
    pg.click("#mrSave")
    pg.wait_for_selector("#mrForm", state="hidden", timeout=5000)


@A.case
def t_form_basics(br):
    ctx, pg = A.open_app(br)
    tops = pg.evaluate("() => ['aNext', 'aSkip', 'aManual', 'aGmaps'].map(id => Math.round($(id).getBoundingClientRect().top))")
    A.check("card: Manual read is in the button row, one row on the tablet (800 px wide)",
            len(set(tops)) == 1 and A.dom(pg, "#aManual") == "Manual read", json.dumps(tops))
    m0 = A.STOPS[2]["meters"][0]
    card_stop = A.dom(pg, "#cNo")
    A.feed(pg, [m0["lat"], m0["lon"]], acc=9)               # the reader stands at stop 2; the card still shows stop 1
    open_form(pg)
    r = pg.evaluate("""() => ({stop: $('mrStop').value, read: $('mrRead').value, mult: $('mrMult').value,
        ac: [$('mrRead').autocomplete, $('mrMult').autocomplete], types: [$('mrRead').type, $('mrMult').type],
        rows: [...document.querySelectorAll('#mrMeters input')].map(i => i.value), title: $('mrFormTitle').textContent,
        gps: $('mrGps').textContent})""")
    A.check("form: opens on the stop nearest the GPS fix (stop 2), not the card's stop (stop 1)", card_stop == "1" and r["stop"] == "2", json.dumps([card_stop, r["stop"]]))
    A.check("form: face read and multiplier start empty; text inputs with autocomplete off (leading zeros kept, nothing prefilled)",
            r["read"] == "" and r["mult"] == "" and r["ac"] == ["off", "off"] and r["types"] == ["text", "text"] and r["title"] == "Manual read", json.dumps(r))
    A.check("form: the stop's meters by route ref, then Other meter", r["rows"] == [m["ref"] for m in A.STOPS[2]["meters"]] + ["__other"], json.dumps(r["rows"]))
    A.check("form: the GPS line gives the accuracy in ft", "GPS \u00b130 ft" in r["gps"], r["gps"])
    pg.click("#mrSave")
    errs = pg.evaluate("() => [$('mrMetersErr').textContent, $('mrReadErr').textContent, $('mrMultErr').textContent, $('mrForm').hidden]")
    A.check("form: Save with nothing filled in shows three messages, keeps the form open and saves nothing",
            all(errs[:3]) and errs[3] is False and len(all_entries(pg)) == 0, json.dumps(errs))
    pg.check("#mrMeters input[value='%s']" % m0["ref"])
    pg.fill("#mrRead", "004512")
    pg.fill("#mrMult", "10")
    pg.fill("#mrNotes", "Lid stuck")
    save_form(pg)
    e = all_entries(pg)[0]
    A.check("form: the saved read keeps leading zeros and copies meter, route ref, building number, site name and stop",
            [e["read"], e["mult"], e["meter"], e["ref"], e["bldg"], e["site"], e["stop"], e["notes"], e["other"]] ==
            ["004512", "10", m0["meter"], m0["ref"], m0["bldg"], m0["where"].split(" \u00b7 ")[0], 2, "Lid stuck", False], json.dumps(e))
    A.check("form: GPS from the fresh fix, 6 decimals, accuracy 9 m = 30 ft",
            [e["lat"], e["lon"], e["accFt"]] == [round(m0["lat"], 6), round(m0["lon"], 6), 30], json.dumps([e["lat"], e["lon"], e["accFt"]]))
    A.check("form: date MM/DD/YYYY and 24 h time",
            bool(re.fullmatch(r"\d\d/\d\d/\d{4}", e["date"]) and re.fullmatch(r"\d\d:\d\d", e["time"])), e["date"] + " " + e["time"])
    A.check("form: a toast says the read is saved", ("Read saved: " + m0["meter"]) in (A.dom(pg, "#toast") or ""), A.dom(pg, "#toast"))
    open_form(pg)
    A.check("form: the next form is empty again (the multiplier is never prefilled)", pg.input_value("#mrMult") == "" and pg.input_value("#mrRead") == "")
    ctx.close()


@A.case
def t_form_card_stop(br):
    """Ruling S1 as the controller amended it (10/01/2026): parked at a stop's parking spot, the form opens on the card's
    stop. Otherwise the candidates are the card's stop and the stop the drive reached last; the candidate with the nearest
    meter within 150 m wins; with none, the stop with the nearest meter within 150 m; else the card's stop. Parked at stop 1,
    a stop 2 meter is nearer than the stop 1 meter, but the form opens on stop 1."""
    ctx, pg = A.open_app(br)
    park = A.STOPS[1]["park"]
    far = A.STOPS[2]["meters"][0]                            # 0353_DW_001: more than 150 m from every stop 1 meter
    A.feed(pg, park, acc=9)                                  # the car reaches stop 1's parking spot
    r = pg.evaluate("""(p) => { const d = st => Math.min(...st.meters.map(m => hav(p, [m.lat, m.lon])));
        return {waiting: S.waiting, card: currentTargetStop().o, d1: Math.round(d(S.stopBy[1])), d2: Math.round(d(S.stopBy[2]))}; }""", park)
    A.check("setup: parked at stop 1; a stop 2 meter is nearer than the stop 1 meter, and both are within 150 m",
            r["waiting"] == "park" and r["card"] == 1 and r["d2"] < r["d1"] <= 150, json.dumps(r))
    open_form(pg)
    A.check("form: parked at stop 1, it opens on the card's stop (stop 1), not on stop 2 with the nearer meter",
            pg.input_value("#mrStop") == "1", pg.input_value("#mrStop"))
    pg.click("#mrCancel")
    r = pg.evaluate("""(far) => { const out = {};
        S.waiting = null; out.meterNear = mrDefaultStop().o;     // not marked parked: the stop 1 meter is within 150 m
        S.fix = {lat: far[0], lon: far[1], acc: 9, heading: null, speed: 0}; S.fixAt = Date.now();
        S.waiting = 'park'; out.parked = mrDefaultStop().o;      // the card shows stop 1's parking spot: stop 1, even beside a stop 2 meter
        S.waiting = null; out.free = mrDefaultStop().o;          // neither: the stop with the nearest meter
        S.waiting = 'park'; return out; }""", [far["lat"], far["lon"]])
    A.check("form: the card's stop wins when one of its meters is within 150 m (no stop reached yet), or when parked at its parking spot; else the nearest meter's stop",
            r == {"meterNear": 1, "parked": 1, "free": 2}, json.dumps(r))
    ctx.close()


@A.case
def t_form_driveby(br):
    """Review Focus 1: drive-by stops move the card on when the car reaches them. Standing at a meter of the stop the drive
    reached last, the form opens on that stop, not on the card's next stop. Real route: a stop 7 meter lies 27 to 67 m from
    the stop 6 meters, and a stop 25 meter 93 m from the stop 24 meters. The arrival runs through the app's own onFix."""
    ctx, pg = A.open_app(br)

    def by_name(n, name):
        return next(m for m in A.STOPS[n]["meters"] if m["meter"] == name)

    def reach(n):                                            # put the guide on the leg to stop n, then a fix at its end
        end = pg.evaluate("(n) => { const i = firstLegOfStop(n); setLeg(i, 'silent'); const g = S.legs[i].geom; return g[g.length - 1]; }", n)
        A.feed(pg, end, acc=9)
        return pg.evaluate("(n) => [currentTargetStop().o, !!S.done[n], S.waiting]", n)

    def form_stop(m):                                        # a fix at meter m, then Manual read: the stop the form opens on
        A.feed(pg, [m["lat"], m["lon"]], acc=9)
        open_form(pg)
        v = pg.input_value("#mrStop")
        pg.click("#mrCancel")
        return [m["meter"], v]

    for n in (6, 24):
        moved = reach(n)
        A.check("setup: the car reaches drive-by stop %d; the card moves on to stop %d" % (n, n + 1),
                moved == [n + 1, True, None], json.dumps(moved))
        got = [form_stop(m) for m in A.STOPS[n]["meters"]]
        A.check("form: at each meter of drive-by stop %d (the stop the drive reached last) it opens on stop %d, not on the card's stop %d" % (n, n, n + 1),
                len(got) > 0 and all(v == str(n) for _, v in got), json.dumps(got))
        if n == 6:
            got = form_stop(by_name(7, "0817ADW_001"))   # 27 m from a stop 6 meter: the card's stop is nearer here
            A.check("form: at a meter of the card's stop (7), 27 m from a stop 6 meter, it opens on the card's stop",
                    got[1] == "7", json.dumps(got))
            moved = reach(7)                             # stop 7 has an attention meter: the card waits there
            pg.click("#aNext")                           # Reached, next: the card moves on to stop 8
            card = pg.evaluate("() => [currentTargetStop().o, !!S.done[7]]")
            got = form_stop(by_name(7, "0817ADW_001"))
            A.check("form: after Reached, next at stop 7 (card on stop 8), a stop 7 meter 27 m from a stop 6 meter opens stop 7, not stop 6",
                    moved[2] == "stop" and card == [8, True] and got[1] == "7", json.dumps([moved, card, got]))
    ctx.close()


@A.case
def t_form_ui_rulings(br):
    """Rulings S2 and S3 (UI samples, 10/01/2026): a bad field stays red while it has focus; the Other meter label uses the
    body font, the meter IDs the meter font."""
    ctx, pg = A.open_app(br)
    open_form(pg)
    f = pg.evaluate("""() => ({rows: [...document.querySelectorAll('#mrMeters .mr-m b')].map(b => getComputedStyle(b).fontFamily),
        body: getComputedStyle(document.body).fontFamily})""")
    A.check("form: meter IDs in the meter font (Consolas); the Other meter label in the body font",
            len(f["rows"]) > 1 and all("Consolas" in x for x in f["rows"][:-1]) and f["rows"][-1] == f["body"], json.dumps(f))
    ref = pg.evaluate("() => document.querySelector('#mrMeters input').value")
    pg.check("#mrMeters input[value='%s']" % ref)
    pg.fill("#mrRead", "12a")
    pg.fill("#mrMult", "1")
    pg.click("#mrSave")
    s = pg.evaluate("""() => { const el = $('mrRead'), cs = getComputedStyle(el);
        return [document.activeElement === el, el.classList.contains('mr-bad'), cs.borderTopColor, cs.outlineStyle, cs.outlineColor]; }""")
    A.check("form: the bad face read has focus and still shows red (red border and a red focus outline)",
            s == [True, True, "rgb(185, 28, 28)", "solid", "rgb(185, 28, 28)"], json.dumps(s))
    ctx.close()
    src = open(os.path.join(A.APP, "manual-reads.js"), encoding="utf-8").read().splitlines()
    raw = [i + 1 for i, line in enumerate(src) if any(ord(c) > 127 for c in line) and not line.lstrip().startswith(("/*", "*", "//"))]
    A.check("code: manual-reads.js writes the middle dot and the plus-minus sign as \\u escapes (every code line is ASCII)",
            raw == [], json.dumps(raw))


@A.case
def t_form_app_save(br):
    ctx, pg = A.open_app(br, mode="app")
    open_form(pg)
    pg.check("#mrMeters input[value='__other']")
    pg.fill("#mrOther", "TEST-1")
    pg.fill("#mrRead", "0042")
    pg.fill("#mrMult", "1")
    save_form(pg)
    st = pg.evaluate("() => Object.values(window.__native.st.entries).map(j => JSON.parse(j))")
    calls = [c[0] for c in A.native(pg)["calls"]]
    A.check("app: Save stores the read in the app's store (storePut), with no photo", len(st) == 1 and st[0]["read"] == "0042" and st[0]["meter"] == "TEST-1"
            and "storePut" in calls and "photoPut" not in calls, json.dumps(st))
    ctx.close()


@A.case
def t_form_off_old_app(br):
    ctx, pg = A.open_app(br, mode="app", native_cfg={"bridge": "1"})
    A.check("an app older than 1.1 (bridge 1): no Manual read button (its store is missing)", pg.evaluate("() => $('aManual').hidden && MR.off"))
    pg.click("#fList")
    help_txt = pg.evaluate("() => document.querySelector('#pBody .help').textContent")
    A.check("an app older than 1.1: the help says a newer AMR Route Guide app is needed",
            "Manual reads need a newer AMR Route Guide app on this tablet." in help_txt, help_txt[-200:])
    ctx.close()
    # The first app 1.1 build (bridge 2) had the store calls only: no camera return and no Gmail export. MIN_BRIDGE cannot
    # tell it from the full build, so the page checks every call it uses.
    store_only = ["takePendingPhoto", "exportBegin", "exportAddText", "exportAddPhoto", "exportOpenGmail"]
    ctx, pg = A.open_app(br, mode="app", native_cfg={"without": store_only})
    pg.click("#fList")
    r = pg.evaluate("() => [$('aManual').hidden, MR.off, $('bManual').hidden, typeof AMRNative.storeAll, typeof AMRNative.exportBegin, "
                    "document.querySelector('#pBody .help').textContent]")
    A.check("an app build with the store calls only (bridge 2, no camera return, no Gmail export): manual reads stay off",
            r[:5] == [True, True, True, "function", "undefined"], json.dumps(r[:5]))
    A.check("that build: the help says a newer AMR Route Guide app is needed (never that Gmail opens)",
            "need a newer AMR Route Guide app" in r[5] and "Open in Gmail" not in r[5], r[5][-200:])
    ctx.close()


@A.case
def t_form_rules(br):
    ctx, pg = A.open_app(br)
    r = pg.evaluate("""() => { const out = {};
        S.fix = null; out.none = mrGpsNow();
        onFix({lat: 46.73, lon: -117.15, acc: 75, heading: null, speed: 0, t: Date.now()}); out.weak = mrGpsNow();
        S.fixAt = Date.now() - CFG.fixStaleMs - 1000; out.stale = mrGpsNow();
        S.fixAt = Date.now(); S.blocked = true; out.blocked = mrGpsNow(); S.blocked = false;
        S.fix = null; return out; }""")
    A.check("GPS at save: none before a fix; a weak fix kept with its accuracy (75 m = 246 ft); stale or blocked gives none",
            r == {"none": None, "weak": {"lat": 46.73, "lon": -117.15, "accFt": 246}, "stale": None, "blocked": None}, json.dumps(r))
    A.feed(pg, [46.70, -117.10], acc=5)                     # 3.7 km from every meter
    open_form(pg)
    cur = pg.evaluate("() => String(currentTargetStop().o)")
    A.check("form: far from every stop it opens on the card's stop", pg.input_value("#mrStop") == cur, cur)
    pg.click("#mrCancel")
    A.check("cancel: an empty form closes on one tap", pg.evaluate("() => $('mrForm').hidden"))
    pg.evaluate("() => { S.fix = null; }")
    open_form(pg)
    pg.select_option("#mrStop", "")
    rows = pg.evaluate("() => [...document.querySelectorAll('#mrMeters input')].map(i => i.value)")
    A.check("form: No stop lists the route's meters with no location on file, then Other meter",
            rows == [m["ref"] for m in A.ROUTE.get("unmapped", [])] + ["__other"], json.dumps(rows))
    pg.check("#mrMeters input[value='__other']")
    pg.fill("#mrRead", "7")
    pg.fill("#mrMult", "1")
    pg.click("#mrSave")
    A.check("form: Other meter needs a typed ID", A.dom(pg, "#mrMetersErr") == "Type the meter ID.", A.dom(pg, "#mrMetersErr"))
    o = pg.evaluate("() => [$('mrOther').classList.contains('mr-bad'), document.activeElement === $('mrOther'), $('mrMeters').classList.contains('mr-bad')]")
    A.check("form: Other meter with no typed ID: the ID field is red and has focus (the meter list is not marked)",
            o == [True, True, False], json.dumps(o))
    pg.fill("#mrOther", "AIRPORT-X")
    pg.fill("#mrRead", "12a")
    pg.fill("#mrMult", "0")
    pg.click("#mrSave")
    errs = pg.evaluate("() => [$('mrReadErr').textContent, $('mrMultErr').textContent]")
    A.check("form: letters in the face read and a multiplier of 0 are refused", all(errs), json.dumps(errs))
    A.check("form: a typed ID clears the red mark on the ID field at the next Save",
            pg.evaluate("() => !$('mrOther').classList.contains('mr-bad') && $('mrMetersErr').textContent === ''"))
    pg.fill("#mrRead", "0007")
    pg.fill("#mrMult", "0.1")
    save_form(pg)
    e = all_entries(pg)[-1]
    A.check("form: Other meter saves the typed ID with no route ref, building or site; no stop; no GPS",
            [e["meter"], e["ref"], e["bldg"], e["site"], e["stop"], e["other"], e["lat"], e["read"], e["mult"]] ==
            ["AIRPORT-X", "", "", "", None, True, None, "0007", "0.1"], json.dumps(e))
    A.check("form: the toast says there was no GPS fix", "No GPS fix" in (A.dom(pg, "#toast") or ""), A.dom(pg, "#toast"))
    if A.ROUTE.get("unmapped"):
        u = A.ROUTE["unmapped"][0]
        open_form(pg)
        pg.select_option("#mrStop", "")
        pg.check("#mrMeters input[value='%s']" % u["ref"])
        pg.fill("#mrRead", "1")
        pg.fill("#mrMult", "1")
        save_form(pg)
        e = all_entries(pg)[-1]
        A.check("form: a meter with no location on file keeps its route ref and site name",
                [e["meter"], e["ref"], e["site"], e["stop"]] == [u["meter"], u["ref"], u["where"].split(" \u00b7 ")[0], None], json.dumps(e))
    ctx.close()


@A.case
def t_form_draft(br):
    for mode in MODES:
        ctx, pg = A.open_app(br, mode=mode)
        open_form(pg)
        ref = pg.evaluate("() => document.querySelector('#mrMeters input').value")
        pg.check("#mrMeters input[value='%s']" % ref)
        pg.fill("#mrRead", "0099")
        pg.fill("#mrMult", "100")
        A.pump_until(pg, lambda: pg.evaluate("async () => { const d = await mrDraftGet(); return !!(d && d.form && d.form.mult === '100'); }"), timeout=5)
        pg.reload()
        pg.wait_for_selector("#startBtns button", timeout=20000)
        back = A.pump_until(pg, lambda: pg.evaluate("() => !$('mrForm').hidden"), timeout=8)
        r = pg.evaluate("() => [$('mrRead').value, $('mrMult').value, (document.querySelector('#mrMeters input:checked') || {}).value]")
        A.check(mode + " draft: after a reload (Android can close the page while the camera is open) the unsaved form comes back",
                back and r == ["0099", "100", ref], json.dumps(r))
        A.check(mode + " draft: a toast says so", "unsaved manual read is back" in (A.dom(pg, "#toast") or ""), A.dom(pg, "#toast"))
        pg.click("#mrCancel")
        armed = [pg.evaluate("() => $('mrForm').hidden"), A.dom(pg, "#mrCancel")]
        pg.click("#mrCancel")
        gone = A.pump_until(pg, lambda: pg.evaluate("async () => $('mrForm').hidden && (await mrDraftGet()) === undefined"), timeout=3)
        A.check(mode + " cancel: a filled form needs a second tap; then the form and its draft are gone",
                armed == [False, "Tap again to discard"] and gone, json.dumps([armed, gone]))
        ctx.close()


@A.case
def t_form_blocked(br):
    for label, mode, kw in (("browser", "browser", {"init": BLOCK_IDB}), ("app", "app", {"native_cfg": {"storeError": "error: disk full"}}),
                            ("app, bridge answers nothing", "app", {"native_cfg": {"notApp": True}})):
        ctx, pg = A.open_app(br, mode=mode, **kw)
        open_form(pg)
        pg.check("#mrMeters input[value='__other']")
        pg.fill("#mrOther", "X1")
        pg.fill("#mrRead", "0042")
        pg.fill("#mrMult", "1")
        pg.click("#mrSave")
        pg.wait_for_timeout(500)
        r = pg.evaluate("() => [$('mrForm').hidden, $('mrRead').value, $('toast').textContent]")
        A.check(label + ": a blocked or full store: Save keeps the form open with the values and says it could not save",
                r[0] is False and r[1] == "0042" and "Could not save" in r[2], json.dumps(r))
        ctx.close()


@A.case
def t_form_phone(br):
    ctx, pg = A.open_app(br, viewport=(412, 915), is_mobile=True, has_touch=True, device_scale_factor=2.6)
    open_form(pg)
    r = pg.evaluate("""() => { const s = document.querySelector('#mrForm .mr-sheet').getBoundingClientRect();
        $('mrSave').scrollIntoView({block: 'center'}); const b = $('mrSave').getBoundingClientRect();
        return {over: document.documentElement.scrollWidth > innerWidth, sheet: [Math.round(s.left), Math.round(s.right)],
                save: b.top >= 0 && b.bottom <= innerHeight}; }""")
    A.check("phone: the form fits the width (no side scroll) and Save can be reached",
            r["over"] is False and r["sheet"][0] >= 0 and r["sheet"][1] <= 412 and r["save"], json.dumps(r))
    ctx.close()
    # The meter list: no height cap on any screen (the sheet scrolls, so Other meter stays reachable and no row is cut;
    # shot 04, 10/02/2026). Stop 2 has 6 meters; Save with nothing filled in must show the Other meter row.
    m = A.STOPS[2]["meters"][0]
    for label, vp, kw, cap in (("phone", (412, 915), {"is_mobile": True, "has_touch": True, "device_scale_factor": 2.6}, "none"),
                               ("tablet", (800, 1280), {}, "none")):
        ctx, pg = A.open_app(br, viewport=vp, **kw)
        A.feed(pg, [m["lat"], m["lon"]], acc=9)
        open_form(pg)
        pg.click("#mrSave")
        pg.wait_for_timeout(300)
        r = pg.evaluate("""() => { const box = $('mrMeters'), cs = getComputedStyle(box), b = box.getBoundingClientRect(),
            o = document.querySelector('#mrMeters .mr-other').getBoundingClientRect();
            return {rows: box.querySelectorAll('.mr-m').length, cap: cs.maxHeight, inner: box.scrollHeight > box.clientHeight + 1,
                    other: o.top >= 0 && o.bottom <= innerHeight && o.bottom <= b.bottom + 1, err: $('mrMetersErr').textContent}; }""")
        if label == "phone":
            A.check("phone: the meter list has no height cap and no inner scroll; after Save with nothing filled in the Other meter row is in view",
                    r["rows"] == 7 and r["cap"] == cap and r["inner"] is False and r["other"] and r["err"] != "", json.dumps(r))
        else:
            A.check("tablet: the meter list has no height cap and no inner scroll either (shot 04: no row cut)",
                    r["cap"] == cap and r["inner"] is False and r["rows"] == 7, json.dumps(r))
        ctx.close()


def jpeg_bytes(w, h, orientation=None, detail=False):
    """A JPEG made with Pillow. orientation: an EXIF Orientation value. detail: a photo-like picture (gradient and noise);
    else one colour with a red block in the stored top-left corner."""
    if detail:
        grad = Image.linear_gradient("L").resize((w, h))
        img = Image.merge("RGB", (grad, Image.effect_noise((w, h), 12), grad.transpose(Image.Transpose.FLIP_LEFT_RIGHT)))
    else:
        img = Image.new("RGB", (w, h), (90, 140, 170))
        img.paste((220, 30, 30), (0, 0, w // 4, h // 4))
    buf = io.BytesIO()
    if orientation:
        exif = Image.Exif()
        exif[0x0112] = orientation
        img.save(buf, "JPEG", quality=90, exif=exif.tobytes())
    else:
        img.save(buf, "JPEG", quality=90)
    return buf.getvalue()


def pick_photo(pg, data, name="IMG_0001.jpg"):
    """Hand a file to the camera input, as the camera app does; True when the page has finished with it."""
    n = pg.evaluate("() => MR.photoSeq || 0")
    pg.set_input_files("#mrCam", files=[{"name": name, "mimeType": "image/jpeg", "buffer": data}])
    return A.pump_until(pg, lambda: pg.evaluate("() => MR.photoSeq || 0") > n, timeout=15)


@A.case
def t_photo(br):
    ctx, pg = A.open_app(br)
    open_form(pg)
    cam = pg.evaluate("() => { const c = $('mrCam'); return [c.type, c.accept, c.getAttribute('capture'), $('mrPhotoBtn').textContent, $('mrThumb').hidden]; }")
    A.check("photo: a camera input for the back camera; the button says Photo; no thumbnail yet",
            cam == ["file", "image/*", "environment", "Photo", True], json.dumps(cam))
    sizes = pg.evaluate("() => [300, 30000, 99999, 100000, 523456].map(mrSizeText)")
    A.check("photo (S6): the size note never says 0.0 MB: under 0.1 MB it gives KB",
            sizes == ["1 KB", "30 KB", "100 KB", "0.1 MB", "0.5 MB"], json.dumps(sizes))
    ok = pick_photo(pg, jpeg_bytes(400, 200, orientation=6))
    r = pg.evaluate("""async () => { const b = await createImageBitmap(MR.form.photo); const c = document.createElement('canvas');
        c.width = b.width; c.height = b.height; const g = c.getContext('2d', {willReadFrequently: true}); g.drawImage(b, 0, 0);
        const tr = g.getImageData(b.width - 10, 10, 1, 1).data, tl = g.getImageData(10, 10, 1, 1).data;
        return {w: b.width, h: b.height, type: MR.form.photo.type, redTopRight: tr[0] > 150 && tr[1] < 100, redTopLeft: tl[0] > 150 && tl[1] < 100,
                thumb: !$('mrThumb').hidden, btn: $('mrPhotoBtn').textContent, del: !$('mrPhotoDel').hidden}; }""")
    A.check("photo: EXIF orientation applied (400x200 tagged 6 becomes 200x400; the red corner moves to the top right); JPEG; Retake photo and Remove photo",
            ok and r == {"w": 200, "h": 400, "type": "image/jpeg", "redTopRight": True, "redTopLeft": False, "thumb": True,
                         "btn": "Retake photo", "del": True}, json.dumps(r))
    ok = pick_photo(pg, jpeg_bytes(3264, 2448, detail=True), "IMG_0002.jpg")
    r = pg.evaluate("() => Object.assign({size: MR.form.photo.size, note: $('mrPhotoNote').textContent}, MR.form.photoInfo)")
    A.check("photo: a 3264x2448 camera photo is kept at 2000x1500, about 0.5 MB (first quality at or under 600 KB, else 0.5)",
            ok and r["w"] == 2000 and r["h"] == 1500 and r["size"] <= 1000000 and (r["size"] <= 600000 or r["q"] == 0.5), json.dumps(r))
    A.check("photo (S6): the note gives the size of a large photo in MB",
            re.fullmatch(r"Photo kept with the read, \d\.\d MB\.", r["note"]) is not None, r["note"])
    head = pg.evaluate("""async () => { const u = new Uint8Array(await MR.form.photo.slice(0, 4096).arrayBuffer());
        return [Array.from(u.slice(0, 3)), String.fromCharCode(...u).includes('Exif')]; }""")
    A.check("photo: the kept photo is a JPEG with no EXIF block (no GPS or time tags inside it)", head == [[255, 216, 255], False], json.dumps(head))
    ok = pick_photo(pg, b"not a picture", "x.jpg")
    r = pg.evaluate("() => [MR.form.photoInfo && MR.form.photoInfo.w, $('mrPhotoNote').textContent]")
    A.check("photo: a file that is not a picture keeps the last photo and says Try again", ok and r == [2000, "The photo could not be read. Try again."], json.dumps(r))
    pg.click("#mrPhotoDel")
    r = pg.evaluate("() => [MR.form.photo, $('mrThumb').hidden, $('mrPhotoBtn').textContent]")
    A.check("photo: Remove photo clears it", r == [None, True, "Photo"], json.dumps(r))
    pick_photo(pg, jpeg_bytes(1200, 900), "IMG_0003.jpg")
    note = pg.evaluate("() => [MR.form.photo.size, $('mrPhotoNote').textContent]")
    A.check("photo (S6): a photo under 0.1 MB shows its size in KB, never 0.0 MB",
            note[0] < 100000 and re.fullmatch(r"Photo kept with the read, \d+ KB\.", note[1]) is not None, json.dumps(note))
    pg.check("#mrMeters input[value='__other']")
    pg.fill("#mrOther", "P1")
    pg.fill("#mrRead", "5")
    pg.fill("#mrMult", "1")
    save_form(pg)
    r = pg.evaluate("async () => { const e = (await mrAll())[0]; const b = await mrPhoto(e.id); return [e.photoBytes, b ? b.size : -1]; }")
    A.check("photo: Save stores the photo; the entry records its size", r[0] > 0 and r[0] == r[1], json.dumps(r))
    ctx.close()


@A.case
def t_photo_app(br):
    ctx, pg = A.open_app(br, mode="app")
    open_form(pg)
    pick_photo(pg, jpeg_bytes(1200, 900), "IMG_0004.jpg")
    pg.check("#mrMeters input[value='__other']")
    pg.fill("#mrOther", "P2")
    pg.fill("#mrRead", "6")
    pg.fill("#mrMult", "1")
    save_form(pg)
    r = pg.evaluate("""() => { const st = window.__native.st, id = Object.keys(st.entries)[0], e = JSON.parse(st.entries[id]);
        return [e.photoBytes === atob(st.photos[id]).length, st.photos[id].slice(0, 4)]; }""")
    A.check("app photo: Save puts the photo in the app's store (base64 JPEG) and the entry records its size", r == [True, "/9j/"], json.dumps(r))
    ctx.close()


SLOW_SHRINK = """() => { const real = mrShrink; window.__shrinkGate = new Promise(r => { window.__shrinkGo = r; });
    window.mrShrink = async f => { await window.__shrinkGate; return real(f); }; }"""


@A.case
def t_photo_busy(br):
    """A photo still being made smaller: Save waits for it (never a read saved without its photo), and a form that
    closed meanwhile never hands its photo to the next form."""
    for mode in MODES:
        ctx, pg = A.open_app(br, mode=mode)
        open_form(pg)
        pg.check("#mrMeters input[value='__other']")
        pg.fill("#mrOther", "BUSY1")
        pg.fill("#mrRead", "0041")
        pg.fill("#mrMult", "1")
        pg.evaluate(SLOW_SHRINK)
        n = pg.evaluate("() => MR.photoSeq || 0")
        pg.set_input_files("#mrCam", files=[{"name": "IMG_0005.jpg", "mimeType": "image/jpeg", "buffer": jpeg_bytes(1440, 1080)}])
        A.pump_until(pg, lambda: A.dom(pg, "#mrPhotoNote") == "Saving the photo...", timeout=5)
        r = pg.evaluate("() => { const off = $('mrSave').disabled; $('mrSave').click(); return [off, $('mrForm').hidden]; }")
        pg.wait_for_timeout(300)
        A.check(mode + " photo busy: Save is off while the photo is made smaller, and a tap then saves nothing",
                r == [True, False] and not pg.evaluate("() => $('mrForm').hidden") and all_entries(pg) == [], json.dumps(r))
        pg.evaluate("() => window.__shrinkGo()")
        A.pump_until(pg, lambda: pg.evaluate("() => MR.photoSeq || 0") > n, timeout=10)
        save_form(pg)
        e = all_entries(pg)
        b = pg.evaluate("async (id) => { const p = await mrPhoto(id); return p ? p.size : 0; }", e[0]["id"] if e else "")
        A.check(mode + " photo busy: once the photo is ready, Save stores the read with its photo",
                len(e) == 1 and e[0]["photoBytes"] > 0 and b == e[0]["photoBytes"], json.dumps([len(e), b]))
        open_form(pg)
        pg.evaluate(SLOW_SHRINK)
        n = pg.evaluate("() => MR.photoSeq || 0")
        pg.set_input_files("#mrCam", files=[{"name": "IMG_0006.jpg", "mimeType": "image/jpeg", "buffer": jpeg_bytes(1440, 1080)}])
        A.pump_until(pg, lambda: A.dom(pg, "#mrPhotoNote") == "Saving the photo...", timeout=5)
        pg.evaluate("() => { mrCloseForm(); }")                # the reader closed form A; form B opens
        open_form(pg)
        pg.evaluate("() => window.__shrinkGo()")
        A.pump_until(pg, lambda: pg.evaluate("() => MR.photoSeq || 0") > n, timeout=10)
        r = pg.evaluate("() => [!!MR.form.photo, $('mrThumb').hidden, $('mrPhotoNote').textContent, $('mrSave').disabled, $('mrPhotoBtn').disabled]")
        A.check(mode + " photo busy: a photo of a form that closed is dropped; the next form gets none, and its buttons work",
                r == [False, True, "Optional: one photo of the meter face.", False, False], json.dumps(r))
        ctx.close()


@A.case
def t_photo_missing(br):
    """A read must never name a photo the store does not hold, and an edit can always clear such a name."""
    ctx, pg = A.open_app(br, mode="app", start=False)
    pg.evaluate("() => { CFG.skipConfirmMs = 1500; }")
    seed(pg, [dict(id="pm1", savedAt=A.T1, meter="M1", ref="200301", stop=2, read="1", mult="1", photo=[160, 120])])
    pg.evaluate("() => mrOpenForm({editId: 'pm1'})")
    pg.wait_for_selector("#mrForm:not([hidden])", timeout=5000)
    pg.click("#mrPhotoDel")
    pg.evaluate("""() => { const N = window.AMRNative, real = N.storePut;                         // storePut fails once
        N.storePut = function () { N.storePut = real; return 'error: No space left on device'; }; }""")
    pg.click("#mrSave")
    pg.wait_for_timeout(400)
    r = pg.evaluate("() => [!!window.__native.st.photos.pm1, JSON.parse(window.__native.st.entries.pm1).photoBytes > 0, $('mrForm').hidden]")
    A.check("app edit: Remove photo, then a save that fails: the photo file stays while the entry still names it",
            r == [True, True, False], json.dumps(r))
    pg.click("#mrSave")
    pg.wait_for_selector("#mrForm", state="hidden", timeout=5000)
    r = pg.evaluate("() => [!!window.__native.st.photos.pm1, JSON.parse(window.__native.st.entries.pm1).photoBytes]")
    A.check("app edit: the save that works writes the entry first, then deletes the photo", r == [False, 0], json.dumps(r))
    ctx.close()
    for mode in MODES:
        ctx, pg = A.open_app(br, mode=mode, start=False)
        seed(pg, [dict(id="pm2", savedAt=A.T1, meter="M2", ref="200302", stop=2, read="2", mult="1", photo=[160, 120])])
        pg.evaluate("() => mrStore() === MR_APP ? (delete window.__native.st.photos.pm2, window.__native.save()) : "
                    "mrTx(['photos'], 'readwrite', st => { st.photos.delete('pm2'); })")       # the photo is gone (any cause)
        pg.evaluate("() => mrOpenForm({editId: 'pm2'})")
        pg.wait_for_selector("#mrForm:not([hidden])", timeout=5000)
        pg.click("#mrSave")
        pg.wait_for_selector("#mrForm", state="hidden", timeout=5000)
        A.check(mode + " edit: a read whose photo is gone: an edit with no change saves it with no photo (photoBytes 0)",
                entry(pg, "pm2")["photoBytes"] == 0, json.dumps(entry(pg, "pm2")["photoBytes"]))
        ctx.close()


@A.case
def t_photo_draft(br):
    ctx, pg = A.open_app(br)
    open_form(pg)
    pg.check("#mrMeters input[value='__other']")
    pg.fill("#mrOther", "D1")
    pg.fill("#mrRead", "0031")
    with pg.expect_file_chooser() as fc:
        pg.click("#mrPhotoBtn")
    saved = A.pump_until(pg, lambda: pg.evaluate("async () => { const d = await mrDraftGet(); return !!(d && d.form && d.form.read === '0031'); }"), timeout=3)
    A.check("browser photo: Photo saves the form as a draft before the camera opens", saved)
    n = pg.evaluate("() => MR.photoSeq || 0")
    fc.value.set_files(files=[{"name": "IMG_0004.jpg", "mimeType": "image/jpeg", "buffer": jpeg_bytes(800, 600)}])
    A.pump_until(pg, lambda: pg.evaluate("() => MR.photoSeq || 0") > n, timeout=10)
    A.pump_until(pg, lambda: pg.evaluate("async () => { const d = await mrDraftGet(); return !!(d && d.form && d.form.photo); }"), timeout=3)
    pg.reload()
    pg.wait_for_selector("#startBtns button", timeout=20000)
    back = A.pump_until(pg, lambda: pg.evaluate("() => !$('mrForm').hidden && !$('mrThumb').hidden"), timeout=8)
    r = pg.evaluate("() => [$('mrOther').value, $('mrRead').value, MR.form && MR.form.photo && MR.form.photo.type]")
    A.check("browser photo: after a reload the draft comes back with its photo", back and r == ["D1", "0031", "image/jpeg"], json.dumps(r))
    ctx.close()


@A.case
def t_photo_pending(br):
    """Android closed the app while the camera was open: the form comes back, and the camera's photo with it."""
    ctx, pg = A.open_app(br, mode="app")
    open_form(pg)
    pg.check("#mrMeters input[value='__other']")
    pg.fill("#mrOther", "D2")
    pg.fill("#mrRead", "0032")
    with pg.expect_file_chooser():
        pg.click("#mrPhotoBtn")
    saved = A.pump_until(pg, lambda: pg.evaluate("() => { const d = window.__native.st.draft; return !!d && JSON.parse(d).form.awaitingPhoto === true; }"), timeout=4)
    A.check("app photo: Photo keeps the form as a draft that waits for a photo, before the camera opens", saved)
    b64 = base64.b64encode(jpeg_bytes(1200, 900)).decode("ascii")
    pg.evaluate("(b) => { window.__native.st.pending = b; window.__native.save(); }", b64)   # the app kept the camera's photo
    pg.reload()
    pg.wait_for_selector("#startBtns button", timeout=20000)
    back = A.pump_until(pg, lambda: pg.evaluate("() => !$('mrForm').hidden && !$('mrThumb').hidden"), timeout=10)
    r = pg.evaluate("() => [$('mrOther').value, $('mrRead').value, MR.form && MR.form.photo && MR.form.photo.type, MR.form && MR.form.awaitingPhoto, window.__native.st.pending || '']")
    A.check("app photo: after Android closed the app, the form comes back with the camera's photo, taken over once",
            back and r == ["D2", "0032", "image/jpeg", False, ""], json.dumps(r[:4]))
    ctx.close()


PERSIST_MOCK = """window.__persistCalls = 0; window.__kept = false;
Object.defineProperty(StorageManager.prototype, 'persisted', {configurable: true, value: async function () { return window.__kept; }});
Object.defineProperty(StorageManager.prototype, 'persist', {configurable: true, value: async function () { window.__persistCalls++; window.__kept = true; return true; }});"""


def entry(pg, eid):
    return next((e for e in all_entries(pg) if e["id"] == eid), None)


@A.case
def t_list(br):
    ctx, pg = A.open_app(br, start=False)
    pg.evaluate("() => { CFG.skipConfirmMs = 1500; }")
    seed(pg, [dict(id="a", savedAt=A.T1, meter="0353_DW_001", ref="200041", bldg="0353", site="CREAM ANNEX", stop=2, read="004512", mult="10", photo=[640, 480]),
              dict(id="b", savedAt=A.T1 + 60000, meter="0357_DW_001", ref="200043", stop=2, read="7", mult="1"),
              dict(id="c", savedAt=A.T1 - 86400000, meter="0066ADW_001", ref="200038", stop=3, read="1", mult="1", status="exported",
                   exportedAt=A.T1 - 10 * 86400000)])
    A.check("start screen: a Manual reads button with the new count", A.dom(pg, "#mrStartList") == "Manual reads (2 new)", A.dom(pg, "#mrStartList"))
    pg.click("#mrStartList")
    pg.wait_for_selector("#mrList:not([hidden])", timeout=5000)
    A.pump_until(pg, lambda: pg.evaluate("() => document.querySelectorAll('#mrListBody .mr-row').length") == 3, timeout=3)
    r = pg.evaluate("""() => ({over: $('mrList').classList.contains('over'), sum: $('mrSum').textContent,
        rows: [...document.querySelectorAll('#mrListBody .mr-row')].map(r => [r.dataset.id, [...r.querySelectorAll('button')].map(b => b.textContent)]),
        exp: $('mrExportBtn').textContent, clear: $('mrClear') && $('mrClear').textContent})""")
    A.check("list: over the start screen; newest first; new reads have Edit and Delete, exported ones Mark new; Export and Clear",
            r == {"over": True, "sum": "2 new, 1 exported. Stored on this device only.",
                  "rows": [["b", ["Edit", "Delete"]], ["a", ["Edit", "Delete"]], ["c", ["Mark new"]]],
                  "exp": "Export 2 new", "clear": "Clear 1 exported over 7 days ago"}, json.dumps(r))
    row_a = pg.evaluate("() => document.querySelector('.mr-row[data-id=\"a\"] .rs').textContent")
    A.check("list: a row shows meter, read x multiplier, date, time, stop and photo",
            row_a.startswith("0353_DW_001: 004512 x 10") and "10/01/2026 14:32" in row_a and "stop 2" in row_a and "photo" in row_a, row_a)
    pg.click(".mr-row[data-id='a'] .mr-edit")
    pg.wait_for_selector("#mrForm:not([hidden])", timeout=5000)
    A.pump_until(pg, lambda: not pg.evaluate("() => $('mrThumb').hidden"), timeout=3)
    r = pg.evaluate("""() => [$('mrFormTitle').textContent, $('mrRead').value, $('mrMult').value, $('mrStop').value,
        (document.querySelector('#mrMeters input:checked') || {}).value, !$('mrThumb').hidden, $('mrGps').textContent]""")
    A.check("edit: the form opens with the saved values and photo",
            r == ["Edit read", "004512", "10", "2", "200041", True, "Date, time and GPS stay as first saved."], json.dumps(r))
    pg.fill("#mrRead", "004513")
    save_form(pg)
    e = entry(pg, "a")
    A.check("edit: Save changes the read; date, time and GPS stay; the photo stays",
            [e["read"], e["savedAt"], e["time"], e["photoBytes"] > 0, e["editedAt"] is not None] == ["004513", A.T1, "14:32", True, True], json.dumps(e))
    A.pump_until(pg, lambda: A.dom(pg, ".mr-row[data-id='b'] .mr-del") == "Delete", timeout=3)
    pg.click(".mr-row[data-id='b'] .mr-del")
    t1 = A.dom(pg, ".mr-row[data-id='b'] .mr-del")
    pg.wait_for_timeout(1700)
    t2 = A.dom(pg, ".mr-row[data-id='b'] .mr-del")
    still = entry(pg, "b") is not None
    pg.click(".mr-row[data-id='b'] .mr-del")
    pg.click(".mr-row[data-id='b'] .mr-del")
    gone = A.pump_until(pg, lambda: entry(pg, "b") is None, timeout=3)
    A.check("delete: one tap arms it (Tap again); when the time runs out nothing is deleted; two taps delete",
            [t1, t2, still, gone] == ["Tap again", "Delete", True, True], json.dumps([t1, t2, still, gone]))
    A.pump_until(pg, lambda: pg.query_selector(".mr-row[data-id='c'] .mr-renew") is not None, timeout=3)
    pg.click(".mr-row[data-id='c'] .mr-renew")
    A.pump_until(pg, lambda: entry(pg, "c")["status"] == "new", timeout=3)
    c = entry(pg, "c")
    A.check("Mark new: an exported read goes back to new, so it goes out with the next export (Gmail closed without Send)",
            [c["status"], c["exportName"]] == ["new", None], json.dumps(c))
    pg.evaluate("() => mrSetStatus(['a', 'c'], 'exported', 'AMR-manual-reads-x.csv').then(mrAfterChange)")
    A.pump_until(pg, lambda: pg.query_selector(".mr-row[data-id='a'] .mr-renew") is not None, timeout=3)
    A.check("list: exported reads have no Edit button", pg.query_selector(".mr-row[data-id='a'] .mr-edit") is None)
    note = A.dom(pg, "#mrClearNote") or ""
    A.check("clear (K8): reads exported today cannot be cleared yet; the list says to clear only after the email is in Gmail Sent",
            pg.query_selector("#mrClear") is None and "Gmail Sent" in note and "7 days" in note, note)
    pg.evaluate("""async () => { for (const id of ['a', 'c']) { const e = await mrGet(id); e.exportedAt = Date.now() - 8 * 86400000;
        await mrSaveEntry(e, undefined); } mrAfterChange(); }""")
    A.pump_until(pg, lambda: A.dom(pg, "#mrClear") == "Clear 2 exported over 7 days ago", timeout=3)
    pg.click("#mrClear")
    t1 = A.dom(pg, "#mrClear")
    pg.click("#mrClear")
    cleared = A.pump_until(pg, lambda: len(all_entries(pg)) == 0, timeout=3)
    A.check("clear: two taps clear the reads exported over 7 days ago", t1 == "Tap again to clear 2" and cleared, t1)
    A.pump_until(pg, lambda: A.dom(pg, "#mrExportBtn") == "Nothing new to export", timeout=3)
    A.check("list: with nothing new, Export says so and is off; the start screen button is gone",
            pg.evaluate("() => $('mrExportBtn').disabled") and A.dom(pg, "#mrStartList") is None)
    pg.click("#mrListClose")
    seed(pg, [dict(id="d", savedAt=A.T1, meter="X", read="1", mult="1", other=True)])
    pg.click("#startBtns button")
    pg.wait_for_timeout(600)
    pg.click("#fList")
    A.check("stop list: a Manual reads button with the new count", A.dom(pg, "#bManual") == "Manual reads (1 new)", A.dom(pg, "#bManual"))
    pg.click("#bManual")
    pg.wait_for_selector("#mrList:not([hidden])", timeout=5000)
    r = pg.evaluate("() => [$('panel').classList.contains('show'), $('mrList').classList.contains('over')]")
    A.check("stop list: Manual reads closes the stop list and opens the reads (normal level while guiding)", r == [False, False], json.dumps(r))
    pg.click("#mrNew")
    pg.wait_for_selector("#mrForm:not([hidden])", timeout=5000)
    z = pg.evaluate("() => [+getComputedStyle($('mrForm')).zIndex, +getComputedStyle($('mrList')).zIndex]")
    A.check("list: New read opens the form above the list", z[0] > z[1], json.dumps(z))
    ctx.close()


@A.case
def t_list_app(br):
    ctx, pg = A.open_app(br, mode="app", start=False)
    pg.evaluate("() => { CFG.skipConfirmMs = 1500; }")
    seed(pg, [dict(id="a", savedAt=A.T1, meter="0353_DW_001", ref="200041", stop=2, read="004512", mult="10", photo=[320, 240]),
              dict(id="c", savedAt=A.T1 - 86400000, meter="0066ADW_001", ref="200038", stop=3, read="1", mult="1", status="exported")])
    pg.click("#mrStartList")
    pg.wait_for_selector("#mrList:not([hidden])", timeout=5000)
    A.pump_until(pg, lambda: pg.evaluate("() => document.querySelectorAll('#mrListBody .mr-row').length") == 2, timeout=3)
    keep = A.dom(pg, "#mrKeep")
    A.check("app list: the reads are kept in the app on this tablet", keep == "Kept in the app on this tablet until you clear them. Uninstalling the app deletes them.", keep)
    pg.click(".mr-row[data-id='a'] .mr-del")
    pg.click(".mr-row[data-id='a'] .mr-del")
    gone = A.pump_until(pg, lambda: pg.evaluate("() => !('a' in window.__native.st.entries) && !('a' in window.__native.st.photos)"), timeout=3)
    A.check("app list: two taps delete the read and its photo from the app's store", gone)
    pg.click(".mr-row[data-id='c'] .mr-renew")
    renewed = A.pump_until(pg, lambda: pg.evaluate("() => JSON.parse(window.__native.st.entries.c).status === 'new'"), timeout=3)
    A.check("app list: Mark new is saved in the app's store", renewed)
    ctx.close()
    # A read in this profile's IndexedDB (browser storage): an app page must never show or read it (spec 5), so the
    # check can fail if the app mode ever fell back to IndexedDB.
    ctx, pg = A.open_app(br, start=False)
    seed(pg, [dict(id="idb1", savedAt=A.T1, meter="M1", ref="200201", read="1", mult="1")])
    pg.close()
    ctx, pg = A.open_app(br, mode="app", start=False, native_cfg={"bridge": "1"}, ctx=ctx)
    pg.evaluate("() => openPanel()")                 # the start screen covers the side buttons
    r = pg.evaluate("() => [document.getElementById('mrStartList'), $('bManual').hidden]")
    A.check("an app older than 1.1: no Manual reads button on the start screen or in the stop list (a read in IndexedDB is never shown)",
            r == [None, True], json.dumps(r))
    ctx.close()


@A.case
def t_list_protected(br):
    ctx, pg = A.open_app(br, init=PERSIST_MOCK)
    seed(pg, [dict(id="p0", savedAt=A.T1, meter="X0", read="1", mult="1", other=True)])
    pg.click("#fList")
    pg.click("#bManual")
    pg.wait_for_selector("#mrKeep", timeout=5000)
    before = A.dom(pg, "#mrKeep")
    pg.click("#mrListClose")
    open_form(pg)
    pg.check("#mrMeters input[value='__other']")
    pg.fill("#mrOther", "X1")
    pg.fill("#mrRead", "1")
    pg.fill("#mrMult", "1")
    save_form(pg)
    asked = A.pump_until(pg, lambda: pg.evaluate("() => window.__persistCalls") >= 1, timeout=3)
    pg.click("#fList")
    pg.click("#bManual")
    A.pump_until(pg, lambda: (A.dom(pg, "#mrKeep") or "").startswith("Protected"), timeout=3)
    after = A.dom(pg, "#mrKeep") or ""
    A.check("browser list: Not protected until the browser keeps the reads; the first Save asks for it; then Protected",
            (before or "").startswith("Not protected") and asked and after.startswith("Protected"), json.dumps([before, after]))
    ctx.close()


@A.case
def t_list_no_route(br):
    ctx = A.new_context(br)
    ctx.route(re.compile(r"/amr-nav/route\.json(\?.*)?$"), lambda route: route.fulfill(status=500, content_type="text/plain", body="down"))
    n = len(A.errors)
    pg = ctx.new_page()
    A.attach(pg)
    pg.goto(A.BASE + "?sim=1")
    A.wait_for(pg, lambda: "did not load" in A.text(pg, "#startBody"), timeout=20)
    seed(pg, [dict(id="n1", savedAt=A.T1, meter="0353_DW_001", ref="200041", read="1", mult="1")])
    pg.click("#mrStartList")
    pg.wait_for_selector("#mrList:not([hidden])", timeout=5000)
    A.pump_until(pg, lambda: pg.evaluate("() => document.querySelectorAll('#mrListBody .mr-row').length") == 1, timeout=3)
    ok = pg.evaluate("() => [document.querySelectorAll('#mrListBody .mr-row').length, $('mrExportBtn').disabled]")
    A.check("no route: the start screen still offers the stored reads; the list opens with Export on", ok == [1, False], json.dumps(ok))
    ctx.close()
    extra = A.errors[n:]
    A.check("no route: the only console errors are the expected route failure ones",
            all(("route.json is missing or damaged" in e) or ("Failed to load resource" in e) for e in extra), " || ".join(extra)[:300])
    del A.errors[n:]


@A.case
def t_list_rulings(br):
    """S4: an exported read's CSV name stays on one line, cut with an ellipsis, full name in the title.
    S5: in portrait (under 900 px wide) the lists use the whole screen; in landscape they stay a side panel."""
    name = "AMR-manual-reads-20261001-1432-part12of12.csv"
    ctx, pg = A.open_app(br, start=False, viewport=(320, 640))
    seed(pg, [dict(id="x", savedAt=A.T1, meter="0353_DW_001", ref="200041", stop=2, read="004512", mult="10", status="exported")])
    pg.evaluate("(n) => mrSetStatus(['x'], 'exported', n).then(mrAfterChange)", name)
    pg.evaluate("() => mrOpenList()")                        # the start card is taller than this small screen
    pg.wait_for_selector(".mr-row[data-id='x'] .mr-file", timeout=5000)
    r = pg.evaluate("""() => { const f = document.querySelector('.mr-row[data-id="x"] .mr-file'), s = getComputedStyle(f);
        return {text: f.textContent, title: f.title, ws: s.whiteSpace, tov: s.textOverflow, ov: s.overflow,
                oneLine: f.getBoundingClientRect().height < 1.6 * parseFloat(s.lineHeight === 'normal' ? s.fontSize : s.lineHeight) + 1,
                cut: f.scrollWidth > f.clientWidth}; }""")
    A.check("S4: the CSV name has its own line: one line, cut with an ellipsis, the full name in the title",
            r == {"text": name, "title": name, "ws": "nowrap", "tov": "ellipsis", "ov": "hidden", "oneLine": True, "cut": True}, json.dumps(r))
    ctx.close()
    ctx, pg = A.open_app(br, start=False)                    # 800 x 1280: the tablet in portrait
    seed(pg, [dict(id="y", savedAt=A.T1, meter="X", read="1", mult="1", other=True)])
    pg.click("#mrStartList")
    pg.wait_for_selector("#mrList:not([hidden])", timeout=5000)
    w = lambda sel: pg.evaluate("(s) => Math.round(document.querySelector(s).getBoundingClientRect().width)", sel)
    portrait = [w("#mrList"), pg.evaluate("() => innerWidth")]
    pg.click("#mrListClose")
    pg.evaluate("() => openPanel()")
    portrait.append(w("#panel"))
    pg.evaluate("() => closePanel()")
    pg.set_viewport_size({"width": 1280, "height": 800})     # landscape: side panels
    pg.click("#mrStartList")
    pg.wait_for_selector("#mrList:not([hidden])", timeout=5000)
    land = [w("#mrList")]
    pg.click("#mrListClose")
    pg.evaluate("() => openPanel()")
    land.append(w("#panel"))
    A.check("S5: portrait (800 px wide): the Manual reads list and the stop list use the whole width; landscape: a 440 px side panel",
            portrait == [800, 800, 800] and land == [440, 440], json.dumps([portrait, land]))
    ctx.close()


SHARE_MOCK = """
window.__shares = []; window.__shareMode = 'resolve';
Object.defineProperty(Navigator.prototype, 'canShare', {configurable: true, writable: true,
  value: function (d) { return !!(d && Array.isArray(d.files)); }});
Object.defineProperty(Navigator.prototype, 'share', {configurable: true, writable: true, value: async function (d) {
  const rec = {keys: Object.keys(d).sort(), title: d.title, text: d.text, files: []};
  for (const f of d.files || []) {
    const u8 = new Uint8Array(await f.arrayBuffer());
    rec.files.push({name: f.name, type: f.type, size: f.size, head: Array.from(u8.slice(0, 3)), csv: f.type === 'text/csv' ? Array.from(u8) : null});
  }
  window.__shares.push(rec);
  const m = window.__shareMode;
  if (m === 'abort') throw new DOMException('Share canceled', 'AbortError');
  if (m === 'fail') throw new DOMException('Permission denied', 'NotAllowedError');
  if (m === 'hang') return new Promise(() => {});
  if (m === 'later') return new Promise(res => { window.__resolveShare = res; });
}});
"""
CSV_HEAD = ("Date,Time,Meter ID,Route ref,Building number,Site name,Face read,Multiplier,Notes,Photo file name,"
            "GPS latitude,GPS longitude,GPS accuracy (ft),Stop number")


def shares(pg):
    return pg.evaluate("() => window.__shares")


def open_export(pg):
    """From the start screen: Manual reads, then Export. Waits until the parts are made."""
    pg.click("#mrStartList")
    pg.wait_for_selector("#mrList:not([hidden])", timeout=5000)
    pg.wait_for_function("() => /^Export \\d+ new$/.test($('mrExportBtn').textContent)", timeout=5000)
    pg.click("#mrExportBtn")
    pg.wait_for_selector("#mrExport:not([hidden]) #mrPart0 button", timeout=10000)


def csv_rows(rec):
    raw = bytes(next(f for f in rec["files"] if f["type"] == "text/csv")["csv"])
    return raw, raw.decode("utf-8-sig").split("\r\n")


def two_reads(pg):
    m = A.STOPS[2]["meters"][0]
    site = m["where"].split(" \u00b7 ")[0]
    seed(pg, [dict(id="a", savedAt=A.T1, meter=m["meter"], ref=m["ref"], bldg=m["bldg"], site=site, stop=2, read="004512", mult="10",
                   notes='Lid "stuck", used bar', gps={"lat": 46.727212, "lon": -117.146276, "accFt": 30}, photo=[640, 480]),
              dict(id="b", savedAt=A.T1 + 180000, meter="AIRPORT-X", other=True, read="7", mult="1")])
    return m, site


@A.case
def t_export_app(br):
    ctx, pg = A.open_app(br, mode="app", start=False)
    m, site = two_reads(pg)
    open_export(pg)
    r = pg.evaluate("() => [$('mrExportBody').textContent, [...document.querySelectorAll('#mrPart0 button')].map(b => b.textContent)]")
    A.check("app export: one part with Open in Gmail; the sheet says Gmail opens with the addresses and to tap Send there",
            r[1] == ["Open in Gmail"] and "addresses" in r[0] and "tap Send in Gmail" in r[0], json.dumps(r))
    head = A.dom(pg, "#mrPart0 b") or ""
    A.check("export (S6): a small part gives its size in KB, never 0.0 MB", re.fullmatch(r"2 reads, 1 photo, \d+ KB", head) is not None, head)
    pg.click("#mrPart0 button")
    A.pump_until(pg, lambda: pg.evaluate("async () => (await mrAll()).every(e => e.status === 'exported')"), timeout=5)
    mail = A.native(pg)["mails"][0]
    A.check("app export: Gmail gets the CSV first, then the photo; the CSV name is the latest read's time (14:35), not today",
            [f["name"] for f in mail["files"]] == ["AMR-manual-reads-20261001-1435.csv", m["ref"] + "-20261001-1432.jpg"], json.dumps([f["name"] for f in mail["files"]]))
    A.check("app export: the photo is a JPEG from the app's store", mail["files"][1]["head"] == [255, 216, 255], json.dumps(mail["files"][1]))
    A.check("app export: subject and body; the page passes no address (three arguments: batch, subject, body)",
            mail["subject"] == "AMR manual reads 10/01/2026 14:35" and mail["body"] == "2 manual reads, 1 photo." and mail["args"] == 3, json.dumps(mail)[:300])
    lines = mail["files"][0]["text"].lstrip("\ufeff").split("\r\n")
    A.check("app export CSV: byte order mark, the 14 columns, CRLF rows",
            mail["files"][0]["text"].startswith("\ufeff") and lines[0] == CSV_HEAD and lines[-1] == "", lines[0])
    want1 = ",".join(["10/01/2026", "14:32", m["meter"], m["ref"], m["bldg"], site, "004512", "10", '"Lid ""stuck"", used bar"',
                      m["ref"] + "-20261001-1432.jpg", "46.727212", "-117.146276", "30", "2"])
    A.check("app export CSV: a row keeps leading zeros, quotes the notes, names the photo, and has GPS and the stop", lines[1] == want1, lines[1])
    A.check("app export CSV: an Other meter row", lines[2] == "10/01/2026,14:35,AIRPORT-X,,,,7,1,,,,,,", lines[2])
    st = pg.evaluate("async () => (await mrAll()).map(e => [e.status, e.exportName])")
    A.check("app export: once Gmail opened, the reads are marked exported with the CSV name",
            st == [["exported", "AMR-manual-reads-20261001-1435.csv"]] * 2, json.dumps(st))
    A.check("app export: the part says Gmail opened and to tap Send there", "Gmail opened" in (A.dom(pg, "#mrPartState0") or ""), A.dom(pg, "#mrPartState0"))
    ctx.close()


@A.case
def t_export_app_parts(br):
    ctx, pg = A.open_app(br, mode="app", start=False)
    seed(pg, [dict(id="p%d" % k, savedAt=A.T1 + k * 60000, meter="M%d" % k, ref=str(200100 + k), read=str(k), mult="1",
                   photo=[160, 120], photoBytes=8000000) for k in range(3)])
    open_export(pg)
    heads = pg.evaluate("() => [...document.querySelectorAll('#mrExportBody .mr-part')].map(p => p.querySelector('b').textContent)")
    A.check("app parts: 3 photos of 8 MB make 2 emails (each part at most 18 MB of files)",
            len(heads) == 2 and heads[0].startswith("Part 1 of 2: 2 reads, 2 photos") and heads[1].startswith("Part 2 of 2: 1 read, 1 photo"), json.dumps(heads))
    pg.click("#mrPart0 button")
    A.pump_until(pg, lambda: len(A.native(pg)["mails"]) == 1, timeout=5)
    st = {e["id"]: e["status"] for e in all_entries(pg)}
    mail = A.native(pg)["mails"][0]
    A.check("app parts: part 1 is one email named part1of2; only its reads are marked exported",
            mail["files"][0]["name"] == "AMR-manual-reads-20261001-1434-part1of2.csv" and mail["subject"] == "AMR manual reads 10/01/2026 14:34, part 1 of 2"
            and st == {"p0": "exported", "p1": "exported", "p2": "new"}, json.dumps([mail["files"][0]["name"], st]))
    pg.click("#mrPart1 button")
    A.pump_until(pg, lambda: all(e["status"] == "exported" for e in all_entries(pg)), timeout=5)
    A.check("app parts: part 2 from its own tap; then every read is exported; All done shows",
            len(A.native(pg)["mails"]) == 2 and "All done" in pg.evaluate("() => $('mrExportBody').textContent"))
    ctx.close()


@A.case
def t_export_app_outcomes(br):
    for gmail, want in (("no gmail", "Gmail is not on this tablet"), ("error: boom", "Gmail did not open")):
        ctx, pg = A.open_app(br, mode="app", start=False, native_cfg={"gmail": gmail})
        seed(pg, [dict(id="o1", savedAt=A.T1, meter="M1", ref="200201", read="1", mult="1", photo=[160, 120])])
        open_export(pg)
        pg.click("#mrPart0 button")
        pg.wait_for_timeout(400)
        r = [entry(pg, "o1")["status"], A.dom(pg, "#mrPartState0"), pg.evaluate("() => [...document.querySelectorAll('#mrPart0 button')].map(b => b.textContent)")]
        A.check("app export, " + gmail + ": nothing is marked; the part says so and offers Open in Gmail again",
                r[0] == "new" and want in (r[1] or "") and r[2] == ["Open in Gmail again"], json.dumps(r))
        ctx.close()
    ctx, pg = A.open_app(br, mode="app", start=False)
    seed(pg, [dict(id="o2", savedAt=A.T1, meter="M2", ref="200202", read="1", mult="1", photo=[160, 120]),
              dict(id="o4", savedAt=A.T1 + 60000, meter="M4", ref="200204", read="4", mult="1", photo=[160, 120])])
    pg.evaluate("() => { delete window.__native.st.photos.o2; window.__native.save(); }")      # the photo is gone from the store
    open_export(pg)
    pg.click("#mrPart0 button")
    A.pump_until(pg, lambda: len(A.native(pg)["mails"]) == 1, timeout=5)
    mails = A.native(pg)["mails"]
    files = [f["name"] for f in mails[0]["files"]] if mails else []
    rows = mails[0]["files"][0]["text"].split("\r\n") if mails else []
    A.check("app export: a photo missing from the app's store is left out (as in a browser); the part still goes to Gmail",
            files == ["AMR-manual-reads-20261001-1433.csv", "200204-20261001-1433.jpg"], json.dumps(files))
    A.check("app export: the CSV row of that read names no photo; the other row keeps its photo name",
            len(rows) > 2 and rows[1].split(",")[9] == "" and rows[2].split(",")[9] == "200204-20261001-1433.jpg"
            and mails[0]["body"] == "2 manual reads, 1 photo.", json.dumps(rows[1:3] + [mails[0]["body"] if mails else ""]))
    note = pg.evaluate("() => $('mrPart0').textContent")
    A.check("app export: the part says which photo was not found; both reads are marked exported",
            "200202-20261001-1432.jpg" in note and "not found" in note.lower()
            and [entry(pg, "o2")["status"], entry(pg, "o4")["status"]] == ["exported", "exported"], note)
    ctx.close()
    ctx, pg = A.open_app(br, mode="app", start=False)
    seed(pg, [dict(id="o3", savedAt=A.T1, meter="M3", ref="200203", read="1", mult="1", photo=[160, 120])])
    open_export(pg)
    pg.evaluate("() => { window.__native.cfg.notApp = true; }")          # the bridge answers nothing for a moment
    pg.click("#mrPart0 button")
    pg.wait_for_timeout(400)
    r = [A.dom(pg, "#mrPartState0"), pg.evaluate("() => [...document.querySelectorAll('#mrPart0 button')].map(b => b.textContent)"),
         pg.evaluate("() => mrInApp()"), len(A.native(pg)["mails"])]
    pg.evaluate("() => { window.__native.cfg.notApp = false; }")
    A.check("app export, the bridge answers nothing: the part fails before Gmail and never falls back to the share menu; the read stays new",
            "could not be made" in (r[0] or "") and r[1] == ["Open in Gmail again"] and r[2] is True and r[3] == 0
            and entry(pg, "o3")["status"] == "new", json.dumps(r))
    ctx.close()


FAIL_MARK = "() => { window.__realSetStatus = mrSetStatus; window.mrSetStatus = async () => { throw new Error('Storage is blocked'); }; }"
REAL_MARK = "() => { window.mrSetStatus = window.__realSetStatus; }"


def part_view(pg):
    return [A.dom(pg, "#mrPartState0") or "", pg.evaluate("() => [...document.querySelectorAll('#mrPart0 button')].map(b => b.textContent)")]


@A.case
def t_export_marking(br):
    """The files went out (Gmail opened, the share went to an app, or Downloads) but the reads could not be marked
    exported: the part never says Not sent and never offers a second email; Mark exported retries only the marking.
    Gmail's answer timed out: the reader says whether it opened. Two Export taps: one set of parts."""
    ctx, pg = A.open_app(br, mode="app", start=False)
    seed(pg, [dict(id="k1", savedAt=A.T1, meter="M1", ref="200201", read="1", mult="1", photo=[160, 120])])
    open_export(pg)
    pg.evaluate(FAIL_MARK)
    pg.click("#mrPart0 button")
    A.pump_until(pg, lambda: len(A.native(pg)["mails"]) == 1 and "Mark exported" in part_view(pg)[1], timeout=5)
    v = part_view(pg)
    A.check("app: Gmail opened but the marking failed: no 'Not sent', no Open in Gmail again; it says not to open Gmail again",
            "Not sent" not in v[0] and "Do not open Gmail again" in v[0] and v[1] == ["Mark exported"]
            and entry(pg, "k1")["status"] == "new", json.dumps(v))
    pg.evaluate(REAL_MARK)
    pg.click("#mrPart0 button:has-text('Mark exported')")
    A.pump_until(pg, lambda: entry(pg, "k1")["status"] == "exported", timeout=5)
    A.check("app: Mark exported marks the reads and opens no second email",
            entry(pg, "k1")["status"] == "exported" and len(A.native(pg)["mails"]) == 1 and "Gmail opened" in part_view(pg)[0],
            json.dumps([part_view(pg), len(A.native(pg)["mails"])]))
    ctx.close()
    ctx, pg = A.open_app(br, mode="app", start=False, native_cfg={"gmail": "error: timeout"})
    seed(pg, [dict(id="k2", savedAt=A.T1, meter="M2", ref="200202", read="1", mult="1")])
    open_export(pg)
    pg.click("#mrPart0 button")
    A.pump_until(pg, lambda: "Mark exported" in part_view(pg)[1], timeout=5)
    v = part_view(pg)
    A.check("app: Gmail's answer timed out (it may still have opened): the reader is asked; Mark exported or Open in Gmail again",
            "Did Gmail open" in v[0] and "Not sent" not in v[0] and v[1] == ["Mark exported", "Open in Gmail again"]
            and entry(pg, "k2")["status"] == "new", json.dumps(v))
    pg.click("#mrPart0 button:has-text('Mark exported')")
    A.check("app: after a timeout, Mark exported marks the reads",
            A.pump_until(pg, lambda: entry(pg, "k2")["status"] == "exported", timeout=5))
    ctx.close()
    ctx, pg = A.open_app(br, start=False, init=SHARE_MOCK)
    seed(pg, [dict(id="k3", savedAt=A.T1, meter="M3", ref="200203", read="1", mult="1", photo=[160, 120])])
    open_export(pg)
    pg.evaluate(FAIL_MARK)
    pg.click("#mrPart0 button")
    A.pump_until(pg, lambda: len(shares(pg)) == 1 and "Mark exported" in part_view(pg)[1], timeout=5)
    v = part_view(pg)
    A.check("browser: shared but the marking failed: no 'Not sent', no Share again or Save to Downloads; it says not to share again",
            "Not sent" not in v[0] and "Do not share them again" in v[0] and v[1] == ["Mark exported"], json.dumps(v))
    pg.evaluate(REAL_MARK)
    pg.click("#mrPart0 button:has-text('Mark exported')")
    A.check("browser: Mark exported marks the reads with no second share",
            A.pump_until(pg, lambda: entry(pg, "k3")["status"] == "exported", timeout=5) and len(shares(pg)) == 1)
    pg.evaluate("() => mrSetStatus(['k3'], 'new').then(() => mrCloseExport())")
    pg.evaluate("""() => { const real = mrBuildParts; let n = 0; window.__buildGo = null;
        window.mrBuildParts = async e => { n++; if (n === 1) await new Promise(r => { window.__buildGo = r; }); return real(e); };
        mrOpenExport(); }""")
    A.pump_until(pg, lambda: pg.evaluate("() => typeof window.__buildGo === 'function'"), timeout=5)   # build 1 is slow
    pg.evaluate("() => { mrOpenExport(); }")                                                           # a second tap
    pg.wait_for_selector("#mrExport:not([hidden]) #mrPart0 button", timeout=10000)
    pg.click("#mrPart0 button")
    A.pump_until(pg, lambda: len(shares(pg)) == 2, timeout=5)
    pg.evaluate("() => window.__buildGo()")
    pg.wait_for_timeout(500)
    v = part_view(pg)
    A.check("browser: two Export taps make one set of parts; a slower first build never replaces the parts on screen",
            v[1] == [] and "Shared" in v[0] and pg.evaluate("() => MRX.parts.length") == 1, json.dumps(v))
    ctx.close()


@A.case
def t_export_share(br):
    ctx, pg = A.open_app(br, start=False, init=SHARE_MOCK)
    m, site = two_reads(pg)
    open_export(pg)
    r = pg.evaluate("() => [$('mrExportBody').textContent, [...document.querySelectorAll('#mrPart0 button')].map(b => b.textContent)]")
    A.check("browser export: one part with a Share button; the sheet says to pick Gmail, type the addresses and tap Send",
            r[1] == ["Share"] and "pick Gmail" in r[0] and "type the addresses" in r[0] and "tap Send" in r[0], json.dumps(r))
    pg.click("#mrPart0 button")
    A.pump_until(pg, lambda: len(shares(pg)) == 1 and pg.evaluate("async () => (await mrAll()).every(e => e.status === 'exported')"), timeout=5)
    rec = shares(pg)[0]
    names = [f["name"] for f in rec["files"]]
    A.check("browser export: one share, the CSV first, then the photo; the name comes from the latest read (14:35)",
            names == ["AMR-manual-reads-20261001-1435.csv", m["ref"] + "-20261001-1432.jpg"], json.dumps(names))
    A.check("browser export: exact types text/csv and image/jpeg (the browser checks them)",
            [f["type"] for f in rec["files"]] == ["text/csv", "image/jpeg"] and rec["files"][1]["head"] == [255, 216, 255], json.dumps([f["type"] for f in rec["files"]]))
    A.check("browser export: the title is the subject, the text says what is in it, no url",
            rec["keys"] == ["files", "text", "title"] and rec["title"] == "AMR manual reads 10/01/2026 14:35" and rec["text"] == "2 manual reads, 1 photo.",
            json.dumps([rec["keys"], rec["title"], rec["text"]]))
    raw, lines = csv_rows(rec)
    A.check("browser CSV: UTF-8 with a byte order mark and CRLF line ends", raw[:3] == b"\xef\xbb\xbf" and raw.endswith(b"\r\n"), repr(raw[:40]))
    A.check("browser CSV: the 14 columns", lines[0] == CSV_HEAD, lines[0])
    st = pg.evaluate("async () => (await mrAll()).map(e => [e.status, e.exportName])")
    A.check("browser export: after the share resolves, the reads are marked exported with the CSV name",
            st == [["exported", "AMR-manual-reads-20261001-1435.csv"]] * 2, json.dumps(st))
    A.check("browser export: the part says Shared", "Shared" in (A.dom(pg, "#mrPartState0") or ""), A.dom(pg, "#mrPartState0"))
    ctx.close()


@A.case
def t_export_parts(br):
    ctx, pg = A.open_app(br, start=False, init=SHARE_MOCK)
    specs = [dict(id="p%02d" % k, savedAt=A.T1 + k * 60000, meter="M%02d" % k, ref=str(200100 + k), read=str(k), mult="1", photo=[320, 240]) for k in range(11)]
    specs.append(dict(id="p11", savedAt=A.T1 + 11 * 60000, meter="M11", ref="200111", read="11", mult="1"))
    seed(pg, specs)
    open_export(pg)
    heads = pg.evaluate("() => [...document.querySelectorAll('#mrExportBody .mr-part')].map(p => p.querySelector('b').textContent)")
    A.check("browser parts: 11 photos make 2 parts (one share carries at most 10 files)",
            len(heads) == 2 and heads[0].startswith("Part 1 of 2: 9 reads, 9 photos") and heads[1].startswith("Part 2 of 2: 3 reads, 2 photos"), json.dumps(heads))
    pg.click("#mrPart0 button")
    A.pump_until(pg, lambda: len(shares(pg)) == 1 and "Shared" in (A.dom(pg, "#mrPartState0") or ""), timeout=5)
    s1 = shares(pg)[0]
    st = {e["id"]: e["status"] for e in all_entries(pg)}
    A.check("browser parts: part 1 shares 10 files (the CSV and 9 photos) named part1of2; only its reads are marked exported",
            len(s1["files"]) == 10 and s1["files"][0]["name"] == "AMR-manual-reads-20261001-1443-part1of2.csv"
            and s1["title"] == "AMR manual reads 10/01/2026 14:43, part 1 of 2"
            and sorted(k for k, v in st.items() if v == "exported") == ["p%02d" % k for k in range(9)],
            json.dumps([len(s1["files"]), s1["files"][0]["name"], s1["title"], st]))
    A.check("browser parts: photo names are <route ref>-<YYYYMMDD-HHMM>.jpg",
            [f["name"] for f in s1["files"][1:4]] == ["200100-20261001-1432.jpg", "200101-20261001-1433.jpg", "200102-20261001-1434.jpg"],
            json.dumps([f["name"] for f in s1["files"][1:4]]))
    pg.click("#mrPart1 button")
    A.pump_until(pg, lambda: len(shares(pg)) == 2, timeout=5)
    A.pump_until(pg, lambda: all(e["status"] == "exported" for e in all_entries(pg)), timeout=5)
    s2 = shares(pg)[1]
    A.check("browser parts: part 2 is a second share, from its own tap, with the rest; then every read is exported",
            [f["name"] for f in s2["files"]] == ["AMR-manual-reads-20261001-1443-part2of2.csv", "200109-20261001-1441.jpg", "200110-20261001-1442.jpg"]
            and all(e["status"] == "exported" for e in all_entries(pg)), json.dumps([f["name"] for f in s2["files"]]))
    A.check("browser parts: All done shows", "All done" in pg.evaluate("() => $('mrExportBody').textContent"))
    ctx.close()


@A.case
def t_export_outcomes(br):
    ctx, pg = A.open_app(br, start=False, init=SHARE_MOCK)
    seed(pg, [dict(id="o1", savedAt=A.T1, meter="M1", ref="200201", read="1", mult="1", photo=[320, 240])])
    open_export(pg)
    pg.evaluate("() => { window.__shareMode = 'abort'; }")
    pg.click("#mrPart0 button")
    A.pump_until(pg, lambda: len(shares(pg)) == 1, timeout=5)
    pg.wait_for_timeout(300)
    r = [entry(pg, "o1")["status"], pg.evaluate("() => [...document.querySelectorAll('#mrPart0 button')].map(b => [b.textContent, b.disabled])")]
    A.check("browser: cancel in the share menu (AbortError): the read stays new and Share is ready again", r == ["new", [["Share", False]]], json.dumps(r))
    pg.evaluate("() => { window.__shareMode = 'fail'; }")
    pg.click("#mrPart0 button")
    A.pump_until(pg, lambda: len(shares(pg)) == 2, timeout=5)
    pg.wait_for_timeout(300)
    r = [entry(pg, "o1")["status"], pg.evaluate("() => [...document.querySelectorAll('#mrPart0 button')].map(b => b.textContent)"), A.dom(pg, "#mrPartState0")]
    A.check("browser: a refused share (NotAllowedError): still new; Share again and Save to Downloads are offered",
            r[0] == "new" and r[1] == ["Share again", "Save to Downloads"] and "NotAllowedError" in (r[2] or ""), json.dumps(r))
    dls = []
    pg.on("download", lambda d: dls.append(d))
    pg.click("#mrPart0 button:has-text('Save to Downloads')")
    A.pump_until(pg, lambda: len(dls) == 2, timeout=8)
    A.pump_until(pg, lambda: entry(pg, "o1")["status"] == "exported", timeout=5)
    A.check("browser: Save to Downloads saves the CSV and the photo, and the read is marked exported",
            sorted(d.suggested_filename for d in dls) == ["200201-20261001-1432.jpg", "AMR-manual-reads-20261001-1432.csv"]
            and entry(pg, "o1")["status"] == "exported", json.dumps([d.suggested_filename for d in dls]))
    pg.evaluate("() => mrSetStatus(['o1'], 'new').then(() => { mrCloseExport(); window.__shareMode = 'hang'; MR_CFG.pendingShareMs = 500; })")
    pg.evaluate("() => mrOpenExport()")
    pg.wait_for_selector("#mrExport:not([hidden]) #mrPart0 button", timeout=10000)
    pg.click("#mrPart0 button")
    A.pump_until(pg, lambda: len(shares(pg)) == 3, timeout=5)
    pg.evaluate("() => document.dispatchEvent(new Event('visibilitychange'))")    # the reader comes back to the page
    A.pump_until(pg, lambda: "Mark exported" in pg.evaluate("() => $('mrPart0').textContent"), timeout=5)
    st0 = entry(pg, "o1")["status"]
    pg.click("#mrPart0 button:has-text('Mark exported')")
    A.pump_until(pg, lambda: entry(pg, "o1")["status"] == "exported", timeout=5)
    A.check("browser: a share that never finishes: the read stays new until the reader taps Mark exported",
            st0 == "new" and entry(pg, "o1")["status"] == "exported", st0)
    ctx.close()
    ctx, pg = A.open_app(br, start=False, init=SHARE_MOCK)
    seed(pg, [dict(id="l1", savedAt=A.T1, meter="M1", ref="200202", read="1", mult="1")])
    open_export(pg)
    pg.evaluate("() => { window.__shareMode = 'later'; }")
    pg.click("#mrPart0 button")
    A.pump_until(pg, lambda: pg.evaluate("() => typeof window.__resolveShare === 'function'"), timeout=5)
    pg.click("#mrExportClose")
    pg.evaluate("() => window.__resolveShare()")
    A.check("browser: a share that resolves after the export sheet closed still marks the read exported",
            A.pump_until(pg, lambda: entry(pg, "l1")["status"] == "exported", timeout=5))
    ctx.close()


@A.case
def t_export_no_share(br):
    ctx, pg = A.open_app(br, start=False)
    if pg.evaluate("() => typeof navigator.share === 'function'"):
        ctx.close()
        ctx, pg = A.open_app(br, start=False, init="delete Navigator.prototype.share; delete Navigator.prototype.canShare;")
    seed(pg, [dict(id="d1", savedAt=A.T1, meter="M1", ref="200301", read="0012", mult="1", photo=[320, 240])])
    open_export(pg)
    r = pg.evaluate("() => [$('mrExportBody').textContent, [...document.querySelectorAll('#mrPart0 button')].map(b => b.textContent)]")
    A.check("browser, no share menu: the sheet says so and offers Save to Downloads", "cannot share files" in r[0] and r[1] == ["Save to Downloads"], json.dumps(r))
    dls = []
    pg.on("download", lambda d: dls.append(d))
    pg.click("#mrPart0 button")
    A.pump_until(pg, lambda: len(dls) == 2, timeout=8)
    csv = next((d for d in dls if d.suggested_filename.endswith(".csv")), None)
    raw = open(csv.path(), "rb").read() if csv else b""
    A.check("browser, no share menu: both files download; the CSV is the same file (BOM, header, leading zeros)",
            len(dls) == 2 and raw.startswith(b"\xef\xbb\xbfDate,Time,") and b",0012,1," in raw, repr(raw[:60]))
    A.pump_until(pg, lambda: entry(pg, "d1")["status"] == "exported", timeout=5)
    A.check("browser, no share menu: the read is marked exported; a toast says to tap Allow if the browser asks",
            entry(pg, "d1")["status"] == "exported" and "tap Allow" in (A.dom(pg, "#toast") or ""), A.dom(pg, "#toast"))
    ctx.close()


@A.case
def t_export_offline(br):
    ctx, pg = A.open_app(br, start=False, init=SHARE_MOCK)
    A.wait_for(pg, lambda: pg.evaluate("() => !!(navigator.serviceWorker && navigator.serviceWorker.controller)"), timeout=20)
    A.wait_for(pg, lambda: "Offline ready." in A.text(pg, "#startBody"), timeout=20)
    ctx.set_offline(True)
    pg.reload()
    pg.wait_for_selector("#startBtns button", timeout=20000)
    pg.click("#startBtns button")
    pg.wait_for_timeout(600)
    open_form(pg)
    pg.check("#mrMeters input[value='__other']")
    pg.fill("#mrOther", "OFF1")
    pg.fill("#mrRead", "0001")
    pg.fill("#mrMult", "1")
    save_form(pg)
    pg.click("#fList")
    pg.click("#bManual")
    pg.wait_for_selector("#mrList:not([hidden])", timeout=5000)
    pg.wait_for_function("() => /^Export \\d+ new$/.test($('mrExportBtn').textContent)", timeout=5000)
    pg.click("#mrExportBtn")
    pg.wait_for_selector("#mrExport:not([hidden]) #mrPart0 button", timeout=10000)
    pg.click("#mrPart0 button")
    A.pump_until(pg, lambda: len(shares(pg)) == 1, timeout=5)
    ok = A.pump_until(pg, lambda: all_entries(pg)[0]["status"] == "exported", timeout=5)
    A.check("browser offline (no network at all): a read is saved and exported",
            ok and shares(pg)[0]["files"][0]["name"].startswith("AMR-manual-reads-"), json.dumps(shares(pg)[0]["files"][0]["name"]))
    ctx.set_offline(False)
    ctx.close()


@A.case
def t_help_layers(br):
    for mode, want in (("app", "Open in Gmail"), ("browser", "Pick Gmail and type the addresses")):
        ctx, pg = A.open_app(br, mode=mode)
        pg.click("#fList")
        help_txt = pg.evaluate("() => document.querySelector('#pBody .help').textContent")
        A.check(mode + " help: the stop list explains Manual read and how to email the reads", "Manual read" in help_txt and want in help_txt, help_txt[-300:])
        z = pg.evaluate("() => ['toast', 'mrExport', 'mrForm', 'start'].map(id => +getComputedStyle($(id)).zIndex)")
        A.check(mode + ": the toast shows above the manual reads screens and the start screen", z[0] > max(z[1:]), json.dumps(z))
        ctx.close()


@A.case
def t_phone_list_export(br):
    ctx, pg = A.open_app(br, viewport=(412, 915), start=False, is_mobile=True, has_touch=True, device_scale_factor=2.6)
    seed(pg, [dict(id="ph%d" % k, savedAt=A.T1 + k * 60000, meter="M%d" % k, ref=str(200400 + k), read="1", mult="1", photo=[320, 240]) for k in range(3)])
    pg.click("#mrStartList")
    pg.wait_for_selector("#mrList:not([hidden])", timeout=5000)
    a = pg.evaluate("() => [document.documentElement.scrollWidth > innerWidth, Math.round($('mrList').getBoundingClientRect().width)]")
    pg.wait_for_function("() => /^Export \\d+ new$/.test($('mrExportBtn').textContent)", timeout=5000)
    pg.click("#mrExportBtn")
    pg.wait_for_selector("#mrExport:not([hidden]) #mrPart0", timeout=10000)
    b = pg.evaluate("() => [document.documentElement.scrollWidth > innerWidth, Math.round(document.querySelector('#mrExport .mr-sheet').getBoundingClientRect().right)]")
    A.check("phone: the list and the export sheet fit the width (no side scroll)", a == [False, 412] and b[0] is False and b[1] <= 412, json.dumps([a, b]))
    ctx.close()


# ---------- meter pins on the map, the map boxes, and Manual read from the map (Task 21, owner features of 10/02/2026) ----------
def hav_m(a, b):
    """Meters between two [lat, lon] points (the page's hav(), the same earth radius)."""
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = p2 - p1, math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371008.8 * math.asin(math.sqrt(h))


def pin_groups(st):
    """The pins of one stop by the rule the owner approved: a meter joins the first pin within 3 m of that pin's first meter."""
    gs = []
    for m in st["meters"]:
        g = next((g for g in gs if hav_m([g[0]["lat"], g[0]["lon"]], [m["lat"], m["lon"]]) <= 3), None)
        if g:
            g.append(m)
        else:
            gs.append([m])
    return gs


def map_at(pg, ll, z=18):
    """Close any box and put ll in the middle of the map at zoom z (no animation)."""
    pg.evaluate("([ll, z]) => { map.closePopup(); map.setView(ll, z, {animate: false}); }", [ll, z])
    pg.wait_for_timeout(300)


def meter(o, ref):
    return next(m for m in A.STOPS[o]["meters"] if m["ref"] == ref)


@A.case
def t_map_pins(br):
    """A pin for each meter at zoom 17 or closer (none at 16); meters at one spot share one pin with a count; an ATTENTION
    pin is gold with !; a pin on its stop pin sits just beside it; every other pin sits on its meter."""
    ctx, pg = A.open_app(br)
    want = sum(len(pin_groups(st)) for st in A.ROUTE["stops"])
    st2 = A.STOPS[2]
    map_at(pg, [st2["lat"], st2["lon"]], 16)
    n16 = pg.evaluate("() => document.querySelectorAll('.mpw').length")
    map_at(pg, [st2["lat"], st2["lon"]], 17)
    n17 = pg.evaluate("() => document.querySelectorAll('.mpw').length")
    A.check("map: no meter pins at zoom 16; at zoom 17 one pin for each spot (%d pins for %d meters)" % (want, sum(len(s["meters"]) for s in A.ROUTE["stops"])),
            n16 == 0 and n17 == want, json.dumps([n16, n17, want]))
    map_at(pg, [st2["lat"], st2["lon"]], 18)
    on = next(g[0] for g in pin_groups(st2) if hav_m([g[0]["lat"], g[0]["lon"]], [st2["lat"], st2["lon"]]) <= 3)
    off = st2["meters"][0]
    r = pg.evaluate("""([on, off, ll]) => { const c = e => { const b = e.getBoundingClientRect(); return [b.left + b.width / 2, b.top + b.height / 2]; };
        const s = c(stopMarkers[2].getElement().querySelector('.sm')), p = c(document.querySelector(".mpw[data-ref='" + on + "'] .mp"));
        const q = c(document.querySelector(".mpw[data-ref='" + off + "'] .mp")), mp = $('map').getBoundingClientRect(), pt = map.latLngToContainerPoint(ll);
        return {side: [Math.round(p[0] - s[0]), Math.round(p[1] - s[1])], own: Math.round(Math.hypot(q[0] - mp.left - pt.x, q[1] - mp.top - pt.y))}; }""",
                    [on["ref"], off["ref"], [off["lat"], off["lon"]]])
    A.check("map: the pin of a meter at its stop pin (stop 2, ref %s) sits just beside the stop pin, up and to the right" % on["ref"],
            15 <= r["side"][0] <= 30 and -25 <= r["side"][1] <= -8, json.dumps(r))
    A.check("map: a pin away from its stop pin sits on its meter", r["own"] <= 1, json.dumps(r))
    ctx.close()


@A.case
def t_map_meter_box(br):
    for mode in MODES:
        ctx, pg = A.open_app(br, mode=mode)
        m = meter(2, "200001")
        where = m["where"].split(" · ")
        map_at(pg, [m["lat"], m["lon"]])
        f0 = pg.evaluate("() => [S.follow, $('fFollow').className]")
        pg.click(".mpw[data-ref='200001']")
        pg.wait_for_selector(".mp-pop .pp-head", timeout=5000)
        r = pg.evaluate("""() => { const p = document.querySelector('.mp-pop');
            return {id: p.querySelector('.pp-head b').textContent, sub: p.querySelector('.pp-head small').textContent,
                    kv: [...p.querySelectorAll('.pp-kv dd')].map(d => d.textContent),
                    btn: [...p.querySelectorAll('.pp-foot button')].map(b => b.textContent), follow: [S.follow, $('fFollow').className]}; }""")
        A.check(mode + " meter box: tapping a meter pin shows the meter ID, its stop, route ref, building number, site and spot, and Manual read",
                r["id"] == m["meter"] and r["sub"] == "Stop 2" and r["kv"] == [m["ref"], m["bldg"], where[0], where[1]] and r["btn"] == ["Manual read"],
                json.dumps(r))
        A.check(mode + " map box: opening it turns map follow off (as a drag does)",
                f0 == [True, "fab on"] and r["follow"] == [False, "fab off"], json.dumps([f0, r["follow"]]))
        pg.click(".mp-pop .pp-foot button")
        pg.wait_for_selector("#mrForm:not([hidden])", timeout=5000)
        A.pump_until(pg, lambda: pg.evaluate("() => !document.querySelector('.mp-pop')"), timeout=3)   # the box fades out (0.2 s)
        f = pg.evaluate("""() => [$('mrStop').value, (document.querySelector('#mrMeters input:checked') || {}).value, $('mrRead').value,
            $('mrMult').value, !!document.querySelector('.mp-pop')]""")
        A.check(mode + " Manual read in the meter box: the form opens on stop 2 with that meter chosen; face read and multiplier empty; the box closes",
                f == ["2", "200001", "", "", False], json.dumps(f))
        pg.fill("#mrRead", "1209334")
        pg.fill("#mrMult", "1")
        save_form(pg)
        e = all_entries(pg)[-1]
        A.check(mode + " a read picked on the map saves with that stop, meter, route ref, building number and site",
                [e["stop"], e["meter"], e["ref"], e["bldg"], e["site"], e["read"]] == [2, m["meter"], m["ref"], m["bldg"], where[0], "1209334"],
                json.dumps(e))
        ctx.close()


@A.case
def t_map_stop_box(br):
    ctx, pg = A.open_app(br)
    st = A.STOPS[2]
    map_at(pg, [st["lat"], st["lon"]])
    pg.click(".leaflet-marker-icon[title^='Stop 2:']")
    pg.wait_for_selector(".mp-pop .pp-list", timeout=5000)
    r = pg.evaluate("""() => { const p = document.querySelector('.mp-pop');
        return {title: p.querySelector('.pp-head b').textContent, sub: p.querySelector('.pp-head small').textContent,
                rows: [...p.querySelectorAll('.pp-m')].map(r => [r.querySelector('b').textContent, r.querySelector('button').textContent]),
                foot: [...p.querySelectorAll('.pp-foot button')].map(b => b.textContent), panel: $('panel').classList.contains('show'),
                follow: S.follow}; }""")
    A.check("stop box: tapping a stop pin opens its box (not the stop list): the stop, its site, every meter with Manual read, Show in stop list",
            r["title"] == "Stop 2: %d meters" % len(st["meters"]) and r["sub"] == st["site"]
            and r["rows"] == [[m["meter"], "Manual read"] for m in st["meters"]] and r["foot"] == ["Show in stop list"]
            and r["panel"] is False and r["follow"] is False, json.dumps(r))
    last = st["meters"][-1]
    pg.click(".mp-pop .pp-m[data-ref='%s'] button" % last["ref"])
    pg.wait_for_selector("#mrForm:not([hidden])", timeout=5000)
    f = pg.evaluate("() => [$('mrStop').value, (document.querySelector('#mrMeters input:checked') || {}).value]")
    A.check("stop box: Manual read on a row opens the form with stop 2 and that meter chosen", f == ["2", last["ref"]], json.dumps(f))
    pg.click("#mrCancel")
    A.check("cancel: a form opened from the map with nothing typed closes on one tap (the chosen meter is not typing)",
            pg.evaluate("() => $('mrForm').hidden"))
    open_form(pg)                                             # from the card: no meter chosen yet
    pg.check("#mrMeters input[value='%s']" % pg.evaluate("() => document.querySelector('#mrMeters input').value"))
    pg.click("#mrCancel")
    A.check("cancel: a form where the reader picked a meter still needs a second tap", pg.evaluate("() => !$('mrForm').hidden"))
    pg.click("#mrCancel")
    map_at(pg, [st["lat"], st["lon"]])
    pg.click(".leaflet-marker-icon[title^='Stop 2:']")
    pg.wait_for_selector(".mp-pop .pp-foot button", timeout=5000)
    pg.click(".mp-pop .pp-foot button")
    A.pump_until(pg, lambda: pg.evaluate("() => $('panel').classList.contains('show') && !document.querySelector('.mp-pop')"), timeout=3)
    A.check("stop box: Show in stop list opens the stop list with stop 2 and closes the box",
            pg.evaluate("() => $('panel').classList.contains('show') && !!$('row2') && !document.querySelector('.mp-pop')"))
    ctx.close()


@A.case
def t_map_groups(br):
    ctx, pg = A.open_app(br)
    st = A.STOPS[22]
    g = st["meters"]                                          # the four meters of stop 22 share one spot
    map_at(pg, [g[0]["lat"], g[0]["lon"]])
    pins = pg.evaluate("""() => [...document.querySelectorAll(".mpw[data-stop='22']")].map(e => [e.dataset.n,
        (e.querySelector('.mpn') || {}).textContent || '', e.querySelector('.mp').classList.contains('attn'), e.parentNode.title])""")
    A.check("map: the four meters of stop 22 share one pin with the count 4; it is gold (two of them are ATTENTION meters)",
            pins == [["4", "4", True, "4 meters at this spot"]], json.dumps(pins))
    pg.click(".mpw[data-stop='22']")
    pg.wait_for_selector(".mp-pop .pp-list", timeout=5000)
    r = pg.evaluate("""() => { const p = document.querySelector('.mp-pop');
        return {title: p.querySelector('.pp-head b').textContent, sub: p.querySelector('.pp-head small').textContent,
                rows: [...p.querySelectorAll('.pp-m')].map(r => [r.dataset.ref, r.classList.contains('attn'), !!r.querySelector('.badge'),
                       r.querySelectorAll('button').length]), foot: p.querySelectorAll('.pp-foot').length}; }""")
    A.check("group box: 4 meters at this spot, the stop and its site, each meter with Manual read, ATTENTION meters marked",
            r["title"] == "4 meters at this spot" and r["sub"] == "Stop 22: " + st["site"]
            and r["rows"] == [[m["ref"], bool(m["attn"]), bool(m["attn"]), 1] for m in g] and r["foot"] == 0, json.dumps(r))
    pg.click(".mp-pop .pp-m[data-ref='%s'] button" % g[1]["ref"])
    pg.wait_for_selector("#mrForm:not([hidden])", timeout=5000)
    f = pg.evaluate("() => [$('mrStop').value, (document.querySelector('#mrMeters input:checked') || {}).value]")
    A.check("group box: Manual read opens the form with stop 22 and that meter chosen", f == ["22", g[1]["ref"]], json.dumps(f))
    pg.click("#mrCancel")
    m7 = meter(7, "200047")
    map_at(pg, [m7["lat"], m7["lon"]], 19)
    a = pg.evaluate("""() => { const e = document.querySelector(".mpw[data-ref='200047'] .mp"), n = document.querySelector(".mpw[data-ref='200009'] .mp");
        return [e.classList.contains('attn'), getComputedStyle(e).backgroundColor, n.classList.contains('attn'), getComputedStyle(n).backgroundColor]; }""")
    A.check("map: an ATTENTION meter's pin is gold (#c69214) with !; another meter's pin is white",
            a == [True, "rgb(198, 146, 20)", False, "rgb(255, 255, 255)"], json.dumps(a))
    pg.click(".mpw[data-ref='200047']")
    pg.wait_for_selector(".mp-pop .pp-head", timeout=5000)
    b = pg.evaluate("() => [document.querySelector('.mp-pop .pp-head b').textContent, (document.querySelector('.mp-pop .pp-note') || {}).textContent || '']")
    A.check("meter box: an ATTENTION meter shows the ATTENTION badge and its note", b == [m7["meter"] + "ATTENTION", m7["note"]], json.dumps(b))
    ctx.close()


@A.case
def t_map_reads_off(br):
    """An app older than 1.1 (manual reads off): the boxes still show the meters, with no Manual read button."""
    ctx, pg = A.open_app(br, mode="app", native_cfg={"bridge": "1"})
    m = A.STOPS[2]["meters"][0]
    map_at(pg, [m["lat"], m["lon"]])
    pg.click(".mpw[data-ref='%s']" % m["ref"])
    pg.wait_for_selector(".mp-pop .pp-head", timeout=5000)
    r = [A.dom(pg, ".mp-pop .pp-head b"), pg.evaluate("() => document.querySelectorAll('.mp-pop button').length")]
    st = A.STOPS[2]
    map_at(pg, [st["lat"], st["lon"]])
    pg.click(".leaflet-marker-icon[title^='Stop 2:']")
    pg.wait_for_selector(".mp-pop .pp-list", timeout=5000)
    s = pg.evaluate("() => [document.querySelectorAll('.mp-pop .pp-m').length, document.querySelectorAll('.mp-pop .pp-m button').length, "
                    "[...document.querySelectorAll('.mp-pop .pp-foot button')].map(b => b.textContent)]")
    A.check("manual reads off (an app older than 1.1): the meter box and the stop box show the meters with no Manual read button",
            r == [m["meter"], 0] and s == [len(st["meters"]), 0, ["Show in stop list"]], json.dumps([r, s]))
    ctx.close()


def fit_from_stop_box(pg, st, m):
    """Open the form for meter m of stop st the way the reader does on the map: tap the stop pin, then Manual read on the
    meter's row (the stop box lists every meter, also the ones that share a pin). Returns where the chosen row sits against
    the sticky Cancel and Save bar."""
    map_at(pg, [st["lat"], st["lon"]])
    pg.click(".leaflet-marker-icon[title^='Stop %d:']" % st["o"])
    pg.wait_for_selector(".mp-pop .pp-list", timeout=5000)
    pg.click(".mp-pop .pp-m[data-ref='%s'] button" % m["ref"])
    pg.wait_for_selector("#mrForm:not([hidden])", timeout=5000)
    pg.wait_for_timeout(300)
    return pg.evaluate("""() => { const fm = $('mrForm'), on = document.querySelector('#mrMeters .mr-m.on');
        const ob = on ? on.getBoundingClientRect() : null, ft = fm.querySelector('.mr-foot').getBoundingClientRect(), fr = fm.getBoundingClientRect();
        return {rows: $('mrMeters').querySelectorAll('.mr-m').length, chosen: on ? on.querySelector('input').value : null,
                row: ob ? [Math.round(ob.top), Math.round(ob.bottom)] : null, foot: Math.round(ft.top), scroll: Math.round(fm.scrollTop),
                seen: !!ob && ob.top >= fr.top && ob.bottom <= ft.top + 1}; }""")


def box_vs_side(pg):
    """Where the open map box sits against the side buttons (px), and whether the right edge of its first button takes a tap."""
    return pg.evaluate("""() => { const w = document.querySelector('.mp-pop .leaflet-popup-content-wrapper').getBoundingClientRect(),
        s = $('side').getBoundingClientRect(), bs = [...document.querySelectorAll('.mp-pop button')], b0 = bs[0].getBoundingClientRect(),
        hit = document.elementFromPoint(b0.right - 3, b0.top + b0.height / 2);
        return {box: [Math.round(w.left), Math.round(w.right)], width: Math.round(w.width), side: Math.round(s.left),
                btn: Math.round(Math.max(...bs.map(b => b.getBoundingClientRect().right))), tap: !!hit && bs[0].contains(hit)}; }""")


@A.case
def t_map_form_fit(br):
    """Shot 04 of the UI samples (10/02/2026): on the field tablet held sideways (1280 x 800) the meter list cut its last
    row and hid Other meter inside a 40% box. Now the list has no height cap: every row shows in full, the form scrolls,
    and the meter chosen on the map is in view above Cancel and Save. Review finding (10/02/2026): on the long stops
    (stop 18 has 23 meters, stop 29 has 17) scrollIntoView put the chosen row under the sticky bar, on both tablet
    orientations; the form now keeps the bar's height free below the row."""
    for mode in MODES:
        ctx, pg = A.open_app(br, mode=mode, viewport=(1280, 800))
        st = A.STOPS[2]
        last = st["meters"][-1]
        map_at(pg, [last["lat"], last["lon"]])
        pg.click(".mpw[data-ref='%s']" % last["ref"])
        pg.wait_for_selector(".mp-pop .pp-foot button", timeout=5000)
        pg.click(".mp-pop .pp-foot button")
        pg.wait_for_selector("#mrForm:not([hidden])", timeout=5000)
        pg.wait_for_timeout(300)
        r = pg.evaluate("""() => { const box = $('mrMeters'), on = document.querySelector('#mrMeters .mr-m.on');
            const ob = on ? on.getBoundingClientRect() : null, ft = document.querySelector('#mrForm .mr-foot').getBoundingClientRect();
            return {cap: getComputedStyle(box).maxHeight, inner: box.scrollHeight > box.clientHeight + 1, rows: box.querySelectorAll('.mr-m').length,
                    chosen: on ? on.querySelector('input').value : null, seen: !!ob && ob.top >= 0 && ob.bottom <= ft.top + 1}; }""")
        A.check(mode + " form from the map, tablet sideways (1280 x 800): no height cap and no inner scroll (no meter row cut, shot 04); "
                "the chosen meter is in view above Cancel and Save",
                r == {"cap": "none", "inner": False, "rows": len(st["meters"]) + 1, "chosen": last["ref"], "seen": True}, json.dumps(r))
        ctx.close()
    A.check("route data: stop 18 has 23 meters and stop 29 has 17 (the long stops the fit checks below need)",
            [len(A.STOPS[18]["meters"]), len(A.STOPS[29]["meters"])] == [23, 17])
    for mode in MODES:
        for label, vp in (("sideways (1280 x 800)", (1280, 800)), ("upright (800 x 1280)", (800, 1280))):
            for o, i in ((18, -1), (18, 15), (29, -1)):
                ctx, pg = A.open_app(br, mode=mode, viewport=vp)     # a fresh page for each: the form keeps its scroll position between opens
                st = A.STOPS[o]
                m = st["meters"][i]
                r = fit_from_stop_box(pg, st, m)
                A.check("%s form from the map, tablet %s: meter %d of %d at stop %d is in full view above Cancel and Save"
                        % (mode, label, i % len(st["meters"]) + 1, len(st["meters"]), o),
                        r["chosen"] == m["ref"] and r["rows"] == len(st["meters"]) + 1 and r["seen"] is True, json.dumps(r))
                ctx.close()


@A.case
def t_map_box_phone(br):
    """Review finding (10/02/2026): on a 412 px phone the stop box of stop 18 (381 px wide) covered the side buttons. A box is
    now as wide as the room between the pads of the map pan (a minimum of 300 px and a maximum of 380 px on a wide screen),
    so it stays left of the side buttons on every phone and keeps its full width on the tablet."""
    st, m = A.STOPS[18], meter(2, "200001")
    for label, vp in (("412 x 915", (412, 915)), ("360 x 780", (360, 780))):
        ctx, pg = A.open_app(br, viewport=vp, is_mobile=True, has_touch=True, device_scale_factor=2.6)
        map_at(pg, [st["lat"], st["lon"]])
        pg.click(".leaflet-marker-icon[title^='Stop 18:']")
        pg.wait_for_selector(".mp-pop .pp-list", timeout=5000)
        pg.wait_for_timeout(700)                                  # the pan that brings the box into the pads settles
        r = box_vs_side(pg)
        A.check("phone %s: the stop box (stop 18, 23 meters) stays inside the screen and left of the side buttons; "
                "the right edge of a Manual read button takes a tap" % label,
                r["box"][0] >= 0 and r["box"][1] <= r["side"] and r["btn"] <= r["side"] and r["tap"] is True, json.dumps(r))
        map_at(pg, [m["lat"], m["lon"]])
        pg.click(".mpw[data-ref='200001']")
        pg.wait_for_selector(".mp-pop .pp-head", timeout=5000)
        pg.wait_for_timeout(700)
        r = box_vs_side(pg)
        A.check("phone %s: the meter box stays inside the screen and left of the side buttons; the right edge of Manual read takes a tap" % label,
                r["box"][0] >= 0 and r["box"][1] <= r["side"] and r["btn"] <= r["side"] and r["tap"] is True, json.dumps(r))
        ctx.close()
    ctx, pg = A.open_app(br, viewport=(800, 1280))
    map_at(pg, [st["lat"], st["lon"]])
    pg.click(".leaflet-marker-icon[title^='Stop 18:']")
    pg.wait_for_selector(".mp-pop .pp-list", timeout=5000)
    pg.wait_for_timeout(700)
    r = box_vs_side(pg)
    A.check("tablet upright (800 x 1280): the stop box keeps its full width (381 px) and is left of the side buttons",
            r["width"] == 381 and r["box"][1] <= r["side"], json.dumps(r))
    ctx.close()


with sync_playwright() as p:
    br = p.chromium.launch()
    A.run_cases(br)
    br.close()
A.finish()
