# db/database.py

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "ads_rules.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def utc_now_str() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def init_db() -> None:
    """Crea le tabelle se non esistono."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                rule_type TEXT NOT NULL,                -- 'ACOS_BAND' o 'LOW_TRAFFIC'
                campaign_id TEXT,                       -- null = tutte
                marketplace TEXT,                       -- 'US', 'IT', ecc.
                match_type TEXT,                        -- 'exact', 'phrase', 'broad'

                acos_min REAL,                          -- per ACOS_BAND
                acos_max REAL,

                clicks_min INTEGER,                     -- per LOW_TRAFFIC (se serve)
                clicks_max INTEGER,

                adjustment_type TEXT NOT NULL,          -- 'ABS' o 'PCT'
                adjustment_value REAL NOT NULL,         -- es: 0.05 o 10

                timeframe_days INTEGER,                 -- 14, 30, 60, 90, -1 = lifetime
                frequency_days INTEGER NOT NULL,        -- 3, 5, 7, 10, 15

                enabled INTEGER NOT NULL DEFAULT 1,

                last_run_at TEXT,                       -- ISO datetime
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS rule_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_id INTEGER NOT NULL,
                run_at TEXT NOT NULL,

                target_id TEXT,
                campaign_id TEXT,
                keyword_text TEXT,
                match_type TEXT,

                old_bid REAL,
                new_bid REAL,

                acos REAL,
                clicks INTEGER,
                impressions INTEGER,

                action TEXT NOT NULL,                   -- 'INCREASE', 'DECREASE', 'NO_ACTION', 'SKIP'
                message TEXT,

                FOREIGN KEY (rule_id) REFERENCES rules (id)
            );

            CREATE INDEX IF NOT EXISTS idx_rules_enabled
                ON rules (enabled);

            CREATE INDEX IF NOT EXISTS idx_rule_exec_rule_id
                ON rule_executions (rule_id);
            """
        )
        conn.commit()


# ------------------------
# CRUD regole
# ------------------------

def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {k: row[k] for k in row.keys()}


def get_all_rules() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM rules ORDER BY id;")
        rows = cur.fetchall()
    return [row_to_dict(r) for r in rows]


def get_rule(rule_id: int) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM rules WHERE id = ?;", (rule_id,))
        row = cur.fetchone()
    return row_to_dict(row) if row else None


def create_rule(data: Dict[str, Any]) -> int:
    now = utc_now_str()
    fields = [
        "name",
        "rule_type",
        "campaign_id",
        "marketplace",
        "match_type",
        "acos_min",
        "acos_max",
        "clicks_min",
        "clicks_max",
        "adjustment_type",
        "adjustment_value",
        "timeframe_days",
        "frequency_days",
        "enabled",
    ]
    values = [data.get(f) for f in fields]

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"""
            INSERT INTO rules (
                {", ".join(fields)},
                last_run_at,
                created_at,
                updated_at
            )
            VALUES (
                {", ".join(["?"] * len(fields))},
                NULL,
                ?,
                ?
            );
            """,
            values + [now, now],
        )
        conn.commit()
        return cur.lastrowid


def update_rule(rule_id: int, data: Dict[str, Any]) -> None:
    now = utc_now_str()
    allowed_fields = {
        "name",
        "rule_type",
        "campaign_id",
        "marketplace",
        "match_type",
        "acos_min",
        "acos_max",
        "clicks_min",
        "clicks_max",
        "adjustment_type",
        "adjustment_value",
        "timeframe_days",
        "frequency_days",
        "enabled",
    }

    set_parts = []
    values: List[Any] = []
    for key, value in data.items():
        if key in allowed_fields:
            set_parts.append(f"{key} = ?")
            values.append(value)

    if not set_parts:
        return

    set_clause = ", ".join(set_parts) + ", updated_at = ?"
    values.append(now)
    values.append(rule_id)

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"UPDATE rules SET {set_clause} WHERE id = ?;",
            values,
        )
        conn.commit()


def delete_rule(rule_id: int) -> None:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM rules WHERE id = ?;", (rule_id,))
        conn.commit()


def set_rule_enabled(rule_id: int, enabled: bool) -> None:
    update_rule(rule_id, {"enabled": 1 if enabled else 0})


# ------------------------
# Regole "due" per scheduler
# ------------------------

def get_due_rules(now: Optional[datetime] = None) -> List[Dict[str, Any]]:
    if now is None:
        now = datetime.utcnow()
    now_str = now.isoformat(timespec="seconds") + "Z"

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT *
            FROM rules
            WHERE enabled = 1
              AND (
                    last_run_at IS NULL
                    OR julianday(?) - julianday(last_run_at) >= frequency_days
                  );
            """,
            (now_str,),
        )
        rows = cur.fetchall()

    return [row_to_dict(r) for r in rows]


def update_rule_last_run(rule_id: int, run_at: Optional[datetime] = None) -> None:
    if run_at is None:
        run_at = datetime.utcnow()
    run_str = run_at.isoformat(timespec="seconds") + "Z"
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE rules SET last_run_at = ?, updated_at = ? WHERE id = ?;",
            (run_str, run_str, rule_id),
        )
        conn.commit()


# ------------------------
# Log esecuzioni
# ------------------------

def log_rule_execution(
    rule_id: int,
    run_at: datetime,
    target: Dict[str, Any],
    old_bid: Optional[float],
    new_bid: Optional[float],
    action: str,
    message: str = "",
) -> None:
    """Salva un log per una singola keyword o target."""

    run_str = run_at.isoformat(timespec="seconds") + "Z"

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO rule_executions (
                rule_id,
                run_at,
                target_id,
                campaign_id,
                keyword_text,
                match_type,
                old_bid,
                new_bid,
                acos,
                clicks,
                impressions,
                action,
                message
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                rule_id,
                run_str,
                target.get("target_id"),
                target.get("campaign_id"),
                target.get("keyword_text"),
                target.get("match_type"),
                old_bid,
                new_bid,
                target.get("acos"),
                target.get("clicks"),
                target.get("impressions"),
                action,
                message,
            ),
        )
        conn.commit()
