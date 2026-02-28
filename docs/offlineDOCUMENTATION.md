# EduDrop — Offline Support Documentation

## Overview

EduDrop works offline using a **Progressive Web App (PWA)** setup. Once a user visits any page while online, that page is automatically cached and can be viewed later without an internet connection. This is powered by a **Service Worker** — a background script that intercepts network requests and serves cached content when the network is unavailable.

---

## How It Works

### 1. Service Worker Registration

When any page loads, the browser registers the Service Worker from `/sw.js`:

```js
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js');
}
```

This runs in:
- `templates/base.html` — covers all dashboard pages (student, teacher, principal)
- `templates/index.html` — covers the public homepage

The Flask route `/sw.js` in `app.py` serves the file from `static/service-worker.js` with the correct `Service-Worker-Allowed: /` header so it has scope over the entire site.

### 2. Caching Strategies

The Service Worker uses different strategies depending on the type of content:

| Content Type | Strategy | How It Works |
|-------------|----------|-------------|
| **HTML pages** (dashboards, records, etc.) | Network-first | Tries to fetch from the server first. If successful, caches the response for offline use. If the network fails, serves the cached version. |
| **Static assets** (CSS, JS, fonts, images) | Cache-first | Checks the cache first for instant loading. If not found in cache, fetches from the network and caches it for next time. |
| **API calls** (`/api/chat`, etc.) | Network only | Not cached. The chatbot and data APIs require a live connection. |
| **Non-GET requests** (form submissions, POST) | Pass-through | Not intercepted. These always go to the server. |

### 3. Pre-cached Assets

When the Service Worker is first installed, it pre-caches these critical assets so they're available immediately:

- `/static/css/main.css` — main stylesheet
- `/static/manifest.json` — PWA manifest
- Bootstrap CSS (`cdn.jsdelivr.net/npm/bootstrap@5.3.3`)
- Bootstrap Icons (`cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3`)
- Chart.js (`cdn.jsdelivr.net/npm/chart.js`)

### 4. Offline Fallback Page

If a user navigates to a page they haven't visited before while offline (so it's not in the cache), they see a friendly offline fallback page at `/offline` instead of the browser's default error. This page:

- Tells the user they're offline
- Explains that previously visited pages are still available
- Provides a "Try Again" button to reload when back online

---

## Files Involved

| File | Location | Purpose |
|------|----------|---------|
| `service-worker.js` | `static/service-worker.js` | The Service Worker script — handles caching logic |
| `manifest.json` | `static/manifest.json` | PWA manifest — app name, theme color, icons, display mode |
| `offline.html` | `templates/offline.html` | Offline fallback page shown for uncached pages |
| `base.html` | `templates/base.html` | Registers the SW + links the manifest (all dashboard pages) |
| `index.html` | `templates/index.html` | Registers the SW (homepage) |
| `app.py` | Root | Flask routes: `/sw.js` serves the SW from root, `/offline` renders the fallback page |

---

## Service Worker Lifecycle

1. **Install** — Downloads and caches the pre-cached assets listed above. Calls `skipWaiting()` to activate immediately.
2. **Activate** — Cleans up old cache versions (any cache not matching the current `CACHE_NAME`). Calls `clients.claim()` to take control of all pages.
3. **Fetch** — Intercepts every network request and applies the appropriate caching strategy (network-first for HTML, cache-first for assets).

### Cache Versioning

The cache is named `edudrop-v2`. When the Service Worker is updated (e.g., new assets to cache), the version name is changed. On activation, old caches with different names are automatically deleted.

---

## PWA Manifest

The `manifest.json` allows the app to be installed on mobile/desktop as a standalone app:

```json
{
  "name": "EduDrop - Student Dropout Prevention",
  "short_name": "EduDrop",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#0f0a2c",
  "theme_color": "#e72191",
  "icons": [{ "src": "/static/icons/s1.png", "sizes": "192x192", "type": "image/png" }]
}
```

---

## What Works Offline

| Feature | Offline? | Notes |
|---------|----------|-------|
| Viewing previously visited dashboards | Yes | All HTML, CSS, JS, charts are cached |
| Viewing student records | Yes | If the page was visited while online |
| Viewing leave requests | Yes | Cached page shows last-known data |
| Homepage | Yes | Pre-cached on first visit |
| AI Chatbot | No | Requires live API call to Gemini |
| Submitting forms (add student, leave, etc.) | No | Requires server connection |
| Login | No | Requires Supabase authentication |

---

## How to Test

1. Open the app and visit the pages you want available offline (e.g., teacher dashboard, student records)
2. Open DevTools > **Application** > **Service Workers** — confirm `sw.js` is registered and active
3. Open DevTools > **Application** > **Cache Storage** — you'll see `edudrop-v2` with cached pages and assets
4. Toggle **Offline** mode in DevTools > **Network** tab
5. Refresh the pages you visited — they should load from cache with all data and charts intact
6. Visit a page you haven't been to — you'll see the "You're Offline" fallback page
