"""
Shopify OAuth and Admin API helpers for Vendor Atlas.

Uses Shopify Admin REST API 2024-01:
- OAuth: authorize URL, token exchange
- Products: GET /admin/api/2024-01/products.json
- Inventory: GET /admin/api/2024-01/inventory_levels.json (by inventory_item_ids from variants)
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import urllib.parse
from typing import Any

import httpx

SHOPIFY_API_VERSION = "2024-01"


def build_authorize_url(
    shop: str,
    client_id: str,
    redirect_uri: str,
    scopes: str = "read_products,read_inventory",
    state: str | None = None,
) -> str:
    """Build the Shopify OAuth authorize URL. shop must be 'store.myshopify.com'."""
    shop = shop.strip().lower()
    if not shop.endswith(".myshopify.com"):
        shop = f"{shop}.myshopify.com"
    state = state or secrets.token_urlsafe(32)
    params = {
        "client_id": client_id,
        "scope": scopes,
        "redirect_uri": redirect_uri,
        "state": state,
    }
    return f"https://{shop}/admin/oauth/authorize?{urllib.parse.urlencode(params)}"


def verify_hmac(query_dict: dict[str, str], secret: str) -> bool:
    """Verify Shopify's HMAC on the callback query."""
    hmac_received = query_dict.pop("hmac", None)
    if not hmac_received or not secret:
        return False
    # Shopify sorts keys and builds message: key=value&key2=value2
    message = urllib.parse.urlencode(sorted(query_dict.items()))
    expected = hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, hmac_received)


def exchange_code_for_token(
    shop: str,
    code: str,
    client_id: str,
    client_secret: str,
) -> dict[str, Any]:
    """
    Exchange the OAuth code for an access token.
    Returns {"access_token": "...", "scope": "..."} or raises on error.
    """
    shop = shop.strip().lower()
    if not shop.endswith(".myshopify.com"):
        shop = f"{shop}.myshopify.com"
    url = f"https://{shop}/admin/oauth/access_token"
    with httpx.Client() as client:
        resp = client.post(
            url,
            json={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
            },
            headers={"Content-Type": "application/json"},
            timeout=15.0,
        )
        resp.raise_for_status()
        return resp.json()


def fetch_products(shop: str, access_token: str, limit: int = 250) -> list[dict[str, Any]]:
    """
    Fetch products from Shopify Admin API.
    Returns list of { id, title, variants: [{ id, price, inventory_item_id }] }.
    """
    shop = shop.strip().lower()
    if not shop.endswith(".myshopify.com"):
        shop = f"{shop}.myshopify.com"
    url = f"https://{shop}/admin/api/{SHOPIFY_API_VERSION}/products.json"
    all_products: list[dict[str, Any]] = []
    params: dict[str, Any] = {"limit": min(limit, 250)}
    with httpx.Client() as client:
        while True:
            resp = client.get(
                url,
                params=params,
                headers={"X-Shopify-Access-Token": access_token},
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
            products = data.get("products") or []
            all_products.extend(products)
            if len(products) < 250 or len(all_products) >= limit:
                break
            # Next page
            link = resp.headers.get("Link", "")
            if "rel=\"next\"" not in link:
                break
            # Parse next page_info from Link header
            next_url = None
            for part in link.split(","):
                if "rel=\"next\"" in part:
                    part = part.split(";")[0].strip(" <>")
                    next_url = part
                    break
            if not next_url:
                break
            parsed = urllib.parse.urlparse(next_url)
            page_info = urllib.parse.parse_qs(parsed.query).get("page_info", [None])[0]
            if not page_info:
                break
            params = {"limit": 250, "page_info": page_info}
    return all_products[:limit]


def fetch_inventory_levels(
    shop: str,
    access_token: str,
    inventory_item_ids: list[int],
) -> dict[int, int]:
    """
    Fetch inventory levels for given inventory_item_ids.
    Returns map of inventory_item_id -> available quantity.
    """
    if not inventory_item_ids:
        return {}
    shop = shop.strip().lower()
    if not shop.endswith(".myshopify.com"):
        shop = f"{shop}.myshopify.com"
    # API accepts up to 50 ids per request
    result: dict[int, int] = {}
    chunk_size = 50
    for i in range(0, len(inventory_item_ids), chunk_size):
        chunk = inventory_item_ids[i : i + chunk_size]
        ids_param = ",".join(str(x) for x in chunk)
        url = f"https://{shop}/admin/api/{SHOPIFY_API_VERSION}/inventory_levels.json"
        with httpx.Client() as client:
            resp = client.get(
                url,
                params={"inventory_item_ids": ids_param},
                headers={"X-Shopify-Access-Token": access_token},
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
            for level in data.get("inventory_levels") or []:
                item_id = level.get("inventory_item_id")
                if item_id is not None:
                    result[int(item_id)] = int(level.get("available", 0) or 0)
    return result


def products_with_inventory(
    shop: str,
    access_token: str,
    limit: int = 250,
) -> list[dict[str, Any]]:
    """
    Fetch products and their inventory, return flattened list for our app:
    [ { id, name, price, inventory_quantity }, ... ]
    Uses first variant per product; sums inventory across locations per item.
    """
    products = fetch_products(shop, access_token, limit=limit)
    inventory_item_ids: list[int] = []
    product_by_item: dict[int, dict[str, Any]] = {}
    for p in products:
        variants = p.get("variants") or []
        for v in variants:
            item_id = v.get("inventory_item_id")
            if item_id is not None:
                try:
                    iid = int(item_id)
                    inventory_item_ids.append(iid)
                    price = float(v.get("price") or 0)
                    product_by_item[iid] = {
                        "id": str(p.get("id", "")),
                        "name": (p.get("title") or "").strip() or (v.get("title") or "Product"),
                        "price": price,
                        "inventory_item_id": iid,
                    }
                except (TypeError, ValueError):
                    continue
    levels = fetch_inventory_levels(shop, access_token, inventory_item_ids)
    # Group by product id and sum inventory
    by_product: dict[str, dict[str, Any]] = {}
    for item_id, qty in levels.items():
        if item_id not in product_by_item:
            continue
        row = product_by_item[item_id]
        pid = row["id"]
        if pid not in by_product:
            by_product[pid] = {"id": pid, "name": row["name"], "price": row["price"], "inventory_quantity": 0}
        by_product[pid]["inventory_quantity"] += qty
    return list(by_product.values())


def fetch_storefront_products(
    shop: str,
    storefront_access_token: str = "",
    limit: int = 10,
    private_token: bool = False,
) -> list[dict[str, Any]]:
    """
    Fetch a lightweight public product payload from Shopify Storefront GraphQL.
    Returns:
    [
      {
        "id": "...",
        "name": "Product",
        "handle": "product-handle",
        "image": "https://...",
        "price": 24.0,
        "product_url": "https://shop.myshopify.com/products/product-handle",
      }
    ]
    """
    shop = shop.strip().lower()
    if not shop.endswith(".myshopify.com"):
        shop = f"{shop}.myshopify.com"
    safe_limit = max(1, min(int(limit or 10), 50))
    url = f"https://{shop}/api/{SHOPIFY_API_VERSION}/graphql.json"
    query = """
    query VendorAtlasStorefrontProducts($first: Int!) {
      products(first: $first) {
        edges {
          node {
            id
            title
            handle
            images(first: 1) {
              edges {
                node {
                  url
                }
              }
            }
            variants(first: 1) {
              edges {
                node {
                  price {
                    amount
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    headers = {"Content-Type": "application/json"}
    if storefront_access_token:
        # Private tokens use a different header per Shopify docs
        if private_token:
            headers["Shopify-Storefront-Private-Token"] = storefront_access_token
        else:
            headers["X-Shopify-Storefront-Access-Token"] = storefront_access_token
    with httpx.Client() as client:
        response = client.post(
            url,
            json={"query": query, "variables": {"first": safe_limit}},
            headers=headers,
            timeout=20.0,
        )
        response.raise_for_status()
        payload = response.json()
    if payload.get("errors"):
        message = payload["errors"][0].get("message") or "Storefront request failed."
        raise RuntimeError(message)
    edges = (((payload.get("data") or {}).get("products") or {}).get("edges") or [])
    products: list[dict[str, Any]] = []
    for edge in edges:
        node = edge.get("node") or {}
        image_edges = (((node.get("images") or {}).get("edges")) or [])
        variant_edges = (((node.get("variants") or {}).get("edges")) or [])
        first_image = (image_edges[0].get("node") or {}) if image_edges else {}
        first_variant = (variant_edges[0].get("node") or {}) if variant_edges else {}
        price = (((first_variant.get("price") or {}).get("amount")))
        handle = str(node.get("handle") or "").strip()
        products.append(
            {
                "id": str(node.get("id") or ""),
                "name": str(node.get("title") or "Product").strip() or "Product",
                "handle": handle,
                "image": str(first_image.get("url") or "").strip(),
                "price": float(price or 0),
                "product_url": f"https://{shop}/products/{handle}" if handle else "",
            }
        )
    return products
