"""Configuración del servidor, leída del entorno y validada al arrancar.

Es la única pieza que lee variables de entorno: los módulos reciben `Settings`.
La lista de variables y su significado viven en `docs/entorno.md`.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from ocr_mcp.shared.security import is_password_hash

LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "[::1]", "::1"}


class ConfigError(ValueError):
    """La configuración no permite arrancar. El mensaje nunca incluye secretos."""


@dataclass(frozen=True)
class Settings:
    core_url: str
    core_token: str
    public_url: str
    host: str
    port: int
    data_dir: Path
    admin_user: str
    admin_password_hash: str
    allowed_url_prefixes: tuple[str, ...] = ()
    access_token_ttl: int = 3600
    refresh_token_ttl: int = 30 * 86400
    link_ttl: int = 1800
    max_upload_bytes: int | None = None
    max_pages: int | None = None

    @property
    def resource_url(self) -> str:
        """Recurso protegido (RFC 8707): el endpoint MCP."""
        return f"{self.public_url}/mcp"

    @property
    def secure_cookies(self) -> bool:
        return self.public_url.startswith("https://")

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Settings:
        env = os.environ if environ is None else environ
        required = {
            "OCR_CORE_URL": "dirección del core",
            "OCR_CORE_TOKEN": "token de este servidor ante el core",
            "OCR_MCP_PUBLIC_URL": "URL pública del servidor",
            "OCR_MCP_DATA_DIR": "carpeta de datos",
            "OCR_MCP_ADMIN_USER": "usuario del panel /admin",
            "OCR_MCP_ADMIN_PASSWORD_HASH": "hash de la contraseña del admin",
        }
        missing = [name for name in required if not env.get(name, "").strip()]
        if missing:
            raise ConfigError("Faltan variables de entorno: " + ", ".join(missing))

        public_url = _url(env["OCR_MCP_PUBLIC_URL"], "OCR_MCP_PUBLIC_URL")
        if public_url.startswith("http://") and urlsplit(public_url).hostname not in LOOPBACK_HOSTS:
            raise ConfigError("OCR_MCP_PUBLIC_URL debe usar https salvo en 127.0.0.1 o localhost")
        password_hash = env["OCR_MCP_ADMIN_PASSWORD_HASH"].strip()
        if not is_password_hash(password_hash):
            raise ConfigError(
                "OCR_MCP_ADMIN_PASSWORD_HASH no tiene el formato esperado; "
                "generarlo con `ocr-mcp hash-password`"
            )
        prefixes = tuple(
            _url(item, "OCR_MCP_ALLOWED_URL_PREFIXES")
            for item in env.get("OCR_MCP_ALLOWED_URL_PREFIXES", "").split(",")
            if item.strip()
        )
        return cls(
            core_url=_url(env["OCR_CORE_URL"], "OCR_CORE_URL"),
            core_token=env["OCR_CORE_TOKEN"].strip(),
            public_url=public_url,
            host=env.get("OCR_MCP_HOST", "127.0.0.1").strip() or "127.0.0.1",
            port=_int(env, "OCR_MCP_PORT", 18040),
            data_dir=Path(env["OCR_MCP_DATA_DIR"]).expanduser(),
            admin_user=env["OCR_MCP_ADMIN_USER"].strip(),
            admin_password_hash=password_hash,
            allowed_url_prefixes=prefixes,
            access_token_ttl=_int(env, "OCR_MCP_ACCESS_TOKEN_TTL_MIN", 60) * 60,
            refresh_token_ttl=_int(env, "OCR_MCP_REFRESH_TOKEN_TTL_DAYS", 30) * 86400,
            link_ttl=_int(env, "OCR_MCP_LINK_TTL_MIN", 30) * 60,
            max_upload_bytes=_optional_int(env, "OCR_MCP_MAX_UPLOAD_BYTES"),
            max_pages=_optional_int(env, "OCR_MCP_MAX_PAGES"),
        )


def _url(value: str, name: str) -> str:
    url = value.strip().rstrip("/")
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.netloc or parts.query or parts.fragment:
        raise ConfigError(f"{name} debe ser una URL http(s) sin consulta ni fragmento")
    return url


def _int(env: Mapping[str, str], name: str, default: int) -> int:
    value = env.get(name, "").strip()
    if not value:
        return default
    if not value.isdigit() or int(value) <= 0:
        raise ConfigError(f"{name} debe ser un entero positivo")
    return int(value)


def _optional_int(env: Mapping[str, str], name: str) -> int | None:
    return _int(env, name, 0) if env.get(name, "").strip() else None
