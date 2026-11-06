"""Panel `/admin`, mínimo (decisiones 0006 y 0007): claves, cuotas, uso, modo público y ejemplos.

No usa OAuth: lo protege la sesión del admin. Todo formulario lleva el token
CSRF de la sesión.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

from starlette.datastructures import FormData
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from starlette.routing import Route

from ocr_mcp.config import Settings
from ocr_mcp.modules import quotas
from ocr_mcp.modules.access import keys
from ocr_mcp.modules.admin.session import AdminSessions, Session
from ocr_mcp.modules.jobs import ledger
from ocr_mcp.shared.db import Database
from ocr_mcp.shared.security import same
from ocr_mcp.shared.web import RateLimiter, client_address, render

TEMPLATES = Path(__file__).parent / "templates"
LOGIN_ATTEMPTS = 5
LOGIN_WINDOW = 600


class FormError(ValueError):
    pass


def routes(db: Database, settings: Settings) -> list[Route]:
    sessions = AdminSessions(db, settings)
    limiter = RateLimiter(db)
    base = settings.public_url

    def page(name: str, session: Session, status: int = 200, **context: Any) -> Response:
        return render(
            TEMPLATES,
            name,
            status,
            base=base,
            csrf=session.csrf,
            mcp_url=settings.resource_url,
            when=_when,
            **context,
        )

    def back(path: str = "/admin") -> Response:
        return RedirectResponse(f"{base}{path}", status_code=303)

    async def authorized(request: Request) -> tuple[Session, FormData | None] | None:
        session = sessions.current(request)
        if session is None:
            return None
        if request.method != "POST":
            return session, None
        form = await request.form()
        if not same(str(form.get("csrf", "")), session.csrf):
            return None
        return session, form

    async def home(request: Request) -> Response:
        session = sessions.current(request)
        if session is None:
            return render(TEMPLATES, "login.html", base=base)
        now = datetime.now(UTC)
        rows = [(key, ledger.usage(db, key.id, now)) for key in keys.list_all(db)]
        return page(
            "panel.html",
            session,
            rows=rows,
            mode=quotas.public.load(db),
            error=request.query_params.get("error"),
        )

    async def login(request: Request) -> Response:
        form = await request.form()
        if not limiter.allow("admin-login", client_address(request), LOGIN_ATTEMPTS, LOGIN_WINDOW):
            return render(
                TEMPLATES,
                "login.html",
                429,
                base=base,
                error="Demasiados intentos. Espera unos minutos.",
            )
        secret = sessions.login(str(form.get("user", "")), str(form.get("password", "")))
        if secret is None:
            return render(
                TEMPLATES, "login.html", 401, base=base, error="Usuario o contraseña incorrectos."
            )
        response = back()
        sessions.set_cookie(response, secret)
        return response

    async def logout(request: Request) -> Response:
        if await authorized(request) is not None:
            sessions.logout(request)
        response = back()
        sessions.clear_cookie(response)
        return response

    async def create_key(request: Request) -> Response:
        found = await authorized(request)
        if found is None:
            return back()
        session, form = found
        try:
            key, secret = keys.create(db, str(form.get("name", "")), _limits(form))
        except (FormError, ValueError) as error:
            return back(f"/admin?error={_quote(error)}")
        return page("created.html", session, key=key, secret=secret)

    async def key_detail(request: Request) -> Response:
        session = sessions.current(request)
        key = keys.get(db, request.path_params["key_id"])
        if session is None or key is None:
            return back()
        stats = ledger.stats(db, key.id, datetime.now(UTC))
        return page(
            "key.html", session, key=key, stats=stats, error=request.query_params.get("error")
        )

    async def update_limits(request: Request) -> Response:
        key_id = request.path_params["key_id"]
        found = await authorized(request)
        if found is not None:
            try:
                keys.set_limits(db, key_id, _limits(found[1]))
            except FormError as error:
                return back(f"/admin/keys/{key_id}?error={_quote(error)}")
        return back(f"/admin/keys/{key_id}")

    async def delete_key(request: Request) -> Response:
        found = await authorized(request)
        if found is not None:
            keys.delete(db, request.path_params["key_id"])
        return back()

    async def public_mode(request: Request) -> Response:
        found = await authorized(request)
        if found is None:
            return back()
        form = found[1]
        try:
            quotas.public.save(
                db,
                quotas.PublicMode(
                    enabled=form.get("enabled") == "on",
                    limits=_limits(form),
                    global_pages_per_day=_number(form, "global_pages_per_day"),
                    keys_per_address_per_day=_number(form, "keys_per_address_per_day") or 1,
                ),
            )
        except (FormError, ValueError) as error:
            return back(f"/admin?error={_quote(error)}")
        return back()

    async def clients(request: Request) -> Response:
        session = sessions.current(request)
        if session is None:
            return back()
        return page("clients.html", session)

    return [
        Route("/admin", home, methods=["GET"]),
        Route("/admin/login", login, methods=["POST"]),
        Route("/admin/logout", logout, methods=["POST"]),
        Route("/admin/keys", create_key, methods=["POST"]),
        Route("/admin/keys/{key_id}", key_detail, methods=["GET"]),
        Route("/admin/keys/{key_id}/limits", update_limits, methods=["POST"]),
        Route("/admin/keys/{key_id}/delete", delete_key, methods=["POST"]),
        Route("/admin/public", public_mode, methods=["POST"]),
        Route("/admin/clients", clients, methods=["GET"]),
    ]


def _limits(form: FormData) -> quotas.Limits:
    return quotas.Limits(
        pages_per_day=_number(form, "pages_per_day"),
        pages_per_month=_number(form, "pages_per_month"),
        max_active_jobs=_number(form, "max_active_jobs"),
    )


def _number(form: FormData, name: str) -> int | None:
    value = str(form.get(name, "")).strip()
    if not value:
        return None
    if not value.isdigit() or int(value) < 1:
        raise FormError("Los límites tienen que ser enteros positivos o quedar vacíos.")
    return int(value)


def _quote(error: Exception) -> str:
    return quote(str(error))


def _when(timestamp: float | None) -> str:
    if timestamp is None:
        return "nunca"
    return datetime.fromtimestamp(timestamp, UTC).strftime("%Y-%m-%d %H:%M UTC")
