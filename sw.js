// Service Worker ─ 盲点マップ（盲点の大きさと形を左右で比べる / Functional Neuro Training）
// 戦略：Network First（新しいコードを最優先で拾う → 開発ナレッジ準拠）。
//       オフライン時のみキャッシュへフォールバック。
// index.html 側で controllerchange を検知して location.reload() する前提。
const CACHE_NAME = 'moten-map-v2.0.0';

const ASSETS_TO_CACHE = [
  './',
  './index.html',
  './manifest.json',
  './FNT512.png',
  './FNT512-transparent.png',
  'https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&family=Shippori+Mincho:wght@500;700&family=Cormorant+Garamond:wght@500;600&display=swap'
];

// インストール：app shell をプリキャッシュし即 skipWaiting
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(ASSETS_TO_CACHE))
      .then(() => self.skipWaiting())
      .catch((err) => console.error('[SW] precache failed', err))
  );
});

// アクティベート：このアプリの古いキャッシュだけ削除して即 claim（同じドメインの他のFNTアプリのキャッシュは消さない）
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((names) => Promise.all(
        names.map((name) => (name.startsWith('moten-map-') && name !== CACHE_NAME) ? caches.delete(name) : null)
      ))
      .then(() => self.clients.claim())
  );
});

// フェッチ：Network First
self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;

  // 対象は同一オリジン ＋ Google Fonts のみ
  const url = req.url;
  const sameOrigin = url.startsWith(self.location.origin);
  const isFont = url.startsWith('https://fonts.');
  if (!sameOrigin && !isFont) return;

  event.respondWith(
    fetch(req)
      .then((networkRes) => {
        // 取得できたら最新をキャッシュへ反映（オフライン用）
        if (networkRes && networkRes.status === 200 &&
            (networkRes.type === 'basic' || networkRes.type === 'cors')) {
          const clone = networkRes.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(req, clone));
        }
        return networkRes;
      })
      .catch(() =>
        // オフライン：キャッシュ → navigate は index.html にフォールバック
        caches.match(req).then((cached) => {
          if (cached) return cached;
          if (req.mode === 'navigate') return caches.match('./index.html');
          return new Response('Offline', { status: 503, statusText: 'Offline' });
        })
      )
  );
});

// メッセージ（将来のSKIP_WAITING手動更新に備える／無害）
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') self.skipWaiting();
});
