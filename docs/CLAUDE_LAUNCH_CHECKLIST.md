# Vendor Atlas Claude Launch Checklist

Use this when you want to load Vendor Atlas locally, inspect the web app, and connect it to Claude as an MCP server.

## 1. Start The Server

From the repo root:

```bash
python server.py --both
```

This gives you:

- the browser app at `http://localhost:3000/`
- the SSE endpoint at `http://localhost:3000/sse`
- local MCP over `stdio`

If you only want one mode:

- browser app only: `python server.py`
- MCP stdio only: `python server.py --stdio`

## 2. Quick Health Check

Open these URLs:

- `http://localhost:3000/health`
- `http://localhost:3000/config.json`
- `http://localhost:3000/consumer/tools`
- `http://localhost:3000/markets/search?city=Austin`

What you should see:

- `/health` returns `status: ok`
- `/consumer/tools` returns a non-zero `count`
- `/markets/search` returns `ok: true`

## 3. Open The App

Open:

```text
http://localhost:3000/
```

Recommended first clicks:

1. Search for a city like `Austin`
2. Save one or two markets
3. Open `View Details`
4. Open the vendor profile quiz
5. Try `Help me choose`

## 4. Connect Claude Over `stdio`

Use a Claude MCP config like:

```json
{
  "mcpServers": {
    "vendor-atlas": {
      "command": "python",
      "args": [
        "C:\\Users\\lizbl\\Documents\\GitHub\\popshop-finder-mcp\\server.py",
        "--stdio"
      ]
    }
  }
}
```

If your Claude setup supports a working directory, use:

```text
C:\Users\lizbl\Documents\GitHub\popshop-finder-mcp
```

## 5. First Claude Prompts

Good first checks inside Claude:

- `List the Vendor Atlas tools`
- `Call search_events for Austin`
- `Call discover_events for Chicago with makers market keywords`
- `Call build_vendor_profile with a handmade jewelry seller profile`

## 6. Known Reality Check

The backend and MCP surface are in good shape and the automated suite passes, but you should still do a human UI pass in a browser for:

- search card layout
- modal interactions
- mobile menu behavior
- compare flow readability
- any remaining visible copy/punctuation rough edges
