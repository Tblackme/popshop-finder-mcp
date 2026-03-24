"""
Production task storage for Vendor Atlas Smart Planner.

Table
-----
production_tasks  — per-vendor production to-do items linked to events
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from db_runtime import connect


def _connect():
    conn = connect()
    if getattr(conn, "kind", "") == "sqlite":
        conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row(row) -> dict[str, Any] | None:
    if not row:
        return None
    return {k: row[k] for k in row.keys()}


def _rows(rows) -> list[dict[str, Any]]:
    return [{k: r[k] for k in r.keys()} for r in rows]


# ── SCHEMA ────────────────────────────────────────────────────────────────────

def init_production_db() -> None:
    conn = _connect()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS production_tasks (
                id           TEXT PRIMARY KEY,
                vendor_id    INTEGER NOT NULL,
                event_id     TEXT,
                event_name   TEXT,
                product_name TEXT NOT NULL,
                quantity_to_make INTEGER NOT NULL DEFAULT 0,
                due_date     TEXT,
                status       TEXT NOT NULL DEFAULT 'pending'
                                 CHECK (status IN ('pending', 'in_progress', 'done', 'cancelled')),
                created_at   TEXT NOT NULL
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_prod_tasks_vendor ON production_tasks(vendor_id)"
        )
        conn.commit()
    finally:
        conn.close()


# ── CRUD ──────────────────────────────────────────────────────────────────────

def create_production_task(
    vendor_id: int,
    product_name: str,
    quantity_to_make: int,
    *,
    event_id: str | None = None,
    event_name: str | None = None,
    due_date: str | None = None,
    status: str = "pending",
) -> dict[str, Any]:
    init_production_db()
    task_id = _uuid()
    now = _now()
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO production_tasks
                (id, vendor_id, event_id, event_name, product_name,
                 quantity_to_make, due_date, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (task_id, vendor_id, event_id, event_name, product_name,
             quantity_to_make, due_date, status, now),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM production_tasks WHERE id = ?", (task_id,)
        ).fetchone()
        return _row(row)  # type: ignore[return-value]
    finally:
        conn.close()


def list_production_tasks(
    vendor_id: int,
    *,
    status: str | None = None,
    event_id: str | None = None,
) -> list[dict[str, Any]]:
    init_production_db()
    clauses = ["vendor_id = ?"]
    params: list[Any] = [vendor_id]
    if status:
        clauses.append("status = ?")
        params.append(status)
    if event_id:
        clauses.append("event_id = ?")
        params.append(event_id)
    sql = (
        "SELECT * FROM production_tasks WHERE "
        + " AND ".join(clauses)
        + " ORDER BY due_date ASC NULLS LAST, created_at ASC"
    )
    conn = _connect()
    try:
        rows = conn.execute(sql, params).fetchall()
        return _rows(rows)
    finally:
        conn.close()


def get_production_task(task_id: str, vendor_id: int) -> dict[str, Any] | None:
    init_production_db()
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM production_tasks WHERE id = ? AND vendor_id = ?",
            (task_id, vendor_id),
        ).fetchone()
        return _row(row)
    finally:
        conn.close()


def update_production_task(
    task_id: str,
    vendor_id: int,
    fields: dict[str, Any],
) -> dict[str, Any] | None:
    init_production_db()
    allowed = {"product_name", "quantity_to_make", "due_date", "status"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return get_production_task(task_id, vendor_id)
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    params = list(updates.values()) + [task_id, vendor_id]
    conn = _connect()
    try:
        conn.execute(
            f"UPDATE production_tasks SET {set_clause} WHERE id = ? AND vendor_id = ?",
            params,
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM production_tasks WHERE id = ? AND vendor_id = ?",
            (task_id, vendor_id),
        ).fetchone()
        return _row(row)
    finally:
        conn.close()


def delete_production_task(task_id: str, vendor_id: int) -> bool:
    init_production_db()
    # Check existence before deleting so we can return a meaningful bool
    # without relying on SQLite-only changes().
    conn = _connect()
    try:
        exists = conn.execute(
            "SELECT id FROM production_tasks WHERE id = ? AND vendor_id = ?",
            (task_id, vendor_id),
        ).fetchone()
        if not exists:
            return False
        conn.execute(
            "DELETE FROM production_tasks WHERE id = ? AND vendor_id = ?",
            (task_id, vendor_id),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def bulk_create_production_tasks(
    vendor_id: int,
    tasks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Create multiple tasks at once; return all created records."""
    return [
        create_production_task(
            vendor_id,
            t["product_name"],
            int(t.get("quantity_to_make", 0)),
            event_id=t.get("event_id"),
            event_name=t.get("event_name"),
            due_date=t.get("due_date"),
            status=t.get("status", "pending"),
        )
        for t in tasks
    ]
