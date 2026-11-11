"""Comando `ocr-mcp` (`docs/cli.md`)."""

from __future__ import annotations

import os

from ocr_mcp import __main__ as cli
from ocr_mcp.shared.security import verify_password


def test_hash_password_prints_a_verifiable_hash(monkeypatch, capsys):
    answers = iter(["una contraseña larga", "una contraseña larga"])
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt: next(answers))
    assert cli.main(["hash-password"]) == 0
    printed = capsys.readouterr().out.strip()
    assert verify_password("una contraseña larga", printed)


def test_hash_password_rejects_short_or_mismatched_passwords(monkeypatch):
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt: "corta")
    assert cli.main(["hash-password"]) == 2
    answers = iter(["una contraseña larga", "otra contraseña larga"])
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt: next(answers))
    assert cli.main(["hash-password"]) == 2


def test_serve_without_configuration_exits_with_2(monkeypatch, capsys):
    for name in list(os.environ):
        if name.startswith(("OCR_MCP_", "OCR_CORE_")):
            monkeypatch.delenv(name)
    assert cli.main(["serve"]) == 2
    assert "Faltan variables" in capsys.readouterr().err


def test_env_file_does_not_override_the_environment(monkeypatch, tmp_path):
    env_file = tmp_path / "servidor.env"
    env_file.write_text("# comentario\nOCR_MCP_PORT=19000\nOCR_MCP_HOST='0.0.0.0'\n")
    monkeypatch.setenv("OCR_MCP_PORT", "18041")
    monkeypatch.delenv("OCR_MCP_HOST", raising=False)
    cli._load_env_file(env_file)
    assert os.environ["OCR_MCP_PORT"] == "18041" and os.environ["OCR_MCP_HOST"] == "0.0.0.0"


def _serve_with(monkeypatch, tmp_path, **variables: str) -> dict:
    """Corre `serve` sin abrir el puerto y devuelve las opciones que recibió uvicorn."""
    import uvicorn

    from ocr_mcp import app as application
    from ocr_mcp.shared.security import hash_password

    for name in list(os.environ):
        if name.startswith(("OCR_MCP_", "OCR_CORE_")) or name == "FORWARDED_ALLOW_IPS":
            monkeypatch.delenv(name)
    base = {
        "OCR_CORE_URL": "http://127.0.0.1:18012",
        "OCR_CORE_TOKEN": "secreto-del-core",
        "OCR_MCP_PUBLIC_URL": "https://ocr.ejemplo.org",
        "OCR_MCP_DATA_DIR": str(tmp_path),
        "OCR_MCP_ADMIN_USER": "admin",
        "OCR_MCP_ADMIN_PASSWORD_HASH": hash_password("contraseña-de-prueba"),
    }
    for name, value in {**base, **variables}.items():
        monkeypatch.setenv(name, value)
    received: dict = {}
    monkeypatch.setattr(application, "build", lambda settings: "app")
    monkeypatch.setattr(uvicorn, "run", lambda app, **options: received.update(options))
    assert cli.main(["serve"]) == 0
    return received


def test_serve_passes_the_trusted_proxies_to_uvicorn(monkeypatch, tmp_path, capsys):
    options = _serve_with(monkeypatch, tmp_path, OCR_MCP_TRUSTED_PROXIES="10.42.0.0/16")
    assert options["forwarded_allow_ips"] == "10.42.0.0/16" and options["proxy_headers"]
    assert "aviso" not in capsys.readouterr().err


def test_serve_warns_behind_a_proxy_without_trusted_proxies(monkeypatch, tmp_path, capsys):
    options = _serve_with(monkeypatch, tmp_path)
    assert "forwarded_allow_ips" not in options
    assert "OCR_MCP_TRUSTED_PROXIES" in capsys.readouterr().err
    _serve_with(monkeypatch, tmp_path, FORWARDED_ALLOW_IPS="*")
    assert "aviso" not in capsys.readouterr().err
