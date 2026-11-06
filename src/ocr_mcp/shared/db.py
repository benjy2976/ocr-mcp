"""Base SQLite del servidor y sus migraciones.

El esquema cambia solo por migraciones SQL numeradas en `ocr_mcp/migrations/`,
que se aplican en orden al arrancar y nunca se editan una vez publicadas. El
significado de cada tabla está en `docs/modelo-datos.md`.
"""

from __future__ import annotations

import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from importlib import resources
from pathlib import Path


class Database:
    def __init__(self, path: Path):
        self.path = path

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Una transacción corta: confirma al salir o deshace ante un error."""
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.execute("COMMIT")
        except BaseException:
            connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    def migrate(self) -> list[str]:
        """Aplica las migraciones pendientes y devuelve sus nombres."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = self.connect()
        try:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations "
                "(name TEXT PRIMARY KEY, applied_at REAL NOT NULL)"
            )
            applied = {
                row["name"] for row in connection.execute("SELECT name FROM schema_migrations")
            }
            done = []
            for name, sql in _migrations():
                if name in applied:
                    continue
                connection.executescript(f"BEGIN;\n{sql}\nCOMMIT;")
                connection.execute(
                    "INSERT INTO schema_migrations (name, applied_at) VALUES (?, ?)",
                    (name, time.time()),
                )
                done.append(name)
            return done
        finally:
            connection.close()


def _migrations() -> list[tuple[str, str]]:
    folder = resources.files("ocr_mcp") / "migrations"
    files = sorted(item for item in folder.iterdir() if item.name.endswith(".sql"))
    return [(item.name, item.read_text(encoding="utf-8")) for item in files]
