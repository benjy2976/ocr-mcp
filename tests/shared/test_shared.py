"""Seguridad y base de datos compartidas."""

from __future__ import annotations

from ocr_mcp.shared.db import Database
from ocr_mcp.shared.security import (
    hash_password,
    is_password_hash,
    new_secret,
    same,
    secret_hash,
    verify_password,
)


def test_passwords_are_salted_and_verified():
    first, second = hash_password("una contraseña larga"), hash_password("una contraseña larga")
    assert first != second and is_password_hash(first)
    assert verify_password("una contraseña larga", first)
    assert not verify_password("otra", first)
    assert not is_password_hash("texto-en-claro") and not verify_password("x", "texto-en-claro")


def test_password_hashes_avoid_dollar_signs_and_accept_the_old_format():
    encoded = hash_password("una contraseña larga")
    assert "$" not in encoded and encoded.startswith("scrypt:")
    old_format = encoded.replace(":", "$")
    assert is_password_hash(old_format) and verify_password("una contraseña larga", old_format)


def test_secrets_are_random_and_stored_as_hashes():
    secret = new_secret("ocrk_")
    assert secret.startswith("ocrk_") and secret != new_secret("ocrk_")
    assert len(secret_hash(secret)) == 64 and secret not in secret_hash(secret)
    assert same("abc", "abc") and not same("abc", "abd")


def test_migrations_apply_once(tmp_path):
    db = Database(tmp_path / "base.sqlite3")
    assert db.migrate() == ["001_inicial.sql"]
    assert db.migrate() == []
    connection = db.connect()
    try:
        tables = {
            row["name"]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
    finally:
        connection.close()
    assert {"access_keys", "oauth_tokens", "jobs", "uploads", "downloads", "settings"} <= tables
