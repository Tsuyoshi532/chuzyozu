const CACHE = 'app-78250237';
const FILES = ["./", "index.html", "manifest.webmanifest", "icons/icon-180.png", "icons/icon-192.png", "icons/icon-512.png", "icons/icon-maskable-512.png"];
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => (k.startsWith('app-') || k.startsWith('chuzyozu-')) && k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const req = e.request, u = new URL(req.url);
  // 地理院タイル（地図・標高）：一度読んだものは端末に残し、圏外でも使えるようにする（先に保存した物を見る）
  if (req.method === 'GET' && (u.hostname === 'cyberjapandata.gsi.go.jp' || (u.hostname === 'gbank.gsj.jp' && /\/(tiles|maptile)\//.test(u.pathname)) || u.hostname === 'tiles.gsj.jp')) {   // 地質図のタイルも
    e.respondWith(caches.open('gsi-tiles').then(c => c.match(req).then(hit => hit || fetch(req).then(r => { if (r.ok || r.type === 'opaque') c.put(req, r.clone()); return r; }))));
    return;
  }
  if (req.method !== 'GET' || u.origin !== location.origin) return;
  // 地質図幅の一覧：新しいものを先に読み、圏外のときは前に読んだものを使う
  if (/\/g50index\.json$/.test(u.pathname)) {
    e.respondWith(fetch(req).then(r => { if (r.ok) { const c = r.clone(); caches.open('gsi-tiles').then(x => x.put('g50index.json', c)); } return r; }).catch(() => caches.open('gsi-tiles').then(x => x.match('g50index.json')).then(h => h || Response.error())));
    return;
  }
  if (req.mode === 'navigate') {
    e.respondWith(fetch(req).then(r => { const c = r.clone(); caches.open(CACHE).then(x => x.put('index.html', c)); return r; })
      .catch(() => caches.match('index.html')));
    return;
  }
  e.respondWith(caches.match(req).then(hit => hit || fetch(req)));
});
