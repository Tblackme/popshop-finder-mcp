# Vendor Atlas Sprint — Next Steps

**Full in-depth plan:** See **`docs/MVP_POPUP_SHOP_FINDER_MASTER_PLAN.md`** for the complete MVP plan, API vs other fixes, and bug list.

## Review summary

- **Frontend**: `site/index.html` is already the Vendor Atlas consumer UI (hero, features, sample markets, pricing, dashboard, vendor quiz, footer). No MCP/SSE/stdio or developer jargon in the UI.
- **Backend**: `server.py` serves the site and exposes `/consumer/run` for tools. Storage returns `apply_url` per market; billing is off by default so anonymous consumer requests work.
- **Gaps**: API base URL literal `{{API_BASE_URL}}`; server returns `ok: true` when tools throw (frontend then sees wrong/empty state); config.py duplicate class; Apply/favorites don’t use `apply_url`; design/copy/polish per spec.

## Recommended order (matches sprint phases)

**Phase 1 — API (easiest first)**  
1. **VA-001** — Fix API base URL (frontend same-origin).  
2. **API-001** — Server + billing return `ok: false` when tool throws.  
3. **API-002** — Frontend handle `!data.ok` and friendly error messages.  
4. **BUG-001** — Fix config.py duplicate ServerConfig.

**Phase 2 — Design and copy**  
5. **VA-002** — Design system (buttons, surfaces).  
6. **VA-003** — Copy audit (consumer language only).

**Phase 3 — Dashboard and apply**  
7. **VA-005** — Dashboard (search, results, saved markets).  
8. **VA-009** — Apply button + save `apply_url` in favorites.  
9. **VA-008** — View Details modal.  
10. **VA-004** — Homepage layout.  
11. **VA-006** — Pro pricing CTA.  
12. **VA-007** — Mobile responsive.  
13. **API-003** — Distance radius (optional: pass from UI, “coming soon” note).

## Quick start

1. Open `sprints/ACTIVE_SPRINT.toml` in ÆtherLight (Sprint tab).  
2. Do **VA-001** → **API-001** → **API-002** → **BUG-001** first (API + one bug).  
3. Then **VA-002**, **VA-003**, **VA-005**, **VA-009**, **VA-008**, **VA-004**, **VA-006**, **VA-007**, **API-003** as dependencies allow.

## Files to touch

- **site/index.html** — API base URL, error handling, apply_url, design, copy.  
- **server.py** — Optional: ensure error response shape includes `ok: false` when billing returns error.  
- **billing.py** — Return structured `error` when handler throws.  
- **config.py** — Single ServerConfig, correct from_env.  
- **tools/vendor_atlas_markets.py** — Optional: accept radius_miles (API-003).
