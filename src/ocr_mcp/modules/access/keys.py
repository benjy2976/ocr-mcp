"""Claves de acceso: la identidad de cada usuario (decisión 0006).

La clave en claro se devuelve una sola vez, al crearla; la base guarda solo su
SHA-256. Borrar una clave revoca en cascada sus códigos y tokens OAuth.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from ocr_mcp.modules.quotas import Limits
from ocr_mcp.shared.db import Database
from ocr_mcp.shared.security import new_id, new_secret, secret_hash

KEY_PREFIX = "ocrk_"
NAME_MAX = 80


@dataclass(frozen=True)
class AccessKey:
    id: str
    name: str
    is_public: bool
    limits: Limits
    created_at: float
    last_used_at: float | None


def create(
    db: Database, name: str, limits: Limits, *, public: bool = False
) -> tuple[AccessKey, str]:
    """Crea una clave y devuelve `(clave, secreto)`. El secreto no vuelve a estar disponible."""
    clean = " ".join(name.split())[:NAME_MAX]
    if not clean:
        raise ValueError("La clave necesita un nombre.")
    secret = new_secret(KEY_PREFIX)
    key = AccessKey(new_id(), clean, public, limits, time.time(), None)
    with db.transaction() as connection:
        connection.execute(
            "INSERT INTO access_keys (id, name, key_hash, is_public, pages_per_day, "
            "pages_per_month, max_active_jobs, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                key.id,
                key.name,
                secret_hash(secret),
                int(public),
                limits.pages_per_day,
                limits.pages_per_month,
                limits.max_active_jobs,
                key.created_at,
            ),
        )
    return key, secret


def find_by_secret(db: Database, secret: str) -> AccessKey | None:
    """La búsqueda es por hash: no compara el secreto carácter a carácter."""
    if not secret.startswith(KEY_PREFIX):
        return None
    return _one(db, "key_hash = ?", secret_hash(secret.strip()))


def get(db: Database, key_id: str) -> AccessKey | None:
    return _one(db, "id = ?", key_id)


def list_all(db: Database) -> list[AccessKey]:
    connection = db.connect()
    try:
        rows = connection.execute("SELECT * FROM access_keys ORDER BY created_at DESC").fetchall()
    finally:
        connection.close()
    return [_from_row(row) for row in rows]


def delete(db: Database, key_id: str) -> bool:
    with db.transaction() as connection:
        return connection.execute("DELETE FROM access_keys WHERE id = ?", (key_id,)).rowcount == 1


def set_limits(db: Database, key_id: str, limits: Limits) -> bool:
    with db.transaction() as connection:
        cursor = connection.execute(
            "UPDATE access_keys SET pages_per_day = ?, pages_per_month = ?, max_active_jobs = ? "
            "WHERE id = ?",
            (limits.pages_per_day, limits.pages_per_month, limits.max_active_jobs, key_id),
        )
        return cursor.rowcount == 1


def touch(db: Database, key_id: str) -> None:
    connection = db.connect()
    try:
        connection.execute(
            "UPDATE access_keys SET last_used_at = ? WHERE id = ?", (time.time(), key_id)
        )
    finally:
        connection.close()


def _one(db: Database, where: str, value: str) -> AccessKey | None:
    connection = db.connect()
    try:
        row = connection.execute(f"SELECT * FROM access_keys WHERE {where}", (value,)).fetchone()
    finally:
        connection.close()
    return _from_row(row) if row else None


def _from_row(row) -> AccessKey:
    return AccessKey(
        id=row["id"],
        name=row["name"],
        is_public=bool(row["is_public"]),
        limits=Limits(row["pages_per_day"], row["pages_per_month"], row["max_active_jobs"]),
        created_at=row["created_at"],
        last_used_at=row["last_used_at"],
    )
