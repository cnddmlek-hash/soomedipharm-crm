/* 수메디팜 미니 CRM — 서비스워커
   규칙
   1) 같은 출처(same-origin)의 정적 파일만 다룬다.
   2) Apps Script 웹앱(script.google.com / script.googleusercontent.com) 등 외부 요청은
      가로채지도, 캐시하지도 않는다. (fetch 핸들러에서 그냥 return → 브라우저가 평소처럼 요청)
   3) 정적 파일은 network-first — GitHub에 새로 push한 화면이 1~2분 안에 그대로 반영되고,
      오프라인일 때만 캐시를 쓴다.
*/
const CACHE = 'soomedipharm-crm-v20';
const ASSETS = [
  './',
  './index.html',
  './manifest.json',
  './icon-192.png',
  './icon-512.png',
  './icon-maskable-512.png',
  './apple-touch-icon.png',
  './favicon-32.png'
];
const SCOPE_PATH = new URL('./', self.location).pathname;

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE)
      .then((cache) => cache.addAll(ASSETS))
      .then(() => self.skipWaiting())
      .catch(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;        // Apps Script(시트 서버)·CDN 은 손대지 않음
  if (url.pathname.indexOf(SCOPE_PATH) !== 0) return;     // 이 앱 범위 밖 경로도 그대로 통과

  event.respondWith(networkFirst(req));
});

async function networkFirst(req) {
  const cache = await caches.open(CACHE);
  try {
    const res = await fetch(req);
    if (res && res.ok && res.type === 'basic') cache.put(req, res.clone());
    return res;
  } catch (e) {
    const hit = await cache.match(req, { ignoreSearch: true });
    if (hit) return hit;
    if (req.mode === 'navigate') {
      const shell = await cache.match('./index.html');
      if (shell) return shell;
    }
    throw e;
  }
}
