/* AMR Route Guide service worker: keeps the app, route and offline map on the device.
   The page and route.json come from the network first (so a new route always shows up) and fall back to the
   saved copy when the network is down or slow. Map tiles and rerouting go straight to the network and are never cached. */
const VERSION = 'amr-nav-2026.09.30-2';
const FRESH_TIMEOUT_MS = 3000;     // network-first files: give up on the network after this long and use the saved copy
const CORE = [
  './', './index.html', './manifest.webmanifest', './route.json', './basemap.json',
  './vendor/leaflet/leaflet.js', './vendor/leaflet/leaflet.css',
  './vendor/leaflet/images/layers.png', './vendor/leaflet/images/layers-2x.png',
  './vendor/leaflet/images/marker-icon.png', './vendor/leaflet/images/marker-icon-2x.png', './vendor/leaflet/images/marker-shadow.png',
  './icons/icon-192.png', './icons/icon-512.png', './icons/maskable-512.png', './icons/favicon-64.png', './icons/apple-touch-icon.png',
];

self.addEventListener('install', e => {
  // 'reload' skips the browser HTTP cache, so a deploy that is under 10 minutes old is not stored as an old copy
  e.waitUntil(caches.open(VERSION).then(c => c.addAll(CORE.map(u => new Request(u, {cache: 'reload'})))).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k.startsWith('amr-nav-') && k !== VERSION).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

const SCOPE_PATH = new URL('./', self.location).pathname;       // for example /amr-nav/
const isAppPage = url => url.pathname === SCOPE_PATH || url.pathname === SCOPE_PATH + 'index.html';

/* Network first: ask the server (no HTTP cache), wait at most FRESH_TIMEOUT_MS. A good reply is saved under `key`
   and returned (when `html` is set, only a text/html reply is saved, so a stray file can never take the app page's place).
   Otherwise return the saved copy; with no saved copy, return the server reply or a 503. */
async function networkFirst(e, key, html) {
  const cache = await caches.open(VERSION);
  const net = fetch(e.request, {cache: 'no-cache'}).then(res => {
    const saveable = res.ok && (!html || /^text\/html/i.test(res.headers.get('content-type') || ''));
    if (saveable) cache.put(key, res.clone()).catch(() => { /* storage full: serve without saving */ });
    return res;
  });
  let timer, res = null;
  const slow = new Promise((_, reject) => { timer = setTimeout(() => reject(new Error('slow')), FRESH_TIMEOUT_MS); });
  try { res = await Promise.race([net, slow]); } catch (err) { /* offline or too slow */ }
  clearTimeout(timer);
  if (res && (res.ok || res.type === 'opaqueredirect')) return res;     // a redirect is for the browser to follow
  e.waitUntil(net.catch(() => null));          // a slow reply still refreshes the saved copy when it arrives
  return (await cache.match(key)) || res ||
    new Response('Offline and not cached yet.', {status: 503, headers: {'Content-Type': 'text/plain'}});
}

self.addEventListener('fetch', e => {
  const req = e.request;
  const url = new URL(req.url);
  if (req.method !== 'GET' || url.origin !== self.location.origin) return;
  // the app page: one saved copy for every address that opens it (./, index.html, with or without ?reset=1 or ?sim=1)
  const page = req.mode === 'navigate' && isAppPage(url);
  if (page || url.pathname.endsWith('route.json')) {
    e.respondWith(networkFirst(e, page ? './' : url.origin + url.pathname, page));    // route.json: saved without its query
    return;
  }
  // everything else, including a tab opened on another file in the scope: saved copy first, refresh in the
  // background (stale while revalidate), exact address only
  e.respondWith(caches.open(VERSION).then(async cache => {
    const hit = await cache.match(req);
    const net = fetch(req).then(res => {
      if (res && res.ok) cache.put(req, res.clone());
      return res;
    }).catch(() => null);
    if (hit) { e.waitUntil(net); return hit; }
    const res = await net;
    return res || new Response('Offline and not cached yet.', {status: 503, headers: {'Content-Type': 'text/plain'}});
  }));
});
