"""Modo público: apagado por defecto, se enciende y configura desde el panel (decisión 0007)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

from ocr_mcp.modules.quotas.policy import Limits
from ocr_mcp.shared.db import Database

SETTING = "public_mode"


@dataclass(frozen=True)
class PublicMode:
    enabled: bool = False
    # Cuota con la que nace cada clave pública. Nunca sin límite.
    limits: Limits = field(
        default_factory=lambda: Limits(pages_per_day=20, pages_per_month=200, max_active_jobs=1)
    )
    # Suma diaria de páginas de todas las claves públicas.
    global_pages_per_day: int | None = 500
    # Claves públicas que puede obtener una misma dirección por día.
    keys_per_address_per_day: int = 3


def load(db: Database) -> PublicMode:
    connection = db.connect()
    try:
        row = connection.execute("SELECT value FROM settings WHERE name = ?", (SETTING,)).fetchone()
    finally:
        connection.close()
    if row is None:
        return PublicMode()
    data = json.loads(row["value"])
    return PublicMode(
        enabled=bool(data["enabled"]),
        limits=Limits(**data["limits"]),
        global_pages_per_day=data["global_pages_per_day"],
        keys_per_address_per_day=int(data["keys_per_address_per_day"]),
    )


def save(db: Database, mode: PublicMode) -> None:
    if mode.limits.pages_per_day is None and mode.limits.pages_per_month is None:
        raise ValueError("La cuota pública necesita al menos un límite de páginas.")
    if mode.keys_per_address_per_day < 1:
        raise ValueError("Cada dirección tiene que poder obtener al menos una clave.")
    value = json.dumps(asdict(mode))
    with db.transaction() as connection:
        connection.execute(
            "INSERT INTO settings (name, value) VALUES (?, ?) "
            "ON CONFLICT (name) DO UPDATE SET value = excluded.value",
            (SETTING, value),
        )
