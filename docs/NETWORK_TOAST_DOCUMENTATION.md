# EduDrop — Network Status Toast Documentation

## Overview

EduDrop displays a real-time toast notification at the bottom of every page that alerts users when they go offline or come back online. This provides immediate visual feedback about connectivity status, which is critical for a school/NGO tool where users may be in areas with unreliable internet.

- **Offline:** A grey toast appears saying "You are offline" and stays visible until connectivity is restored
- **Online:** A green toast appears saying "You are back online", auto-dismisses after 3 seconds, and the page reloads with fresh data

---

## How It Works

### Connectivity Detection

The toast uses a **client-side image-based ping** to detect connectivity. Every 15 seconds, it tries to load Google's favicon:

```javascript
var img = new Image();
img.src = 'https://www.google.com/favicon.ico?_=' + Date.now();
```

| Event | Meaning |
|-------|---------|
| `img.onload` fires | Internet is reachable → user is online |
| `img.onerror` fires | Image failed to load → user is offline |
| 4-second timeout | No response in time → user is offline |

The `?_=` cache-buster query parameter ensures each check makes a fresh request and doesn't return a cached image.

### Why Not `navigator.onLine`?

The `navigator.onLine` browser API was tested first but proved unreliable — it reports `true` when the local Flask server (`127.0.0.1`) is reachable, even if there is no actual internet connection. The image-based approach checks real internet connectivity by hitting an external resource (Google's favicon).

### Why Not a Server-Side Ping?

A `/api/ping` endpoint was also tried, but it had issues:
- When the server itself was unreachable (offline), the ping would fail with a network error rather than returning a meaningful response
- The Flask app has two `app = Flask(__name__)` initializations — routes registered before the second one were lost, causing 404 errors
- A pure client-side approach is simpler and more reliable since it doesn't depend on the Flask server being operational

---

## Toast Behavior

### State Machine

```
Page Load → checkNet()
                ↓
        ┌── Online ──┐
        │  (no toast) │
        └─────────────┘
                ↓ (network lost)
        ┌── Offline ─────────────────┐
        │  Grey toast: "You are      │
        │  offline" (stays visible)  │
        └────────────────────────────┘
                ↓ (network restored)
        ┌── Back Online ─────────────┐
        │  Green toast: "You are     │
        │  back online" (3s dismiss) │
        │  Page reloads after 2s     │
        └────────────────────────────┘
```

### Key Behaviors

| Scenario | What Happens |
|----------|-------------|
| Page loads while online | No toast shown (silent) |
| Page loads while offline | Grey "You are offline" toast appears immediately |
| Connection drops while browsing | Grey toast appears within 15 seconds (next poll) |
| Connection restored | Green toast appears, page auto-reloads after 2 seconds |
| Intermittent connection | Toast toggles only on state change (no duplicate toasts) |

### Deduplication

The `wasOffline` flag prevents duplicate toasts:
- `goOffline()` only triggers if `wasOffline` is `false`
- `goOnline()` only triggers if `wasOffline` is `true`
- This ensures the toast only appears on state transitions, not on every poll cycle

---

## Visual Design

### Offline Toast (Grey)
- **Background:** `#6b7280` (neutral grey)
- **Icon:** `bi-wifi-off` (Bootstrap Icons)
- **Text:** "You are offline"
- **Auto-hide:** No — stays visible until connection is restored
- **Position:** Fixed, bottom center of screen

### Online Toast (Green)
- **Background:** `#22c55e` (success green)
- **Icon:** `bi-wifi` (Bootstrap Icons)
- **Text:** "You are back online"
- **Auto-hide:** Yes — disappears after 3 seconds
- **Action:** Page reloads automatically after 2 seconds to fetch fresh data

### Animation
- Slides up from below the viewport using `translateY(100px) → translateY(0)`
- Uses CSS transition: `transform 0.4s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.4s`
- Shadow: `0 4px 20px rgba(0,0,0,0.15)` for elevation effect
- Border radius: `12px` for rounded appearance

---

## Pages Covered

The toast is included on **every page** via a reusable Jinja2 partial:

```html
{% include 'partials/network_toast.html' %}
```

| Template | Pages It Covers |
|----------|----------------|
| `base.html` | All dashboard pages (student, teacher, principal, volunteer, admin) |
| `index.html` | Public homepage |
| `base_auth.html` | Login and registration pages |
| `select_role.html` | Role selection page |
| `ngo_role.html` | NGO portal (volunteer/admin selection) |
| `offline.html` | Offline fallback page |

This ensures consistent network status feedback regardless of which page the user is on.

---

## Polling Configuration

| Setting | Value | Reason |
|---------|-------|--------|
| Poll interval | 15 seconds | Balances responsiveness with resource usage |
| Timeout per check | 4 seconds | Long enough for slow connections, short enough for quick detection |
| Initial check | On page load | Immediate status detection |
| Browser events | `online` / `offline` listeners | Instant detection when browser detects change |

The browser `offline` event triggers `goOffline()` immediately (no wait for next poll). The `online` event triggers `checkNet()` to verify actual internet connectivity before showing the green toast.

---

## Files Involved

| File | Location | Purpose |
|------|----------|---------|
| `network_toast.html` | `templates/partials/network_toast.html` | The reusable toast partial (HTML + CSS + JS) |
| `base.html` | `templates/base.html` | Includes toast for all dashboard pages |
| `index.html` | `templates/index.html` | Includes toast for homepage |
| `base_auth.html` | `templates/base_auth.html` | Includes toast for auth pages |
| `select_role.html` | `templates/select_role.html` | Includes toast for role selection |
| `ngo_role.html` | `templates/ngo_role.html` | Includes toast for NGO portal |
| `offline.html` | `templates/offline.html` | Includes toast for offline fallback |

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Google's favicon server is down | Toast may incorrectly show "offline" — extremely rare since Google has 99.99% uptime |
| Very slow connection (>4s for a 1KB favicon) | Treated as offline — the 4-second timeout errs on the side of caution |
| JavaScript disabled | Toast won't appear — no fallback needed since the app itself requires JS |
| Multiple tabs open | Each tab runs its own polling independently |

---

## How to Test

1. Open the app in Chrome
2. Open DevTools → **Network** tab
3. Toggle **Offline** mode → grey toast should appear within a few seconds
4. Toggle back to **Online** → green toast should appear and page reloads
5. Alternatively, disconnect from WiFi for a real-world test
6. Check the **Console** tab — no errors should appear during toast transitions
