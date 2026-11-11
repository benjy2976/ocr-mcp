"""Claves públicas autoservicio (decisiones 0007 y 0009).

Con el modo público encendido, cualquiera obtiene una clave con la cuota
pública, desde la página de inicio de sesión de OAuth o, sin OAuth, en
`/public/key`. Las dos vías comparten el límite diario por dirección.
`/public/key` responde en HTML a un navegador y en JSON a todo lo demás, para
que un agente o un script obtengan su clave sin navegador.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from ocr_mcp.config import Settings
from ocr_mcp.modules.access import keys
from ocr_mcp.modules.quotas import public
from ocr_mcp.shared.db import Database
from ocr_mcp.shared.web import RateLimiter, client_address, render

TEMPLATES = Path(__file__).parent / "templates"
BUCKET = "public-key"
KEY_NAME = "Clave pública"


class Refused(Exception):
    """El modo público está apagado o la dirección agotó sus claves del día."""

    def __init__(self, message: str, status: int):
        super().__init__(message)
        self.message = message
        self.status = status


def issue(db: Database, address: str) -> tuple[keys.AccessKey, str]:
    """Crea una clave pública para `address` o lanza `Refused`."""
    mode = public.load(db)
    if not mode.enabled:
        raise Refused("El servidor no ofrece claves públicas.", 404)
    if not RateLimiter(db).allow(BUCKET, address, mode.keys_per_address_per_day, 86400):
        raise Refused("Ya obtuviste las claves públicas permitidas por hoy.", 429)
    return keys.create(db, KEY_NAME, mode.limits, public=True)


def routes(db: Database, settings: Settings) -> list[Route]:
    base = settings.public_url

    def page(name: str, status: int = 200, **context: object) -> Response:
        return render(TEMPLATES, name, status, base=base, mcp_url=settings.resource_url, **context)

    async def show(request: Request) -> Response:
        mode = public.load(db)
        if not mode.enabled:
            return _refused_page(Refused("El servidor no ofrece claves públicas.", 404))
        return page("public_start.html", limits=mode.limits)

    async def create(request: Request) -> Response:
        wants_html = "text/html" in request.headers.get("accept", "")
        try:
            key, secret = issue(db, client_address(request))
        except Refused as refused:
            if wants_html:
                return _refused_page(refused)
            return _json({"error": refused.message}, refused.status)
        if wants_html:
            return page("public_key.html", secret=secret, limits=key.limits, request_id=None)
        return _json(
            {
                "key": secret,
                "mcp_url": settings.resource_url,
                "header": f"Authorization: Bearer {secret}",
                "limits": asdict(key.limits),
            },
            201,
        )

    return [
        Route("/public/key", show, methods=["GET"]),
        Route("/public/key", create, methods=["POST"]),
    ]


def _refused_page(refused: Refused) -> Response:
    return render(
        TEMPLATES, "message.html", refused.status, title="No disponible", message=refused.message
    )


def _json(payload: dict[str, object], status: int) -> JSONResponse:
    response = JSONResponse(payload, status_code=status)
    response.headers["Cache-Control"] = "no-store"
    return response
