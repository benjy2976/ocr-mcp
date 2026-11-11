"""Claves públicas autoservicio en `/public/key` (decisiones 0007 y 0009)."""

from __future__ import annotations

import pytest

from ocr_mcp.modules import quotas
from ocr_mcp.modules.access import keys
from tests.modules.access.test_key_as_token import database, initialize
from tests.modules.access.test_oauth_flow import pkce, register, start

pytestmark = pytest.mark.anyio
BROWSER = {"Accept": "text/html,application/xhtml+xml"}


def open_public_mode(settings, **overrides) -> quotas.PublicMode:
    mode = quotas.PublicMode(enabled=True, **overrides)
    quotas.public.save(database(settings), mode)
    return mode


async def test_public_keys_are_closed_while_public_mode_is_off(client):
    assert (await client.get("/public/key")).status_code == 404
    answer = await client.post("/public/key")
    assert answer.status_code == 404 and answer.json() == {
        "error": "El servidor no ofrece claves públicas."
    }
    assert (await client.post("/public/key", headers=BROWSER)).status_code == 404


async def test_a_script_gets_a_public_key_as_json(client, settings):
    mode = open_public_mode(settings)
    answer = await client.post("/public/key")
    assert answer.status_code == 201 and answer.headers["cache-control"] == "no-store"
    data = answer.json()
    created = keys.find_by_secret(database(settings), data["key"])
    assert created.is_public and created.limits == mode.limits
    assert data["mcp_url"] == f"{settings.public_url}/mcp"
    assert data["header"] == f"Authorization: Bearer {data['key']}"
    assert data["limits"]["pages_per_day"] == mode.limits.pages_per_day


async def test_a_browser_gets_the_page_and_the_key_with_client_examples(client, settings):
    open_public_mode(settings)
    start_page = await client.get("/public/key")
    assert start_page.status_code == 200 and 'action="http://127.0.0.1:18040/public/key"' in (
        start_page.text
    )
    page = await client.post("/public/key", headers=BROWSER)
    assert page.status_code == 200 and "ocrk_" in page.text
    assert "bearer_token_env_var" in page.text and "Continuar con esta clave" not in page.text


async def test_the_daily_limit_per_address_is_shared_with_the_login_page(client, settings):
    open_public_mode(settings, keys_per_address_per_day=1)
    assert (await client.post("/public/key")).status_code == 201
    refused = await client.post("/public/key")
    assert refused.status_code == 429 and "por hoy" in refused.json()["error"]
    request_id = await start(client, await register(client), pkce()[1])
    login = await client.post("/login/public", data={"request": request_id})
    assert login.status_code == 429 and "por hoy" in login.text


def test_a_public_key_works_as_a_bearer_token(app, settings):
    open_public_mode(settings)
    _, secret = keys.create(database(settings), "Clave pública", quotas.PublicMode().limits)
    assert initialize(app, secret).status_code == 200
