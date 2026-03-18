from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "vendor_atlas.db"


def _database_url() -> str:
    return (os.environ.get("DATABASE_URL") or "").strip()


def using_postgres() -> bool:
    url = _database_url().lower()
    return url.startswith("postgres://") or url.startswith("postgresql://")


def sqlite_db_path() -> Path:
    env_path = os.environ.get("VENDOR_ATLAS_DB_PATH")
    return Path(env_path).expanduser() if env_path else DEFAULT_DB_PATH


def backend_summary() -> dict[str, Any]:
    if using_postgres():
        parsed = urlparse(_database_url())
        database_name = (parsed.path or "").lstrip("/") or "postgres"
        return {
            "engine": "postgres",
            "provider": "external",
            "host": parsed.hostname or "",
            "port": parsed.port or 5432,
            "database": database_name,
            "configured": True,
        }

    db_path = sqlite_db_path()
    return {
        "engine": "sqlite",
        "provider": "local",
        "path": str(db_path),
        "configured": True,
    }


class DBRow(dict):
    def keys(self):
        return super().keys()


class DBResult:
    def __init__(self, rows: list[DBRow] | None = None, lastrowid: Any = None):
        self._rows = rows or []
        self.lastrowid = lastrowid

    def fetchone(self) -> DBRow | None:
        return self._rows[0] if self._rows else None

    def fetchall(self) -> list[DBRow]:
        return list(self._rows)


def _normalize_rows_from_sqlite(cursor: sqlite3.Cursor) -> list[DBRow]:
    if cursor.description is None:
        return []
    rows = cursor.fetchall()
    normalized: list[DBRow] = []
    for row in rows:
        normalized.append(DBRow({key: row[key] for key in row.keys()}))
    return normalized


def _split_sql_script(script: str) -> list[str]:
    statements = []
    current = []
    in_single = False
    in_double = False
    for ch in script:
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        if ch == ";" and not in_single and not in_double:
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
        else:
            current.append(ch)
    tail = "".join(current).strip()
    if tail:
        statements.append(tail)
    return statements


_NAMED_PARAM_RE = re.compile(r":([A-Za-z_][A-Za-z0-9_]*)")


def _translate_sql(sql: str, params: Any) -> tuple[str, Any]:
    if isinstance(params, dict):
        return _NAMED_PARAM_RE.sub(r"%(\1)s", sql), params
    if params is None:
        return sql, params
    translated = []
    for ch in sql:
        translated.append("%s" if ch == "?" else ch)
    return "".join(translated), params


class DBConnection:
    def __init__(self, raw: Any, kind: str):
        self.raw = raw
        self.kind = kind

    def execute(self, sql: str, params: Any = None) -> DBResult:
        if self.kind == "sqlite":
            cursor = self.raw.execute(sql, params or ())
            return DBResult(_normalize_rows_from_sqlite(cursor), getattr(cursor, "lastrowid", None))

        translated_sql, translated_params = _translate_sql(sql, params)
        with self.raw.cursor() as cur:
            cur.execute(translated_sql, translated_params)
            rows: list[DBRow] = []
            if cur.description is not None:
                rows = [DBRow(dict(row)) for row in cur.fetchall()]
            return DBResult(rows)

    def executemany(self, sql: str, seq_of_params: list[Any]) -> None:
        if self.kind == "sqlite":
            self.raw.executemany(sql, seq_of_params)
            return

        translated_sql, _ = _translate_sql(sql, seq_of_params[0] if seq_of_params else None)
        with self.raw.cursor() as cur:
            cur.executemany(translated_sql, seq_of_params)

    def executescript(self, script: str) -> None:
        if self.kind == "sqlite":
            self.raw.executescript(script)
            return
        for statement in _split_sql_script(script):
            self.execute(statement)

    def table_columns(self, table_name: str) -> set[str]:
        if self.kind == "sqlite":
            rows = self.execute(f"PRAGMA table_info({table_name})").fetchall()
            return {str(row["name"]) for row in rows}
        rows = self.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            """,
            (table_name,),
        ).fetchall()
        return {str(row["column_name"]) for row in rows}

    def commit(self) -> None:
        self.raw.commit()

    def close(self) -> None:
        self.raw.close()


def connect() -> DBConnection:
    if using_postgres():
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError(
                "DATABASE_URL is set to Postgres, but psycopg is not installed. "
                "Install dependencies from requirements.txt."
            ) from exc
        raw = psycopg.connect(_database_url(), row_factory=dict_row)
        return DBConnection(raw, "postgres")

    db_path = sqlite_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    raw = sqlite3.connect(db_path)
    raw.row_factory = sqlite3.Row
    return DBConnection(raw, "sqlite")
