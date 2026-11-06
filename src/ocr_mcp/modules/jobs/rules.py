"""Reglas sin estado de las herramientas: artefactos disponibles, títulos y mensajes."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ocr_mcp.modules.core import CoreAuthError, CoreError

TITLE_MAX = 500


def available(data: dict[str, Any]) -> list[str]:
    artifacts = data.get("artifacts") or {}
    return [
        name
        for name in ("md", "text", "pdf")
        if (info := artifacts.get(name))
        and info.get("written")
        and info.get("staged")
        and not info.get("expired")
    ]


def why_unavailable(data: dict[str, Any], name: str) -> str:
    info = (data.get("artifacts") or {}).get(name) or {}
    if name == "pdf" and info.get("reused_source"):
        return "El PDF ya tenía texto útil: el original sirve como PDF buscable."
    if info.get("expired"):
        return "El artefacto venció en el core."
    return "No se pidió en este trabajo."


def title(title: str | None) -> str | None:
    if title is None:
        return None
    clean = " ".join("".join(ch if ch.isprintable() else " " for ch in title).split())
    return clean[:TITLE_MAX] or None


def core_message(error: CoreError) -> str:
    if isinstance(error, CoreAuthError):
        return "Este servidor no está autorizado ante el core. Avisa a quien lo opera."
    return str(error)


def with_renewal(error: Exception) -> str:
    renews_at = getattr(error, "renews_at", None)
    return f"{error} Se renueva el {renews_at:%Y-%m-%d %H:%M} UTC." if renews_at else str(error)


def iso(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, UTC).isoformat(timespec="seconds")
