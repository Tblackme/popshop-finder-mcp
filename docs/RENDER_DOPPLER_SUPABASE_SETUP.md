# Render + Doppler + Supabase Setup

This repo is ready to deploy on Render now. Supabase is prepared as the next database/auth target, but the app still uses the current local SQLite-backed storage layer until you migrate it.

## What each service does

- Render: hosts the FastAPI app and MCP/SSE server
- Doppler: stores secrets and injects env vars
- Supabase: Postgres database and optional auth layer

## 1. Render

This repo now includes [render.yaml](/c:/Users/lizbl/Documents/GitHub/popshop-finder-mcp/render.yaml).

Recommended Render setup:

- Runtime: Python
- Build command: `pip install -r requirements.txt`
- Start command: `python server.py --host 0.0.0.0 --port $PORT`
- Health check path: `/health`

After the first deploy, set:

- `APP_BASE_URL=https://<your-render-service>.onrender.com`

Useful local parity check:

```bash
python server.py --host 0.0.0.0 --port 3000
```

## 2. Doppler

Create a Doppler project for this app, then add your secrets there. A starter config file is included as [doppler.yaml.example](/c:/Users/lizbl/Documents/GitHub/popshop-finder-mcp/doppler.yaml.example).

Suggested secrets:

- `SESSION_SECRET`
- `APP_BASE_URL`
- `SHOPIFY_API_KEY`
- `SHOPIFY_API_SECRET`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `DATABASE_URL`
- billing or auth secrets you add later

Typical local workflow:

```bash
doppler setup
copy doppler.yaml.example doppler.yaml
doppler secrets set SESSION_SECRET=replace-me
doppler run -- python server.py
```

If you want to keep `.env` out of local development entirely, use Doppler as the source of truth and only mirror secrets into Render.

## 3. Supabase

Create a Supabase project and copy these values into Doppler and/or Render:

- Project URL -> `SUPABASE_URL`
- anon key -> `SUPABASE_ANON_KEY`
- service role key -> `SUPABASE_SERVICE_ROLE_KEY`
- Postgres connection string -> `DATABASE_URL`

The marketplace SQL schema already exists in [vendor_atlas_mvp_schema.sql](/c:/Users/lizbl/Documents/GitHub/popshop-finder-mcp/docs/vendor_atlas_mvp_schema.sql).

Use that schema in Supabase SQL editor or migrations when you are ready to migrate.

## 4. Important current limitation

Supabase is not fully wired into the runtime yet.

Right now this app still reads and writes through local storage modules such as:

- [storage_events.py](/c:/Users/lizbl/Documents/GitHub/popshop-finder-mcp/storage_events.py)
- [storage_marketplace.py](/c:/Users/lizbl/Documents/GitHub/popshop-finder-mcp/storage_marketplace.py)
- [storage_users.py](/c:/Users/lizbl/Documents/GitHub/popshop-finder-mcp/storage_users.py)

That means:

- Render hosting works now
- Doppler secret management works now
- Supabase credentials can be staged now
- full Supabase database usage still needs a migration pass

## 5. Recommended rollout order

1. Deploy the current app to Render
2. Put secrets in Doppler
3. Mirror the needed secrets into Render
4. Create the Supabase project
5. Apply [vendor_atlas_mvp_schema.sql](/c:/Users/lizbl/Documents/GitHub/popshop-finder-mcp/docs/vendor_atlas_mvp_schema.sql)
6. Migrate the storage modules from SQLite to Postgres/Supabase
