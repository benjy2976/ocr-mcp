"""Página de inicio de sesión: el usuario pega su clave y vuelve a su cliente (decisión 0006).

Si el modo público está encendido, la página ofrece además obtener una clave
propia con la cuota pública (decisión 0007).
"""

from __future__ import annotations

from pathlib import Path

from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from starlette.routing import Route

from ocr_mcp.modules.access import keys
from ocr_mcp.modules.access.oauth import AccessProvider
from ocr_mcp.modules.quotas import public
from ocr_mcp.shared.db import Database
from ocr_mcp.shared.web import RateLimiter, client_address, render

TEMPLATES = Path(__file__).parent / "templates"
LOGIN_ATTEMPTS = 10
LOGIN_WINDOW = 600
GENERIC_ERROR = "La clave no es válida."


def routes(db: Database, provider: AccessProvider) -> list[Route]:
    limiter = RateLimiter(db)
    base = provider.settings.public_url

    async def show(request: Request) -> Response:
        request_id = request.query_params.get("request", "")
        if provider.pending(request_id) is None:
            return _expired()
        return _login_page(db, base, request_id)

    async def submit(request: Request) -> Response:
        form = await request.form()
        request_id = str(form.get("request", ""))
        if provider.pending(request_id) is None:
            return _expired()
        if not limiter.allow("login", client_address(request), LOGIN_ATTEMPTS, LOGIN_WINDOW):
            return _login_page(
                db, base, request_id, "Demasiados intentos. Espera unos minutos.", 429
            )
        key = keys.find_by_secret(db, str(form.get("key", "")))
        if key is None:
            return _login_page(db, base, request_id, GENERIC_ERROR, 401)
        return RedirectResponse(provider.approve(request_id, key.id), status_code=302)

    async def public_key(request: Request) -> Response:
        form = await request.form()
        request_id = str(form.get("request", ""))
        mode = public.load(db)
        if not mode.enabled:
            return render(
                TEMPLATES,
                "message.html",
                404,
                title="No disponible",
                message="El servidor no ofrece claves públicas.",
            )
        if provider.pending(request_id) is None:
            return _expired()
        address = client_address(request)
        if not limiter.allow("public-key", address, mode.keys_per_address_per_day, 86400):
            return _login_page(
                db, base, request_id, "Ya obtuviste las claves públicas permitidas por hoy.", 429
            )
        key, secret = keys.create(db, "Clave pública", mode.limits, public=True)
        return render(
            TEMPLATES,
            "public_key.html",
            base=base,
            request_id=request_id,
            secret=secret,
            limits=key.limits,
        )

    return [
        Route("/login", show, methods=["GET"]),
        Route("/login", submit, methods=["POST"]),
        Route("/login/public", public_key, methods=["POST"]),
    ]


def _login_page(
    db: Database, base: str, request_id: str, error: str | None = None, status: int = 200
) -> Response:
    return render(
        TEMPLATES,
        "login.html",
        status,
        base=base,
        request_id=request_id,
        error=error,
        public_mode=public.load(db).enabled,
    )


def _expired() -> Response:
    return render(
        TEMPLATES,
        "message.html",
        400,
        title="Pedido vencido",
        message="Este pedido de acceso no existe o venció. Vuelve a conectar el servidor desde tu "
        "cliente.",
    )
