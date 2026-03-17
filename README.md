# Vendor Atlas

Vendor Atlas is a consumer-friendly market discovery app for vendors, makers, and pop-up sellers. It includes:

- a browser-facing dashboard in [site/index.html](/c:/Users/lizbl/Documents/GitHub/popshop-finder-mcp/site/index.html)
- a FastAPI MCP server in [server.py](/c:/Users/lizbl/Documents/GitHub/popshop-finder-mcp/server.py)
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

- [server.py](/c:/Users/lizbl/Documents/GitHub/popshop-finder-mcp/server.py): app entrypoint and HTTP/MCP routes
- [billing.py](/c:/Users/lizbl/Documents/GitHub/popshop-finder-mcp/billing.py): billing/error middleware and endpoints
- [config.py](/c:/Users/lizbl/Documents/GitHub/popshop-finder-mcp/config.py): environment-driven config
- [site/index.html](/c:/Users/lizbl/Documents/GitHub/popshop-finder-mcp/site/index.html): Vendor Atlas frontend
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
