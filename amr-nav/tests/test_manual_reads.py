"""Manual reads checks for the AMR Route Guide (manual-reads.js): in a browser (IndexedDB, the share menu) and in the
Android app (fake_native.js stands in for the app's store, camera and Gmail export).
Run (repository root served on 127.0.0.1, port from AMR_TEST_PORT):  py amr-nav\\tests\\test_manual_reads.py
One case only: set AMR_TEST_CASE to its name first.
Never put an email address in this file: the repository is public."""
import io
import json
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


with sync_playwright() as p:
    br = p.chromium.launch()
    A.run_cases(br)
    br.close()
A.finish()
