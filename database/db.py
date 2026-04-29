"""SQLite database layer for menu comparison persistence."""

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "menu_comparisons.db"


def _get_connection() -> sqlite3.Connection:
    """Return a connection to the SQLite database, creating it if needed."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create the comparisons table if it does not exist."""
    conn = _get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS comparisons (
            id              TEXT PRIMARY KEY,
            title           TEXT NOT NULL,
            url_our         TEXT NOT NULL DEFAULT '',
            url_reference   TEXT NOT NULL DEFAULT '',
            source_type_our TEXT NOT NULL DEFAULT '',
            source_type_ref TEXT NOT NULL DEFAULT '',
            status          TEXT NOT NULL DEFAULT 'Pending',
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL,
            our_menu_data   TEXT DEFAULT '[]',
            ref_menu_data   TEXT DEFAULT '[]',
            our_normalized  TEXT DEFAULT '[]',
            ref_normalized  TEXT DEFAULT '[]',
            report_data     TEXT DEFAULT '{}',
            pdf_report      BLOB DEFAULT NULL
        )
    """)
    conn.commit()
    conn.close()


# ── CRUD helpers ────────────────────────────────────────────────────

def create_comparison(title: str, url_our: str, url_reference: str,
                      source_type_our: str = "Website URL",
                      source_type_ref: str = "Website URL") -> str:
    """Insert a new comparison row and return its id."""
    comp_id = uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_connection()
    conn.execute(
        """INSERT INTO comparisons
           (id, title, url_our, url_reference, source_type_our, source_type_ref,
            status, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, 'Pending', ?, ?)""",
        (comp_id, title, url_our, url_reference, source_type_our, source_type_ref, now, now),
    )
    conn.commit()
    conn.close()
    return comp_id


def update_comparison(comp_id: str, **kwargs):
    """Update one or more columns for a comparison."""
    allowed = {
        "title", "url_our", "url_reference", "status",
        "our_menu_data", "ref_menu_data", "our_normalized", "ref_normalized",
        "report_data", "pdf_report", "source_type_our", "source_type_ref",
    }
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [comp_id]
    conn = _get_connection()
    conn.execute(f"UPDATE comparisons SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()


def get_comparison(comp_id: str) -> dict | None:
    """Retrieve a single comparison as a dict."""
    conn = _get_connection()
    row = conn.execute("SELECT * FROM comparisons WHERE id = ?", (comp_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_comparisons() -> list[dict]:
    """Return all comparisons ordered by most recent first."""
    conn = _get_connection()
    rows = conn.execute(
        "SELECT id, title, url_our, url_reference, status, created_at, updated_at "
        "FROM comparisons ORDER BY updated_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_comparison(comp_id: str):
    """Delete a comparison by id."""
    conn = _get_connection()
    conn.execute("DELETE FROM comparisons WHERE id = ?", (comp_id,))
    conn.commit()
    conn.close()


def save_report(comp_id: str, report: dict, pdf_bytes: bytes,
                our_menu, ref_menu, our_norm, ref_norm):
    """Persist full comparison results."""
    update_comparison(
        comp_id,
        status="Completed",
        our_menu_data=json.dumps(our_menu, default=str),
        ref_menu_data=json.dumps(ref_menu, default=str),
        our_normalized=json.dumps(our_norm, default=str),
        ref_normalized=json.dumps(ref_norm, default=str),
        report_data=json.dumps(report, default=str),
        pdf_report=pdf_bytes,
    )


def load_report(comp_id: str) -> tuple[dict, bytes | None]:
    """Load report JSON and PDF bytes for a comparison."""
    comp = get_comparison(comp_id)
    if not comp:
        return {}, None
    report = json.loads(comp.get("report_data") or "{}")
    pdf = comp.get("pdf_report")
    return report, pdf


# Auto-init on import
init_db()
