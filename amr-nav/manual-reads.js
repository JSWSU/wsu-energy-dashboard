/* AMR Route Guide: manual reads.
   A reader saves a meter's face read, multiplier, notes and one photo, with the date, time and GPS, with no signal.
   The reads stay on this device and never go to the web site: in the AMR Route Guide app (window.AMRNative, bridge
   version 2 or later) in the app's own files; in a browser in IndexedDB. Export makes one CSV plus the photos per
   part: the app opens Gmail with the addresses filled in by the app itself; a browser shares the files (the reader
   picks Gmail and types the addresses) or saves them to Downloads. The reader taps Send in Gmail; nothing here sends.
   This file loads before the main script. Its functions use these names from the main script, at call time only:
   S, CFG, $, toast, armTap, armButton, disarm, hav, currentTargetStop, closePanel. Every name here starts with mr or MR. */
'use strict';
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
