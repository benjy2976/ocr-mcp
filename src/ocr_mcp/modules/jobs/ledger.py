"""Registro de los trabajos que este servidor creó en el core.

Es la fuente de la propiedad (un usuario solo ve sus trabajos, decisión 0006),
del uso que consumen las cuotas y de las estadísticas por clave (decisión
0007). Solo guarda conteos: nunca nombres de archivo, títulos ni contenido.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from ocr_mcp.modules.access import AccessKey
from ocr_mcp.modules.quotas import Usage, day_start, month_start
from ocr_mcp.shared.db import Database

ACTIVE = ("queued", "processing")
TERMINAL = ("done", "failed", "blocked")
STATS_DAYS = 30


@dataclass(frozen=True)
class Job:
    job_id: str
    key_id: str | None
    pages: int
    bytes: int
    artifacts: list[str]
    status: str


@dataclass(frozen=True)
class DailyUsage:
    day: str
    documents: int
    pages: int


@dataclass(frozen=True)
class KeyStats:
    documents: int
    pages: int
    bytes: int
    done: int
    failed: int
    blocked: int
    usage: Usage
    daily: list[DailyUsage]


def record(
    db: Database,
    job_id: str,
    key: AccessKey,
    request_hash: str,
    pages: int,
    size: int,
    artifacts: list[str],
) -> bool:
    """Registra un trabajo nuevo. Devuelve `False` si el core devolvió uno ya registrado."""
    with db.transaction() as connection:
        cursor = connection.execute(
            "INSERT OR IGNORE INTO jobs (job_id, key_id, request_hash, is_public, pages, bytes, "
            "artifacts, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'queued', ?)",
            (
                job_id,
                key.id,
                request_hash,
                int(key.is_public),
                pages,
                size,
                json.dumps(artifacts),
                time.time(),
            ),
        )
        return cursor.rowcount == 1


def by_request(db: Database, key_id: str, request_hash: str) -> Job | None:
    """Trabajo de esta clave con la misma huella de pedido, si existe."""
    row = _fetchone(
        db, "SELECT * FROM jobs WHERE request_hash = ? AND key_id = ?", request_hash, key_id
    )
    return _job(row) if row else None


def release_request(db: Database, job_id: str) -> None:
    """Libera la huella de un trabajo fallido para que el mismo pedido pueda reintentarse."""
    with db.transaction() as connection:
        connection.execute(
            "UPDATE jobs SET request_hash = request_hash || ':' || job_id WHERE job_id = ?",
            (job_id,),
        )


def owned(db: Database, job_id: str, key_id: str) -> Job | None:
    """El trabajo si pertenece a la clave; uno ajeno responde como si no existiera."""
    row = _fetchone(db, "SELECT * FROM jobs WHERE job_id = ? AND key_id = ?", job_id, key_id)
    return _job(row) if row else None


def update_status(db: Database, job_id: str, status: str) -> None:
    """Guarda el estado; un trabajo fallido por el core devuelve sus páginas a la cuota."""
    if status not in ACTIVE + TERMINAL:
        return
    finished = time.time() if status in TERMINAL else None
    with db.transaction() as connection:
        connection.execute(
            "UPDATE jobs SET status = ?, finished_at = COALESCE(finished_at, ?), "
            "refunded = CASE WHEN ? = 'failed' THEN 1 ELSE refunded END WHERE job_id = ?",
            (status, finished, status, job_id),
        )


def usage(db: Database, key_id: str, now: datetime) -> Usage:
    row = _fetchone(
        db,
        "SELECT "
        " COALESCE(SUM(CASE WHEN refunded = 0 AND created_at >= ? THEN pages END), 0) AS today,"
        " COALESCE(SUM(CASE WHEN refunded = 0 AND created_at >= ? THEN pages END), 0) AS month,"
        " COALESCE(SUM(CASE WHEN status IN ('queued', 'processing') THEN 1 END), 0) AS active "
        "FROM jobs WHERE key_id = ?",
        day_start(now).timestamp(),
        month_start(now).timestamp(),
        key_id,
    )
    return Usage(row["today"], row["month"], row["active"])


def public_pages_today(db: Database, now: datetime) -> int:
    row = _fetchone(
        db,
        "SELECT COALESCE(SUM(pages), 0) AS pages FROM jobs "
        "WHERE is_public = 1 AND refunded = 0 AND created_at >= ?",
        day_start(now).timestamp(),
    )
    return row["pages"]


def stats(db: Database, key_id: str, now: datetime) -> KeyStats:
    totals = _fetchone(
        db,
        "SELECT COUNT(*) AS documents, COALESCE(SUM(pages), 0) AS pages, COALESCE(SUM(bytes), 0) "
        "AS bytes,"
        " COALESCE(SUM(status = 'done'), 0) AS done, COALESCE(SUM(status = 'failed'), 0) AS failed,"
        " COALESCE(SUM(status = 'blocked'), 0) AS blocked FROM jobs WHERE key_id = ?",
        key_id,
    )
    since = day_start(now) - timedelta(days=STATS_DAYS - 1)
    connection = db.connect()
    try:
        rows = connection.execute(
            "SELECT date(created_at, 'unixepoch') AS day, COUNT(*) AS documents, SUM(pages) AS "
            "pages "
            "FROM jobs WHERE key_id = ? AND created_at >= ? GROUP BY day ORDER BY day",
            (key_id, since.timestamp()),
        ).fetchall()
    finally:
        connection.close()
    by_day = {row["day"]: DailyUsage(row["day"], row["documents"], row["pages"]) for row in rows}
    daily = []
    for offset in range(STATS_DAYS):
        day = (since + timedelta(days=offset)).astimezone(UTC).strftime("%Y-%m-%d")
        daily.append(by_day.get(day, DailyUsage(day, 0, 0)))
    return KeyStats(
        documents=totals["documents"],
        pages=totals["pages"],
        bytes=totals["bytes"],
        done=totals["done"],
        failed=totals["failed"],
        blocked=totals["blocked"],
        usage=usage(db, key_id, now),
        daily=daily,
    )


def _job(row) -> Job:
    return Job(
        row["job_id"],
        row["key_id"],
        row["pages"],
        row["bytes"],
        json.loads(row["artifacts"]),
        row["status"],
    )


def _fetchone(db: Database, sql: str, *params: object):
    connection = db.connect()
    try:
        return connection.execute(sql, params).fetchone()
    finally:
        connection.close()
