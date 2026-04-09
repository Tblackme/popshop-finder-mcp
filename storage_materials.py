"""
Material inventory storage for Vendor Atlas AI Production Planner.

Tables
------
material_inventory   — raw materials a vendor tracks (wax, jars, wicks, etc.)
product_materials    — recipe: how much of each material is required per product
"""
from __future__ import annotations

from typing import Any

from db_runtime import connect


def _connect():
    conn = connect()
    if getattr(conn, "kind", "") == "sqlite":
        conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _mat_from_row(row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "vendor_id": row["vendor_id"],
        "material_name": row["material_name"] or "",
        "quantity": float(row["quantity"] or 0),
        "unit": row["unit"] or "",
        "supplier_url": row["supplier_url"] or "",
        "shipping_days": int(row["shipping_days"] or 0),
        "last_price": float(row["last_price"] or 0),
        "low_stock_threshold": float(row["low_stock_threshold"] or 0),
        "last_updated": row["last_updated"] or "",
    }


def _recipe_from_row(row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "product_id": row["product_id"],
        "material_id": row["material_id"],
        "quantity_required": float(row["quantity_required"] or 0),
    }


# ── SCHEMA ────────────────────────────────────────────────────────────────────

def init_materials_db() -> None:
    conn = _connect()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS material_inventory (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                vendor_id            INTEGER NOT NULL,
                material_name        TEXT    NOT NULL,
                quantity             REAL    NOT NULL DEFAULT 0,
                unit                 TEXT    NOT NULL DEFAULT 'units',
                supplier_url         TEXT,
                shipping_days        INTEGER NOT NULL DEFAULT 0,
                last_price           REAL    NOT NULL DEFAULT 0,
                low_stock_threshold  REAL    NOT NULL DEFAULT 0,
                last_updated         TEXT    DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_mat_inv_vendor ON material_inventory(vendor_id)"
        )
        conn.execute("""
            CREATE TABLE IF NOT EXISTS product_materials (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id        INTEGER NOT NULL,
                material_id       INTEGER NOT NULL,
                quantity_required REAL    NOT NULL DEFAULT 1,
                UNIQUE (product_id, material_id)
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_prod_mat_product ON product_materials(product_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_prod_mat_material ON product_materials(material_id)"
        )
        conn.commit()
    finally:
        conn.close()


# ── Material Inventory CRUD ───────────────────────────────────────────────────

def create_material(
    vendor_id: int,
    material_name: str,
    quantity: float,
    unit: str = "units",
    *,
    supplier_url: str = "",
    shipping_days: int = 0,
    last_price: float = 0.0,
    low_stock_threshold: float = 0.0,
) -> dict[str, Any]:
    init_materials_db()
    name = str(material_name or "").strip()
    if not name:
        raise ValueError("material_name is required.")
    conn = _connect()
    try:
        cursor = conn.execute(
            """
            INSERT INTO material_inventory
                (vendor_id, material_name, quantity, unit,
                 supplier_url, shipping_days, last_price, low_stock_threshold,
                 last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                int(vendor_id),
                name,
                float(quantity or 0),
                str(unit or "units").strip(),
                str(supplier_url or "").strip(),
                int(shipping_days or 0),
                float(last_price or 0),
                float(low_stock_threshold or 0),
            ),
        )
        mat_id = cursor.lastrowid
        conn.commit()
        row = conn.execute(
            "SELECT * FROM material_inventory WHERE id = ?", (mat_id,)
        ).fetchone()
    finally:
        conn.close()
    if not row:
        raise ValueError("Material could not be created.")
    return _mat_from_row(row)


def get_material(material_id: int, vendor_id: int) -> dict[str, Any] | None:
    init_materials_db()
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM material_inventory WHERE id = ? AND vendor_id = ?",
            (int(material_id), int(vendor_id)),
        ).fetchone()
    finally:
        conn.close()
    return _mat_from_row(row) if row else None


def list_materials(vendor_id: int) -> list[dict[str, Any]]:
    init_materials_db()
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT * FROM material_inventory
            WHERE vendor_id = ?
            ORDER BY material_name ASC
            """,
            (int(vendor_id),),
        ).fetchall()
    finally:
        conn.close()
    return [_mat_from_row(r) for r in rows]


def update_material(
    material_id: int,
    vendor_id: int,
    fields: dict[str, Any],
) -> dict[str, Any] | None:
    init_materials_db()
    allowed = {
        "material_name", "quantity", "unit",
        "supplier_url", "shipping_days", "last_price", "low_stock_threshold",
    }
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return get_material(material_id, vendor_id)
    updates["last_updated"] = "CURRENT_TIMESTAMP"
    # Build SET clause; handle CURRENT_TIMESTAMP specially
    set_parts = []
    params: list[Any] = []
    for k, v in updates.items():
        if k == "last_updated":
            set_parts.append("last_updated = CURRENT_TIMESTAMP")
        else:
            set_parts.append(f"{k} = ?")
            params.append(v)
    params += [int(material_id), int(vendor_id)]
    conn = _connect()
    try:
        conn.execute(
            f"UPDATE material_inventory SET {', '.join(set_parts)} WHERE id = ? AND vendor_id = ?",
            params,
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM material_inventory WHERE id = ? AND vendor_id = ?",
            (int(material_id), int(vendor_id)),
        ).fetchone()
    finally:
        conn.close()
    return _mat_from_row(row) if row else None


def delete_material(material_id: int, vendor_id: int) -> bool:
    init_materials_db()
    conn = _connect()
    try:
        exists = conn.execute(
            "SELECT id FROM material_inventory WHERE id = ? AND vendor_id = ?",
            (int(material_id), int(vendor_id)),
        ).fetchone()
        if not exists:
            return False
        conn.execute(
            "DELETE FROM material_inventory WHERE id = ? AND vendor_id = ?",
            (int(material_id), int(vendor_id)),
        )
        conn.commit()
    finally:
        conn.close()
    return True


def get_low_stock_materials(vendor_id: int) -> list[dict[str, Any]]:
    """Return materials where quantity <= low_stock_threshold."""
    init_materials_db()
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT * FROM material_inventory
            WHERE vendor_id = ?
              AND low_stock_threshold > 0
              AND quantity <= low_stock_threshold
            ORDER BY (quantity - low_stock_threshold) ASC
            """,
            (int(vendor_id),),
        ).fetchall()
    finally:
        conn.close()
    return [_mat_from_row(r) for r in rows]


# ── Product Material Recipes CRUD ────────────────────────────────────────────

def upsert_product_material(
    product_id: int,
    material_id: int,
    quantity_required: float,
) -> dict[str, Any]:
    """Set how much of a material is needed to make one unit of a product."""
    init_materials_db()
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO product_materials (product_id, material_id, quantity_required)
            VALUES (?, ?, ?)
            ON CONFLICT (product_id, material_id)
            DO UPDATE SET quantity_required = excluded.quantity_required
            """,
            (int(product_id), int(material_id), float(quantity_required or 0)),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM product_materials WHERE product_id = ? AND material_id = ?",
            (int(product_id), int(material_id)),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        raise ValueError("Recipe entry could not be saved.")
    return _recipe_from_row(row)


def get_product_recipe(product_id: int) -> list[dict[str, Any]]:
    """Return all material requirements for a given product."""
    init_materials_db()
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT pm.*, mi.material_name, mi.unit, mi.quantity AS stock,
                   mi.vendor_id, mi.shipping_days, mi.last_price
            FROM product_materials pm
            JOIN material_inventory mi ON mi.id = pm.material_id
            WHERE pm.product_id = ?
            ORDER BY mi.material_name ASC
            """,
            (int(product_id),),
        ).fetchall()
    finally:
        conn.close()
    result = []
    for r in rows:
        entry = _recipe_from_row(r)
        entry["material_name"] = r["material_name"] or ""
        entry["unit"] = r["unit"] or ""
        entry["stock"] = float(r["stock"] or 0)
        entry["shipping_days"] = int(r["shipping_days"] or 0)
        entry["last_price"] = float(r["last_price"] or 0)
        result.append(entry)
    return result


def get_recipes_for_vendor(vendor_id: int) -> list[dict[str, Any]]:
    """Return all product–material relationships for a vendor's materials."""
    init_materials_db()
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT pm.*,
                   mi.material_name, mi.unit, mi.quantity AS stock,
                   mi.shipping_days, mi.last_price, mi.low_stock_threshold
            FROM product_materials pm
            JOIN material_inventory mi ON mi.id = pm.material_id
            WHERE mi.vendor_id = ?
            ORDER BY pm.product_id ASC, mi.material_name ASC
            """,
            (int(vendor_id),),
        ).fetchall()
    finally:
        conn.close()
    result = []
    for r in rows:
        entry = _recipe_from_row(r)
        entry["material_name"] = r["material_name"] or ""
        entry["unit"] = r["unit"] or ""
        entry["stock"] = float(r["stock"] or 0)
        entry["shipping_days"] = int(r["shipping_days"] or 0)
        entry["last_price"] = float(r["last_price"] or 0)
        entry["low_stock_threshold"] = float(r["low_stock_threshold"] or 0)
        result.append(entry)
    return result


def delete_product_material(product_id: int, material_id: int) -> bool:
    init_materials_db()
    conn = _connect()
    try:
        exists = conn.execute(
            "SELECT id FROM product_materials WHERE product_id = ? AND material_id = ?",
            (int(product_id), int(material_id)),
        ).fetchone()
        if not exists:
            return False
        conn.execute(
            "DELETE FROM product_materials WHERE product_id = ? AND material_id = ?",
            (int(product_id), int(material_id)),
        )
        conn.commit()
    finally:
        conn.close()
    return True
