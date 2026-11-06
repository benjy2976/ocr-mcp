"""Fixtures comunes: configuración, core simulado, aplicación y PDF de prueba."""

from __future__ import annotations

import io
from collections.abc import AsyncIterator, Iterator
from contextlib import contextmanager
from dataclasses import replace

import httpx
import pytest
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import AccessToken
from pypdf import PdfWriter

from ocr_mcp.app import build
from ocr_mcp.config import Settings
from ocr_mcp.shared.security import hash_password
from tests.fakes.core import TOKEN, FakeCore

PUBLIC_URL = "http://127.0.0.1:18040"
ADMIN_PASSWORD = "contraseña-de-prueba"
_PASSWORD_HASH = hash_password(ADMIN_PASSWORD)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def make_pdf(pages: int = 3) -> bytes:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=200, height=200)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        core_url="http://core.test",
        core_token=TOKEN,
        public_url=PUBLIC_URL,
        host="127.0.0.1",
        port=18040,
        data_dir=tmp_path / "datos",
        admin_user="admin",
        admin_password_hash=_PASSWORD_HASH,
    )


@pytest.fixture
def fake_core() -> FakeCore:
    return FakeCore()


@pytest.fixture
def make_app(fake_core):
    def factory(settings: Settings, **overrides):
        return build(
            replace(settings, **overrides),
            core_transport=httpx.ASGITransport(app=fake_core.app),
        )

    return factory


@pytest.fixture
def app(make_app, settings):
    return make_app(settings)


@pytest.fixture
async def client(app) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url=PUBLIC_URL) as http:
        yield http


@contextmanager
def as_user(key_id: str) -> Iterator[None]:
    """Fija el usuario autenticado, como lo haría el middleware OAuth del SDK."""
    token = AccessToken(token="t", client_id="cliente", scopes=["ocr"], subject=key_id)
    reset = auth_context_var.set(AuthenticatedUser(token))
    try:
        yield
    finally:
        auth_context_var.reset(reset)
