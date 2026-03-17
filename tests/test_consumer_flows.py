import importlib
import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import server
import storage_events
import storage_users
from billing import UsageTracker, create_billing_middleware
from tools import (
    vendor_atlas_events,
    vendor_atlas_markets,
    vendor_atlas_pipeline,
    vendor_atlas_profile,
    vendor_atlas_scoring,
)


@pytest.fixture
def consumer_client(monkeypatch):
    async def test_billing_middleware(tool_name, arguments, api_key, handler):
        try:
            result = await handler(**arguments)
        except Exception as exc:
            return {"error": str(exc)}
        return {"content": [{"type": "text", "text": result}]}

    monkeypatch.setattr(server, "billing_middleware", test_billing_middleware)
    importlib.reload(storage_users)
    with TestClient(server.create_app()) as client:
        yield client


@pytest.fixture
def temp_event_storage(monkeypatch):
    temp_root = Path.cwd() / ".tmp_test_storage"
    if temp_root.exists():
        shutil.rmtree(temp_root, ignore_errors=True)
    db_path = temp_root / "nested" / "vendor-atlas-test.db"
    monkeypatch.setenv("VENDOR_ATLAS_DB_PATH", str(db_path))
    module = importlib.reload(storage_events)
    try:
        yield module, db_path
    finally:
        monkeypatch.delenv("VENDOR_ATLAS_DB_PATH", raising=False)
        shutil.rmtree(temp_root, ignore_errors=True)
        importlib.reload(storage_events)


@pytest.fixture
def temp_user_storage(monkeypatch):
    temp_root = Path.cwd() / ".tmp_auth_storage"
    if temp_root.exists():
        shutil.rmtree(temp_root, ignore_errors=True)
    db_path = temp_root / "auth" / "vendor-atlas-auth.db"
    monkeypatch.setenv("VENDOR_ATLAS_DB_PATH", str(db_path))
    importlib.reload(storage_events)
    importlib.reload(storage_users)
    importlib.reload(server)
    try:
        yield db_path
    finally:
        monkeypatch.delenv("VENDOR_ATLAS_DB_PATH", raising=False)
        shutil.rmtree(temp_root, ignore_errors=True)
        importlib.reload(storage_events)
        importlib.reload(storage_users)
        importlib.reload(server)


@pytest.mark.asyncio
async def test_build_vendor_profile_returns_profile_payload():
    payload = json.loads(
        await vendor_atlas_profile.handle_build_vendor_profile(
            {
                "what_you_sell": "Handmade earrings and necklaces",
                "style": "playful",
                "price_range": "Most items are under $20",
                "main_goal": "Grow my audience",
                "event_preferences": "Indoor markets",
                "experience_level": "Brand new",
            }
        )
    )

    profile = payload["profile"]
    assert profile["category"] == "Handmade Jewelry"
    assert profile["preferred_env"] == "indoor"
    assert profile["goal"] == "grow_audience"
    assert profile["experience_level"] == "early_stage"
    assert profile["summary"]


@pytest.mark.asyncio
async def test_search_markets_returns_payload_and_preserves_radius(monkeypatch):
    fake_events = [
        {
            "id": "market-1",
            "name": "Austin Night Market",
            "city": "Austin",
            "state": "TX",
            "date": "2026-05-01",
            "application_link": "https://example.com/apply",
            "vendor_category": "art",
            "vendor_count": 75,
        }
    ]

    def fake_search_events(filters):
        assert filters["city"] == "Austin"
        assert filters["event_size"] == "medium"
        assert filters["vendor_category"] == "art"
        return fake_events

    monkeypatch.setattr(vendor_atlas_markets, "search_events", fake_search_events)

    payload = json.loads(
        await vendor_atlas_markets.handle_search_markets(
            city="Austin",
            radius_miles="25",
            event_size="medium",
            vendor_category="art",
        )
    )

    assert payload["filters"]["radius_miles"] == "25"
    assert payload["sources_requested"]
    assert payload["results_count"] == 1
    assert payload["events"][0]["id"] == "market-1"
    assert payload["markets"][0]["apply_url"] == "https://example.com/apply"


@pytest.mark.asyncio
async def test_compare_markets_returns_recommendation_order():
    vendor_profile = {
        "preferred_env": "indoor",
        "max_booth_price": 150,
        "risk_tolerance": "low",
    }
    markets = [
        {
            "id": "market-a",
            "booth_price": 100,
            "estimated_traffic": 3500,
            "indoor_outdoor": "indoor",
            "popularity_score": 85,
        },
        {
            "id": "market-b",
            "booth_price": 275,
            "estimated_traffic": 700,
            "indoor_outdoor": "outdoor",
            "popularity_score": 40,
        },
    ]

    payload = json.loads(
        await vendor_atlas_scoring.handle_compare_markets_for_vendor(vendor_profile, markets)
    )

    assert len(payload["recommendation_order"]) == 2
    assert payload["recommendation_order"][0]["market_id"] == "market-a"
    assert payload["recommendation_order"][0]["fit_score"] >= payload["recommendation_order"][1]["fit_score"]


@pytest.mark.asyncio
async def test_consumer_run_executes_existing_tool(consumer_client):
    response = consumer_client.post(
        "/consumer/run",
        json={
            "tool": "build_vendor_profile",
            "arguments": {
                "answers": {
                    "what_you_sell": "Soy candles",
                    "main_goal": "Grow my audience",
                    "event_preferences": "Indoor events",
                }
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True

    result = json.loads(payload["result"])
    assert result["profile"]["category"] == "Home & Body"


@pytest.mark.asyncio
async def test_consumer_run_returns_ok_false_when_handler_raises(monkeypatch, consumer_client):
    async def boom_tool(**_kwargs):
        raise RuntimeError("kaboom")

    monkeypatch.setitem(server.ALL_HANDLERS, "boom_tool", boom_tool)

    response = consumer_client.post(
        "/consumer/run",
        json={"tool": "boom_tool", "arguments": {}},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload == {"ok": False, "error": "kaboom"}


@pytest.mark.asyncio
async def test_consumer_run_returns_404_for_unknown_tool(consumer_client):
    response = consumer_client.post(
        "/consumer/run",
        json={"tool": "not_a_real_tool", "arguments": {}},
    )

    assert response.status_code == 404
    payload = response.json()
    assert payload == {"ok": False, "error": "Unknown tool: not_a_real_tool"}


def test_consumer_run_passes_bearer_api_key_to_billing(monkeypatch, consumer_client):
    captured = {}

    async def capture_billing(tool_name, arguments, api_key, handler):
        captured["tool_name"] = tool_name
        captured["api_key"] = api_key
        result = await handler(**arguments)
        return {"content": [{"type": "text", "text": result}]}

    monkeypatch.setattr(server, "billing_middleware", capture_billing)

    response = consumer_client.post(
        "/consumer/run",
        json={
            "tool": "build_vendor_profile",
            "arguments": {
                "answers": {
                    "what_you_sell": "Soy candles",
                }
            },
        },
        headers={"Authorization": "Bearer test-consumer-key"},
    )

    assert response.status_code == 200
    assert captured["tool_name"] == "build_vendor_profile"
    assert captured["api_key"] == "test-consumer-key"


def test_consumer_run_passes_x_api_key_to_billing(monkeypatch, consumer_client):
    captured = {}

    async def capture_billing(tool_name, arguments, api_key, handler):
        captured["tool_name"] = tool_name
        captured["api_key"] = api_key
        result = await handler(**arguments)
        return {"content": [{"type": "text", "text": result}]}

    monkeypatch.setattr(server, "billing_middleware", capture_billing)

    response = consumer_client.post(
        "/consumer/run",
        json={
            "tool": "build_vendor_profile",
            "arguments": {
                "answers": {
                    "what_you_sell": "Soy candles",
                }
            },
        },
        headers={"X-API-Key": "x-consumer-key"},
    )

    assert response.status_code == 200
    assert captured["tool_name"] == "build_vendor_profile"
    assert captured["api_key"] == "x-consumer-key"


@pytest.mark.asyncio
async def test_billing_middleware_wraps_json_string_results_as_json_content():
    middleware = create_billing_middleware(UsageTracker())

    async def json_string_handler(**_kwargs):
        return '{"status":"ok","count":2}'

    payload = await middleware("json_tool", {}, "", json_string_handler)

    assert payload == {
        "content": [
            {
                "type": "json",
                "json": {"status": "ok", "count": 2},
            }
        ]
    }


@pytest.mark.asyncio
async def test_billing_middleware_wraps_dict_results_as_json_content():
    middleware = create_billing_middleware(UsageTracker())

    async def dict_handler(**_kwargs):
        return {"status": "ok", "count": 2}

    payload = await middleware("dict_tool", {}, "", dict_handler)

    assert payload == {
        "content": [
            {
                "type": "json",
                "json": {"status": "ok", "count": 2},
            }
        ]
    }


def test_consumer_run_returns_400_for_invalid_json_body(consumer_client):
    response = consumer_client.post(
        "/consumer/run",
        content='{"tool":"build_vendor_profile",',
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400
    assert response.json() == {"ok": False, "error": "Invalid JSON body"}


def test_consumer_run_returns_400_when_tool_is_missing(consumer_client):
    response = consumer_client.post("/consumer/run", json={"arguments": {}})

    assert response.status_code == 400
    assert response.json() == {"ok": False, "error": "tool is required"}


def test_signup_signin_and_dashboard_flow(temp_user_storage):
    with TestClient(server.create_app()) as client:
        signup = client.post(
            "/api/auth/signup",
            json={
                "name": "Liz Vendor",
                "email": "liz@example.com",
                "username": "lizvendor",
                "password": "supersecure123",
                "interests": "jewelry, popups",
                "bio": "Weekend market seller",
            },
        )

        assert signup.status_code == 200
        payload = signup.json()
        assert payload["ok"] is True
        assert payload["user"]["email"] == "liz@example.com"

        auth_state = client.get("/api/auth/me")
        assert auth_state.status_code == 200
        assert auth_state.json()["authenticated"] is True

        dashboard_page = client.get("/dashboard")
        assert dashboard_page.status_code == 200
        assert "Saved markets" in dashboard_page.text

        logout = client.post("/api/auth/logout")
        assert logout.status_code == 200

        signin = client.post(
            "/api/auth/signin",
            json={"email": "liz@example.com", "password": "supersecure123"},
        )
        assert signin.status_code == 200
        assert signin.json()["user"]["username"] == "lizvendor"


def test_dashboard_redirects_when_not_authenticated(temp_user_storage):
    with TestClient(server.create_app()) as client:
        response = client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == "/signin"


def test_profile_and_saved_markets_require_auth(temp_user_storage):
    with TestClient(server.create_app()) as client:
        response = client.get("/api/dashboard")
        assert response.status_code == 401
        assert response.json() == {"ok": False, "error": "Authentication required."}


def test_availability_planner_updates_and_returns_recommendations(temp_user_storage):
    with TestClient(server.create_app()) as client:
        signup = client.post(
            "/api/auth/signup",
            json={
                "name": "Planner User",
                "email": "planner@example.com",
                "username": "planneruser",
                "password": "supersecure123",
            },
        )
        assert signup.status_code == 200

        response = client.post(
            "/api/availability",
            json={
                "weekdays": ["Saturday", "Sunday"],
                "preferred_months": ["April", "May"],
                "weekly_capacity": 2,
                "monthly_goal": 5,
                "notes": "Prefer weekends.",
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["availability"]["weekdays"] == ["Saturday", "Sunday"]
        assert payload["availability"]["preferred_months"] == ["April", "May"]
        assert "recommended_markets" in payload


def test_kansas_city_listings_endpoint_combines_current_and_discovered(monkeypatch, consumer_client):
    monkeypatch.setattr(
        server,
        "run_search_events",
        lambda filters: {
            "events": [
                {
                    "id": "kc-current-1",
                    "name": "Kansas City Night Market",
                    "city": "Kansas City",
                    "state": "MO",
                    "date": "2026-05-16",
                    "application_link": "https://example.com/kc-current",
                }
            ]
        },
    )

    async def fake_discover_events(**_kwargs):
        return json.dumps(
            {
                "events": [
                    {
                        "title": "Kansas City Makers Market",
                        "url": "https://example.com/kc-makers",
                        "source": "google",
                        "city": "Kansas City",
                        "state": "MO",
                    }
                ]
            }
        )

    monkeypatch.setitem(server.ALL_HANDLERS, "discover_events", fake_discover_events)

    response = consumer_client.get("/api/listings/kansas-city")
    assert response.status_code == 200
    payload = response.json()
    assert payload["city"] == "Kansas City"
    assert payload["current_count"] == 1
    assert payload["more_count"] == 1
    assert payload["current_events"][0]["name"] == "Kansas City Night Market"
    assert payload["more_events"][0]["title"] == "Kansas City Makers Market"


def test_kansas_city_listing_evaluation_returns_ratings(monkeypatch, consumer_client):
    monkeypatch.setattr(
        server,
        "_load_kansas_city_listings",
        lambda: None,
    )

    async def fake_loader():
        return {
            "ok": True,
            "city": "Kansas City",
            "state": "MO",
            "current_events": [
                {
                    "id": "kc-eval-1",
                    "name": "Kansas City Spring Bazaar",
                    "city": "Kansas City",
                    "state": "MO",
                    "date": "2026-04-18",
                    "vendor_count": 70,
                    "estimated_traffic": 3200,
                    "booth_price": 125,
                    "popularity_score": 84,
                    "application_link": "https://example.com/apply",
                }
            ],
            "current_count": 1,
            "more_events": [],
            "more_count": 0,
        }

    monkeypatch.setattr(server, "_load_kansas_city_listings", fake_loader)

    response = consumer_client.post(
        "/api/listings/kansas-city/evaluate",
        json={
            "avg_sale_price": 50,
            "avg_sales_per_event": 20,
            "typical_cogs": 250,
            "travel_cost": 40,
            "booth_budget": 150,
            "preferred_min_profit": 250,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    analysis = payload["current_events"][0]["analysis"]
    assert analysis["estimated_revenue"] == 1000.0
    assert "overall_worth_it" in analysis["ratings"]
    assert analysis["recommendation"] in {"Strong Yes", "Maybe", "Not Worth It"}


def test_find_market_endpoint_combines_search_and_discovery(monkeypatch, consumer_client):
    monkeypatch.setattr(
        server,
        "run_search_events",
        lambda filters: {
            "events": [
                {
                    "id": "finder-1",
                    "name": "Austin Makers Market",
                    "city": "Austin",
                    "state": "TX",
                    "date": "2026-05-20",
                }
            ]
        },
    )

    async def fake_discover_events(**_kwargs):
        return json.dumps(
            {
                "events": [
                    {
                        "title": "Austin Popup Series",
                        "url": "https://example.com/austin-popup",
                        "source": "google",
                        "city": "Austin",
                        "state": "TX",
                    }
                ]
            }
        )

    monkeypatch.setitem(server.ALL_HANDLERS, "discover_events", fake_discover_events)

    response = consumer_client.get(
        "/api/find-market",
        params={"city": "Austin", "state": "TX", "vendor_category": "jewelry"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["mcp_tools_used"] == ["search_events", "discover_events"]
    assert payload["search_count"] == 1
    assert payload["discover_count"] == 1
    assert payload["search_results"][0]["name"] == "Austin Makers Market"
    assert payload["discovered_results"][0]["title"] == "Austin Popup Series"


@pytest.mark.asyncio
async def test_scrape_event_extracts_structured_fields(monkeypatch):
    html = """
    <html>
      <head>
        <title>Austin Handmade Pop-Up</title>
        <script type="application/ld+json">
          {
            "@context": "https://schema.org",
            "@type": "Event",
            "name": "Austin Handmade Pop-Up",
            "startDate": "2026-05-14T10:00:00-05:00",
            "location": {
              "@type": "Place",
              "name": "Eastside Hall",
              "address": {
                "@type": "PostalAddress",
                "addressLocality": "Austin",
                "addressRegion": "TX"
              }
            }
          }
        </script>
      </head>
      <body>
        <p>Join 85 vendors for a weekend market with 3,200 attendees expected.</p>
        <p>Booth fee: $175</p>
        <p>Contact hello@eastsideguild.example for details.</p>
        <a href="/apply-now">Apply as a vendor</a>
      </body>
    </html>
    """

    async def fake_fetch(url):
        assert url == "https://example.com/events/austin-handmade-popup"
        return html

    monkeypatch.setattr(vendor_atlas_events, "_fetch_page", fake_fetch)

    payload = json.loads(
        await vendor_atlas_events.handle_scrape_event(
            "https://example.com/events/austin-handmade-popup"
        )
    )

    event = payload["event"]
    assert event["name"] == "Austin Handmade Pop-Up"
    assert event["city"] == "Austin"
    assert event["state"] == "TX"
    assert event["date"] == "2026-05-14"
    assert event["vendor_count"] == 85
    assert event["estimated_traffic"] == 3200
    assert event["booth_price"] == 175.0
    assert event["organizer_contact"] == "hello@eastsideguild.example"
    assert event["application_link"] == "https://example.com/apply-now"


@pytest.mark.asyncio
async def test_search_events_pipeline_returns_structured_results(monkeypatch):
    fake_events = [
        {
            "id": "event-1",
            "name": "Vintage Makers Market",
            "city": "Chicago",
            "state": "IL",
            "date": "2026-07-14",
            "vendor_category": "vintage",
        }
    ]

    def fake_query_events(filters):
        assert filters["city"] == "Chicago"
        assert filters["vendor_category"] == "vintage"
        return fake_events

    monkeypatch.setattr(vendor_atlas_pipeline, "query_events", fake_query_events)

    payload = json.loads(
        await vendor_atlas_pipeline.handle_search_events(
            city="Chicago",
            vendor_category="vintage",
            distance_radius="25",
        )
    )

    assert payload["results_count"] == 1
    assert payload["events"][0]["name"] == "Vintage Makers Market"
    assert payload["filters"]["distance_radius"] == "25"


@pytest.mark.asyncio
async def test_discover_events_pipeline_filters_and_returns_candidates(monkeypatch):
    async def fake_live_discovery(city, state, keywords, requested_sources):
        assert city == "Chicago"
        assert keywords == ["vintage"]
        assert requested_sources == ["eventbrite"]
        return [
            {
                "title": "Vintage Makers Market",
                "url": "https://example.com/vintage-makers",
                "source": "eventbrite",
                "city": "Chicago",
                "state": "IL",
                "date": None,
                "event_id": None,
                "discovered_via": "web",
            }
        ]

    monkeypatch.setattr(vendor_atlas_pipeline, "_discover_live_candidates", fake_live_discovery)
    monkeypatch.setattr(
        vendor_atlas_pipeline,
        "_persist_discovered_candidates",
        lambda events, city, state: [{**events[0], "event_id": "discovered-1"}],
    )

    payload = json.loads(
        await vendor_atlas_pipeline.handle_discover_events(
            city="Chicago",
            keywords=["vintage"],
            sources=["eventbrite"],
        )
    )

    assert payload["results_count"] == 1
    assert payload["events"][0]["title"] == "Vintage Makers Market"
    assert payload["events"][0]["source"] == "eventbrite"
    assert payload["events"][0]["discovered_via"] == "web"
    assert payload["events"][0]["event_id"] == "discovered-1"


def test_extract_search_results_parses_duckduckgo_redirect_links():
    html = """
    <html>
      <body>
        <a href="https://duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.eventbrite.com%2Fe%2Fmakers-market">
          Makers Market Tickets, Sat, Jul 14
        </a>
        <a href="https://example.com/local-market">Kansas City Local Market</a>
        <a href="/about">About</a>
      </body>
    </html>
    """

    results = vendor_atlas_pipeline._extract_search_results(html, "eventbrite")

    assert results[0]["url"] == "https://www.eventbrite.com/e/makers-market"
    assert results[0]["title"] == "Makers Market Tickets, Sat, Jul 14"
    assert results[0]["source"] == "eventbrite"
    assert results[1]["url"] == "https://example.com/local-market"


def test_extract_search_results_filters_generic_non_event_links():
    html = """
    <html>
      <body>
        <a href="https://example.com/about">About Our Organization</a>
        <a href="https://example.com/kansas-city-popup-market">Kansas City Popup Market</a>
        <a href="https://example.com/vendors">Vendor Resources</a>
      </body>
    </html>
    """

    results = vendor_atlas_pipeline._extract_search_results(
        html,
        "google",
        city="Kansas City",
        state="MO",
        keywords=["popup market"],
    )

    assert len(results) == 1
    assert results[0]["title"] == "Kansas City Popup Market"
    assert results[0]["url"] == "https://example.com/kansas-city-popup-market"


def test_precise_discovery_candidate_prefers_event_like_titles():
    assert vendor_atlas_pipeline._is_precise_discovery_candidate(
        "Kansas City Makers Market",
        "https://example.com/events/kansas-city-makers-market",
        "google",
        city="Kansas City",
        state="MO",
        keywords=["makers market"],
    )


@pytest.mark.asyncio
async def test_refine_discovered_events_prefers_verified_event_pages():
    class FakeResponse:
        def __init__(self, text):
            self.text = text

        def raise_for_status(self):
            return None

    class FakeClient:
        async def get(self, url, headers=None):
            if "makers" in url:
                return FakeResponse(
                    """
                    <html>
                      <head><title>Kansas City Makers Market</title></head>
                      <body>
                        <script type="application/ld+json">{"@type":"Event","startDate":"2026-05-20"}</script>
                        <p>Apply now for our popup market event in Kansas City.</p>
                      </body>
                    </html>
                    """
                )
            return FakeResponse("<html><head><title>About Us</title></head><body>Company info only.</body></html>")

    refined = await vendor_atlas_pipeline._refine_discovered_events(
        FakeClient(),
        [
            {
                "title": "Kansas City Makers Market",
                "url": "https://example.com/kansas-city-makers",
                "source": "google",
                "precision_score": 5,
            },
            {
                "title": "Vendor Collective",
                "url": "https://example.com/about",
                "source": "google",
                "precision_score": 2,
            },
        ],
        city="Kansas City",
        keywords=["makers market"],
    )

    assert len(refined) == 1
    assert refined[0]["title"] == "Kansas City Makers Market"
    assert refined[0]["verified"] is True
    assert refined[0]["date"] == "2026-05-20"
    assert not vendor_atlas_pipeline._is_precise_discovery_candidate(
        "About Our Team",
        "https://example.com/about",
        "google",
        city="Kansas City",
        state="MO",
        keywords=["makers market"],
    )


def test_persist_discovered_candidates_assigns_ids_and_saves(monkeypatch):
    captured = []

    def fake_upsert(event):
        captured.append(event)

    monkeypatch.setattr(vendor_atlas_pipeline, "upsert_event", fake_upsert)

    persisted = vendor_atlas_pipeline._persist_discovered_candidates(
        [
            {
                "title": "Kansas City Makers Market",
                "url": "https://example.com/kc-makers",
                "source": "google",
            }
        ],
        city="Kansas City",
        state="MO",
    )

    assert persisted[0]["event_id"].startswith("discovered-")
    assert captured[0].name == "Kansas City Makers Market"
    assert captured[0].city == "Kansas City"
    assert captured[0].state == "MO"
    assert captured[0].source_url == "https://example.com/kc-makers"


@pytest.mark.asyncio
async def test_discover_events_falls_back_to_stored_events_when_live_search_is_empty(monkeypatch):
    fake_events = [
        {
            "id": "event-1",
            "name": "Chicago Handmade Bazaar",
            "city": "Chicago",
            "state": "IL",
            "date": "2026-07-14",
            "vendor_category": "handmade jewelry",
            "source_url": "https://example.com/chicago-bazaar",
        }
    ]

    async def fake_live_discovery(*_args, **_kwargs):
        return []

    def fake_query_events(filters):
        assert filters["city"] == "Chicago"
        return fake_events

    monkeypatch.setattr(vendor_atlas_pipeline, "_discover_live_candidates", fake_live_discovery)
    monkeypatch.setattr(vendor_atlas_pipeline, "query_events", fake_query_events)

    payload = json.loads(
        await vendor_atlas_pipeline.handle_discover_events(
            city="Chicago",
            keywords=["handmade"],
            sources=["google"],
        )
    )

    assert payload["results_count"] == 1
    assert payload["events"][0]["title"] == "Chicago Handmade Bazaar"
    assert payload["events"][0]["discovered_via"] == "database"


@pytest.mark.asyncio
async def test_enrich_event_pipeline_adds_social_and_history_signals(monkeypatch):
    event = {
        "id": "event-1",
        "name": "Vintage Makers Market",
        "city": "Chicago",
        "state": "IL",
        "date": "2026-07-14",
        "vendor_count": 80,
        "estimated_traffic": None,
        "popularity_score": 70,
        "source_url": "https://example.com/event",
        "organizer_contact": "hello@example.com",
    }
    peer_events = [
        event,
        {
            "id": "event-2",
            "name": "Chicago Indie Bazaar",
            "city": "Chicago",
            "state": "IL",
            "date": "2026-06-01",
            "vendor_count": 60,
        },
    ]

    monkeypatch.setattr(vendor_atlas_pipeline, "query_events", lambda filters: peer_events)
    monkeypatch.setattr(vendor_atlas_pipeline, "_persist_event_payload", lambda event: None)

    payload = json.loads(await vendor_atlas_pipeline.handle_enrich_event(event=event))

    assert payload["event_id"] == "event-1"
    assert payload["enrichment"]["social_mentions"] > 0
    assert payload["enrichment"]["previous_events"] == 1
    assert payload["event"]["estimated_traffic"] is not None


@pytest.mark.asyncio
async def test_score_event_pipeline_returns_profit_signal(monkeypatch):
    event = {
        "id": "event-1",
        "name": "Vintage Makers Market",
        "city": "Chicago",
        "state": "IL",
        "date": "2026-07-14",
        "vendor_count": 80,
        "estimated_traffic": 3200,
        "booth_price": 120,
        "popularity_score": 70,
        "source_url": "https://example.com/event",
    }
    enrichment = {
        "social_mentions": 180,
        "previous_events": 4,
        "organizer_reputation": 82,
        "estimated_traffic": 3200,
    }

    monkeypatch.setattr(vendor_atlas_pipeline, "_persist_event_payload", lambda event: None)

    payload = json.loads(
        await vendor_atlas_pipeline.handle_score_event(event=event, enrichment=enrichment)
    )

    assert payload["event_id"] == "event-1"
    assert payload["profit_score"] >= 75
    assert payload["signal"] == "High Opportunity"


@pytest.mark.asyncio
async def test_save_event_pipeline_generates_id_when_missing(monkeypatch):
    captured = {}

    def fake_persist(event):
        captured.update(event)

    monkeypatch.setattr(vendor_atlas_pipeline, "_persist_event_payload", fake_persist)

    payload = json.loads(
        await vendor_atlas_pipeline.handle_save_event(
            {
                "name": "Sunset Popup",
                "city": "Austin",
                "state": "TX",
                "date": "2026-08-08",
            }
        )
    )

    assert payload["ok"] is True
    assert payload["event_id"].startswith("saved-")
    assert captured["id"] == payload["event_id"]


def test_markets_search_endpoint_returns_frontend_ready_results(monkeypatch, consumer_client):
    fake_payload = {
        "filters": {
            "city": "Chicago",
            "state": "IL",
            "date_range": "2026-07-01:2026-07-31",
            "event_size": "medium",
            "vendor_category": "vintage",
            "distance_radius": "25",
            "start_date": "2026-07-01",
            "end_date": "2026-07-31",
        },
        "results_count": 1,
        "events": [
            {
                "id": "event-1",
                "name": "Vintage Makers Market",
                "city": "Chicago",
                "state": "IL",
                "date": "2026-07-14",
                "application_link": "https://example.com/apply",
            }
        ],
    }

    monkeypatch.setattr(server, "run_search_events", lambda filters: fake_payload)

    response = consumer_client.get(
        "/markets/search",
        params={
            "city": "Chicago",
            "state": "IL",
            "date_range": "2026-07-01:2026-07-31",
            "event_size": "medium",
            "vendor_category": "vintage",
            "distance_radius": "25",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["results_count"] == 1
    assert payload["events"][0]["name"] == "Vintage Makers Market"
    assert payload["markets"][0]["apply_url"] == "https://example.com/apply"
    assert "result" in payload
    assert payload["filters"]["distance_radius"] == "25"


def test_markets_search_endpoint_parses_date_range_into_filters(monkeypatch, consumer_client):
    captured = {}

    def fake_run_search_events(filters):
        captured.update(filters)
        return {"filters": filters, "results_count": 0, "events": []}

    monkeypatch.setattr(server, "run_search_events", fake_run_search_events)

    response = consumer_client.get(
        "/markets/search",
        params={
            "city": "Austin",
            "date_range": "2026-08-01:2026-08-31",
            "event_size": "any",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert captured["start_date"] == "2026-08-01"
    assert captured["end_date"] == "2026-08-31"
    assert captured["event_size"] == ""
    assert payload["filters"]["start_date"] == "2026-08-01"
    assert payload["filters"]["end_date"] == "2026-08-31"


def test_markets_search_endpoint_returns_compat_result_json(monkeypatch, consumer_client):
    fake_payload = {
        "filters": {"city": "Austin"},
        "results_count": 1,
        "events": [
            {
                "id": "event-1",
                "name": "Austin Night Market",
                "city": "Austin",
                "state": "TX",
                "date": "2026-05-01",
                "application_link": "https://example.com/apply",
            }
        ],
    }

    monkeypatch.setattr(server, "run_search_events", lambda filters: fake_payload)

    response = consumer_client.get("/markets/search", params={"city": "Austin"})

    assert response.status_code == 200
    payload = response.json()
    compat = json.loads(payload["result"])
    assert compat["markets"][0]["id"] == "event-1"
    assert compat["markets"][0]["apply_url"] == "https://example.com/apply"


def test_markets_search_endpoint_returns_empty_compat_shape(monkeypatch, consumer_client):
    monkeypatch.setattr(
        server,
        "run_search_events",
        lambda filters: {"filters": filters, "results_count": 0, "events": []},
    )

    response = consumer_client.get("/markets/search", params={"city": "Nowhere"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["results_count"] == 0
    assert payload["events"] == []
    assert payload["markets"] == []
    assert json.loads(payload["result"]) == {"markets": []}


def test_runtime_config_endpoint_returns_api_base_and_flags(consumer_client):
    response = consumer_client.get("/config.json")

    assert response.status_code == 200
    payload = response.json()
    assert "api_base_url" in payload
    assert payload["api_base_url"] == "http://testserver"
    assert payload["product"]["pro_status"] == "coming_soon"
    assert payload["features"]["dashboard_search"] is True


def test_public_comparison_endpoint_returns_fallback_payload(consumer_client):
    response = consumer_client.get("/public-comparison.json")

    assert response.status_code == 200
    payload = response.json()
    assert "summary" in payload
    assert payload["items"] == []


def test_site_static_mount_serves_index_html(consumer_client):
    response = consumer_client.get("/site/index.html")

    assert response.status_code == 200
    assert "Vendor Atlas" in response.text


def test_health_endpoint_reports_ok_and_tool_count(consumer_client):
    response = consumer_client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["server"] == "Vendor Atlas"
    assert payload["version"] == server.SERVER_INFO["version"]
    assert payload["protocol"] == server.PROTOCOL_VERSION
    assert payload["tools"] == len(server.ALL_TOOLS)
    assert payload["connected_clients"] == 0


def test_consumer_tools_endpoint_lists_pipeline_tools(consumer_client):
    response = consumer_client.get("/consumer/tools")

    assert response.status_code == 200
    payload = response.json()
    names = {tool["name"] for tool in payload["tools"]}
    assert payload["count"] == len(server.ALL_TOOLS)
    assert "discover_events" in names
    assert "extract_event" in names
    assert "enrich_event" in names
    assert "score_event" in names
    assert "save_event" in names
    assert "search_events" in names
    assert all("description" in tool for tool in payload["tools"])
    assert all("inputSchema" in tool for tool in payload["tools"])


def test_tool_registry_has_unique_names_and_handlers():
    tool_names = [tool["name"] for tool in server.ALL_TOOLS]

    assert len(tool_names) == len(set(tool_names))
    assert all(name in server.ALL_HANDLERS for name in tool_names)
    assert all(callable(server.ALL_HANDLERS[name]) for name in tool_names)
    assert set(server.ALL_HANDLERS).issuperset(tool_names)


def test_tool_registry_metadata_has_required_fields():
    for tool in server.ALL_TOOLS:
        assert isinstance(tool["name"], str) and tool["name"].strip()
        assert isinstance(tool.get("description", ""), str)
        assert isinstance(tool.get("inputSchema", {}), dict)


def test_jsonrpc_initialize_returns_protocol_and_server_info(consumer_client):
    response = consumer_client.post(
        "/message",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["jsonrpc"] == "2.0"
    assert payload["id"] == 1
    assert payload["result"]["protocolVersion"] == server.PROTOCOL_VERSION
    assert payload["result"]["serverInfo"]["name"] == "Vendor Atlas"


@pytest.mark.asyncio
async def test_sse_transport_connect_bootstraps_message_endpoint():
    session_id, queue = await server.sse_transport.connect()
    try:
        assert session_id
        assert server.sse_transport.has_session(session_id) is True
        bootstrap = await queue.get()
        assert "event: endpoint" in bootstrap
        assert f"/message?sessionId={session_id}" in bootstrap
    finally:
        await server.sse_transport.disconnect(session_id)


@pytest.mark.asyncio
async def test_health_endpoint_reflects_connected_sse_clients(consumer_client):
    session_id, queue = await server.sse_transport.connect()
    try:
        await queue.get()
        response = consumer_client.get("/health")
        assert response.status_code == 200
        payload = response.json()
        assert payload["connected_clients"] >= 1
    finally:
        await server.sse_transport.disconnect(session_id)


@pytest.mark.asyncio
async def test_sse_transport_send_enqueues_message_event():
    session_id, queue = await server.sse_transport.connect()
    try:
        await queue.get()
        await server.sse_transport.send(session_id, {"ok": True, "message": "hello"})
        payload = await queue.get()
        assert "event: message" in payload
        assert '"ok": true' in payload
        assert '"message": "hello"' in payload
    finally:
        await server.sse_transport.disconnect(session_id)


@pytest.mark.asyncio
async def test_message_route_sends_jsonrpc_response_to_active_sse_session(consumer_client):
    session_id, queue = await server.sse_transport.connect()
    try:
        await queue.get()
        response = consumer_client.post(
            f"/message?sessionId={session_id}",
            json={
                "jsonrpc": "2.0",
                "id": 12,
                "method": "ping",
                "params": {},
            },
        )

        assert response.status_code == 200
        assert response.json() == {"jsonrpc": "2.0", "id": 12, "result": {}}

        pushed = await queue.get()
        assert "event: message" in pushed
        assert '"id": 12' in pushed
        assert '"jsonrpc": "2.0"' in pushed
    finally:
        await server.sse_transport.disconnect(session_id)


def test_jsonrpc_tools_list_returns_registered_tools(consumer_client):
    response = consumer_client.post(
        "/message",
        json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    names = {tool["name"] for tool in payload["result"]["tools"]}
    assert payload["jsonrpc"] == "2.0"
    assert payload["id"] == 2
    assert "discover_events" in names
    assert "search_events" in names
    assert "build_vendor_profile" in names


def test_jsonrpc_tools_call_executes_registered_tool(consumer_client):
    response = consumer_client.post(
        "/message",
        json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "build_vendor_profile",
                "arguments": {
                    "answers": {
                        "what_you_sell": "Soy candles",
                        "main_goal": "Grow my audience",
                        "event_preferences": "Indoor events",
                    }
                },
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["jsonrpc"] == "2.0"
    assert payload["id"] == 3
    result_text = payload["result"]["content"][0]["text"]
    result = json.loads(result_text)
    assert result["profile"]["category"] == "Home & Body"


def test_jsonrpc_tools_call_passes_bearer_api_key_to_billing(monkeypatch, consumer_client):
    captured = {}

    async def capture_billing(tool_name, arguments, api_key, handler):
        captured["tool_name"] = tool_name
        captured["api_key"] = api_key
        result = await handler(**arguments)
        return {"content": [{"type": "text", "text": result}]}

    monkeypatch.setattr(server, "billing_middleware", capture_billing)

    response = consumer_client.post(
        "/message",
        json={
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {
                "name": "build_vendor_profile",
                "arguments": {
                    "answers": {
                        "what_you_sell": "Soy candles",
                    }
                },
            },
        },
        headers={"Authorization": "Bearer test-mcp-key"},
    )

    assert response.status_code == 200
    assert captured["tool_name"] == "build_vendor_profile"
    assert captured["api_key"] == "test-mcp-key"


def test_jsonrpc_tools_call_passes_x_api_key_to_billing(monkeypatch, consumer_client):
    captured = {}

    async def capture_billing(tool_name, arguments, api_key, handler):
        captured["tool_name"] = tool_name
        captured["api_key"] = api_key
        result = await handler(**arguments)
        return {"content": [{"type": "text", "text": result}]}

    monkeypatch.setattr(server, "billing_middleware", capture_billing)

    response = consumer_client.post(
        "/message",
        json={
            "jsonrpc": "2.0",
            "id": 11,
            "method": "tools/call",
            "params": {
                "name": "build_vendor_profile",
                "arguments": {
                    "answers": {
                        "what_you_sell": "Soy candles",
                    }
                },
            },
        },
        headers={"X-API-Key": "x-mcp-key"},
    )

    assert response.status_code == 200
    assert captured["tool_name"] == "build_vendor_profile"
    assert captured["api_key"] == "x-mcp-key"


def test_jsonrpc_tools_call_returns_unknown_tool_error(consumer_client):
    response = consumer_client.post(
        "/message",
        json={
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {
                "name": "definitely_not_real",
                "arguments": {},
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["jsonrpc"] == "2.0"
    assert payload["id"] == 7
    assert payload["error"]["code"] == -32601
    assert payload["error"]["message"] == "Unknown tool: definitely_not_real"


def test_jsonrpc_tools_call_returns_handler_error(monkeypatch, consumer_client):
    async def boom_tool(**_kwargs):
        raise RuntimeError("kaboom")

    monkeypatch.setitem(server.ALL_HANDLERS, "boom_tool", boom_tool)

    response = consumer_client.post(
        "/message",
        json={
            "jsonrpc": "2.0",
            "id": 9,
            "method": "tools/call",
            "params": {
                "name": "boom_tool",
                "arguments": {},
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["jsonrpc"] == "2.0"
    assert payload["id"] == 9
    assert payload["error"] == "kaboom"


def test_jsonrpc_ping_returns_empty_result(consumer_client):
    response = consumer_client.post(
        "/message",
        json={
            "jsonrpc": "2.0",
            "id": 8,
            "method": "ping",
            "params": {},
        },
    )

    assert response.status_code == 200
    assert response.json() == {"jsonrpc": "2.0", "id": 8, "result": {}}


def test_jsonrpc_message_returns_parse_error_for_invalid_json(consumer_client):
    response = consumer_client.post(
        "/message",
        content='{"jsonrpc":"2.0","id":1,"method":"initialize",',
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["jsonrpc"] == "2.0"
    assert payload["error"]["code"] == -32700
    assert payload["error"]["message"] == "Parse error"


def test_jsonrpc_unknown_method_returns_method_not_found(consumer_client):
    response = consumer_client.post(
        "/message",
        json={
            "jsonrpc": "2.0",
            "id": 4,
            "method": "not/a/real_method",
            "params": {},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["jsonrpc"] == "2.0"
    assert payload["id"] == 4
    assert payload["error"]["code"] == -32601
    assert payload["error"]["message"] == "Method not found: not/a/real_method"


def test_jsonrpc_notification_returns_no_content(consumer_client):
    response = consumer_client.post(
        "/message",
        json={
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        },
    )

    assert response.status_code == 204
    assert response.text == ""


def test_jsonrpc_message_returns_404_for_unknown_session(consumer_client):
    response = consumer_client.post(
        "/message?sessionId=missing-session",
        json={
            "jsonrpc": "2.0",
            "id": 5,
            "method": "ping",
            "params": {},
        },
    )

    assert response.status_code == 404
    assert response.json() == {"error": "Unknown session"}


def test_jsonrpc_messages_alias_matches_message_route(consumer_client):
    response = consumer_client.post(
        "/messages",
        json={
            "jsonrpc": "2.0",
            "id": 6,
            "method": "ping",
            "params": {},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload == {"jsonrpc": "2.0", "id": 6, "result": {}}


def test_storage_events_respects_env_db_path_and_creates_parent_dir(temp_event_storage):
    module, db_path = temp_event_storage

    module.init_events_db()

    assert db_path.parent.exists()
    assert db_path.exists()
