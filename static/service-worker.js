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

// Fetch: cache static assets only, let pages go to network naturally
self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);

  // Skip non-GET requests
  if (e.request.method !== "GET") return;

  // Skip /api/, /logout, /export* — go straight to Flask (no caching)
  if (url.pathname.startsWith("/api/")) return;
  if (url.pathname.startsWith("/export")) return;
  if (url.pathname === "/logout") return;

  // For HTML pages — always go to network, let browser show default error if offline
  if (e.request.mode === "navigate" ||
      (e.request.headers.get("accept") && e.request.headers.get("accept").includes("text/html"))) {
    return;
  }

  // For static assets — cache first, then network
  e.respondWith(
    caches.match(e.request).then(cached => {
      if (cached) return cached;
      return fetch(e.request).then(resp => {
        if (resp.ok) {
          const clone = resp.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(e.request, clone));
        }
        return resp;
      }).catch(() => new Response("", { status: 408 }));
    })
  );
});
