"""Persistent agent state management.

Stores the trading agent's state (curriculum stage, active strategies,
portfolio snapshot, learning log, self-assessment) in a SQLite database
so that state survives restarts.
"""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class AgentState:
    """Snapshot of the trading agent's persistent state."""

    current_stage: int = 1
    active_strategies: list[str] = field(default_factory=list)
    portfolio_snapshot: dict = field(default_factory=dict)
    learning_log: list[dict] = field(default_factory=list)
    self_assessment: str = ""


class StateManager:
    """Reads and writes ``AgentState`` fields to a SQLite key-value store.

    Each field of ``AgentState`` is stored as a separate row in the
    ``agent_state`` table (key = field name, value = JSON-serialised).

    Parameters
    ----------
    db_path:
        Path to the SQLite database file.  Parent directories are created
        automatically if they do not exist.
    """

    _FIELDS: tuple[str, ...] = (
        "current_stage",
        "active_strategies",
        "portfolio_snapshot",
        "learning_log",
        "self_assessment",
    )

    def __init__(self, db_path: str = "data/agent_state.db") -> None:
        self._db_path = db_path
        os.makedirs(os.path.dirname(self._db_path) or ".", exist_ok=True)
        self._init_db()

    # ------------------------------------------------------------------
    # Database helpers
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self) -> None:
        """Create the ``agent_state`` table if it does not exist."""
        con = self._connect()
        try:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_state (
                    key   TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            con.commit()
        finally:
            con.close()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save_state(self, state: AgentState) -> None:
        """Serialise *state* to JSON and persist every field to SQLite."""
        state_dict: dict[str, Any] = asdict(state)
        con = self._connect()
        try:
            for key in self._FIELDS:
                value_json = json.dumps(state_dict[key])
                con.execute(
                    """
                    INSERT INTO agent_state (key, value)
                    VALUES (?, ?)
                    ON CONFLICT(key)
                    DO UPDATE SET value = excluded.value
                    """,
                    (key, value_json),
                )
            con.commit()
        finally:
            con.close()

    def load_state(self) -> AgentState:
        """Load state from SQLite, returning defaults for missing fields."""
        defaults = AgentState()
        defaults_dict: dict[str, Any] = asdict(defaults)

        con = self._connect()
        try:
            rows = con.execute(
                "SELECT key, value FROM agent_state"
            ).fetchall()
        finally:
            con.close()

        stored: dict[str, Any] = {}
        for key, value_json in rows:
            if key in self._FIELDS:
                try:
                    stored[key] = json.loads(value_json)
                except (json.JSONDecodeError, TypeError):
                    stored[key] = defaults_dict[key]

        return AgentState(
            current_stage=stored.get("current_stage", defaults_dict["current_stage"]),
            active_strategies=stored.get(
                "active_strategies", defaults_dict["active_strategies"]
            ),
            portfolio_snapshot=stored.get(
                "portfolio_snapshot", defaults_dict["portfolio_snapshot"]
            ),
            learning_log=stored.get("learning_log", defaults_dict["learning_log"]),
            self_assessment=stored.get(
                "self_assessment", defaults_dict["self_assessment"]
            ),
        )

    def update_field(self, key: str, value: Any) -> None:
        """Update a single field in the persisted state.

        Parameters
        ----------
        key:
            Must be one of the ``AgentState`` field names.
        value:
            The new value; will be JSON-serialised before storage.

        Raises
        ------
        ValueError
            If *key* is not a recognised ``AgentState`` field.
        """
        if key not in self._FIELDS:
            raise ValueError(
                f"Unknown state field '{key}'. "
                f"Must be one of {self._FIELDS}"
            )

        value_json = json.dumps(value)
        con = self._connect()
        try:
            con.execute(
                """
                INSERT INTO agent_state (key, value)
                VALUES (?, ?)
                ON CONFLICT(key)
                DO UPDATE SET value = excluded.value
                """,
                (key, value_json),
            )
            con.commit()
        finally:
            con.close()

    def add_learning_entry(self, topic: str, summary: str) -> None:
        """Append a timestamped entry to the learning log.

        Loads the current learning_log from the database, appends the new
        entry, and writes it back.
        """
        state = self.load_state()
        entry: dict[str, str] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "topic": topic,
            "summary": summary,
        }
        state.learning_log.append(entry)
        self.update_field("learning_log", state.learning_log)
