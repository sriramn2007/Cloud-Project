from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./hospital_audit.db")
PROJECT_ROOT = Path(__file__).resolve().parents[1]

_engine = None


def _is_postgres() -> bool:
    return DATABASE_URL.startswith(("postgresql://", "postgres://", "postgresql+psycopg://"))


def init_db() -> None:
    global _engine
    if _is_postgres():
        try:
            from sqlalchemy import create_engine, text
            _engine = create_engine(DATABASE_URL, pool_pre_ping=True)
            with _engine.begin() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS audit_events (
                        id BIGSERIAL PRIMARY KEY,
                        event_type VARCHAR(80) NOT NULL,
                        actor VARCHAR(120),
                        role VARCHAR(40),
                        payload JSONB NOT NULL DEFAULT '{}'::jsonb,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                """))
            return
        except Exception:
            if os.getenv("DATABASE_REQUIRED", "false").lower() == "true":
                raise
    path = PROJECT_ROOT / "backend" / "hospital_audit.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS audit_events (id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT NOT NULL, actor TEXT, role TEXT, payload TEXT NOT NULL, created_at TEXT NOT NULL)")
        conn.commit()


def record_event(event_type: str, actor: str | None, role: str | None, payload: dict[str, Any] | None = None) -> None:
    if _engine is None:
        init_db()
    payload = payload or {}
    created = datetime.now(timezone.utc)
    if _engine is not None:
        from sqlalchemy import text
        with _engine.begin() as conn:
            conn.execute(text("INSERT INTO audit_events (event_type, actor, role, payload) VALUES (:event_type, :actor, :role, :payload)"), {"event_type": event_type, "actor": actor, "role": role, "payload": json.dumps(payload)})
        return
    path = PROJECT_ROOT / "backend" / "hospital_audit.db"
    with sqlite3.connect(path) as conn:
        conn.execute("INSERT INTO audit_events (event_type, actor, role, payload, created_at) VALUES (?, ?, ?, ?, ?)", (event_type, actor, role, json.dumps(payload), created.isoformat()))
        conn.commit()


def recent_events(limit: int = 50) -> list[dict[str, Any]]:
    limit = max(1, min(limit, 200))
    if _engine is not None:
        from sqlalchemy import text
        with _engine.connect() as conn:
            rows = conn.execute(text("SELECT id, event_type, actor, role, payload, created_at FROM audit_events ORDER BY id DESC LIMIT :limit"), {"limit": limit}).mappings().all()
            return [dict(row) for row in rows]
    path = PROJECT_ROOT / "backend" / "hospital_audit.db"
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT id, event_type, actor, role, payload, created_at FROM audit_events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    output = []
    for row in rows:
        item = dict(row)
        item["payload"] = json.loads(item["payload"])
        output.append(item)
    return output
