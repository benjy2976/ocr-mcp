"""Configuración desde el entorno (`docs/entorno.md`)."""

from __future__ import annotations

import pytest

from ocr_mcp.config import ConfigError, Settings
from ocr_mcp.shared.security import hash_password

HASH = hash_password("contraseña-de-prueba")


def environment(**overrides: str) -> dict[str, str]:
    values = {
        "OCR_CORE_URL": "http://127.0.0.1:18012/",
        "OCR_CORE_TOKEN": "secreto-del-core",
        "OCR_MCP_PUBLIC_URL": "http://127.0.0.1:18040",
        "OCR_MCP_DATA_DIR": "/tmp/ocr-mcp-prueba",
        "OCR_MCP_ADMIN_USER": "admin",
        "OCR_MCP_ADMIN_PASSWORD_HASH": HASH,
    }
    values.update(overrides)
    return values


def test_a_complete_environment_loads_with_defaults():
    settings = Settings.from_env(environment())
    assert settings.core_url == "http://127.0.0.1:18012" and settings.port == 18040
    assert settings.resource_url == "http://127.0.0.1:18040/mcp"
    assert settings.allowed_url_prefixes == () and settings.max_pages is None
    assert settings.access_token_ttl == 3600 and not settings.secure_cookies


def test_missing_variables_are_listed_without_secrets():
    with pytest.raises(ConfigError) as error:
        Settings.from_env(environment(OCR_CORE_TOKEN="", OCR_MCP_ADMIN_USER=" "))
    assert "OCR_CORE_TOKEN" in str(error.value) and "secreto" not in str(error.value)


@pytest.mark.parametrize(
    "name,value",
    [
        ("OCR_MCP_PUBLIC_URL", "http://ocr.ejemplo.org"),
        ("OCR_MCP_PUBLIC_URL", "https://ocr.ejemplo.org/?a=1"),
        ("OCR_MCP_ADMIN_PASSWORD_HASH", "contraseña-en-claro"),
        ("OCR_MCP_PORT", "cero"),
        ("OCR_MCP_ALLOWED_URL_PREFIXES", "ftp://archivos"),
    ],
)
def test_unsafe_values_stop_the_server(name, value):
    with pytest.raises(ConfigError):
        Settings.from_env(environment(**{name: value}))


def test_https_public_urls_and_prefixes():
    settings = Settings.from_env(
        environment(
            OCR_MCP_PUBLIC_URL="https://ocr.ejemplo.org/",
            OCR_MCP_ALLOWED_URL_PREFIXES="https://a.ejemplo.org/docs, https://b.ejemplo.org",
            OCR_MCP_MAX_PAGES="200",
        )
    )
    assert settings.secure_cookies and settings.max_pages == 200
    assert settings.allowed_url_prefixes == ("https://a.ejemplo.org/docs", "https://b.ejemplo.org")
