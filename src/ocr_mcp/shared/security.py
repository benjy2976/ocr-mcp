"""Primitivas de seguridad: secretos aleatorios, hashes y contraseñas.

Las claves, los tokens y los enlaces se guardan solo como SHA-256 (decisión
0006). La contraseña del admin usa scrypt con sal. Ninguna función registra ni
devuelve el secreto en un error.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets

TOKEN_BYTES = 32
_SCRYPT = {"n": 2**14, "r": 8, "p": 1}


def new_secret(prefix: str = "") -> str:
    """Secreto aleatorio apto para URL, con un prefijo opcional que ayuda a reconocerlo."""
    return prefix + secrets.token_urlsafe(TOKEN_BYTES)


def new_id() -> str:
    return secrets.token_hex(12)


def secret_hash(secret: str) -> str:
    """Huella con la que se guarda y se busca un secreto."""
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def same(left: str, right: str) -> bool:
    """Comparación en tiempo constante."""
    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))


def hash_password(password: str) -> str:
    """`scrypt:n:r:p:sal:hash`. Sin `$`: Docker Compose y las shells lo interpretan."""
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, **_SCRYPT)
    return ":".join(
        [
            "scrypt",
            *(str(_SCRYPT[name]) for name in ("n", "r", "p")),
            base64.b64encode(salt).decode(),
            base64.b64encode(digest).decode(),
        ]
    )


def is_password_hash(encoded: str) -> bool:
    return _parse_password_hash(encoded) is not None


def verify_password(password: str, encoded: str) -> bool:
    parsed = _parse_password_hash(encoded)
    if parsed is None:
        return False
    n, r, p, salt, expected = parsed
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n, r=r, p=p)
    return hmac.compare_digest(digest, expected)


def _parse_password_hash(encoded: str) -> tuple[int, int, int, bytes, bytes] | None:
    # Acepta también el formato anterior, separado por `$`.
    parts = re.split(r"[:$]", encoded.strip())
    if len(parts) != 6 or parts[0] != "scrypt":
        return None
    try:
        n, r, p = (int(value) for value in parts[1:4])
        salt = base64.b64decode(parts[4], validate=True)
        digest = base64.b64decode(parts[5], validate=True)
    except ValueError:
        return None
    if n < 2 or r < 1 or p < 1 or not salt or not digest:
        return None
    return n, r, p, salt, digest
