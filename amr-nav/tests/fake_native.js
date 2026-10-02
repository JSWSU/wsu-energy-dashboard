/* Test stand-in for the Android app's bridge, window.AMRNative (Bridge.java in the app). The tests inject it with
   add_init_script before the page runs. It keeps its state in localStorage (key __fakeNative), so the state survives a
   reload or a new page in the same browser profile, and it records every call in window.__native. Set
   window.__nativeCfg before it runs to change its answers. It never holds an email address: the real app fixes the To
   line in its own code, and the web page never passes one.
   Version 1 calls: bridgeVersion, info, ready, setDriveActive, speak, stopSpeech, ttsInfo, openExternal.
   Later blocks at the end of this file add the version 2 calls. */
(() => {
  const KEY = '__fakeNative';
  let saved = {};
  try { saved = JSON.parse(localStorage.getItem(KEY) || '{}') || {}; } catch (e) { saved = {}; }
  const st = Object.assign({drive: false}, saved);
  const save = () => { try { localStorage.setItem(KEY, JSON.stringify(st)); } catch (e) { /* full: the tests keep their data small */ } };
  const cfg = Object.assign({bridge: '2', app: '1.1', web: '', source: 'built in', pending: '', check: 'never', speak: 'ok', open: 'ok'},
    window.__nativeCfg || {});
  const N = window.__native = {calls: [], spoken: [], opened: [], ready: [], drive: [], cfg, st, save};
  const rec = (name, args) => { N.calls.push([name].concat(Array.from(args))); };
  window.AMRNative = {
    bridgeVersion() { rec('bridgeVersion', arguments); return String(cfg.bridge); },
    info() {
      rec('info', arguments);
      return JSON.stringify({bridge: Number(cfg.bridge), app: cfg.app, code: 1, debug: true, web: cfg.web, source: cfg.source,
        pending: cfg.pending, check: cfg.check, checkedAt: 0, driveActive: !!st.drive, blocked: 0});
    },
    ready(v) { rec('ready', arguments); N.ready.push(String(v)); return 'ok'; },
    setDriveActive(on) { rec('setDriveActive', arguments); st.drive = !!on; N.drive.push(!!on); save(); return 'ok'; },
    speak(t, u) { rec('speak', arguments); N.spoken.push([String(t), !!u]); return cfg.speak; },
    stopSpeech() { rec('stopSpeech', arguments); return 'ok'; },
    ttsInfo() { rec('ttsInfo', arguments); return JSON.stringify({ready: true, engine: 'fake', voice: 'en-US', offline: true, error: ''}); },
    openExternal(url) { rec('openExternal', arguments); N.opened.push(String(url)); return cfg.open; },
  };
})();

/* Version 2: the manual reads store (ReadStore.java in the app): entries as JSON text by id, photos as base64 by id,
   one draft. It answers as the app does (ruling C1): the id 'draft' is the open form's photo, never an entry; a missing
   photo or draft answers ''; the deletes always answer 'ok'; the same size limits; storeAll is one JSON list that leaves
   out a damaged entry (the app logs it and keeps the file). cfg.storeError (for example 'error: disk full') makes the
   reads and writes answer it, like a full app store (the deletes still answer 'ok', as the app's cannot fail).
   cfg.notApp makes every call answer '', as the real bridge does while the page does not count as the app's own.
   An app older than 1.1 (cfg.bridge '1') has none of these calls. */
(() => {
  const N = window.__native, st = N.st, cfg = N.cfg;
  if (cfg.bridge !== '' && Number(cfg.bridge) < 2) return;
  st.entries = st.entries || {}; st.photos = st.photos || {}; st.draft = st.draft || '';
  const MAX_JSON = 64 * 1024, MAX_PHOTO = 8 * 1024 * 1024, MAX_ENTRIES = 5000;     // ReadStore.java
  const short = a => (typeof a === 'string' && a.length > 200 ? a.slice(0, 20) + '...(' + a.length + ')' : a);
  const rec = (name, args) => { N.calls.push([name].concat(Array.from(args).map(short))); };
  const off = () => !!cfg.notApp;
  const fail = () => (cfg.storeError ? String(cfg.storeError) : '');
  const okId = id => /^[A-Za-z0-9_-]{1,64}$/.test(String(id));                       // Names.validId
  const text = j => (j == null ? '' : String(j).trim());
  const braces = j => j.startsWith('{') && j.endsWith('}');                           // ReadStore.isObject
  const bytes = j => new TextEncoder().encode(j).length;
  const isEntry = j => { try { const o = JSON.parse(j); return !!o && typeof o === 'object' && !Array.isArray(o); } catch (e) { return false; } };
  Object.assign(window.AMRNative, {
    storeAll() {
      rec('storeAll', arguments);
      if (off()) return '';
      return fail() || '[' + Object.keys(st.entries).sort().map(k => st.entries[k]).filter(isEntry).join(',') + ']';
    },
    storePut(id, json) {
      rec('storePut', arguments);
      if (off()) return '';
      if (fail()) return fail();
      const j = text(json);
      if (!okId(id) || id === 'draft') return 'error: bad id';
      if (!braces(j)) return 'error: not an entry';
      if (bytes(j) > MAX_JSON) return 'error: the entry is too large';
      if (!(id in st.entries) && Object.keys(st.entries).length >= MAX_ENTRIES) return 'error: too many entries; export and clear some';
      st.entries[id] = j; N.save(); return 'ok';
    },
    storeDelete(id) {
      rec('storeDelete', arguments);
      if (off()) return '';
      if (okId(id) && id !== 'draft') { delete st.entries[id]; delete st.photos[id]; N.save(); }
      return 'ok';
    },
    photoPut(id, b64) {
      rec('photoPut', arguments);
      if (off()) return '';
      if (fail()) return fail();
      if (!okId(id)) return 'error: bad id';
      let bin;
      try { bin = atob(text(b64)); } catch (e) { return 'error: Illegal base64 character'; }
      if (bin.length < 4 || bin.length > MAX_PHOTO) return 'error: bad photo size';
      if (bin.charCodeAt(0) !== 0xFF || bin.charCodeAt(1) !== 0xD8 || bin.charCodeAt(2) !== 0xFF) return 'error: not a JPEG';
      st.photos[id] = text(b64); N.save(); return 'ok';
    },
    photoGet(id) { rec('photoGet', arguments); if (off()) return ''; return fail() || (okId(id) && st.photos[id]) || ''; },
    photoDelete(id) { rec('photoDelete', arguments); if (off()) return ''; if (okId(id)) { delete st.photos[id]; N.save(); } return 'ok'; },
    draftGet() { rec('draftGet', arguments); if (off()) return ''; return fail() || st.draft || ''; },
    draftPut(json) {
      rec('draftPut', arguments);
      if (off()) return '';
      if (fail()) return fail();
      const j = text(json);
      if (!braces(j) || bytes(j) > MAX_JSON) return 'error: bad draft';
      st.draft = j; N.save(); return 'ok';
    },
    draftDelete() { rec('draftDelete', arguments); if (off()) return ''; st.draft = ''; N.save(); return 'ok'; },
  });
})();

/* Version 2: a photo the camera took while Android had closed the app (the app keeps it once; st.pending, base64). */
(() => {
  const N = window.__native, st = N.st, cfg = N.cfg;
  if (cfg.bridge !== '' && Number(cfg.bridge) < 2) return;
  window.AMRNative.takePendingPhoto = function () {
    N.calls.push(['takePendingPhoto']);
    if (cfg.notApp) return '';
    const b = st.pending || '';
    st.pending = ''; N.save();
    return b;
  };
})();
