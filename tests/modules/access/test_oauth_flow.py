"""Flujo OAuth 2.1 completo por HTTP (reglas de `src/ocr_mcp/modules/access/context.md`)."""

from __future__ import annotations

import base64
import hashlib
import re
import secrets
from urllib.parse import parse_qs, urlsplit

import pytest
from starlette.testclient import TestClient

from ocr_mcp.modules import quotas
from ocr_mcp.modules.access import keys
from ocr_mcp.modules.quotas import Limits
from ocr_mcp.shared.db import Database
from tests.conftest import PUBLIC_URL

pytestmark = pytest.mark.anyio
REDIRECT = "http://localhost:3000/callback"


def database(settings) -> Database:
    return Database(settings.data_dir / "ocr-mcp.sqlite3")


def pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    digest = hashlib.sha256(verifier.encode()).digest()
    return verifier, base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


async def register(client) -> str:
    response = await client.post(
        "/register",
        json={
            "redirect_uris": [REDIRECT],
            "token_endpoint_auth_method": "none",
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "client_name": "cliente de prueba",
            "scope": "ocr",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["client_id"]


async def start(client, client_id: str, challenge: str) -> str:
    """Pedido de autorización; devuelve el identificador del pedido que espera la clave."""
    response = await client.get(
        "/authorize",
        params={
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": REDIRECT,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": "estado-1",
            "scope": "ocr",
            "resource": f"{PUBLIC_URL}/mcp",
        },
    )
    assert response.status_code == 302, response.text
    location = urlsplit(response.headers["location"])
    assert location.path == "/login"
    return parse_qs(location.query)["request"][0]


async def exchange(client, client_id: str, code: str, verifier: str):
    return await client.post(
        "/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT,
            "client_id": client_id,
            "code_verifier": verifier,
            "resource": f"{PUBLIC_URL}/mcp",
        },
    )


async def sign_in(client, secret: str) -> tuple[str, dict]:
    """Recorre el flujo completo y devuelve `(client_id, tokens)`."""
    client_id = await register(client)
    verifier, challenge = pkce()
    request_id = await start(client, client_id, challenge)
    response = await client.post("/login", data={"request": request_id, "key": secret})
    assert response.status_code == 302, response.text
    query = parse_qs(urlsplit(response.headers["location"]).query)
    assert query["state"] == ["estado-1"]
    tokens = await exchange(client, client_id, query["code"][0], verifier)
    assert tokens.status_code == 200, tokens.text
    return client_id, tokens.json()


async def test_metadata_is_published(client):
    server = (await client.get("/.well-known/oauth-authorization-server")).json()
    resource = (await client.get("/.well-known/oauth-protected-resource/mcp")).json()
    assert server["issuer"].rstrip("/") == PUBLIC_URL
    assert "S256" in server["code_challenge_methods_supported"]
    assert resource["resource"] == f"{PUBLIC_URL}/mcp"


async def test_mcp_without_a_token_is_rejected(client):
    response = await client.post("/mcp", json={})
    assert response.status_code == 401
    assert "resource_metadata" in response.headers["www-authenticate"]


async def test_the_key_page_rejects_with_a_generic_message(client, settings):
    keys.create(database(settings), "ana", Limits())
    client_id = await register(client)
    _, challenge = pkce()
    request_id = await start(client, client_id, challenge)
    page = await client.get("/login", params={"request": request_id})
    assert page.status_code == 200 and 'name="key"' in page.text
    wrong = await client.post("/login", data={"request": request_id, "key": "ocrk_inventada"})
    assert wrong.status_code == 401 and "La clave no es válida." in wrong.text


async def test_a_valid_key_obtains_tokens_bound_to_its_user(app, client, settings):
    key, secret = keys.create(database(settings), "ana", Limits())
    _, tokens = await sign_in(client, secret)
    provider = app.state.mcp._auth_server_provider
    access = await provider.load_access_token(tokens["access_token"])
    assert access.subject == key.id and access.resource == f"{PUBLIC_URL}/mcp"
    assert tokens["token_type"] == "Bearer" and tokens["scope"] == "ocr"


async def test_the_code_works_only_once(client, settings):
    _, secret = keys.create(database(settings), "ana", Limits())
    client_id = await register(client)
    verifier, challenge = pkce()
    request_id = await start(client, client_id, challenge)
    response = await client.post("/login", data={"request": request_id, "key": secret})
    code = parse_qs(urlsplit(response.headers["location"]).query)["code"][0]
    assert (await exchange(client, client_id, code, verifier)).status_code == 200
    assert (await exchange(client, client_id, code, verifier)).status_code == 400


async def test_refresh_rotates_and_the_old_refresh_token_stops_working(client, settings):
    _, secret = keys.create(database(settings), "ana", Limits())
    client_id, tokens = await sign_in(client, secret)

    async def refresh(token: str):
        return await client.post(
            "/token",
            data={"grant_type": "refresh_token", "refresh_token": token, "client_id": client_id},
        )

    first = await refresh(tokens["refresh_token"])
    assert first.status_code == 200 and first.json()["access_token"] != tokens["access_token"]
    assert (await refresh(tokens["refresh_token"])).status_code == 400


async def test_deleting_the_key_revokes_its_tokens_at_once(app, client, settings):
    db = database(settings)
    key, secret = keys.create(db, "ana", Limits())
    _, tokens = await sign_in(client, secret)
    keys.delete(db, key.id)
    provider = app.state.mcp._auth_server_provider
    assert await provider.load_access_token(tokens["access_token"]) is None
    response = await client.post(
        "/mcp", json={}, headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert response.status_code == 401


async def test_an_unknown_request_shows_a_message(client):
    response = await client.get("/login", params={"request": "inexistente"})
    assert response.status_code == 400 and "venció" in response.text


async def test_key_attempts_are_limited(client, settings):
    client_id = await register(client)
    _, challenge = pkce()
    request_id = await start(client, client_id, challenge)
    for _ in range(10):
        await client.post("/login", data={"request": request_id, "key": "ocrk_mala"})
    blocked = await client.post("/login", data={"request": request_id, "key": "ocrk_mala"})
    assert blocked.status_code == 429


async def test_public_mode_hands_out_limited_keys(client, settings):
    db = database(settings)
    client_id = await register(client)
    _, challenge = pkce()
    request_id = await start(client, client_id, challenge)
    closed = await client.post("/login/public", data={"request": request_id})
    assert closed.status_code == 404
    quotas.public.save(db, quotas.PublicMode(enabled=True, keys_per_address_per_day=1))
    assert "Obtener una clave pública" in (await client.get(f"/login?request={request_id}")).text
    page = await client.post("/login/public", data={"request": request_id})
    assert page.status_code == 200
    secret = re.search(r"(ocrk_[A-Za-z0-9_-]+)", page.text).group(1)
    created = keys.find_by_secret(db, secret)
    assert created.is_public and created.limits == quotas.PublicMode().limits
    again = await client.post("/login/public", data={"request": request_id})
    assert again.status_code == 429
    used = await client.post("/login", data={"request": request_id, "key": secret})
    assert used.status_code == 302


def test_a_valid_token_reaches_the_mcp_endpoint(app, settings):
    """Con el ciclo de vida del servidor activo, el token abre una sesión MCP."""
    _, secret = keys.create(database(settings), "ana", Limits())
    with TestClient(app, base_url=PUBLIC_URL, follow_redirects=False) as http:
        client_id = http.post(
            "/register",
            json={
                "redirect_uris": [REDIRECT],
                "token_endpoint_auth_method": "none",
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"],
                "scope": "ocr",
            },
        ).json()["client_id"]
        verifier, challenge = pkce()
        location = http.get(
            "/authorize",
            params={
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": REDIRECT,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "state": "s",
                "scope": "ocr",
            },
        ).headers["location"]
        request_id = parse_qs(urlsplit(location).query)["request"][0]
        back = http.post("/login", data={"request": request_id, "key": secret}).headers["location"]
        code = parse_qs(urlsplit(back).query)["code"][0]
        token = http.post(
            "/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT,
                "client_id": client_id,
                "code_verifier": verifier,
            },
        ).json()["access_token"]
        response = http.post(
            "/mcp",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json, text/event-stream",
            },
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "prueba", "version": "1"},
                },
            },
        )
    assert response.status_code == 200, response.text
    assert "ocr-mcp" in response.text
