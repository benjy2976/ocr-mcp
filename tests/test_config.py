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


def test_tls_needs_both_files_and_an_https_public_url(tmp_path):
    cert, key = tmp_path / "servidor.crt", tmp_path / "servidor.key"
    cert.write_text("certificado")
    key.write_text("llave")
    https = {"OCR_MCP_PUBLIC_URL": "https://ocr.ejemplo.lan:18040"}
    loaded = Settings.from_env(
        environment(**https, OCR_MCP_TLS_CERT=str(cert), OCR_MCP_TLS_KEY=str(key))
    )
    assert loaded.tls_cert == cert and loaded.tls_key == key and loaded.secure_cookies
    with pytest.raises(ConfigError, match="van juntas"):
        Settings.from_env(environment(**https, OCR_MCP_TLS_CERT=str(cert)))
    with pytest.raises(ConfigError, match="debe usar https"):
        Settings.from_env(environment(OCR_MCP_TLS_CERT=str(cert), OCR_MCP_TLS_KEY=str(key)))
    with pytest.raises(ConfigError, match="no apunta"):
        Settings.from_env(
            environment(**https, OCR_MCP_TLS_CERT=str(cert), OCR_MCP_TLS_KEY=str(tmp_path / "x"))
        )
    assert Settings.from_env(environment()).tls_cert is None


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


def test_trusted_proxies_accept_ips_ranges_or_everyone():
    assert Settings.from_env(environment()).trusted_proxies is None
    assert Settings.from_env(environment(OCR_MCP_TRUSTED_PROXIES=" * ")).trusted_proxies == "*"
    loaded = Settings.from_env(environment(OCR_MCP_TRUSTED_PROXIES="10.42.0.0/16, 192.0.2.7"))
    assert loaded.trusted_proxies == "10.42.0.0/16,192.0.2.7"
    for bad in ("proxy.interno", "10.0.0.0/8,*", "300.1.1.1"):
        with pytest.raises(ConfigError, match="OCR_MCP_TRUSTED_PROXIES"):
            Settings.from_env(environment(OCR_MCP_TRUSTED_PROXIES=bad))


def test_a_proxy_in_front_without_trusted_proxies_is_detected():
    behind = environment(OCR_MCP_PUBLIC_URL="https://ocr.ejemplo.org")
    assert Settings.from_env(behind).behind_untrusted_proxy
    trusted = dict(behind, OCR_MCP_TRUSTED_PROXIES="10.42.0.0/16")
    assert not Settings.from_env(trusted).behind_untrusted_proxy
    assert not Settings.from_env(environment()).behind_untrusted_proxy
