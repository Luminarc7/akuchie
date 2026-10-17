// 悪知恵 service worker: lets the site (and the app installed from it) open
// without a connection - the search works on the card database it kept.
//
// It always asks the network first and only falls back to what it kept when the
// network cannot answer, so it never keeps visitors on an old version of the site.
// The card database (about 22 MB once unpacked) is stored again only when it changed.
const CACHE = 'warujie-v2';
const KEEP = ['/ja_cards.json', '/printings.json.gz', '/meta.json', '/meta_decks.json', '/combo_ja.js', '/manifest.webmanifest'];

self.addEventListener('install', (e) => {
  self.skipWaiting();
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(['/', '/manifest.webmanifest', '/icons/icon-192-v2.png'])).catch(() => {}));
});
self.addEventListener('activate', (e) => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) if (k !== CACHE) await caches.delete(k);
    await self.clients.claim();
  })());
});
self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;   // Scryfall, fonts, price data: left to the browser
  const page = req.mode === 'navigate';
  if (!page && !KEEP.includes(url.pathname) && !url.pathname.startsWith('/meta_lists/') && !url.pathname.startsWith('/icons/')) return;
  const key = url.pathname;   // every page is the same file whatever its ?…
  e.respondWith((async () => {
    try {
      const res = await fetch(req);
      if (res.ok && res.status === 200) {
        const cache = await caches.open(CACHE);
        const old = await cache.match(key);
        const tag = res.headers.get('ETag');
        if (!old || !tag || old.headers.get('ETag') !== tag) e.waitUntil(cache.put(key, res.clone()).catch(() => {}));
      }
      return res;
    } catch (err) {
      const hit = await caches.match(key);
      if (hit) return hit;
      throw err;
    }
  })());
});
