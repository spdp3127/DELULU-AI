// DELULU PWA Service Worker - v3.1 (ADA, SEO & Real Features)
const CACHE_NAME = 'delulu-core-v3.1';
const ASSETS_TO_CACHE = [
  '/',
  '/static/css/style.css?v=3.1',
  '/static/js/app.js?v=3.1',
  '/static/img/spdp_logo.png',
  '/manifest.json'
];

self.addEventListener('install', (e) => {
  self.skipWaiting();
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE).catch(() => {});
    })
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((k) => caches.delete(k))
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (e) => {
  // Only handle GET requests and skip API / dynamic endpoints
  if (e.request.method !== 'GET' || e.request.url.includes('/api/')) {
    return;
  }

  // Network-First: always fetch fresh assets, cache them, fallback to cache if offline
  e.respondWith(
    fetch(e.request)
      .then((networkRes) => {
        if (networkRes && networkRes.status === 200) {
          const resClone = networkRes.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(e.request, resClone));
        }
        return networkRes;
      })
      .catch(() => caches.match(e.request))
  );
});
