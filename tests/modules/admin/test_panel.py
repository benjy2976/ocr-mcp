"""Panel /admin (reglas de `src/ocr_mcp/modules/admin/context.md`)."""

from __future__ import annotations

import re

import pytest

from ocr_mcp.modules import quotas
from ocr_mcp.modules.access import keys
from ocr_mcp.modules.quotas import Limits
from ocr_mcp.shared.db import Database
from tests.conftest import ADMIN_PASSWORD, PUBLIC_URL

pytestmark = pytest.mark.anyio


def database(settings) -> Database:
    return Database(settings.data_dir / "ocr-mcp.sqlite3")


async def sign_in(client) -> str:
    response = await client.post("/admin/login", data={"user": "admin", "password": ADMIN_PASSWORD})
    assert response.status_code == 303
    panel = await client.get("/admin")
    return re.search(r'name="csrf" value="([^"]+)"', panel.text).group(1)


async def test_without_a_session_the_panel_asks_for_credentials(client):
    page = await client.get("/admin")
    assert page.status_code == 200 and 'name="password"' in page.text


async def test_wrong_credentials_get_a_generic_error(client):
    response = await client.post("/admin/login", data={"user": "admin", "password": "otra"})
    assert response.status_code == 401 and "Usuario o contraseña incorrectos." in response.text


async def test_the_session_cookie_is_protected(client):
    response = await client.post("/admin/login", data={"user": "admin", "password": ADMIN_PASSWORD})
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie and "path=/admin" in cookie


async def test_admin_login_attempts_are_limited(client):
    for _ in range(5):
        await client.post("/admin/login", data={"user": "admin", "password": "mala"})
    response = await client.post("/admin/login", data={"user": "admin", "password": ADMIN_PASSWORD})
    assert response.status_code == 429


async def test_creating_a_key_shows_it_once_with_client_examples(client, settings):
    csrf = await sign_in(client)
    created = await client.post(
        "/admin/keys", data={"csrf": csrf, "name": "equipo de análisis", "pages_per_day": "50"}
    )
    secret = re.search(r"(ocrk_[A-Za-z0-9_-]+)", created.text).group(1)
    assert f"claude mcp add --transport http ocr {PUBLIC_URL}/mcp" in created.text
    key = keys.find_by_secret(database(settings), secret)
    assert key.name == "equipo de análisis" and key.limits == Limits(pages_per_day=50)
    panel = await client.get("/admin")
    assert "equipo de análisis" in panel.text and secret not in panel.text


async def test_forms_without_the_csrf_token_do_nothing(client, settings):
    await sign_in(client)
    await client.post("/admin/keys", data={"csrf": "falso", "name": "intrusa"})
    assert keys.list_all(database(settings)) == []


async def test_limits_can_be_changed_and_keys_deleted(client, settings):
    db = database(settings)
    key, _ = keys.create(db, "ana", Limits())
    csrf = await sign_in(client)
    detail = await client.get(f"/admin/keys/{key.id}")
    assert detail.status_code == 200 and "Últimos 30 días" in detail.text
    await client.post(
        f"/admin/keys/{key.id}/limits",
        data={"csrf": csrf, "pages_per_month": "300", "max_active_jobs": "2"},
    )
    assert keys.get(db, key.id).limits == Limits(pages_per_month=300, max_active_jobs=2)
    invalid = await client.post(
        f"/admin/keys/{key.id}/limits", data={"csrf": csrf, "pages_per_day": "-4"}
    )
    assert invalid.status_code == 303 and "error=" in invalid.headers["location"]
    await client.post(f"/admin/keys/{key.id}/delete", data={"csrf": csrf})
    assert keys.get(db, key.id) is None


async def test_public_mode_is_saved_from_the_panel(client, settings):
    csrf = await sign_in(client)
    await client.post(
        "/admin/public",
        data={
            "csrf": csrf,
            "enabled": "on",
            "pages_per_day": "5",
            "global_pages_per_day": "100",
            "keys_per_address_per_day": "2",
        },
    )
    mode = quotas.public.load(database(settings))
    assert mode.enabled and mode.limits == Limits(pages_per_day=5)
    assert mode.global_pages_per_day == 100 and mode.keys_per_address_per_day == 2
    rejected = await client.post("/admin/public", data={"csrf": csrf, "enabled": "on"})
    assert "error=" in rejected.headers["location"]


async def test_logout_closes_the_session(client):
    csrf = await sign_in(client)
    await client.post("/admin/logout", data={"csrf": csrf})
    assert 'name="password"' in (await client.get("/admin")).text
