/* AMR Route Guide: manual reads.
   A reader saves a meter's face read, multiplier, notes and one photo, with the date, time and GPS, with no signal.
   The reads stay on this device and never go to the web site: in the AMR Route Guide app (window.AMRNative, bridge
   version 2 or later) in the app's own files; in a browser in IndexedDB. Export makes one CSV plus the photos per
   part: the app opens Gmail with the addresses filled in by the app itself; a browser shares the files (the reader
   picks Gmail and types the addresses) or saves them to Downloads. The reader taps Send in Gmail; nothing here sends.
   This file loads before the main script. Its functions use these names from the main script, at call time only:
   S, CFG, $, toast, armTap, armButton, disarm, hav, currentTargetStop, closePanel. Every name here starts with mr or MR. */
'use strict';
/* This file's version: always the same as APP_VERSION in index.html (bump both together; test_app_manifest.py checks).
   The page runs manual reads only when they match, so a page and an older or newer copy of this file never mix. */
const MR_JS_VERSION = '2026.10.01-9';
const MR_CFG = {
  db: 'amrNav-manualReads',     // IndexedDB name (browser); jswsu.github.io is shared with other pages, so the name says whose it is
  dbVersion: 1,                 // a schema change raises this by one and adds one step in mrDb(); an old step never changes
  nearStopM: 150,               // m: the form opens on the stop with a meter this close to a fresh GPS fix
  photoLongPx: 2000,            // px: long side of a saved photo
  photoQualities: [0.8, 0.7, 0.6, 0.5],
  photoTargetBytes: 600000,     // the first JPEG quality that gives this size or less is kept (about 0.5 MB)
  maxFilesPerShare: 10,         // browser share limit: 1 CSV and 9 photos (the app has no file limit)
  maxBytesPerPart: 18000000,    // bytes of files per email: under 20 MB, and under Gmail's 25 MB once encoded (about 1.37 times)
  csvReserveBytes: 262144,      // room kept in each part for its CSV
  notesMax: 500,
  draftDelayMs: 500,            // ms after the last keystroke, the open form is saved as a draft
  pendingShareMs: 3000,         // ms after the reader comes back, a browser share that has not finished offers Mark exported
  clearAfterMs: 7 * 86400000,   // Clear removes only reads exported this long ago (K8): "exported" is not "sent"
};
const MR_COLS = ['Date', 'Time', 'Meter ID', 'Route ref', 'Building number', 'Site name', 'Face read', 'Multiplier', 'Notes',
  'Photo file name', 'GPS latitude', 'GPS longitude', 'GPS accuracy (ft)', 'Stop number'];
const MR_NUM = /^(\d+(\.\d*)?|\.\d+)$/;   // digits, with one optional decimal point

/* ---------- pure helpers: dates, CSV, file names, parts, checks ---------- */
const mrPad = n => String(n).padStart(2, '0');
/* Local date and time of a time in ms: date MM/DD/YYYY, time HH:MM (24 h), stamp YYYYMMDD-HHMM (for file names). */
function mrStamp(ms) {
  const d = new Date(ms), Y = d.getFullYear(), M = mrPad(d.getMonth() + 1), D = mrPad(d.getDate());
  const h = mrPad(d.getHours()), m = mrPad(d.getMinutes());
  return {date: M + '/' + D + '/' + Y, time: h + ':' + m, stamp: '' + Y + M + D + '-' + h + m};
}
/* One CSV field (RFC 4180): quoted when it holds a comma, a quote, a line break, or a space at either end. */
function mrCsvField(v) {
  const s = v == null ? '' : String(v);
  return /[",\r\n]/.test(s) || /^\s|\s$/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
}
/* The building name from a route meter's "where" text: "CREAM ANNEX · M100" gives "CREAM ANNEX". */
function mrSiteName(where) { return String(where || '').split(' \u00b7 ')[0].trim(); }
function mrCsvRow(e, photoName) {
  return [e.date, e.time, e.meter, e.ref, e.bldg, e.site, e.read, e.mult, e.notes, photoName || '',
    e.lat == null ? '' : e.lat.toFixed(6), e.lon == null ? '' : e.lon.toFixed(6), e.accFt == null ? '' : String(e.accFt),
    e.stop == null ? '' : String(e.stop)];
}
/* The CSV text: a byte order mark (so Excel reads UTF-8), the header, one row per entry, CRLF line ends.
   names: Map of entry id to photo file name. */
function mrCsvText(entries, names) {
  const rows = [MR_COLS].concat(entries.map(e => mrCsvRow(e, names.get(e.id))));
  return '\uFEFF' + rows.map(r => r.map(mrCsvField).join(',')).join('\r\n') + '\r\n';
}
/* A typed meter ID as a file name part: letters, digits, _ and - only. It starts with a letter or a digit (the app's file
   name check needs that) and does not end with a dash. */
function mrSafeId(s) { return String(s || '').replace(/[^A-Za-z0-9_-]+/g, '-').replace(/^[-_]+|-+$/g, '') || 'meter'; }
/* Photo file names for the entries that have a photo: <route ref>-<YYYYMMDD-HHMM>.jpg (the typed ID for Other meter).
   A second photo with the same name in one export gets -2, then -3. Returns a Map of entry id to name. */
function mrPhotoNames(entries) {
  const out = new Map(), used = new Set();
  entries.forEach(e => {
    if (!(e.photoBytes > 0)) return;
    const base = (e.ref || mrSafeId(e.meter)) + '-' + e.stamp;
    let name = base + '.jpg';
    for (let k = 2; used.has(name.toLowerCase()); k++) name = base + '-' + k + '.jpg';
    used.add(name.toLowerCase());
    out.set(e.id, name);
  });
  return out;
}
/* CSV file name and email subject of part i (from 0) of n. The time is the latest entry's, never today's (the same rule
   as the AMR export). A file name holds digits, letters and hyphens only: no "/" and no ":". */
function mrPartNames(latestMs, i, n) {
  const t = mrStamp(latestMs), many = n > 1;
  return {csv: 'AMR-manual-reads-' + t.stamp + (many ? '-part' + (i + 1) + 'of' + n : '') + '.csv',
          subject: 'AMR manual reads ' + t.date + ' ' + t.time + (many ? ', part ' + (i + 1) + ' of ' + n : '')};
}
/* Split entries (in save order) into parts, one email each: at most maxFiles files with the CSV (Infinity in the app),
   and at most MR_CFG.maxBytesPerPart bytes. An entry with no photo adds no file. */
function mrSplit(entries, maxFiles) {
  const parts = [];
  let cur = [], files = 1, bytes = MR_CFG.csvReserveBytes;
  entries.forEach(e => {
    const f = e.photoBytes > 0 ? 1 : 0, b = e.photoBytes > 0 ? e.photoBytes : 0;
    if (cur.length && (files + f > maxFiles || bytes + b > MR_CFG.maxBytesPerPart)) {
      parts.push(cur); cur = []; files = 1; bytes = MR_CFG.csvReserveBytes;
    }
    cur.push(e); files += f; bytes += b;
  });
  if (cur.length) parts.push(cur);
  return parts;
}
/* Form checks. f: {meterRef, other, otherId, read, mult}. Returns {} when good, else field name to message. */
function mrCheck(f) {
  const err = {}, r = String(f.read || '').trim(), m = String(f.mult || '').trim();
  if (f.other ? !String(f.otherId || '').trim() : !f.meterRef) err.meter = f.other ? 'Type the meter ID.' : 'Pick a meter, or pick Other meter.';
  if (!r) err.read = 'Type the face read.';
  else if (!MR_NUM.test(r)) err.read = 'Use digits only, as the dial shows. A decimal point is OK.';
  if (!m) err.mult = 'Type the multiplier.';
  else if (!MR_NUM.test(m) || !(Number(m) > 0)) err.mult = 'Use a number above 0, like 1, 10 or 100.';
  return err;
}
/* A complete entry record, schema v1. o: savedAt (ms), gps ({lat, lon, accFt} or null), stop, other, meter, ref, bldg,
   site, read, mult, notes, photoBytes, and id (optional). Each entry keeps its own copy of the meter facts, so a later
   route change cannot alter a saved read. The id uses letters, digits and "-" only (the app's store takes no other). */
function mrMakeEntry(o) {
  const t = mrStamp(o.savedAt), g = o.gps || null;
  return {id: o.id || 'mr-' + o.savedAt.toString(36) + '-' + Math.random().toString(36).slice(2, 7), v: 1, status: 'new',
    savedAt: o.savedAt, editedAt: null, exportedAt: null, exportName: null, date: t.date, time: t.time, stamp: t.stamp,
    stop: o.stop == null || o.stop === '' ? null : Number(o.stop), other: !!o.other, meter: String(o.meter || ''),
    ref: String(o.ref || ''), bldg: String(o.bldg || ''), site: String(o.site || ''), read: String(o.read || ''),
    mult: String(o.mult || ''), notes: String(o.notes || ''), photoBytes: o.photoBytes > 0 ? o.photoBytes : 0,
    lat: g ? g.lat : null, lon: g ? g.lon : null, accFt: g ? g.accFt : null,
    routeSig: (typeof S !== 'undefined' && S.routeSig) || ''};
}

/* ---------- storage: the app's own files (installed app) or IndexedDB (browser), on this device only ---------- */
const MR = {count: {new: 0, exported: 0}, storeOk: true, persisted: false, form: null, saving: false, draftT: null, gpsT: null,
  photoUrl: null, off: false, skew: false, draftPhotoSent: null, photoBusy: false};
/* The mode is fixed once, when this file loads. Inside the app (window.AMRNative is there) the reads always go to the
   app's store and the export always goes through the app: never to IndexedDB (WebView storage, spec 5) and never to the
   share menu (spec 7), even when one bridge call answers nothing for a moment. The calls exist from bridge version 2
   (app 1.1), but the first 1.1 build had the store calls only (no camera return, no Gmail export) with the same bridge
   version, so manual reads need every call in MR_CALLS. */
const MR_CALLS = ['storeAll', 'storePut', 'storeDelete', 'photoPut', 'photoGet', 'photoDelete', 'draftGet', 'draftPut',
  'draftDelete', 'takePendingPhoto', 'exportBegin', 'exportAddText', 'exportAddPhoto', 'exportOpenGmail'];
const MR_APP_MODE = (() => { try { return !!window.AMRNative; } catch (e) { return false; } })();
const MR_HAS_STORE = (() => {
  try { return MR_APP_MODE && MR_CALLS.every(k => typeof window.AMRNative[k] === 'function'); } catch (e) { return false; }
})();
/* The app's store, or null (a browser, or an app without every call). In the app the reads live in the app's own files:
   Android never clears them, app updates keep them, an uninstall deletes them. */
function mrBridge() { return MR_HAS_STORE ? window.AMRNative : null; }
/* One call to the app's store. An answer that starts with "error", or no store, throws. */
function mrN(name, ...args) {
  const n = mrBridge();
  if (!n || typeof n[name] !== 'function') throw new Error('the app store has no ' + name);
  const r = n[name](...args), s = r == null ? '' : String(r);
  if (s.startsWith('error')) throw new Error(s);
  return s;
}
/* A store write: any answer but "ok" throws, '' included (the bridge answers '' while the page does not count as the
   app's own), so the form says "Could not save" instead of losing the read. */
function mrOk(name, ...args) {
  const s = mrN(name, ...args);
  if (s !== 'ok') throw new Error('the app did not save (' + (s || 'no answer') + ')');
  return s;
}
/* A Blob as base64 text for the bridge, and back. */
function mrBlobB64(blob) {
  return new Promise((res, rej) => {
    const r = new FileReader();
    r.onload = () => res(String(r.result).split(',')[1] || '');
    r.onerror = () => rej(r.error);
    r.readAsDataURL(blob);
  });
}
function mrB64Blob(b64, type) {
  const bin = atob(b64), u = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
  return new Blob([u], {type: type || 'image/jpeg'});
}

/* The app's store. The draft's photo is kept as the photo with id "draft"; it is sent again only when it changed. */
const MR_APP = {
  all: async () => JSON.parse(mrN('storeAll')),
  photo: async id => { const b = mrN('photoGet', id); return b ? mrB64Blob(b, 'image/jpeg') : null; },
  /* Two writes with no rollback, so the order keeps every entry true: a new photo goes in before the entry that names
     it, and a removed photo goes only after the entry that no longer names it (a failed write leaves at most a spare
     photo file, never an entry that names a missing photo). */
  save: async (e, photo) => {
    if (photo) mrOk('photoPut', e.id, await mrBlobB64(photo));
    mrOk('storePut', e.id, JSON.stringify(e));
    if (photo === null) { try { mrOk('photoDelete', e.id); } catch (x) { /* a spare photo file; the entry names none */ } }
  },
  del: async id => { mrOk('storeDelete', id); },
  draftGet: async () => {
    const j = mrN('draftGet');
    if (!j) return undefined;
    const d = JSON.parse(j);
    if (d.form) {
      if (d.form.hasPhoto) { const b = mrN('photoGet', 'draft'); d.form.photo = b ? mrB64Blob(b, 'image/jpeg') : null; MR.draftPhotoSent = d.form.photo; }
      delete d.form.hasPhoto;
    }
    return d;
  },
  draftPut: async d => {
    const form = Object.assign({}, d.form || {}), photo = form.photo || null;
    delete form.photo;
    form.hasPhoto = !!photo;
    if (photo && photo !== MR.draftPhotoSent) { mrOk('photoPut', 'draft', await mrBlobB64(photo)); MR.draftPhotoSent = photo; }
    mrOk('draftPut', JSON.stringify(Object.assign({k: 'current', at: Date.now()}, d, {form})));
  },
  draftDel: async () => { mrOk('draftDelete'); mrOk('photoDelete', 'draft'); MR.draftPhotoSent = null; },
};

let mrDbP = null;
/* IndexedDB (browser). Open it once. One upgrade step per version: a later version adds a step and never changes an
   earlier one, so a device that skipped versions runs every missing step in order. */
function mrDb() {
  if (mrDbP) return mrDbP;
  mrDbP = new Promise((resolve, reject) => {
    let req;
    try { req = indexedDB.open(MR_CFG.db, MR_CFG.dbVersion); } catch (e) { reject(e); return; }
    req.onupgradeneeded = ev => {
      const db = req.result;
      if (ev.oldVersion < 1) {
        db.createObjectStore('entries', {keyPath: 'id'}).createIndex('status', 'status');
        db.createObjectStore('photos', {keyPath: 'id'});    // {id: entry id, blob: the JPEG}
        db.createObjectStore('drafts', {keyPath: 'k'});     // {k: 'current', form, at}: the open form, kept across a reload
      }
    };
    req.onsuccess = () => {
      const db = req.result;
      db.onversionchange = () => { db.close(); mrDbP = null; };   // a newer page version in another tab can upgrade
      resolve(db);
    };
    req.onerror = () => reject(req.error);
    req.onblocked = () => toast('Close the other Route Guide tabs to finish the update.');
  });
  mrDbP.catch(() => { mrDbP = null; });                 // try again at the next use
  return mrDbP;
}
/* Run work(stores) in one transaction. Resolves when it is complete, with work's return value (or, when that is a
   request, its result). */
function mrTx(names, mode, work) {
  return mrDb().then(db => new Promise((resolve, reject) => {
    let tx, out;
    try { tx = db.transaction(names, mode); } catch (e) { reject(e); return; }
    const st = {};
    names.forEach(n => { st[n] = tx.objectStore(n); });
    tx.oncomplete = () => resolve(out instanceof IDBRequest ? out.result : out);
    tx.onerror = () => reject(tx.error);
    tx.onabort = () => reject(tx.error || new DOMException('Transaction aborted', 'AbortError'));
    try { out = work(st); } catch (e) { try { tx.abort(); } catch (x) { /* already finished */ } reject(e); }
  }));
}
const MR_IDB = {
  all: () => mrTx(['entries'], 'readonly', st => st.entries.getAll()),
  photo: id => mrTx(['photos'], 'readonly', st => st.photos.get(id)).then(r => (r ? r.blob : null)),
  save: (e, photo) => mrTx(['entries', 'photos'], 'readwrite', st => {
    st.entries.put(e);
    if (photo) st.photos.put({id: e.id, blob: photo});
    else if (photo === null) st.photos.delete(e.id);
  }),
  del: id => mrTx(['entries', 'photos'], 'readwrite', st => { st.entries.delete(id); st.photos.delete(id); }),
  draftGet: () => mrTx(['drafts'], 'readonly', st => st.drafts.get('current')),
  draftPut: d => mrTx(['drafts'], 'readwrite', st => { st.drafts.put(Object.assign({k: 'current', at: Date.now()}, d)); }),
  draftDel: () => mrTx(['drafts'], 'readwrite', st => { st.drafts.delete('current'); }),
};

const mrStore = () => (MR_APP_MODE ? MR_APP : MR_IDB);      // in the app never IndexedDB, whatever one call answers
const mrAll = () => Promise.resolve().then(() => mrStore().all()).then(a => a.sort((x, y) => x.savedAt - y.savedAt));
const mrGet = id => mrAll().then(a => a.find(e => e.id === id));
const mrPhoto = id => Promise.resolve().then(() => mrStore().photo(id));
/* Save an entry. photo: a Blob to store, null to remove the stored photo, undefined to keep it. */
const mrSaveEntry = (e, photo) => Promise.resolve().then(() => mrStore().save(e, photo));
const mrDelete = id => Promise.resolve().then(() => mrStore().del(id));
const mrDraftGet = () => Promise.resolve().then(() => mrStore().draftGet());
const mrDraftPut = d => Promise.resolve().then(() => mrStore().draftPut(d));
const mrDraftDel = () => Promise.resolve().then(() => mrStore().draftDel());
/* Mark entries 'exported' (with the CSV name and the time) or back to 'new'. */
async function mrSetStatus(ids, status, csvName) {
  const now = Date.now(), want = new Set(ids);
  for (const e of await mrAll()) {
    if (!want.has(e.id)) continue;
    e.status = status;
    e.exportedAt = status === 'exported' ? now : null;
    e.exportName = status === 'exported' ? csvName : null;
    await mrSaveEntry(e, undefined);
  }
}
/* Delete the exported entries (and their photos) exported more than MR_CFG.clearAfterMs ago. In the app "exported"
   means only that Gmail's compose screen opened, not that the mail went out (K8). Resolves with the number deleted. */
async function mrClearExported() {
  let n = 0;
  const cut = Date.now() - MR_CFG.clearAfterMs;
  for (const e of await mrAll()) {
    if (e.status !== 'exported' || !(e.exportedAt > 0 && e.exportedAt < cut)) continue;
    await mrDelete(e.id);
    n++;
  }
  return n;
}
/* True when the reads are kept when storage runs low: always in the app (its own files); in a browser, when it grants
   persistent storage. ask: request it (the browser shows no prompt). */
async function mrPersist(ask) {
  if (MR_APP_MODE) return MR_HAS_STORE;
  try {
    if (!navigator.storage || !navigator.storage.persisted) return false;
    if (await navigator.storage.persisted()) return true;
    return !!(ask && navigator.storage.persist && await navigator.storage.persist());
  } catch (e) { return false; }
}
/* ---------- the Manual read form ---------- */
/* GPS for a new read: the newest fix while it is fresh (CFG.fixStaleMs), with its accuracy in ft; else null.
   A weak fix is kept: the accuracy column says how good it is. */
function mrGpsNow() {
  const f = S.fix;
  if (!f || S.blocked || Date.now() - S.fixAt > CFG.fixStaleMs) return null;
  return {lat: +f.lat.toFixed(6), lon: +f.lon.toFixed(6), accFt: Math.round((f.acc || 0) * 3.28084)};
}
/* The stop the drive reached last: the newest stop marked reached (a drive-by arrival, Reached or Done, Read from car) or
   passed (the car left it after it was reached). Skipped stops do not count: a stop can be skipped from far away. */
function mrLastReached() {
  let best = null, bt = -Infinity;
  [S.done, S.passed].forEach(m => Object.keys(m || {}).forEach(o => {
    const t = Number(m[o]);
    if (S.stopBy[o] && t > bt) { bt = t; best = S.stopBy[o]; }
  }));
  return best;
}
/* The stop the form opens on. Parked at the card's parking spot: the card's stop. Otherwise the candidates are the card's
   stop and the stop the drive reached last (drive-by stops move the card on when reached, so the reader can still stand at
   that stop): the candidate with the nearest meter within MR_CFG.nearStopM of a fresh fix wins (the card's stop on a tie).
   With no candidate that near: the stop with the nearest meter within MR_CFG.nearStopM; else the card's stop; else none. */
function mrDefaultStop() {
  if (!S.route) return null;
  const card = currentTargetStop() || null, g = mrGpsNow();
  if (!g || (card && S.waiting === 'park')) return card;
  const nearM = st => Math.min(...st.meters.concat([st]).filter(p => p.lat != null && p.lon != null)
    .map(p => hav([g.lat, g.lon], [p.lat, p.lon])));
  const nearest = sts => {
    let best = null, bd = Infinity;
    sts.forEach(st => { if (!st) return; const d = nearM(st); if (d < bd) { bd = d; best = st; } });
    return bd <= MR_CFG.nearStopM ? best : null;
  };
  return nearest([card, mrLastReached()]) || nearest(S.route.stops) || card;
}
/* The meters the form lists for a stop number; null lists the route's meters with no location on file. */
function mrStopMeters(stopO) {
  if (!S.route) return [];
  if (stopO == null) return S.route.unmapped || [];
  const st = S.stopBy[stopO];
  return st ? st.meters : [];
}
function mrBlankForm(stopO) {
  return {editId: null, stopO: stopO == null ? null : Number(stopO), meterRef: null, other: false, otherId: '', read: '', mult: '',
    notes: '', keep: null, photo: null, photoChanged: false, photoInfo: null, awaitingPhoto: false};
}
/* Open the form: {} for a new read, {editId} to change a new read, {draft} to bring back a form that was dropped. */
async function mrOpenForm(opts) {
  opts = opts || {};
  let f;
  try {
    if (opts.draft) f = Object.assign(mrBlankForm(null), opts.draft);
    else if (opts.editId) {
      const e = await mrGet(opts.editId);
      if (!e || e.status !== 'new') { toast('Only new reads can change.'); return; }
      const photo = e.photoBytes ? await mrPhoto(e.id) : null;
      f = Object.assign(mrBlankForm(e.stop), {editId: e.id, meterRef: e.other ? null : e.ref, other: e.other,
        otherId: e.other ? e.meter : '', read: e.read, mult: e.mult, notes: e.notes,
        keep: {meter: e.meter, ref: e.ref, bldg: e.bldg, site: e.site}, photo,
        photoChanged: !!e.photoBytes && !photo});   // its photo is gone from storage: Save clears the name (photoBytes 0)
    } else {
      const st = mrDefaultStop();
      f = mrBlankForm(st ? st.o : null);
    }
  } catch (x) { toast('The reads cannot be opened. Storage is blocked on this device.', 6000); return; }
  MR.form = f;
  mrPaintForm();
  $('mrForm').hidden = false;
  clearInterval(MR.gpsT);
  MR.gpsT = setInterval(mrGpsLine, 2000);
}
function mrPaintForm() {
  const f = MR.form, sel = $('mrStop');
  $('mrFormTitle').textContent = f.editId ? 'Edit read' : 'Manual read';
  sel.innerHTML = '';
  sel.add(new Option(S.route && S.route.unmapped && S.route.unmapped.length ? 'No stop (meters with no location on file)' : 'No stop', ''));
  if (S.route) S.route.stops.forEach(st => sel.add(new Option('Stop ' + st.o + ': ' + st.site, String(st.o))));
  sel.value = f.stopO == null ? '' : String(f.stopO);
  mrPaintMeters();
  $('mrRead').value = f.read; $('mrMult').value = f.mult; $('mrNotes').value = f.notes;
  mrShowErrors({}, true);
  disarm('mrCancel');
  armButton($('mrCancel'), 'mrCancel', 'Cancel', 'Tap again to discard');
  mrPaintPhoto();
  mrGpsLine();
}
function mrPaintMeters() {
  const f = MR.form, box = $('mrMeters');
  box.innerHTML = '';
  mrStopMeters(f.stopO).forEach(m => box.appendChild(mrMeterRow(m.ref, m.meter, 'ref ' + m.ref + (m.where ? ' \u00b7 ' + m.where : ''),
    m.note, !f.other && f.meterRef === m.ref)));
  box.appendChild(mrMeterRow('', 'Other meter', 'Not on this list. Type its ID.', '', f.other));
  $('mrOther').hidden = !f.other;
  $('mrOther').value = f.otherId;
}
/* One row of the meter list; ref '' is the Other meter row (its title is a label, not a meter ID: body font). */
function mrMeterRow(ref, title, sub, note, on) {
  const lab = document.createElement('label');
  lab.className = 'mr-m' + (ref ? '' : ' mr-other') + (on ? ' on' : '');
  lab.innerHTML = '<input type="radio" name="mrMeter"><span><b></b><small></small><em></em></span>';
  const inp = lab.querySelector('input');
  inp.value = ref || '__other';
  inp.checked = on;
  lab.querySelector('b').textContent = title;
  lab.querySelector('small').textContent = sub;
  if (note) lab.querySelector('em').textContent = note; else lab.querySelector('em').remove();
  inp.onchange = () => {
    MR.form.other = !ref;
    MR.form.meterRef = ref || null;
    document.querySelectorAll('#mrMeters .mr-m').forEach(l => l.classList.toggle('on', l.querySelector('input').checked));
    $('mrOther').hidden = !MR.form.other;
    if (MR.form.other) $('mrOther').focus();
    mrDraftSoon();
  };
  return lab;
}
function mrStopChanged() {
  const f = mrReadForm();
  if (!f.other && !mrStopMeters(f.stopO).some(m => m.ref === f.meterRef)) f.meterRef = null;
  mrPaintMeters();
  mrDraftSoon();
}
/* Copy the inputs into MR.form and return it. */
function mrReadForm() {
  const f = MR.form, v = $('mrStop').value;
  f.stopO = v === '' ? null : Number(v);
  f.otherId = $('mrOther').value; f.read = $('mrRead').value; f.mult = $('mrMult').value; f.notes = $('mrNotes').value;
  return f;
}
/* Show the check messages. A meter error with Other meter picked is about the typed ID: the ID field turns red and takes
   the focus, not the meter list. */
function mrShowErrors(err, quiet) {
  const idBad = !!err.meter && !!(MR.form && MR.form.other);
  [['meter', 'mrMeters'], ['read', 'mrRead'], ['mult', 'mrMult']].forEach(([k, id]) => {
    $(id + 'Err').textContent = err[k] || '';
    $(id).classList.toggle('mr-bad', !!err[k] && !(k === 'meter' && idBad));
  });
  $('mrOther').classList.toggle('mr-bad', idBad);
  const first = ['meter', 'read', 'mult'].find(k => err[k]);
  if (first && !quiet) {
    const el = $({meter: idBad ? 'mrOther' : 'mrMeters', read: 'mrRead', mult: 'mrMult'}[first]);
    el.scrollIntoView({block: 'center'});
    if (el.id !== 'mrMeters') el.focus();
  }
}
/* The meter facts an entry stores: from the list (the stop's meters, or the meters with no location), or the typed ID.
   An edited read whose meter is no longer on the route keeps its saved facts. */
function mrMeterInfo(f) {
  if (f.other) return {meter: f.otherId.trim(), ref: '', bldg: '', site: ''};
  const m = mrStopMeters(f.stopO).find(x => x.ref === f.meterRef);
  if (m) return {meter: m.meter, ref: m.ref, bldg: m.bldg || '', site: mrSiteName(m.where)};
  return f.keep && f.keep.ref && f.keep.ref === f.meterRef ? f.keep : null;
}
async function mrSave() {
  if (!MR.form || MR.saving || MR.photoBusy) return;      // a photo still being made smaller: Save waits for it
  const f = mrReadForm(), err = mrCheck(f);
  const info = err.meter ? null : mrMeterInfo(f);
  if (!err.meter && !info) err.meter = 'Pick a meter, or pick Other meter.';
  mrShowErrors(err);
  if (Object.keys(err).length) return;
  MR.saving = true;
  $('mrSave').disabled = true;
  const fields = Object.assign({}, info, {stop: f.stopO, other: f.other, read: f.read.trim(), mult: f.mult.trim(),
    notes: f.notes.trim().slice(0, MR_CFG.notesMax)});
  try {
    let e, photo;
    if (f.editId) {
      e = await mrGet(f.editId);
      if (!e || e.status !== 'new') { toast('This read was exported, so it cannot change.'); mrCloseForm(); return; }
      Object.assign(e, fields, {other: !!fields.other, editedAt: Date.now()});
      if (f.photoChanged) e.photoBytes = f.photo ? f.photo.size : 0;
      photo = f.photoChanged ? (f.photo || null) : undefined;
    } else {
      e = mrMakeEntry(Object.assign({savedAt: Date.now(), gps: mrGpsNow(), photoBytes: f.photo ? f.photo.size : 0}, fields));
      photo = f.photo || null;
    }
    await mrSaveEntry(e, photo);
    mrCloseForm();
    toast((f.editId ? 'Read updated: ' : 'Read saved: ') + e.meter + (!f.editId && e.lat == null ? '. No GPS fix.' : '.'));
    MR.persisted = await mrPersist(true);
    mrAfterChange();
  } catch (x) {
    toast('Could not save on this device. Storage is blocked or full. Write the read down.', 7000);
  } finally {
    MR.saving = false;
    $('mrSave').disabled = !!MR.photoBusy;
  }
}
/* Close the form and drop its draft. */
function mrCloseForm() {
  $('mrForm').hidden = true;
  clearInterval(MR.gpsT); clearTimeout(MR.draftT); disarm('mrCancel');
  if (MR.photoUrl) { URL.revokeObjectURL(MR.photoUrl); MR.photoUrl = null; }
  MR.form = null;
  mrDraftDel().catch(() => { /* storage blocked: nothing to delete */ });
}
/* Cancel: a new form with anything filled in needs a second tap, so one stray tap cannot lose a read. */
function mrCancelTap() {
  const f = MR.form ? mrReadForm() : null;
  const filled = !!f && !f.editId && !!(f.read.trim() || f.mult.trim() || f.notes.trim() || f.otherId.trim() || f.meterRef || f.other || f.photo);
  if (filled && !armTap('mrCancel', CFG.skipConfirmMs)) return;
  mrCloseForm();
}
function mrDraftSoon() { clearTimeout(MR.draftT); MR.draftT = setTimeout(mrDraftNow, MR_CFG.draftDelayMs); }
/* Save the open form as the draft now (also before the camera opens: Android can close the page meanwhile). */
function mrDraftNow() {
  clearTimeout(MR.draftT);
  if (!MR.form) return Promise.resolve();
  return mrDraftPut({form: Object.assign({}, mrReadForm())}).catch(() => { /* storage blocked: Save says so */ });
}
function mrGpsLine() {
  if (!MR.form) return;
  const el = $('mrGps');
  if (MR.form.editId) { el.textContent = 'Date, time and GPS stay as first saved.'; return; }
  const g = mrGpsNow();
  el.textContent = g ? 'GPS \u00b1' + g.accFt + ' ft. It is saved with the read.' : 'No current GPS fix. The read saves without a position.';
}
/* Keep a focused field in view above the on-screen keyboard. */
function mrFocusInto(ev) { setTimeout(() => { try { ev.target.scrollIntoView({block: 'center'}); } catch (x) { /* gone */ } }, 300); }
/* Going to the back: keep the open form. Coming back: a browser share that has not finished after MR_CFG.pendingShareMs
   offers Mark exported (an Android browser can miss the end of a share, so its promise never settles). */
function mrVisibility() {
  if (document.visibilityState !== 'visible') { if (MR.form) mrDraftNow(); return; }
  MRX.parts.forEach(pt => {
    if (pt.state !== 'sharing' || mrInApp()) return;
    const at = Date.now();
    pt.back = at;
    setTimeout(() => { if (pt.state === 'sharing' && pt.back === at) { pt.state = 'unknown'; mrRenderExport(); } }, MR_CFG.pendingShareMs);
  });
}
/* Called once by the main script after it starts load(). A page of another version (an older page did not check
   MR_JS_VERSION) keeps manual reads off: MR.skew, no button, no help line. */
function mrInit() {
  if (typeof APP_VERSION === 'undefined' || APP_VERSION !== MR_JS_VERSION) {
    MR.off = true; MR.skew = true;
    $('aManual').hidden = true;
    return;
  }
  MR.off = MR_APP_MODE && !MR_HAS_STORE;               // an app without every MR_CALLS call: keep manual reads off there
  $('aManual').hidden = MR.off;
  $('aManual').onclick = () => mrOpenForm({});
  $('mrStop').onchange = mrStopChanged;
  ['mrRead', 'mrMult', 'mrNotes', 'mrOther'].forEach(id => {
    $(id).addEventListener('input', mrDraftSoon);
    $(id).addEventListener('focus', mrFocusInto);
  });
  $('mrCancel').onclick = mrCancelTap;
  $('mrSave').onclick = mrSave;
  $('mrPhotoBtn').onclick = mrPhotoTap;
  $('mrPhotoDel').onclick = mrPhotoRemove;
  $('mrCam').onchange = () => mrPhotoPicked($('mrCam').files && $('mrCam').files[0]);
  $('mrListClose').onclick = mrCloseList;
  $('mrNew').onclick = () => mrOpenForm({});
  $('mrExportBtn').onclick = mrOpenExport;
  $('mrExportClose').onclick = mrCloseExport;
  document.addEventListener('visibilitychange', mrVisibility);
  mrRefreshCounts();
}
/* Called by load() when the route is on screen (ok) or failed to load: a form that was dropped comes back. */
function mrAfterLoad(ok) {
  mrRefreshCounts();
  if (MR.off) return;
  mrDraftGet().then(d => {
    if (d && d.form && !MR.form) return mrOpenForm({draft: d.form}).then(() => { toast('Your unsaved manual read is back.'); mrPendingPhoto(); });
  }).catch(() => { /* storage blocked */ });
}

/* ---------- photo ---------- */
/* Shrink a camera photo: upright pixels (createImageBitmap applies the EXIF orientation), long side at most
   MR_CFG.photoLongPx, JPEG at the first quality in MR_CFG.photoQualities that gives MR_CFG.photoTargetBytes or less
   (else the last quality). The canvas JPEG has no EXIF, so no GPS or time tags leave the device inside the photo. */
async function mrShrink(file) {
  const bmp = await createImageBitmap(file, {imageOrientation: 'from-image'});
  const k = Math.min(1, MR_CFG.photoLongPx / Math.max(bmp.width, bmp.height));
  const w = Math.max(1, Math.round(bmp.width * k)), h = Math.max(1, Math.round(bmp.height * k));
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  c.getContext('2d').drawImage(bmp, 0, 0, w, h);
  bmp.close();
  let blob = null, q = 0;
  for (q of MR_CFG.photoQualities) {
    blob = await new Promise(r => c.toBlob(r, 'image/jpeg', q));
    if (blob && blob.size <= MR_CFG.photoTargetBytes) break;
  }
  c.width = c.height = 0;                        // free the canvas memory at once
  if (!blob) throw new Error('JPEG encode failed');
  return {blob, w, h, q};
}
/* Photo: keep the form as a draft that waits for a photo first (Android can close the page, or the app, while the
   camera is open), then open the camera. The camera opens from this tap, so nothing slow runs before cam.click(). */
function mrPhotoTap() {
  if (!MR.form) return;
  MR.form.awaitingPhoto = true;
  mrDraftNow();
  const cam = $('mrCam');
  cam.value = '';
  cam.click();
}
/* While the photo is made smaller, Save is off (MR.photoBusy), so a read is never saved without the photo the reader
   took. The photo belongs to the form it was taken for: when that form closed meanwhile (or another one opened), the
   photo is dropped and never goes to another read. */
async function mrPhotoPicked(file) {
  if (!file || !MR.form) return;
  const form = MR.form;
  MR.photoBusy = true;
  $('mrPhotoBtn').disabled = true;
  $('mrSave').disabled = true;
  $('mrPhotoNote').textContent = 'Saving the photo...';
  try {
    const out = await mrShrink(file);
    if (MR.form !== form) return;
    form.photo = out.blob; form.photoChanged = true; form.photoInfo = {w: out.w, h: out.h, q: out.q}; form.awaitingPhoto = false;
    mrPaintPhoto();
    mrDraftNow();
  } catch (e) {
    if (MR.form === form) $('mrPhotoNote').textContent = 'The photo could not be read. Try again.';
  } finally {
    MR.photoBusy = false;
    $('mrPhotoBtn').disabled = false;
    $('mrSave').disabled = MR.saving;
    $('mrCam').value = '';
    MR.photoSeq = (MR.photoSeq || 0) + 1;
  }
}
function mrPhotoRemove() {
  if (!MR.form) return;
  MR.form.photo = null; MR.form.photoChanged = true; MR.form.photoInfo = null;
  mrPaintPhoto();
  mrDraftSoon();
}
/* A file size for the reader: KB under 0.1 MB, so a small photo never shows "0.0 MB" (ruling S6); else MB, one decimal. */
function mrSizeText(bytes) {
  return bytes < 100000 ? Math.max(1, Math.round(bytes / 1000)) + ' KB' : (bytes / 1e6).toFixed(1) + ' MB';
}
function mrPaintPhoto() {
  const f = MR.form, img = $('mrThumb');
  if (MR.photoUrl) { URL.revokeObjectURL(MR.photoUrl); MR.photoUrl = null; }
  if (f.photo) { MR.photoUrl = URL.createObjectURL(f.photo); img.src = MR.photoUrl; img.hidden = false; }
  else { img.removeAttribute('src'); img.hidden = true; }
  $('mrPhotoBtn').textContent = f.photo ? 'Retake photo' : 'Photo';
  $('mrPhotoDel').hidden = !f.photo;
  $('mrPhotoNote').textContent = f.photo ? 'Photo kept with the read, ' + mrSizeText(f.photo.size) + '.' : 'Optional: one photo of the meter face.';
}
/* A restored form that waited for a photo: in the app, take the photo the camera made while Android had closed the app. */
function mrPendingPhoto() {
  if (!MR.form || !MR.form.awaitingPhoto) return;
  MR.form.awaitingPhoto = false;
  let b = '';
  if (mrBridge()) { try { b = mrN('takePendingPhoto'); } catch (e) { b = ''; } }
  if (b) mrPhotoPicked(new File([mrB64Blob(b, 'image/jpeg')], 'camera.jpg', {type: 'image/jpeg'}));
  else mrDraftSoon();
}

/* ---------- the Manual reads list ---------- */
const mrEntryText = () => 'Manual reads' + (MR.count.new ? ' (' + MR.count.new + ' new)' : '');
/* Counts (MR.count; MR.storeOk is false when the store cannot be read), then the entry points: the start screen button
   (only when a read is stored) and the stop list button. With manual reads off (an app without every MR_CALLS call) nothing is read. */
async function mrRefreshCounts() {
  let all = [];
  if (!MR.off) {
    try { all = await mrAll(); MR.storeOk = true; } catch (e) { MR.storeOk = false; }
  }
  MR.count = {new: all.filter(e => e.status === 'new').length, exported: all.filter(e => e.status === 'exported').length};
  const box = $('mrStartBtns');
  box.innerHTML = '';
  if (all.length) {
    const b = document.createElement('button');
    b.className = 'btn'; b.id = 'mrStartList'; b.type = 'button'; b.textContent = mrEntryText(); b.onclick = mrOpenList;
    box.appendChild(b);
  }
  const pb = $('bManual');
  if (pb) { pb.textContent = mrEntryText(); pb.hidden = MR.off; }
  return MR.count;
}
function mrOpenList() {
  const l = $('mrList');
  l.classList.toggle('over', $('start').style.display !== 'none');
  l.hidden = false;
  mrRenderList();
}
function mrCloseList() { $('mrList').hidden = true; }
async function mrRenderList() {
  const body = $('mrListBody'), xb = $('mrExportBtn');
  let all;
  try { all = await mrAll(); } catch (e) {
    body.innerHTML = '<p class="mr-note">The reads cannot be opened. Storage is blocked or full on this device, or it holds data from a newer app version. Restart the app.</p>';
    xb.disabled = true;
    return;
  }
  MR.persisted = await mrPersist(false);
  const nw = all.filter(e => e.status === 'new'), ex = all.filter(e => e.status === 'exported');
  body.innerHTML = '';
  const add = (tag, cls, txt, id) => {
    const el = document.createElement(tag);
    el.className = cls; el.textContent = txt;
    if (id) el.id = id;
    body.appendChild(el);
    return el;
  };
  add('p', 'sum', nw.length + ' new, ' + ex.length + ' exported. Stored on this device only.', 'mrSum');
  add('p', 'mr-note', mrBridge() ? 'Kept in the app on this tablet until you clear them. Uninstalling the app deletes them.'
    : MR.persisted ? 'Protected: the browser keeps these reads when storage runs low.'
    : 'Not protected: the browser can delete these reads when storage runs low or when site data is cleared. Export them soon.', 'mrKeep');
  add('div', 'sec', 'New');
  if (!nw.length) add('p', 'mr-note', 'No new reads.');
  nw.slice().reverse().forEach(e => body.appendChild(mrRow(e, true)));
  if (ex.length) {
    add('div', 'sec', 'Exported');
    ex.slice().reverse().forEach(e => body.appendChild(mrRow(e, false)));
    /* "Exported" means Gmail opened (or the share went to an app), not that the mail went out: Clear waits 7 days (K8). */
    const cut = Date.now() - MR_CFG.clearAfterMs, old = ex.filter(e => e.exportedAt > 0 && e.exportedAt < cut).length;
    add('p', 'mr-note', 'Clear only after you see the email in Gmail Sent. Reads can be cleared 7 days after export.', 'mrClearNote');
    if (old) {
      const b = document.createElement('button');
      b.className = 'btn'; b.id = 'mrClear'; b.type = 'button';
      armButton(b, 'mrClear', 'Clear ' + old + ' exported over 7 days ago', 'Tap again to clear ' + old);
      b.onclick = mrClearTap;
      const wrap = document.createElement('div');
      wrap.className = 'pbtns';
      wrap.appendChild(b);
      body.appendChild(wrap);
    }
  }
  xb.disabled = !nw.length;
  xb.textContent = nw.length ? 'Export ' + nw.length + ' new' : 'Nothing new to export';
}
/* One read in the list: meter, read x multiplier, then date, time, stop, photo and GPS. An exported read shows its CSV file
   name on a line of its own, kept on one line and cut with an ellipsis when it is too long (ruling S4). */
function mrRow(e, isNew) {
  const row = document.createElement('div');
  row.className = 'row mr-row';
  row.dataset.id = e.id;
  row.innerHTML = '<div class="rs"><div></div><div></div></div>';
  const rs = row.querySelector('.rs');
  rs.children[0].textContent = e.meter + ': ' + e.read + ' x ' + e.mult;
  rs.children[1].textContent = e.date + ' ' + e.time + (e.stop != null ? ' \u00b7 stop ' + e.stop : '') +
    (e.photoBytes ? ' \u00b7 photo' : '') + (e.lat == null ? ' \u00b7 no GPS' : '');
  if (e.exportName) {
    const f = document.createElement('div');
    f.className = 'mr-file'; f.textContent = e.exportName; f.title = e.exportName;
    rs.appendChild(f);
  }
  const btn = (txt, fn, cls) => {
    const b = document.createElement('button');
    b.type = 'button'; b.textContent = txt; b.className = cls; b.onclick = fn;
    row.appendChild(b);
    return b;
  };
  if (isNew) {
    btn('Edit', () => mrOpenForm({editId: e.id}), 'mr-edit');
    armButton(btn('Delete', () => mrDeleteTap(e.id), 'mr-del'), 'mrDel:' + e.id, 'Delete', 'Tap again');
  } else {
    btn('Mark new', () => mrMarkNew(e.id), 'mr-renew');
  }
  return row;
}
async function mrDeleteTap(id) {
  if (!armTap('mrDel:' + id, CFG.skipConfirmMs)) return;
  try { await mrDelete(id); toast('Read deleted.'); } catch (x) { toast('Could not delete. Storage is blocked.'); }
  mrAfterChange();
}
async function mrMarkNew(id) {
  try { await mrSetStatus([id], 'new'); toast('Marked new. It goes out with the next export.'); } catch (x) { toast('Could not change it. Storage is blocked.'); }
  mrAfterChange();
}
async function mrClearTap() {
  if (!armTap('mrClear', CFG.skipConfirmMs)) return;
  try {
    const n = await mrClearExported();
    toast(n + (n === 1 ? ' exported read cleared.' : ' exported reads cleared.'));
  } catch (x) { toast('Could not clear. Storage is blocked.'); }
  mrAfterChange();
}
/* After any change: the counts, and the list when it is open. */
function mrAfterChange() {
  mrRefreshCounts();
  if (!$('mrList').hidden) mrRenderList();
}

/* ---------- export ---------- */
const MRX = {parts: [], ready: false, error: '', seq: 0};
/* In the app, Gmail opens through the app (the To line is the app's own); in a browser, the share menu or Downloads.
   Fixed at load (MR_APP_MODE): a bridge call that answers nothing for a moment never sends the app to the share menu. */
const mrInApp = () => MR_APP_MODE;
/* True when this browser can share files. Without it, Export saves the files to Downloads. */
function mrCanShareFiles() {
  try { return !!(navigator.share && navigator.canShare && navigator.canShare({files: [new File(['x'], 'x.csv', {type: 'text/csv'})]})); }
  catch (e) { return false; }
}
/* Open the export sheet and make its parts. Each call (and each close) takes a new number (MRX.seq): a build that ends
   after a newer Export tap, or after the sheet closed, is dropped, so parts on screen are never replaced while the
   reader shares them. */
async function mrOpenExport() {
  const seq = ++MRX.seq;
  let nw;
  try { nw = (await mrAll()).filter(e => e.status === 'new'); } catch (e) { toast('The reads cannot be opened. Storage is blocked.'); return; }
  if (seq !== MRX.seq) return;
  if (!nw.length) { toast('No new reads to export.'); return; }
  MRX.parts = []; MRX.ready = false; MRX.error = '';
  $('mrExport').hidden = false;
  mrRenderExport();
  let parts = null, err = '';
  try { parts = await mrBuildParts(nw); }
  catch (e) { err = 'The files could not be made: ' + ((e && e.message) || 'storage error') + '.'; }
  if (seq !== MRX.seq) return;
  if (parts) { MRX.parts = parts; MRX.ready = true; } else MRX.error = err;
  mrRenderExport();
}
function mrCloseExport() {
  MRX.seq++;
  $('mrExport').hidden = true;
  MRX.parts = []; MRX.ready = false; MRX.error = '';
  mrAfterChange();
}
/* Make the parts before any tap. In a browser every file is made now (a share must start within a few seconds of its
   tap); a photo gone from storage is left out and its read goes with no photo name. In the app the CSV text is made
   now and the app copies the photos from its own store when the part is emailed. */
async function mrBuildParts(entries) {
  const app = mrInApp(), blobs = new Map();
  if (!app) {
    for (const e of entries) {
      if (!(e.photoBytes > 0)) continue;
      const b = await mrPhoto(e.id);
      if (b) blobs.set(e.id, b);
    }
  }
  const list = app ? entries.slice() : entries.map(e => Object.assign({}, e, {photoBytes: blobs.has(e.id) ? blobs.get(e.id).size : 0}));
  const names = mrPhotoNames(list), groups = mrSplit(list, app ? Infinity : MR_CFG.maxFilesPerShare), n = groups.length;
  const latest = Math.max(...list.map(e => e.savedAt));
  return groups.map((g, i) => {
    const nm = mrPartNames(latest, i, n), csv = mrCsvText(g, names);
    const photoList = g.filter(e => names.has(e.id)).map(e => ({id: e.id, name: names.get(e.id), bytes: e.photoBytes}));
    const files = app ? null : [new File([csv], nm.csv, {type: 'text/csv'})]
      .concat(photoList.map(p => new File([blobs.get(p.id)], p.name, {type: 'image/jpeg'})));
    const bytes = app ? new Blob([csv]).size + photoList.reduce((a, p) => a + p.bytes, 0) : files.reduce((a, f) => a + f.size, 0);
    if ((!app && files.length > MR_CFG.maxFilesPerShare) || bytes > MR_CFG.maxBytesPerPart) throw new Error('part ' + (i + 1) + ' is too large');
    const photos = photoList.length, tail = n > 1 ? ' Part ' + (i + 1) + ' of ' + n + '.' : '';
    return {ids: g.map(e => e.id), entries: g, names, csv, files, photoList, bytes, photos, reads: g.length, csvName: nm.csv,
      subject: nm.subject, tail, text: mrPartText(g.length, photos, tail), state: 'ready', err: '', note: '', back: 0};
  });
}
/* The email body: what the part holds. */
function mrPartText(reads, photos, tail) {
  return reads + (reads === 1 ? ' manual read, ' : ' manual reads, ') + photos + (photos === 1 ? ' photo.' : ' photos.') + (tail || '');
}
function mrRenderExport() {
  const body = $('mrExportBody');
  body.innerHTML = '';
  const p = (txt, cls) => { const el = document.createElement('p'); el.className = cls || 'mr-note'; el.textContent = txt; body.appendChild(el); return el; };
  if (MRX.error) { p(MRX.error, 'mr-err'); return; }
  if (!MRX.ready) { p('Making the files...'); return; }
  const n = MRX.parts.length, app = mrInApp(), share = !app && mrCanShareFiles();
  p(app ? 'Tap Open in Gmail. Gmail opens with the addresses, the subject and the files. Check the email, then tap Send in Gmail.'
    : share ? 'Tap Share, then pick Gmail and type the addresses. Check the email, then tap Send.'
    : 'This browser cannot share files. Save them to Downloads, then attach them to an email.', 'sum');
  if (n > 1) p('This export has ' + n + ' parts. Send one email for each part.');
  MRX.parts.forEach((pt, i) => {
    const box = document.createElement('div');
    box.className = 'mr-part'; box.id = 'mrPart' + i;
    const head = document.createElement('b');
    head.textContent = (n > 1 ? 'Part ' + (i + 1) + ' of ' + n + ': ' : '') + pt.reads + (pt.reads === 1 ? ' read, ' : ' reads, ') +
      pt.photos + (pt.photos === 1 ? ' photo, ' : ' photos, ') + mrSizeText(pt.bytes);     // never "0.0 MB" (ruling S6)
    box.appendChild(head);
    const st = document.createElement('div');
    st.className = 'mr-note'; st.id = 'mrPartState' + i;
    /* markfail: the files went out (Gmail opened, the share went to an app, or Downloads) but the reads could not be
       marked exported. Never "Not sent", and never a second email: Mark exported retries only the marking. */
    const markfail = (pt.markAs === 'saved' ? 'Saved to Downloads' : app ? 'Gmail opened' : 'Shared') +
      ', but the reads could not be marked exported (storage is blocked). ' +
      (pt.markAs === 'saved' ? 'Do not save them again.' : app ? 'Do not open Gmail again for this part.' : 'Do not share them again.') +
      ' Tap Mark exported.';
    st.textContent = {ready: 'Ready.', sharing: app ? 'Opening Gmail...' : 'Waiting for the share menu.',
      unknown: 'Did Gmail open with these files? If yes, mark this part exported.', failed: 'Not sent. ' + pt.err,
      markfail,
      done: app ? 'Gmail opened. Marked exported. Check the email, then tap Send in Gmail.' : 'Shared. Marked exported.',
      saved: 'Saved to Downloads. Marked exported.'}[pt.state];
    box.appendChild(st);
    if (pt.note) {
      const nt = document.createElement('div');
      nt.className = 'mr-note'; nt.textContent = pt.note;
      box.appendChild(nt);
    }
    const btns = document.createElement('div');
    btns.className = 'pbtns';
    const btn = (txt, fn, cls, off) => {
      const b = document.createElement('button');
      b.type = 'button'; b.className = 'btn' + (cls ? ' ' + cls : ''); b.textContent = txt; b.disabled = !!off; b.onclick = fn;
      btns.appendChild(b);
    };
    if (pt.state === 'markfail') {
      btn('Mark exported', () => mrExported(pt, pt.markAs), 'primary');
    } else if (app) {
      if (pt.state === 'ready' || pt.state === 'sharing') btn('Open in Gmail', () => mrEmailTap(i), 'primary', pt.state === 'sharing');
      else if (pt.state === 'failed') btn('Open in Gmail again', () => mrEmailTap(i), 'primary');
      else if (pt.state === 'unknown') {
        btn('Mark exported', () => mrExported(pt, 'done'), 'primary');
        btn('Open in Gmail again', () => mrEmailTap(i));
      }
    } else if (pt.state === 'ready' || pt.state === 'sharing') {
      if (share) btn('Share', () => mrShareTap(i), 'primary', pt.state === 'sharing');
      else btn('Save to Downloads', () => mrSaveTap(i), 'primary');
    } else if (pt.state === 'failed') {
      if (share) btn('Share again', () => mrShareTap(i), 'primary');
      btn('Save to Downloads', () => mrSaveTap(i));
    } else if (pt.state === 'unknown') {
      btn('Mark exported', () => mrExported(pt, 'done'), 'primary');
    }
    if (btns.childNodes.length) box.appendChild(btns);
    body.appendChild(box);
  });
  if (n && MRX.parts.every(pt => pt.state === 'done' || pt.state === 'saved')) {
    p('All done. The reads stay on this device until you clear them in Manual reads.', 'sum');
  }
}
/* App: email part i. The app copies the CSV and the photos into its export folder and opens Gmail's compose screen with
   its own To line. The part is marked exported only when Gmail opened. */
async function mrEmailTap(i) {
  const pt = MRX.parts[i];
  if (!pt || pt.state === 'sharing' || pt.state === 'done' || pt.state === 'markfail') return;
  pt.state = 'sharing'; pt.err = ''; pt.note = '';
  mrRenderExport();
  let b, text = pt.text;
  try {
    b = mrN('exportBegin');
    if (!b) throw new Error('the app did not answer');
    /* The photos first. A photo gone from the app's store is left out, as in a browser: its read goes with no photo
       name, so one lost file never blocks the part. Then the CSV, made again when a photo was left out. */
    const missing = [];
    pt.photoList.forEach(ph => {
      try { mrOk('exportAddPhoto', b, ph.id, ph.name); }
      catch (e) { if (/^error: no photo for /.test(String(e && e.message))) missing.push(ph); else throw e; }
    });
    let csv = pt.csv;
    if (missing.length) {
      const names = new Map(pt.names);
      missing.forEach(ph => names.delete(ph.id));
      csv = mrCsvText(pt.entries, names);
      text = mrPartText(pt.reads, pt.photos - missing.length, pt.tail);
      pt.note = 'Not found on this tablet, so left out: ' + missing.map(ph => ph.name).join(', ') + '. The read goes with no photo name.';
    }
    mrOk('exportAddText', b, pt.csvName, csv);
  } catch (e) {
    pt.state = 'failed'; pt.err = 'The files could not be made: ' + ((e && e.message) || 'storage error') + '.';
    mrRenderExport();
    return;
  }
  let r;
  try { r = String(mrBridge().exportOpenGmail(b, pt.subject, text)); } catch (e) { r = 'error: ' + ((e && e.message) || 'no answer'); }
  if (r === 'opened') { await mrExported(pt, 'done'); return; }
  if (r === 'error: timeout') {                       // no answer in time: Gmail may still have opened, so the reader says
    pt.state = 'unknown';
    mrRenderExport();
    return;
  }
  pt.state = 'failed';
  pt.err = r === 'no gmail' ? 'Gmail is not on this tablet, or it is turned off. Nothing was sent.' : 'Gmail did not open (' + r + '). Nothing was sent.';
  mrRenderExport();
}
/* Browser: share part i, straight from its tap (navigator.share needs the tap). The part is marked exported only when
   the share resolves, which means the reader picked an app; a cancel (AbortError) leaves the reads new. */
function mrShareTap(i) {
  const pt = MRX.parts[i];
  if (!pt || pt.state === 'sharing' || pt.state === 'done' || pt.state === 'saved' || pt.state === 'markfail') return;
  pt.state = 'sharing'; pt.err = '';
  let pr;
  try { pr = navigator.share({files: pt.files, title: pt.subject, text: pt.text}); } catch (e) { pr = Promise.reject(e); }
  mrRenderExport();
  pr.then(() => mrExported(pt, 'done'), e => {
    if (pt.state === 'done' || pt.state === 'saved') return;
    if (e && e.name === 'AbortError') pt.state = 'ready';
    else { pt.state = 'failed'; pt.err = ((e && e.name) || 'Error') + (e && e.message ? ': ' + e.message : '') + '.'; }
    mrRenderExport();
  });
}
/* Browser: save part i to Downloads, one link per file, all from this one tap. The browser may ask once to allow
   several downloads. */
function mrSaveTap(i) {
  const pt = MRX.parts[i];
  if (!pt || pt.state === 'done' || pt.state === 'saved' || pt.state === 'markfail') return;
  pt.files.forEach(f => {
    const a = document.createElement('a'), url = URL.createObjectURL(f);
    a.href = url; a.download = f.name; a.style.display = 'none';
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  });
  toast('Saved ' + pt.files.length + (pt.files.length === 1 ? ' file' : ' files') + ' to Downloads. If the browser asks, tap Allow.', 6000);
  mrExported(pt, 'saved');
}
/* Mark the part's reads exported: state 'done' (Gmail opened, or the share went to an app) or 'saved' (Downloads). When
   the marking fails the files have still gone out: state 'markfail' remembers which (pt.markAs). */
async function mrExported(pt, state) {
  if (pt.state === 'done' || pt.state === 'saved') return;
  try { await mrSetStatus(pt.ids, 'exported', pt.csvName); pt.state = state; pt.err = ''; }
  catch (e) { pt.state = 'markfail'; pt.markAs = state; }
  mrRenderExport();
  mrAfterChange();
}

/* ---------- help ---------- */
/* The help list items about manual reads (the stop list, How to use), in the app's or the browser's words. */
function mrHelpLines() {
  if (MR.skew) return '';                               // a page of another version: nothing about manual reads this time
  if (MR.off) return '<li>Manual reads need a newer AMR Route Guide app on this tablet.</li>';
  return '<li>Manual read: tap Manual read on the stop card. Pick the meter, type the face read as the dial shows and the multiplier, and add a photo if needed. The reads stay on this tablet.</li>' +
    (mrBridge() ? '<li>To email them: Manual reads (in this list), Export, then Open in Gmail. Gmail opens with the addresses filled in. Check the email, then tap Send.</li>'
      : '<li>To email them: Manual reads (in this list), Export, then Share. Pick Gmail and type the addresses. One email holds up to 9 photos.</li>');
}
