const CACHE_NAME = "edudrop-v2";

// Static assets to pre-cache on install
const PRECACHE = [
  "/static/css/main.css",
  "/static/manifest.json",
  "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css",
  "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css",
  "https://cdn.jsdelivr.net/npm/chart.js"
];

// Install: pre-cache static assets
self.addEventListener("install", e => {
  e.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(PRECACHE))
  );
  self.skipWaiting();
});

// Activate: clean old caches
self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.map(key => key !== CACHE_NAME ? caches.delete(key) : null))
    )
  );
  self.clients.claim();
});

// Fetch: network-first for pages, cache-first for static assets
self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);

  // Skip non-GET requests (POST to /api/chat, form submissions, etc.)
  if (e.request.method !== "GET") return;

  // For API routes — network only, don't cache
  if (url.pathname.startsWith("/api/")) return;

  // For HTML pages — network first, fall back to cache
  if (e.request.headers.get("accept") && e.request.headers.get("accept").includes("text/html")) {
    e.respondWith(
      fetch(e.request)
        .then(resp => {
          const clone = resp.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(e.request, clone));
          return resp;
        })
        .catch(() => caches.match(e.request).then(r => r || caches.match("/offline")))
    );
    return;
  }

  // For static assets (CSS, JS, fonts, images) — cache first, then network
  e.respondWith(
    caches.match(e.request).then(cached => {
      if (cached) return cached;
      return fetch(e.request).then(resp => {
        const clone = resp.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(e.request, clone));
        return resp;
      });
    })
  );
});
