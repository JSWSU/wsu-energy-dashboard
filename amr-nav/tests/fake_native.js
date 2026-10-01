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
  const cfg = Object.assign({bridge: '1', app: '1.0', web: '', source: 'built in', pending: '', check: 'never', speak: 'ok', open: 'ok'},
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
