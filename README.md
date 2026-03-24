# Vendor Atlas

Vendor Atlas is a market discovery and community platform for vendors, makers, pop-up sellers, shoppers, and market organizers. It is a full-stack web app served from a single FastAPI server with no separate frontend build step.

## What's Inside

### Roles & Dashboards

- **Vendors** — apply to markets, manage a shop profile, track events, import inventory, connect Shopify
- **Shoppers** — discover vendors and markets, RSVP to events, follow vendors
- **Market Organizers** — manage listings, review vendor applications, view analytics
- **Admins** — user management, vendor verification queue, feature flags

Each role gets a purpose-built dashboard under [site/](site/) served at its own route.

### Core Features

| Feature | Files |
|---|---|
| Multi-step signup + sign-in | [site/signup.html](site/signup.html), [site/signin.html](site/signin.html) |
| Role-based dashboards | [site/dashboard.html](site/dashboard.html), [site/shopper-dashboard.html](site/shopper-dashboard.html), [site/market-dashboard.html](site/market-dashboard.html) |
| Vendor shop profiles | [site/my-shop.html](site/my-shop.html), [site/vendor-shop.html](site/vendor-shop.html) |
| Vendor discovery | [site/vendor-discovery.html](site/vendor-discovery.html) |
| Market search + RSVP | [site/find-market.html](site/find-market.html), [site/event.html](site/event.html) |
| TikTok-style social feed | [site/feed.html](site/feed.html), [storage_feed.py](storage_feed.py) |
| Discord-style community rooms | [site/community.html](site/community.html), [site/community-room.html](site/community-room.html), [storage_community.py](storage_community.py) |
| Direct + group messaging | [site/messages.html](site/messages.html), [storage_messages.py](storage_messages.py) |
| Vendor verification | [site/vendor-verify.html](site/vendor-verify.html), [site/admin-verify.html](site/admin-verify.html) |
| Marketplace listings | [site/listings.html](site/listings.html), [storage_marketplace.py](storage_marketplace.py) |
| Market applications | [site/market-applications.html](site/market-applications.html) |
| Market analytics | [site/market-analytics.html](site/market-analytics.html) |
| Profit planner + final plan | [site/profit.html](site/profit.html), [site/final-plan.html](site/final-plan.html) |
| CSV inventory import | [site/integrations.html](site/integrations.html) (Etsy, Square, WooCommerce, etc.) |
| Shopify OAuth + product sync | [shopify_oauth.py](shopify_oauth.py), [storage_shopify.py](storage_shopify.py) |
| Admin panel | [site/admin.html](site/admin.html), [site/admin-users.html](site/admin-users.html) |
| Feature flags | [features/flags.py](features/flags.py) |

### Backend Modules

| Module | Purpose |
|---|---|
| [server.py](server.py) | App entrypoint — all HTTP routes, MCP/SSE, file serving |
| [storage_users.py](storage_users.py) | Auth, user records, roles, availability, verification |
| [storage_marketplace.py](storage_marketplace.py) | Listings, applications, marketplace data |
| [storage_events.py](storage_events.py) | Market events, RSVPs, MCP pipeline events |
| [storage_markets.py](storage_markets.py) | Curated market data |
| [storage_feed.py](storage_feed.py) | Vendor social posts and feed |
| [storage_community.py](storage_community.py) | Community groups, channels, live rooms |
| [storage_messages.py](storage_messages.py) | Direct and group conversations |
| [storage_ai.py](storage_ai.py) | AI chat and AI-generated content |
| [storage_shopify.py](storage_shopify.py) | Shopify tokens and product cache |
| [billing.py](billing.py) | Billing middleware and endpoints |
| [config.py](config.py) | Environment-driven config |
| [db_runtime.py](db_runtime.py) | SQLite / Postgres connection abstraction |

### MCP Pipeline

Vendor Atlas exposes a six-tool MCP event-discovery pipeline:

- `discover_events`
- `extract_event`
- `enrich_event`
- `score_event`
- `save_event`
- `search_events`

See [docs/VENDOR_ATLAS_MCP.md](docs/VENDOR_ATLAS_MCP.md) for full documentation.

---

## Local Setup

Create and activate a virtual environment, then install the project with dev dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

For runtime dependencies only:

```bash
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` to configure secrets and overrides.

## Run The App

```bash
python server.py
```

The app is available at `http://localhost:3000/`.

### Key Routes

| Route | Description |
|---|---|
| `GET /` | Landing page |
| `GET /dashboard` | Vendor dashboard |
| `GET /shopper-dashboard` | Shopper dashboard |
| `GET /market-dashboard` | Organizer dashboard |
| `GET /admin` | Admin panel |
| `GET /feed` | Social feed |
| `GET /community` | Community rooms |
| `GET /messages` | Messaging |
| `GET /health` | Health check with version and tool count |
| `GET /config.json` | Runtime config |
| `GET /markets/search` | Market/event search |
| `POST /consumer/run` | MCP tool execution |

---

## Shopify Integration

Users can connect a Shopify store to power **What to Bring**, **Profit Estimate**, and **Inventory Check** features.

### Setup

1. Create a Shopify app at [partners.shopify.com](https://partners.shopify.com).
2. Set **App URL** to your base URL; set **Allowed redirection URL(s)** to `{APP_URL}/api/shopify/callback`.
3. Enable `read_products` and `read_inventory` scopes. Copy **Client ID** and **Client secret**.
4. In `.env` set `SHOPIFY_API_KEY`, `SHOPIFY_API_SECRET`, and `APP_BASE_URL`.

Backend: [shopify_oauth.py](shopify_oauth.py), [storage_shopify.py](storage_shopify.py).

---

## Deployment (Render + Doppler + Supabase)

- [render.yaml](render.yaml)
- [docs/RENDER_DOPPLER_SUPABASE_SETUP.md](docs/RENDER_DOPPLER_SUPABASE_SETUP.md)
- [.env.render.example](.env.render.example)

The app deploys on Render using SQLite by default. Supabase/Postgres migration is optional via `DATABASE_URL`.

---

## Docker

```bash
docker build -t vendor-atlas-mcp .
docker run --rm -p 3000:3000 vendor-atlas-mcp
```

Or with Compose:

```bash
docker compose up --build
```

---

## Testing

Run the full test suite:

```bash
python -m pytest
```

Run consumer flow smoke tests only:

```bash
python -m pytest tests/test_consumer_flows.py -q
```

Run browser smoke tests (Playwright):

```bash
npm run test:smoke
```

Reports: `playwright-report/` and `test-results/playwright/`.

Run lint:

```bash
python -m ruff check .
```

If `pytest` is missing, install dev deps first: `python -m pip install -e ".[dev]"`.

---

## Data & Storage

- Primary DB: `vendor_atlas.db` (SQLite, repo root by default)
- Session/auth state: `popshop.db`
- Fresh installs auto-seed demo market and event data
- Postgres supported via `DATABASE_URL` env var

Optional env vars:

| Var | Purpose |
|---|---|
| `VENDOR_ATLAS_DB_PATH` | Override SQLite path |
| `VENDOR_ATLAS_DEMO_DATA_PATH` | Override demo seed data path |
| `SERVER_HOST` | Bind host (default `0.0.0.0`) |
| `SERVER_PORT` | Bind port (default `3000`) |
| `DATABASE_URL` | Postgres connection string |

---

## Design

Official colors, typography, and UI patterns: [site/DESIGN.md](site/DESIGN.md).
