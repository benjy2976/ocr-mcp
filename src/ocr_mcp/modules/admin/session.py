"""Sesión del admin del panel (decisión 0006).

Usuario y contraseña vienen del entorno (la contraseña solo como hash scrypt).
La sesión es una cookie `HttpOnly` y `SameSite=Strict` (además `Secure` detrás
de TLS) cuyo secreto se guarda como hash; cada sesión tiene su token CSRF.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from urllib.parse import urlsplit

from starlette.requests import Request
from starlette.responses import Response

from ocr_mcp.config import Settings
from ocr_mcp.shared.db import Database
from ocr_mcp.shared.security import new_secret, same, secret_hash, verify_password

COOKIE = "ocr_mcp_admin"
SESSION_TTL = 8 * 3600


@dataclass(frozen=True)
class Session:
    csrf: str


class AdminSessions:
    def __init__(self, db: Database, settings: Settings):
        self.db = db
        self.settings = settings
        # Respeta un prefijo de ruta en la URL pública (por ejemplo, detrás de un proxy).
        self.cookie_path = urlsplit(settings.public_url).path + "/admin"

    def login(self, user: str, password: str) -> str | None:
        """Secreto de una sesión nueva, o `None` si las credenciales no valen."""
        user_ok = same(user, self.settings.admin_user)
        password_ok = verify_password(password, self.settings.admin_password_hash)
        if not (user_ok and password_ok):
            return None
        secret = new_secret()
        now = time.time()
        with self.db.transaction() as connection:
            connection.execute("DELETE FROM admin_sessions WHERE expires_at < ?", (now,))
            connection.execute(
                "INSERT INTO admin_sessions (token_hash, csrf, expires_at) VALUES (?, ?, ?)",
                (secret_hash(secret), new_secret(), now + SESSION_TTL),
            )
        return secret

    def current(self, request: Request) -> Session | None:
        secret = request.cookies.get(COOKIE, "")
        if not secret:
            return None
        connection = self.db.connect()
        try:
            row = connection.execute(
                "SELECT csrf FROM admin_sessions WHERE token_hash = ? AND expires_at >= ?",
                (secret_hash(secret), time.time()),
            ).fetchone()
        finally:
            connection.close()
        return Session(row["csrf"]) if row else None

    def logout(self, request: Request) -> None:
        secret = request.cookies.get(COOKIE, "")
        if secret:
            with self.db.transaction() as connection:
                connection.execute(
                    "DELETE FROM admin_sessions WHERE token_hash = ?", (secret_hash(secret),)
                )

    def set_cookie(self, response: Response, secret: str) -> None:
        response.set_cookie(
            COOKIE,
            secret,
            max_age=SESSION_TTL,
            path=self.cookie_path,
            httponly=True,
            samesite="strict",
            secure=self.settings.secure_cookies,
        )

    def clear_cookie(self, response: Response) -> None:
        response.delete_cookie(COOKIE, path=self.cookie_path)
