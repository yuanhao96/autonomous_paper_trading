"""SQLite database management for strategy registry."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.core.config import PROJECT_ROOT


_DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "registry.db"


def get_engine(db_path: Path | None = None) -> Engine:
    """Create or get a SQLAlchemy engine for the strategy registry."""
    if db_path is None:
        db_path = _DEFAULT_DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{db_path}", echo=False)


def init_db(engine: Engine) -> None:
    """Initialize the database schema."""
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS strategies (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                template TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                spec_json TEXT NOT NULL,
                parent_id TEXT,
                generation INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                created_by TEXT NOT NULL DEFAULT 'human'
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                spec_id TEXT NOT NULL,
                phase TEXT NOT NULL,
                passed INTEGER NOT NULL DEFAULT 0,
                metrics_json TEXT NOT NULL,
                failure_reason TEXT,
                failure_details TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (spec_id) REFERENCES strategies(id)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS universes (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                spec_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS deployments (
                id TEXT PRIMARY KEY,
                spec_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                mode TEXT NOT NULL DEFAULT 'paper',
                status TEXT NOT NULL DEFAULT 'pending',
                symbols_json TEXT NOT NULL,
                initial_cash REAL NOT NULL DEFAULT 100000,
                config_json TEXT NOT NULL DEFAULT '{}',
                started_at TEXT NOT NULL,
                stopped_at TEXT,
                FOREIGN KEY (spec_id) REFERENCES strategies(id)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deployment_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                commission REAL NOT NULL DEFAULT 0,
                order_id TEXT,
                executed_at TEXT NOT NULL,
                FOREIGN KEY (deployment_id) REFERENCES deployments(id)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deployment_id TEXT NOT NULL,
                equity REAL NOT NULL,
                cash REAL NOT NULL,
                daily_pnl REAL NOT NULL DEFAULT 0,
                total_pnl REAL NOT NULL DEFAULT 0,
                total_trades INTEGER NOT NULL DEFAULT 0,
                total_fees REAL NOT NULL DEFAULT 0,
                positions_json TEXT NOT NULL DEFAULT '[]',
                recorded_at TEXT NOT NULL,
                FOREIGN KEY (deployment_id) REFERENCES deployments(id)
            )
        """))
