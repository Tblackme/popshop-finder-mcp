# Vendor Atlas

Vendor Atlas is a consumer-friendly market discovery app for vendors, makers, and pop-up sellers. It includes:

- **A single, built-in UI** in [site/](site/) — HTML, CSS, and JS served **by the same MCP server** (no separate frontend app). The canonical color scheme and design are documented in [site/DESIGN.md](site/DESIGN.md).
- A FastAPI MCP server in [server.py](server.py) that serves both the app and MCP/API routes.
- tool handlers for profile building, market search, ranking, and compare flows in [tools](/c:/Users/lizbl/Documents/GitHub/popshop-finder-mcp/tools)
- local SQLite-backed market storage in [storage_markets.py](/c:/Users/lizbl/Documents/GitHub/popshop-finder-mcp/storage_markets.py)
- local SQLite-backed event storage in [storage_events.py](/c:/Users/lizbl/Documents/GitHub/popshop-finder-mcp/storage_events.py)

## Local Setup

Create and activate a virtual environment, then install the project with dev dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

If you only want runtime dependencies, use:

```bash
python -m pip install -r requirements.txt
```

Optional: copy `.env.example` to `.env` if you want to override defaults.

## Run The App

Start the local server:

```bash
python server.py
```

The app will be available at:

```text
http://localhost:3000/
```

Useful endpoints:

- `GET /` landing page + consumer dashboard
- `GET /health` health check with version, protocol, tool count, and SSE client count
- `GET /config.json` runtime config for API base and product flags
- `GET /markets/search` canonical frontend-ready stored event search
- `GET /consumer/tools` browser-friendly tool listing with names, descriptions, and input schemas
- `POST /consumer/run` browser-friendly tool execution

## Render + Doppler + Supabase

Deployment scaffolding for Render and secret setup notes for Doppler/Supabase are in:

- [render.yaml](/c:/Users/lizbl/Documents/GitHub/popshop-finder-mcp/render.yaml)
- [docs/RENDER_DOPPLER_SUPABASE_SETUP.md](/c:/Users/lizbl/Documents/GitHub/popshop-finder-mcp/docs/RENDER_DOPPLER_SUPABASE_SETUP.md)
- [doppler.yaml.example](/c:/Users/lizbl/Documents/GitHub/popshop-finder-mcp/doppler.yaml.example)

Important: the app can deploy on Render now, but it still uses the current local storage modules until a separate Supabase/Postgres migration is completed.

## MCP Backend

Vendor Atlas now exposes a six-tool MCP pipeline:

- `discover_events`
- `extract_event`
- `enrich_event`
- `score_event`
- `save_event`
- `search_events`

Backend and tool documentation:

- [docs/VENDOR_ATLAS_MCP.md](/c:/Users/lizbl/Documents/GitHub/popshop-finder-mcp/docs/VENDOR_ATLAS_MCP.md)
- [docs/example_mcp_tools.json](/c:/Users/lizbl/Documents/GitHub/popshop-finder-mcp/docs/example_mcp_tools.json)
- [docs/QA_CHECKLIST.md](/c:/Users/lizbl/Documents/GitHub/popshop-finder-mcp/docs/QA_CHECKLIST.md)
- [docs/CLAUDE_LAUNCH_CHECKLIST.md](/c:/Users/lizbl/Documents/GitHub/popshop-finder-mcp/docs/CLAUDE_LAUNCH_CHECKLIST.md)
- [docs/MVP_POPUP_SHOP_FINDER_MASTER_PLAN.md](/c:/Users/lizbl/Documents/GitHub/popshop-finder-mcp/docs/MVP_POPUP_SHOP_FINDER_MASTER_PLAN.md) historical MVP planning notes from the earlier Pop-Up Shop Finder phase

## Shopify integration (Connect My Store)

Users can connect a Shopify store so Vendor Atlas can use real products and inventory to power:

- **What to bring** — top products by stock
- **Profit estimate** — range based on inventory and prices
- **Inventory check** — low-stock warnings

### Setup

1. Create a Shopify app at [partners.shopify.com](https://partners.shopify.com) (Development store or custom app).
2. In the app’s **App setup**: set **App URL** to your app’s base URL (e.g. `https://yourdomain.com` or `http://localhost:3001` for local dev). Set **Allowed redirection URL(s)** to `{APP_URL}/api/shopify/callback`.
3. In **Configuration** → **Admin API integration**, enable **Read products** and **Read inventory** (scopes: `read_products`, `read_inventory`). Copy the **Client ID** and **Client secret**.
4. In `.env` (see [.env.example](.env.example)) set:
   - `SHOPIFY_API_KEY` = Client ID  
   - `SHOPIFY_API_SECRET` = Client secret  
   - `APP_BASE_URL` = same as App URL (e.g. `http://localhost:3001` if you run on 3001)

### Flow

- User signs in, goes to **Profit** (Final Plan), and in the sidebar enters their store name (e.g. `mystore`) and clicks **Connect**.
- They are sent to Shopify to approve; after approval they are redirected back and products/inventory are synced.
- **Sync products** re-fetches from Shopify; **Disconnect** removes the connection and cached products.

Backend: [shopify_oauth.py](shopify_oauth.py) (OAuth + Admin API), [storage_shopify.py](storage_shopify.py) (tokens and product cache in SQLite).

## Docker

Build and run with Docker:

```bash
docker build -t vendor-atlas-mcp .
docker run --rm -p 3000:3000 vendor-atlas-mcp
```

Or use Compose:

```bash
docker compose up --build
```

## Validate Changes

Run the test suite:

```bash
python -m pytest
```

Run the smoke tests added for consumer flows only:

```bash
python -m pytest tests/test_consumer_flows.py -q
```

Run the browser smoke suite:

```bash
npm run test:smoke
```

Useful Playwright outputs:

- `playwright-report/` HTML report
- `test-results/playwright/` traces, screenshots, and per-test smoke logs for routes, buttons, and API checks

Run lint:

```bash
python -m ruff check .
```

## Current Test Note

If `python -m pytest` fails with `No module named pytest`, install the dev dependencies first:

```bash
python -m pip install -e ".[dev]"
```

## Data + Storage

- Market data is stored in `vendor_atlas.db` in the repo root by default.
- Fresh local setups automatically seed a bundled demo dataset if the markets table is empty.
- The `events` table is also auto-seeded from the bundled demo dataset for FastAPI/MCP event workflows.
- Billing and usage state can write to environment-configured paths.
- Distance radius is accepted by the API for MVP, but geographic filtering is still a future enhancement.
- Optional env vars:
  - `VENDOR_ATLAS_DB_PATH`
  - `VENDOR_ATLAS_DEMO_DATA_PATH`
  - `SERVER_HOST`
  - `SERVER_PORT`

## Project Structure

- [server.py](server.py): app entrypoint; serves the **built-in UI** from `site/` and all HTTP/MCP routes
- [billing.py](billing.py): billing/error middleware and endpoints
- [config.py](config.py): environment-driven config
- [site/](site/): **canonical Vendor Atlas UI** (landing, discover, dashboard, find-market, etc.). Served at `/`, `/discover`, `/dashboard`, etc. Official colors and design: [site/DESIGN.md](site/DESIGN.md)
- [storage_events.py](/c:/Users/lizbl/Documents/GitHub/popshop-finder-mcp/storage_events.py): event storage for discovered markets and MCP workflows
- [tools/vendor_atlas_markets.py](/c:/Users/lizbl/Documents/GitHub/popshop-finder-mcp/tools/vendor_atlas_markets.py): legacy-compatible `search_markets` wrapper
- [tools/vendor_atlas_pipeline.py](/c:/Users/lizbl/Documents/GitHub/popshop-finder-mcp/tools/vendor_atlas_pipeline.py): canonical six-tool event discovery pipeline
- [tools/vendor_atlas_profile.py](/c:/Users/lizbl/Documents/GitHub/popshop-finder-mcp/tools/vendor_atlas_profile.py): vendor profile tool
- [tools/vendor_atlas_scoring.py](/c:/Users/lizbl/Documents/GitHub/popshop-finder-mcp/tools/vendor_atlas_scoring.py): ranking and compare tools
- [tests/test_consumer_flows.py](/c:/Users/lizbl/Documents/GitHub/popshop-finder-mcp/tests/test_consumer_flows.py): smoke tests for core flows
- [sprints/ACTIVE_SPRINT.toml](/c:/Users/lizbl/Documents/GitHub/popshop-finder-mcp/sprints/ACTIVE_SPRINT.toml): current sprint plan

## Notes

- Billing is off by default for the current MVP flow.
- The dashboard search flow should use `GET /markets/search`; `POST /consumer/run` remains in use for profile, ranking, compare, and other tool-driven actions.
- `search_markets` remains available as a compatibility wrapper, but the forward path is `search_events` plus `GET /markets/search`.
- The repo still contains MCP/SSE support for broader integrations, but the main product experience is the browser dashboard.
