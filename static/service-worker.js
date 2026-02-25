const CACHE_NAME = "dropout-assistant-v1";
const urlsToCache = ["/", "/static/js/app.js", "/static/manifest.json", "/static/css/style.css"];
self.addEventListener("install", e => e.waitUntil(
  caches.open(CACHE_NAME).then(cache => cache.addAll(urlsToCache))
));
self.addEventListener("activate", e => e.waitUntil(
  caches.keys().then(keys => Promise.all(
    keys.map(key => key !== CACHE_NAME ? caches.delete(key) : null)
  ))
));
self.addEventListener("fetch", e => {
  e.respondWith(
    caches.match(e.request).then(r => r || fetch(e.request))
  );
});
