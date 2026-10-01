/* AMR Route Guide service worker: keeps the app, route and offline map on the device.
   The app page opens at once from the saved copy and is refreshed in the background (a new app version shows on the next open;
   a drive in progress is safe, because the page keeps the route it started on). route.json comes from the network first (so a
   new route always shows up) and falls back to the saved copy when the network is down or slow; a damaged route.json is never
   saved. graph.json, the road map that the page plans new routes on when the driver leaves the route, comes the same way
   (network first, so the first open after a deploy gets the road map that belongs to the new route), and only a reply that
   is a whole graph is saved or served: a damaged one gives way to the saved copy. Map tiles go straight to the network and
   are never cached. */
const VERSION = 'amr-nav-2026.10.01-2';
const FRESH_TIMEOUT_MS = 3000;     // route.json and graph.json: give up on the network after this long and use the saved copy
const CORE = [
  './', './index.html', './manifest.webmanifest', './route.json', './graph.json', './basemap.json',
  './vendor/leaflet/leaflet.js', './vendor/leaflet/leaflet.css',
  './vendor/leaflet/images/layers.png', './vendor/leaflet/images/layers-2x.png',
  './vendor/leaflet/images/marker-icon.png', './vendor/leaflet/images/marker-icon-2x.png', './vendor/leaflet/images/marker-shadow.png',
  './icons/icon-192.png', './icons/icon-512.png', './icons/maskable-512.png', './icons/favicon-64.png', './icons/apple-touch-icon.png',
];
const OFFLINE = () => new Response('Offline and not cached yet.', {status: 503, headers: {'Content-Type': 'text/plain'}});

/* A reply worth saving: JSON that passes `test`. Reads a copy, so the reply itself can still be used. */
const goodJson = test => async res => {
  try { return !!test(await res.clone().json()); } catch (err) { return false; }
};
/* route.json: a non-empty legs array */
const goodRoute = goodJson(r => r && Array.isArray(r.legs) && r.legs.length > 0);
/* graph.json: format amr-graph-2 that the page can decode: every list as long as n or m says, every edge end a node, as many
   interior points as the edges count, and every barrier, turn row, roundabout and island index in range (the checks of the
   page's decodeGraph) */
function graphFits(g) {
  const n = g && g.n, m = g && g.m, fits = (a, k) => Array.isArray(a) && a.length === k;
  if (!(g && g.format === 'amr-graph-2' && n > 0 && m > 0 && fits(g.nlat, n) && fits(g.nlon, n) &&
        ['ea', 'eb', 'ef', 'en', 'el', 'ek'].every(k => fits(g[k], m)) && Array.isArray(g.ec) && Array.isArray(g.names) &&
        Array.isArray(g.car_kmh) && g.h_car_kmh > 0 && Array.isArray(g.classes) && fits(g.bbox, 4) && g.bbox.every(Number.isFinite) &&
        g.uturn_s >= 0 && g.heading_snap_m >= 0 && ['car_block', 'turns', 'ra', 'car_island'].every(k => Array.isArray(g[k])))) return false;
  const ea = new Int32Array(m), eb = new Int32Array(m);
  let pts = 0;
  for (let i = 0, a = 0; i < m; i++) {
    a += g.ea[i]; ea[i] = a; eb[i] = a + g.eb[i];
    if (!(a >= 0 && a < n && eb[i] >= 0 && eb[i] < n && g.ek[i] >= 0)) return false;
    pts += g.ek[i];
  }
  const inRange = (list, k) => list.every(x => Number.isInteger(x) && x >= 0 && x < k);
  return g.ec.length === 2 * pts && inRange(g.car_block, n) && inRange(g.ra, m) && inRange(g.car_island, m) &&
    g.turns.every(t => Array.isArray(t) && t.length === 4 && t.every(Number.isInteger) && t[0] >= 0 && t[0] < m && t[2] >= 0 && t[2] < m &&
      t[1] >= 0 && t[1] < n && (t[3] === 0 || t[3] === 1) && (ea[t[0]] === t[1] || eb[t[0]] === t[1]) && (ea[t[2]] === t[1] || eb[t[2]] === t[1]));
}
const goodGraph = goodJson(graphFits);
const CHECKED = {'./route.json': goodRoute, './graph.json': goodGraph};   // CORE files saved only when they pass their test
/* Save a copy of a reply in the background; e.waitUntil keeps the worker alive until it is stored. With `check` (an async test
   of the reply), only a reply that passes it is saved. The reply itself is not read, so it can go to the page at once. */
function save(e, cache, key, res, check) {
  const copy = res.clone(), ok = check ? check(res) : Promise.resolve(true);
  try { e.waitUntil(ok.then(good => good ? cache.put(key, copy) : null).catch(() => { /* storage full: serve without saving */ })); }
  catch (err) { /* the event is already over: serve without saving */ }
}

self.addEventListener('install', e => {
  // 'reload' skips the browser HTTP cache, so a deploy that is under 10 minutes old is not stored as an old copy.
  // route.json and graph.json are saved only when they pass their test; otherwise the copy an older version saved is kept.
  e.waitUntil(caches.open(VERSION).then(async c => {
    await c.addAll(CORE.filter(u => !CHECKED[u]).map(u => new Request(u, {cache: 'reload'})));
    for (const u of Object.keys(CHECKED)) {
      const r = await fetch(new Request(u, {cache: 'reload'}));
      const keep = r.ok && await CHECKED[u](r) ? r : await caches.match(u);
      if (keep) await c.put(u, keep);
    }
  }).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k.startsWith('amr-nav-') && k !== VERSION).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

const SCOPE_PATH = new URL('./', self.location).pathname;       // for example /amr-nav/
const isAppPage = url => url.pathname === SCOPE_PATH || url.pathname === SCOPE_PATH + 'index.html';

/* The app page: the saved copy at once, one copy for every address that opens it (./, index.html, with or without ?reset=1 or
   ?sim=1), refreshed from the server in the background (no HTTP cache) for the next open. Only a text/html reply is saved, so a
   stray file can never take the app page's place. With no saved copy, wait for the server. */
async function appPage(e) {
  const cache = await caches.open(VERSION);
  const net = fetch(e.request, {cache: 'no-cache'}).then(res => {
    if (res.ok && /^text\/html/i.test(res.headers.get('content-type') || '')) save(e, cache, './', res);
    return res;
  });
  const hit = await cache.match('./');
  if (hit) { e.waitUntil(net.catch(() => null)); return hit; }
  return net.catch(OFFLINE);
}

/* route.json and graph.json, network first: ask the server (no HTTP cache), wait at most FRESH_TIMEOUT_MS. A reply that passes
   `check` is saved under `key`. The reply is returned when it came in time: for route.json even a damaged one (the page then
   falls back to its pinned or saved route); with needGood (graph.json) only one that passes `check`. Otherwise the saved copy;
   with no saved copy, the server reply or a 503. */
async function networkFirst(e, key, check, needGood) {
  const cache = await caches.open(VERSION);
  const net = fetch(e.request, {cache: 'no-cache'}).then(res => {
    if (res.ok) save(e, cache, key, res, check);
    return res;
  });
  let timer, res = null;
  const slow = new Promise((_, reject) => { timer = setTimeout(() => reject(new Error('slow')), FRESH_TIMEOUT_MS); });
  try { res = await Promise.race([net, slow]); } catch (err) { /* offline or too slow */ }
  clearTimeout(timer);
  if (res && res.type === 'opaqueredirect') return res;                 // a redirect is for the browser to follow
  if (res && res.ok && (!needGood || await check(res))) return res;
  e.waitUntil(net.catch(() => null));          // a slow reply still refreshes the saved copy when it arrives
  return (await cache.match(key)) || res || OFFLINE();
}

/* Everything else, including a tab opened on another file in the scope: saved copy first, refreshed in the background
   (stale while revalidate), exact address only. With `check`, only a reply that passes it is saved. */
async function savedFirst(e, check) {
  const cache = await caches.open(VERSION);
  const hit = await cache.match(e.request);
  const net = fetch(e.request).then(res => {
    if (res && res.ok) save(e, cache, e.request, res, check);
    return res;
  }).catch(() => null);
  if (hit) { e.waitUntil(net); return hit; }
  return (await net) || OFFLINE();
}

self.addEventListener('fetch', e => {
  const req = e.request;
  const url = new URL(req.url);
  if (req.method !== 'GET' || url.origin !== self.location.origin) return;
  if (req.mode === 'navigate' && isAppPage(url)) e.respondWith(appPage(e));
  else if (url.pathname.endsWith('route.json')) e.respondWith(networkFirst(e, url.origin + url.pathname, goodRoute));   // saved without its query
  else if (url.pathname.endsWith('graph.json')) e.respondWith(networkFirst(e, url.origin + url.pathname, goodGraph, true));
  else e.respondWith(savedFirst(e));
});
