"""Utilidades web compartidas: plantillas, dirección del cliente y límite de intentos.

No contiene reglas de negocio. Las plantillas viven en la carpeta `templates/`
de cada módulo y siempre escapan el HTML.
"""

from __future__ import annotations

import time
from functools import cache
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from starlette.requests import Request
from starlette.responses import HTMLResponse

from ocr_mcp.shared.db import Database
from ocr_mcp.shared.security import secret_hash

BASE_TEMPLATES = Path(__file__).parent / "templates"


@cache
def _environment(folder: str) -> Environment:
    return Environment(
        loader=FileSystemLoader([folder, str(BASE_TEMPLATES)]),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render(folder: Path, name: str, status_code: int = 200, **context: Any) -> HTMLResponse:
    """Plantilla `name` de `folder`, con la base común disponible para heredar."""
    html = _environment(str(folder)).get_template(name).render(**context)
    response = HTMLResponse(html, status_code=status_code)
    # Páginas con claves o formularios: nunca en caché ni dentro de otro sitio.
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


def client_address(request: Request) -> str:
    """Dirección del cliente. Detrás de un proxy, uvicorn la toma de `X-Forwarded-For` solo si el
    proxy es de confianza (`OCR_MCP_TRUSTED_PROXIES`); si no, es la del proxy."""
    return request.client.host if request.client else "desconocida"


class RateLimiter:
    """Ventana deslizante en SQLite. Guarda la huella de la dirección, no la dirección."""

    def __init__(self, db: Database):
        self.db = db

    def allow(self, bucket: str, subject: str, limit: int, window_seconds: int) -> bool:
        now = time.time()
        key = secret_hash(subject)
        with self.db.transaction() as connection:
            connection.execute("DELETE FROM rate_limits WHERE at < ?", (now - 86400 * 2,))
            count = connection.execute(
                "SELECT COUNT(*) FROM rate_limits WHERE bucket = ? AND subject = ? AND at >= ?",
                (bucket, key, now - window_seconds),
            ).fetchone()[0]
            if count >= limit:
                return False
            connection.execute(
                "INSERT INTO rate_limits (bucket, subject, at) VALUES (?, ?, ?)",
                (bucket, key, now),
            )
            return True
