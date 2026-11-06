"""Enlaces de descarga de artefactos (decisión 0003).

Vencen y pertenecen a la clave que los pidió.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from ocr_mcp.shared.db import Database
from ocr_mcp.shared.security import new_secret, secret_hash

ARTIFACTS = ("pdf", "text", "md")


@dataclass(frozen=True)
class Download:
    key_id: str
    job_id: str
    artifact: str


class Downloads:
    def __init__(self, db: Database, public_url: str, ttl: int):
        self.db = db
        self.public_url = public_url
        self.ttl = ttl

    def create(self, key_id: str, job_id: str, artifact: str) -> tuple[str, float]:
        """URL de descarga y su vencimiento. Sirve varias veces hasta vencer."""
        if artifact not in ARTIFACTS:
            raise ValueError(f"Artefacto desconocido: {artifact}")
        secret = new_secret()
        expires_at = time.time() + self.ttl
        with self.db.transaction() as connection:
            connection.execute("DELETE FROM downloads WHERE expires_at < ?", (time.time(),))
            connection.execute(
                "INSERT INTO downloads (token_hash, key_id, job_id, artifact, expires_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (secret_hash(secret), key_id, job_id, artifact, expires_at),
            )
        return f"{self.public_url}/d/{secret}", expires_at

    def resolve(self, secret: str) -> Download | None:
        connection = self.db.connect()
        try:
            row = connection.execute(
                "SELECT key_id, job_id, artifact FROM downloads WHERE token_hash = ? AND "
                "expires_at >= ?",
                (secret_hash(secret), time.time()),
            ).fetchone()
        finally:
            connection.close()
        return Download(row["key_id"], row["job_id"], row["artifact"]) if row else None
