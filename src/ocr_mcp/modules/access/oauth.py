"""Proveedor del servidor de autorización incluido (decisiones 0002 y 0006).

El SDK de MCP monta `/authorize`, `/token`, `/register`, `/revoke` y los
metadatos; este proveedor guarda clientes, códigos y tokens en SQLite (solo sus
hashes) y envía al usuario a la página que pide su clave. El `subject` de cada
código y token es el identificador de la clave: así cada herramienta sabe quién
la llama.
"""

from __future__ import annotations

import json
import time

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    RefreshToken,
    construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

from ocr_mcp.config import Settings
from ocr_mcp.modules.access import keys
from ocr_mcp.shared.db import Database
from ocr_mcp.shared.security import new_secret, secret_hash

SCOPE = "ocr"
PENDING_TTL = 600
CODE_TTL = 300


class AccessProvider:
    def __init__(self, db: Database, settings: Settings):
        self.db = db
        self.settings = settings

    # --- clientes (registro dinámico) -------------------------------------

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        row = self._fetch("SELECT info FROM oauth_clients WHERE client_id = ?", client_id)
        return OAuthClientInformationFull.model_validate_json(row["info"]) if row else None

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        with self.db.transaction() as connection:
            connection.execute(
                "INSERT INTO oauth_clients (client_id, info, created_at) VALUES (?, ?, ?)",
                (client_info.client_id, client_info.model_dump_json(), time.time()),
            )

    # --- autorización: el usuario pega su clave en `/login` ----------------

    async def authorize(
        self, client: OAuthClientInformationFull, params: AuthorizationParams
    ) -> str:
        request_id = new_secret()
        with self.db.transaction() as connection:
            connection.execute("DELETE FROM oauth_pending WHERE expires_at < ?", (time.time(),))
            connection.execute(
                "INSERT INTO oauth_pending (request_hash, client_id, params, expires_at) "
                "VALUES (?, ?, ?, ?)",
                (
                    secret_hash(request_id),
                    client.client_id,
                    params.model_dump_json(),
                    time.time() + PENDING_TTL,
                ),
            )
        return f"{self.settings.public_url}/login?request={request_id}"

    def pending(self, request_id: str) -> tuple[str, AuthorizationParams] | None:
        """Pedido de autorización que espera la clave, o `None` si no existe o venció."""
        row = self._fetch(
            "SELECT client_id, params FROM oauth_pending WHERE request_hash = ? AND expires_at >= "
            "?",
            secret_hash(request_id),
            time.time(),
        )
        if row is None:
            return None
        return row["client_id"], AuthorizationParams.model_validate_json(row["params"])

    def approve(self, request_id: str, key_id: str) -> str:
        """Cambia el pedido por un código de un solo uso y devuelve la URL de vuelta al cliente."""
        found = self.pending(request_id)
        if found is None:
            raise LookupError("El pedido de autorización no existe o venció.")
        client_id, params = found
        code = new_secret()
        with self.db.transaction() as connection:
            connection.execute(
                "DELETE FROM oauth_pending WHERE request_hash = ?", (secret_hash(request_id),)
            )
            connection.execute(
                "INSERT INTO oauth_codes (code_hash, client_id, key_id, params, expires_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    secret_hash(code),
                    client_id,
                    key_id,
                    params.model_dump_json(),
                    time.time() + CODE_TTL,
                ),
            )
        return construct_redirect_uri(str(params.redirect_uri), code=code, state=params.state)

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> AuthorizationCode | None:
        row = self._fetch(
            "SELECT key_id, params, expires_at FROM oauth_codes "
            "WHERE code_hash = ? AND client_id = ? AND expires_at >= ?",
            secret_hash(authorization_code),
            client.client_id,
            time.time(),
        )
        if row is None:
            return None
        params = AuthorizationParams.model_validate_json(row["params"])
        return AuthorizationCode(
            code=authorization_code,
            scopes=params.scopes or [SCOPE],
            expires_at=row["expires_at"],
            client_id=client.client_id,
            code_challenge=params.code_challenge,
            redirect_uri=params.redirect_uri,
            redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly,
            resource=self.settings.resource_url,
            subject=row["key_id"],
        )

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        with self.db.transaction() as connection:
            used = connection.execute(
                "DELETE FROM oauth_codes WHERE code_hash = ?",
                (secret_hash(authorization_code.code),),
            ).rowcount
            if used != 1:
                raise ValueError("El código ya se usó.")
        return self._issue(
            client.client_id, str(authorization_code.subject), authorization_code.scopes
        )

    # --- tokens -------------------------------------------------------------

    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str
    ) -> RefreshToken | None:
        row = self._token(refresh_token, "refresh", client.client_id)
        if row is None:
            return None
        return RefreshToken(
            token=refresh_token,
            client_id=client.client_id,
            scopes=json.loads(row["scopes"]),
            expires_at=int(row["expires_at"]),
            resource=row["resource"],
            subject=row["key_id"],
        )

    async def exchange_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: RefreshToken, scopes: list[str]
    ) -> OAuthToken:
        # Rotación: el token de refresco usado deja de valer.
        with self.db.transaction() as connection:
            connection.execute(
                "DELETE FROM oauth_tokens WHERE token_hash = ?", (secret_hash(refresh_token.token),)
            )
        return self._issue(
            client.client_id, str(refresh_token.subject), scopes or refresh_token.scopes
        )

    async def load_access_token(self, token: str) -> AccessToken | None:
        row = self._token(token, "access", None)
        if row is None:
            return None
        keys.touch(self.db, row["key_id"])
        return AccessToken(
            token=token,
            client_id=row["client_id"],
            scopes=json.loads(row["scopes"]),
            expires_at=int(row["expires_at"]),
            resource=row["resource"],
            subject=row["key_id"],
        )

    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        with self.db.transaction() as connection:
            connection.execute(
                "DELETE FROM oauth_tokens WHERE token_hash = ?", (secret_hash(token.token),)
            )

    # --- internos -------------------------------------------------------------

    def _issue(self, client_id: str, key_id: str, scopes: list[str]) -> OAuthToken:
        access, refresh = new_secret(), new_secret()
        now = time.time()
        rows = [
            (access, "access", now + self.settings.access_token_ttl),
            (refresh, "refresh", now + self.settings.refresh_token_ttl),
        ]
        with self.db.transaction() as connection:
            connection.execute("DELETE FROM oauth_tokens WHERE expires_at < ?", (now,))
            for secret, kind, expires_at in rows:
                connection.execute(
                    "INSERT INTO oauth_tokens (token_hash, kind, client_id, key_id, scopes, "
                    "resource, "
                    "expires_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        secret_hash(secret),
                        kind,
                        client_id,
                        key_id,
                        json.dumps(scopes),
                        self.settings.resource_url,
                        expires_at,
                        now,
                    ),
                )
        return OAuthToken(
            access_token=access,
            expires_in=self.settings.access_token_ttl,
            scope=" ".join(scopes),
            refresh_token=refresh,
        )

    def _token(self, token: str, kind: str, client_id: str | None):
        row = self._fetch(
            "SELECT * FROM oauth_tokens WHERE token_hash = ? AND kind = ? AND expires_at >= ?",
            secret_hash(token),
            kind,
            time.time(),
        )
        if row is None or (client_id is not None and row["client_id"] != client_id):
            return None
        return row

    def _fetch(self, sql: str, *params: object):
        connection = self.db.connect()
        try:
            return connection.execute(sql, params).fetchone()
        finally:
            connection.close()
