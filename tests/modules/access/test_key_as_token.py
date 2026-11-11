"""La clave de acceso vale como token Bearer directo en `/mcp` (decisión 0009)."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from ocr_mcp.modules.access import keys
from ocr_mcp.modules.quotas import Limits
from ocr_mcp.shared.db import Database
from tests.conftest import PUBLIC_URL

INITIALIZE = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "prueba", "version": "1"},
    },
}


def database(settings) -> Database:
    return Database(settings.data_dir / "ocr-mcp.sqlite3")


def post_initialize(http: TestClient, bearer: str):
    return http.post(
        "/mcp",
        headers={
            "Authorization": f"Bearer {bearer}",
            "Accept": "application/json, text/event-stream",
        },
        json=INITIALIZE,
    )


def initialize(app, bearer: str):
    """`initialize` de MCP con el ciclo de vida del servidor activo (una vez por aplicación)."""
    with TestClient(app, base_url=PUBLIC_URL) as http:
        return post_initialize(http, bearer)


def test_a_key_opens_an_mcp_session_without_oauth(app, settings):
    _, secret = keys.create(database(settings), "ana", Limits())
    response = initialize(app, secret)
    assert response.status_code == 200, response.text
    assert "ocr-mcp" in response.text


@pytest.mark.anyio
async def test_the_key_token_identifies_its_user_for_this_resource(app, settings):
    key, secret = keys.create(database(settings), "ana", Limits())
    provider = app.state.mcp._auth_server_provider
    token = await provider.load_access_token(secret)
    assert token.subject == key.id and token.scopes == ["ocr"]
    assert token.resource == f"{PUBLIC_URL}/mcp" and token.expires_at is None
    assert keys.get(database(settings), key.id).last_used_at is not None


def test_an_unknown_or_deleted_key_is_rejected(app, settings):
    db = database(settings)
    key, secret = keys.create(db, "ana", Limits())
    with TestClient(app, base_url=PUBLIC_URL) as http:
        assert post_initialize(http, "ocrk_inventada").status_code == 401
        assert post_initialize(http, secret).status_code == 200
        keys.delete(db, key.id)
        response = post_initialize(http, secret)
    assert response.status_code == 401
    assert "resource_metadata" in response.headers["www-authenticate"]
