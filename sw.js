const CACHE_NAME = 'anthropac-v1';
const assetsToCache = [
  './',
  './index.html',
  './style.css',
  './app.js',
  './calc.py',
  './manifest.json'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(assetsToCache);
    })
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request).then(response => {
      return response || fetch(event.request);
    })
  );
});
