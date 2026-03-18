"""
Shopify connection and product cache for Vendor Atlas.

Stores OAuth tokens and synced product/inventory data per user.
Uses the same SQLite DB as storage_users (same DB_PATH).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from db_runtime import connect, using_postgres

def _connect():
    return connect()


def init_shopify_db() -> None:
    conn = _connect()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS shopify_connections (
                user_id INTEGER PRIMARY KEY,
                shop_domain TEXT NOT NULL,
                access_token TEXT NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        columns = conn.table_columns("shopify_connections")
        if "storefront_domain" not in columns:
            conn.execute("ALTER TABLE shopify_connections ADD COLUMN storefront_domain TEXT")
        if "storefront_access_token" not in columns:
            conn.execute("ALTER TABLE shopify_connections ADD COLUMN storefront_access_token TEXT")
        if using_postgres():
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS shopify_products (
                    id BIGSERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    shop_product_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    price REAL NOT NULL DEFAULT 0,
                    inventory_quantity INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, shop_product_id),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
                """
            )
        else:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS shopify_products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    shop_product_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    price REAL NOT NULL DEFAULT 0,
                    inventory_quantity INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, shop_product_id),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
                """
            )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_shopify_products_user ON shopify_products(user_id)"
        )
        conn.commit()
    finally:
        conn.close()


def get_shopify_connection(user_id: int) -> dict[str, Any] | None:
    init_shopify_db()
    conn = _connect()
    try:
        row = conn.execute(
            """
            SELECT user_id, shop_domain, access_token, storefront_domain, storefront_access_token, updated_at
            FROM shopify_connections
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    return {
        "user_id": row["user_id"],
        "shop_domain": row["shop_domain"],
        "storefront_domain": row["storefront_domain"] or "",
        "storefront_connected": bool(row["storefront_access_token"]),
        "updated_at": row["updated_at"] or "",
    }


def set_shopify_connection(
    user_id: int,
    shop_domain: str,
    access_token: str,
) -> None:
    init_shopify_db()
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO shopify_connections (user_id, shop_domain, access_token, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                shop_domain = excluded.shop_domain,
                access_token = excluded.access_token,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, shop_domain.strip().lower(), access_token),
        )
        conn.commit()
    finally:
        conn.close()


def get_shopify_access_token(user_id: int) -> str | None:
    init_shopify_db()
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT access_token FROM shopify_connections WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()
    return row["access_token"] if row else None


def set_shopify_storefront_connection(
    user_id: int,
    storefront_domain: str,
    storefront_access_token: str,
) -> None:
    init_shopify_db()
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO shopify_connections (
                user_id,
                shop_domain,
                access_token,
                storefront_domain,
                storefront_access_token,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                storefront_domain = excluded.storefront_domain,
                storefront_access_token = excluded.storefront_access_token,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, storefront_domain.strip().lower(), "", storefront_domain.strip().lower(), storefront_access_token),
        )
        conn.commit()
    finally:
        conn.close()


def get_shopify_storefront_access_token(user_id: int) -> str | None:
    init_shopify_db()
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT storefront_access_token FROM shopify_connections WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()
    return row["storefront_access_token"] if row and row["storefront_access_token"] else None


def disconnect_shopify(user_id: int) -> None:
    init_shopify_db()
    conn = _connect()
    try:
        conn.execute("DELETE FROM shopify_connections WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM shopify_products WHERE user_id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()


def upsert_shopify_products(user_id: int, products: list[dict[str, Any]]) -> None:
    """Replace cached products for this user."""
    init_shopify_db()
    conn = _connect()
    try:
        conn.execute("DELETE FROM shopify_products WHERE user_id = ?", (user_id,))
        for p in products:
            conn.execute(
                """
                INSERT INTO shopify_products (user_id, shop_product_id, name, price, inventory_quantity, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    user_id,
                    str(p.get("id", "")),
                    str(p.get("name", ""))[:500],
                    float(p.get("price", 0)),
                    int(p.get("inventory_quantity", 0)),
                ),
            )
        conn.commit()
    finally:
        conn.close()


def get_shopify_products(user_id: int) -> list[dict[str, Any]]:
    init_shopify_db()
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT shop_product_id, name, price, inventory_quantity, updated_at
            FROM shopify_products
            WHERE user_id = ?
            ORDER BY inventory_quantity DESC, price DESC
            """,
            (user_id,),
        ).fetchall()
    finally:
        conn.close()
    return [
        {
            "id": row["shop_product_id"],
            "name": row["name"],
            "price": row["price"],
            "inventory_quantity": row["inventory_quantity"],
            "updated_at": row["updated_at"] or "",
        }
        for row in rows
    ]
