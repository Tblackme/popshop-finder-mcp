from __future__ import annotations

from typing import Any

from db_runtime import connect


def _connect():
    return connect()


def _inventory_from_row(row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "vendor_id": row["vendor_id"],
        "product_name": row["product_name"] or "",
        "sku": row["sku"] or "",
        "quantity": int(row["quantity"] or 0),
        "material_type": row["material_type"] or "",
        "last_updated": row["last_updated"] or "",
    }


def init_inventory_db() -> None:
    conn = _connect()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vendor_id INTEGER NOT NULL,
                product_name TEXT NOT NULL,
                sku TEXT,
                quantity INTEGER NOT NULL DEFAULT 0,
                material_type TEXT,
                last_updated TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def create_inventory_item(
    vendor_id: int,
    product_name: str,
    sku: str,
    quantity: int,
    material_type: str,
) -> dict[str, Any]:
    init_inventory_db()
    name = str(product_name or "").strip()
    if not name:
        raise ValueError("Product name is required.")

    conn = _connect()
    try:
        cursor = conn.execute(
            """
            INSERT INTO inventory (
                vendor_id,
                product_name,
                sku,
                quantity,
                material_type,
                last_updated
            ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                int(vendor_id),
                name,
                str(sku or "").strip(),
                int(quantity or 0),
                str(material_type or "").strip(),
            ),
        )
        item_id = cursor.lastrowid
        conn.commit()
        row = conn.execute("SELECT * FROM inventory WHERE id = ?", (item_id,)).fetchone()
    finally:
        conn.close()

    if not row:
        raise ValueError("Inventory item could not be created.")
    return _inventory_from_row(row)


def update_inventory_item(id: int, quantity: int) -> dict[str, Any] | None:
    init_inventory_db()
    conn = _connect()
    try:
        conn.execute(
            """
            UPDATE inventory
            SET quantity = ?, last_updated = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (int(quantity or 0), int(id)),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM inventory WHERE id = ?", (int(id),)).fetchone()
    finally:
        conn.close()

    return _inventory_from_row(row) if row else None


def get_vendor_inventory(vendor_id: int) -> list[dict[str, Any]]:
    init_inventory_db()
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT *
            FROM inventory
            WHERE vendor_id = ?
            ORDER BY product_name ASC, id ASC
            """,
            (int(vendor_id),),
        ).fetchall()
    finally:
        conn.close()

    return [_inventory_from_row(row) for row in rows]


def delete_inventory_item(id: int) -> bool:
    init_inventory_db()
    conn = _connect()
    try:
        existing = conn.execute("SELECT id FROM inventory WHERE id = ?", (int(id),)).fetchone()
        deleted = existing is not None
        if deleted:
            conn.execute("DELETE FROM inventory WHERE id = ?", (int(id),))
        conn.commit()
    finally:
        conn.close()

    return deleted
