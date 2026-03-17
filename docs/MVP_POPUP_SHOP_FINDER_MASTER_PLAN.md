# Pop-Up Shop Finder MCP → Vendor Atlas: MVP Master Plan

**Goal:** Maximum viable product with minimal bugs — consumer-ready Vendor Atlas frontend and a reliable API layer.

**Audience:** Small business vendors, craft sellers, pop-up shop owners. No developer jargon in the UI.

---

## 1. Easiest path: API-related fixes (do these first)

### 1.1 Fix consumer API base URL (frontend-only — no server change)

**Problem:** `site/index.html` uses `CONFIG.API_BASE_URL = '{{API_BASE_URL}}'`. There is no build step or server substitution, so the browser sends requests to the literal string and they fail.

**Easiest fix:** In the frontend, set the base URL at runtime to the same origin when the page is served from the same app:

- In `site/index.html`, replace the single line that sets `API_BASE_URL` with logic that uses `window.location.origin` (e.g. `''` or `window.location.origin`) so that requests go to `/consumer/run` on the same host.
- Optional: if the page is ever served from a different host (e.g. static CDN), you can later add a small `/api/config` or `/config.json` that returns `{ "api_base_url": "https://api.example.com" }` and have the frontend fetch that first; for MVP, same-origin is enough.

**Result:** When you open `http://localhost:3000/`, “Find Markets”, “Save my profile”, and “Help me choose” all hit `http://localhost:3000/consumer/run` and work.

---

### 1.2 Server: return `ok: false` when a tool throws

**Problem:** When a tool handler raises an exception, the billing middleware catches it and returns `{"content": [{"type": "text", "text": "Error: ..."}]}`. The server still returns `{"ok": true, "result": "Error: ..."}`. The frontend then does `JSON.parse(data.result)`, which fails on the string `"Error: ..."`, and either throws or falls back to empty data, so the user sees “No markets found” or a generic failure instead of the real error.

**Easiest fix:** In `server.py`, in `handle_consumer_run`, after calling `billing_middleware`:

- If `result.get("content", [{}])[0].get("text", "").strip().startswith("Error:")`, return a JSON response with `ok: false` and `error: <message>` (e.g. the text after `"Error: "`) and use status 500 or 200 with `ok: false`.
- Optionally, have the billing middleware itself return a structured `{"error": "..."}` when the handler raises, and then the server can just check `if "error" in result` (already done for billing errors) and return that to the client. So the minimal change is: in the billing middleware, when an exception is caught, return `{"error": error_msg}` in the same shape as other billing errors so the existing `if "error" in result: return web.json_response(result, status=400)` in `handle_consumer_run` sends a proper error to the frontend.

**Result:** Frontend receives `{ ok: false, error: "..." }` and can show a friendly message instead of wrong “No markets found” or a parse error.

---

### 1.3 Frontend: handle API errors and non-JSON results

**Problem:** Some code paths assume `data.result` is always valid JSON. When the server returns an error string in `result` or `ok: false`, the UI should show a clear, friendly message.

**Easiest fix:**

- For every `fetch(...).then(res => res.json()).then(data => ...)` that calls the consumer API:
  - If `!data.ok`, use `data.error` (or `data.message` or fallback “Something went wrong”) and display it in the UI (e.g. `results-summary`, `quiz-error`, or a small toast), and do not call `JSON.parse(data.result)`.
  - When parsing `data.result`, keep the existing `try { payload = JSON.parse(data.result || '{}') } catch (_e) { payload = {} }` and, in the catch or when the parsed value looks like an error string, set a user-visible error message instead of silently showing empty state.

**Result:** Users see “We couldn’t load that right now. Please try again.” (or the actual server message) instead of blank or misleading text.

---

### 1.4 Apply button: use `apply_url` from API

**Problem:** Backend already returns `apply_url` per market (`storage_markets.Market.apply_url`, exposed in `get_markets()`). The frontend ignores it and shows an alert.

**Easiest fix:**

- In the market card template and “Apply” handlers (sample, search results, saved list, and later “View Details” modal), use the market’s `apply_url` (or `application_url` if you ever alias it). If present, open it in a new tab (`window.open(m.apply_url, '_blank')`). If missing, show a short message like “Application link isn’t available for this market yet.”
- When saving a favorite, store the full market object (or at least `apply_url`) so “Apply” from the saved list can open the link too.

**Result:** “Apply” works whenever the backend has an application link; no backend change required.

---

### 1.5 Distance radius filter (backend optional for MVP)

**Problem:** The dashboard has a “Distance radius” dropdown (10/25/50/100 miles), but `search_markets` and `get_markets()` do not accept or use radius. So the filter has no effect.

**Easiest options:**

- **A (MVP):** Leave the UI as-is. Optionally pass `radius_miles` in the request body so the backend can ignore it without error. Add a small note in the UI: “Distance filter coming soon” so users don’t expect it to work. No backend change.
- **B (later):** Add optional `radius_miles` and geocode city to lat/lon (or store lat/lon per market), then filter markets by distance in `get_markets()`. More work; not required for MVP.

**Recommendation:** Use option A in the sprint; add a single task “Distance radius: pass from UI and document as coming soon” so the API is ready when you implement B.

---

## 2. Bugs to fix (in order)

### 2.1 Config.py duplicate class and broken `from_env`

**Problem:** `config.py` defines `ServerConfig` twice. The second definition overwrites the first. The second class’s `from_env()` passes keyword arguments (`signal_capture_enabled`, `serper_api_key`, etc.) that the second class does not define, which can cause `TypeError` when `get_config()` runs.

**Fix:** Keep a single `ServerConfig` class with all required fields (port, host, auth_token, transport, signal_capture_enabled, signal_log_path, serper_api_key, etc.) and one `from_env()` that sets them from the environment. Use `@dataclass` if you want, and ensure every keyword passed in `from_env()` is a field on that class.

---

### 2.2 Billing middleware: return structured error when handler raises

**Problem:** When a tool raises, the middleware returns `{"content": [{"type": "text", "text": "Error: ..."}]}`. The HTTP consumer path then treats that as success and returns `ok: true, result: "Error: ..."`.

**Fix:** In `billing.py`, in the middleware’s `except` block, return the same shape as other errors, e.g. `return {"error": {"code": -32003, "message": error_msg}}` (or a simple `{"error": error_msg}` if the server expects that). Then `handle_consumer_run`’s existing `if "error" in result: return web.json_response(result, status=400)` will send a proper error body. Ensure the frontend reads `data.error` or `data.error.message` and shows it in the UI.

---

### 2.3 Saved favorites: persist `apply_url` (and useful fields)

**Problem:** When the user clicks “Save Event”, the frontend only stores a minimal object (e.g. id, name, city, state, date). The saved list’s “Apply” button then has no `apply_url` and can only show “link not available.”

**Fix:** When saving a favorite, store the full market object from the card (or at least include `apply_url`, `application_deadline`, and any other fields you show in the detail view). When rendering the saved list and “Apply”, use the stored `apply_url` the same way as in search results.

---

## 3. Backend / API checklist (no UI copy)

- Ensure **billing is off for MVP** (default): `BILLING_ENABLED` is false so anonymous consumer requests are allowed.
- **Consumer run** returns JSON with `ok` and either `result` (string) or `error` (string or object). All tool errors surface as `ok: false` + `error`.
- **search_markets**: Accepts city, state, start_date, end_date, event_size, category, indoor_outdoor; returns `{ markets: [...] }`. Each market includes `apply_url` when present.
- **build_vendor_profile**: Accepts `answers`; returns JSON string with `profile` and optional `summary`.
- **rank_markets_for_vendor**: Accepts `vendor_profile`, `markets`; returns JSON with `ranked_markets` (e.g. `{ market_id, fit_score, fit_label, why }`).
- **compare_markets_for_vendor**: Accepts `vendor_profile`, `markets` (2–5); returns JSON with `recommendation_order` (e.g. `{ market_id, why }`).
- **Database:** `storage_markets` uses `vendor_atlas.db` in the repo root; `init_db()` creates the table if missing. Ensure the process has write permission to that path (or set a path via env) so ingest and future tools don’t fail.

---

## 4. Frontend / UX checklist (Vendor Atlas consumer experience)

- **API base URL:** Set at runtime to same origin (or from a config endpoint).
- **Errors:** Every consumer API call handles `!data.ok` and non-JSON `result`; show a friendly, non-technical message.
- **Buttons:** Rounded rectangle (e.g. `rounded-xl`), lavender primary, white + lavender outline secondary, subtle shadow.
- **Copy:** No MCP, API, SSE, stdio, JSON, or endpoint jargon anywhere the user sees.
- **Hero:** City input + “Find My Next Market” → scroll to dashboard and run search (with hero city pre-filled).
- **Dashboard:** Filters (City, Date range, Event size, Category, Indoor/Outdoor, Distance); “Find Markets” → results as cards; “Saved markets” list; “Help me choose from saved” when profile + 2+ saved.
- **Market cards:** Name, location, date, vendor count, traffic, booth price, application deadline, popularity; “View Details”, “Save Event”, “Apply”. Use `apply_url` for “Apply” when present.
- **View Details:** Modal or expand with same fields + description + Apply (and Save) so users can open the application link from there.
- **Pro pricing:** Replace “$?” with “Coming soon” or a real price; keep “Upgrade to Pro” CTA.
- **Mobile:** Responsive, adequate touch targets, no horizontal scroll.

---

## 5. Recommended order of work

| Phase | What | Why |
|-------|------|-----|
| **1** | Fix API base URL (frontend) | Unblocks all consumer flows with zero server change. |
| **2** | Server + billing: return `ok: false` / structured error when tool throws | Prevents misleading “No results” and parse errors. |
| **3** | Frontend: handle `!data.ok` and show friendly error message everywhere | Good UX and fewer “silent” failures. |
| **4** | Fix `config.py` (single ServerConfig, correct from_env) | Prevents startup/runtime errors in deployment. |
| **5** | Apply button: use `apply_url`; save full market (or apply_url) in favorites | High value for users; backend already supports it. |
| **6** | Design system (buttons, surfaces) + copy audit | Aligns UI with Vendor Atlas spec and removes dev language. |
| **7** | Homepage + dashboard layout and wiring | Makes the product feel complete. |
| **8** | View Details modal; Pro pricing CTA | Polish and clarity. |
| **9** | Mobile pass; distance filter note (“coming soon”) | Final polish and honest expectation-setting. |

---

## 6. Out of scope for MVP (do later)

- Real geocoding and distance-based filtering (radius).
- Billing/Stripe (keep off for MVP).
- MCP/SSE/stdio transport changes (consumer path is HTTP only).
- Authentication for the web app (anonymous usage for MVP).
- Organizer-facing or admin UI.
- Email vendor alerts or “Notify me” for new markets.

---

## 7. Files to touch (summary)

| Area | Files |
|------|--------|
| API base URL | `site/index.html` |
| Server error handling | `server.py`, `billing.py` |
| Frontend error handling | `site/index.html` (all fetch blocks) |
| Apply + favorites | `site/index.html` (card data shape, save payload, Apply handlers) |
| Config bug | `config.py` |
| Design + copy | `site/index.html` (styles, labels, error strings) |
| View Details / Pro | `site/index.html` |
| Distance (optional) | `site/index.html` (optional note), `tools/vendor_atlas_markets.py` (optional param) |

This plan gets the Pop-Up Shop Finder MCP to a maximum viable product as “Vendor Atlas” with minimal bugs, with the easiest API-related fixes called out and ordered first.
