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
