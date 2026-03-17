# Vendor Atlas MCP Backend

Vendor Atlas ships with a FastAPI app plus MCP-style tool endpoints for event discovery, extraction, enrichment, scoring, storage, and search.

## Transports

- HTTP app: [server.py](/c:/Users/lizbl/Documents/GitHub/popshop-finder-mcp/server.py)
- SSE transport: `GET /sse`
- MCP message routes: `POST /message` and `POST /messages`
- Stdio transport: `python server.py --stdio`
- Combined mode: `python server.py --both`

## HTTP Routes

- `GET /`
  Serves the Vendor Atlas frontend.
- `GET /health`
  Returns service health, version, protocol, registered tool count, and connected SSE client count.
- `GET /markets/search`
  Canonical stored-event query route for the dashboard and browser-facing search.
- `GET /consumer/tools`
  Returns a browser-friendly list of tool names, descriptions, and input schemas.
- `POST /consumer/run`
  Runs a tool through the consumer-friendly wrapper and returns `{"ok": true|false, ...}` for profile, ranking, compare, and compatibility flows.

## MCP Tool Pipeline

Vendor Atlas now uses a six-tool pipeline:

1. `discover_events`
   Finds candidate event URLs/titles from supported source categories.
2. `extract_event`
   Scrapes a source URL and extracts normalized event fields.
3. `enrich_event`
   Adds extra signals like social buzz, repeat-event hints, and traffic estimates.
4. `score_event`
   Calculates a Vendor Atlas profit score and opportunity signal.
5. `save_event`
   Persists a normalized event to the local events database.
6. `search_events`
   Queries stored events for dashboard and agent workflows.

Legacy note:

- `search_markets` still exists as a compatibility wrapper for older integrations.
- The forward path is `discover_events -> extract_event -> enrich_event -> score_event -> save_event -> search_events`.
- The dashboard should query `GET /markets/search`, which is backed by the stored-event search layer.

## Tool Summary

### `discover_events`

- Purpose: return candidate event discoveries before deeper scraping.
- Key inputs: `city`, `state`, `keywords`, `sources`, `start_date`, `end_date`
- Key outputs: `searched_at`, `results_count`, `events`

### `extract_event`

- Purpose: turn one event URL into a structured event object.
- Key inputs: `url`
- Key outputs: `url`, `event`, `extracted_fields`

### `enrich_event`

- Purpose: add lightweight web/social signal fields to an event.
- Key inputs: `event_id` or `event`
- Key outputs: `event_id`, `enrichment`, `event`

### `score_event`

- Purpose: convert event data into a vendor-friendly profit signal.
- Key inputs: `event_id` or `event`, optional `enrichment`
- Key outputs: `event_id`, `profit_score`, `signal`, `factors`, `event`

### `save_event`

- Purpose: upsert a normalized event into local storage.
- Key inputs: `event`
- Key outputs: `ok`, `event_id`, `saved_at`

### `search_events`

- Purpose: query stored opportunities for frontend or agent use.
- Key inputs: `city`, `state`, `start_date`, `end_date`, `date_range`, `event_size`, `vendor_category`, `distance_radius`
- Key outputs: `filters`, `results_count`, `events`

## Stored Event Shape

The local SQLite `events` table is managed by [storage_events.py](/c:/Users/lizbl/Documents/GitHub/popshop-finder-mcp/storage_events.py).

Core stored fields:

- `id`
- `name`
- `city`
- `state`
- `date`
- `vendor_count`
- `estimated_traffic`
- `booth_price`
- `application_link`
- `organizer_contact`
- `popularity_score`
- `source_url`

Additional helper fields currently used by the pipeline:

- `vendor_category`
- `event_size`

## Example Flow

1. Call `discover_events`
2. Call `extract_event` for a chosen URL
3. Call `enrich_event`
4. Call `score_event`
5. Call `save_event`
6. Query saved opportunities with `search_events` or `GET /markets/search`

## Example Tool Definitions

See [example_mcp_tools.json](/c:/Users/lizbl/Documents/GitHub/popshop-finder-mcp/docs/example_mcp_tools.json) for example MCP tool definitions based on the current implementation.
