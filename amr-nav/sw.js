/* AMR Route Guide service worker: keeps the app, route and offline map on the device.
   The app page opens at once from the saved copy and is refreshed in the background (a new app version shows on the next open;
   a drive in progress is safe, because the page keeps the route it started on). route.json comes from the network first (so a
   new route always shows up) and falls back to the saved copy when the network is down or slow; a damaged route.json is never
   saved. Map tiles and rerouting go straight to the network and are never cached. */
const VERSION = 'amr-nav-2026.09.30-3';
const FRESH_TIMEOUT_MS = 3000;     // route.json: give up on the network after this long and use the saved copy
const CORE = [
  './', './index.html', './manifest.webmanifest', './route.json', './basemap.json',
  './vendor/leaflet/leaflet.js', './vendor/leaflet/leaflet.css',
  './vendor/leaflet/images/layers.png', './vendor/leaflet/images/layers-2x.png',
  './vendor/leaflet/images/marker-icon.png', './vendor/leaflet/images/marker-icon-2x.png', './vendor/leaflet/images/marker-shadow.png',
  './icons/icon-192.png', './icons/icon-512.png', './icons/maskable-512.png', './icons/favicon-64.png', './icons/apple-touch-icon.png',
];
const OFFLINE = () => new Response('Offline and not cached yet.', {status: 503, headers: {'Content-Type': 'text/plain'}});

/* A route.json reply worth saving: JSON with a non-empty legs array. Reads a copy, so the reply itself can still be used. */
async function goodRoute(res) {
  try {
    const r = await res.clone().json();
    return !!r && Array.isArray(r.legs) && r.legs.length > 0;
  } catch (err) { return false; }
}
/* Save a copy of a reply in the background; e.waitUntil keeps the worker alive until it is stored. With `check` (an async test
   of the reply), only a reply that passes it is saved. The reply itself is not read, so it can go to the page at once. */
function save(e, cache, key, res, check) {
  const copy = res.clone(), ok = check ? check(res) : Promise.resolve(true);
  try { e.waitUntil(ok.then(good => good ? cache.put(key, copy) : null).catch(() => { /* storage full: serve without saving */ })); }
  catch (err) { /* the event is already over: serve without saving */ }
}

self.addEventListener('install', e => {
  // 'reload' skips the browser HTTP cache, so a deploy that is under 10 minutes old is not stored as an old copy.
  // route.json is saved only when it is a good route; otherwise the copy an older version saved is kept.
  e.waitUntil(caches.open(VERSION).then(async c => {
    await c.addAll(CORE.filter(u => u !== './route.json').map(u => new Request(u, {cache: 'reload'})));
    const r = await fetch(new Request('./route.json', {cache: 'reload'}));
    const keep = r.ok && await goodRoute(r) ? r : await caches.match('./route.json');
    if (keep) await c.put('./route.json', keep);
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

/* route.json, network first: ask the server (no HTTP cache), wait at most FRESH_TIMEOUT_MS. A good route is saved under `key`.
   The reply is returned when it came in time, even a damaged one (the page then falls back to its pinned or saved route);
   otherwise the saved copy; with no saved copy, the server reply or a 503. */
async function networkFirst(e, key) {
  const cache = await caches.open(VERSION);
  const net = fetch(e.request, {cache: 'no-cache'}).then(res => {
    if (res.ok) save(e, cache, key, res, goodRoute);
    return res;
  });
  let timer, res = null;
  const slow = new Promise((_, reject) => { timer = setTimeout(() => reject(new Error('slow')), FRESH_TIMEOUT_MS); });
  try { res = await Promise.race([net, slow]); } catch (err) { /* offline or too slow */ }
  clearTimeout(timer);
  if (res && (res.ok || res.type === 'opaqueredirect')) return res;     // a redirect is for the browser to follow
  e.waitUntil(net.catch(() => null));          // a slow reply still refreshes the saved copy when it arrives
  return (await cache.match(key)) || res || OFFLINE();
}

/* Everything else, including a tab opened on another file in the scope: saved copy first, refreshed in the background
   (stale while revalidate), exact address only. */
async function savedFirst(e) {
  const cache = await caches.open(VERSION);
  const hit = await cache.match(e.request);
  const net = fetch(e.request).then(res => {
    if (res && res.ok) save(e, cache, e.request, res);
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
  else if (url.pathname.endsWith('route.json')) e.respondWith(networkFirst(e, url.origin + url.pathname));   // saved without its query
  else e.respondWith(savedFirst(e));
});
