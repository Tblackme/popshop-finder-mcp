"""Minimal MCP client for testing Vendor Atlas over SSE + JSON-RPC.

Usage:
    python scripts/test_discover_events_mcp.py
    python scripts/test_discover_events_mcp.py --port 3001 --city "Kansas City" --state MO
"""

from __future__ import annotations

import argparse
import json
from typing import Any
from urllib.parse import urljoin
from urllib.request import Request, urlopen


def read_endpoint_event(sse_url: str) -> str:
    request = Request(sse_url, method="GET")
    with urlopen(request, timeout=30) as response:
        event_name = ""
        data = ""

        while True:
            raw_line = response.readline()
            if not raw_line:
                break

            line = raw_line.decode("utf-8").strip()
            if not line:
                if event_name == "endpoint" and data:
                    return data
                event_name = ""
                data = ""
                continue

            if line.startswith("event:"):
                event_name = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data = line.split(":", 1)[1].strip()

    raise RuntimeError("Did not receive an endpoint event from the SSE stream.")


def post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def unpack_mcp_content(payload: dict[str, Any]) -> dict[str, Any]:
    result = payload.get("result", {})
    content_items = result.get("content", [])
    if not content_items:
        raise RuntimeError(f"Unexpected MCP payload: {json.dumps(payload, indent=2)}")

    first = content_items[0]
    if first.get("type") == "json":
        return first["json"]

    if first.get("type") == "text":
        return json.loads(first["text"])

    raise RuntimeError(f"Unsupported MCP content type: {first.get('type')}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Call Vendor Atlas discover_events over MCP.")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=3001)
    parser.add_argument("--city", default="Kansas City")
    parser.add_argument("--state", default="MO")
    parser.add_argument(
        "--keywords",
        nargs="+",
        default=["popup market", "makers market", "craft fair", "flea market"],
    )
    args = parser.parse_args()

    base_http_url = f"http://{args.host}:{args.port}"
    sse_url = f"{base_http_url}/sse"

    endpoint_path = read_endpoint_event(sse_url)
    message_url = urljoin(f"{base_http_url}/", endpoint_path.lstrip("/"))

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "discover_events",
            "arguments": {
                "city": args.city,
                "state": args.state,
                "keywords": args.keywords,
            },
        },
    }

    response_payload = post_json(message_url, payload)

    if "error" in response_payload:
        raise RuntimeError(json.dumps(response_payload["error"], indent=2))

    body = unpack_mcp_content(response_payload)
    events = body.get("events", [])

    print(f"Connected via: {message_url}")
    print(f"Found {len(events)} events\n")

    for event in events:
        title = event.get("title", "<no title>")
        source = event.get("source", "<unknown>")
        url = (
            event.get("url")
            or event.get("application_link")
            or event.get("source_url")
            or "<no url>"
        )
        print(f"- {title}")
        print(f"  source: {source}")
        print(f"  url:    {url}\n")


if __name__ == "__main__":
    main()
