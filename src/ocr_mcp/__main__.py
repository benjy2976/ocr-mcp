"""Comando `ocr-mcp` (contrato en `docs/cli.md`).

- `ocr-mcp serve [--env-file RUTA]`: arranca el servidor (por defecto).
- `ocr-mcp hash-password`: pide una contraseña y escribe su hash para
  `OCR_MCP_ADMIN_PASSWORD_HASH`.
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path

from ocr_mcp.config import ConfigError, Settings
from ocr_mcp.shared.security import hash_password

MIN_PASSWORD = 12
PROXY_WARNING = (
    "ocr-mcp: aviso: la URL pública usa https sin TLS propio (hay un proxy delante) y "
    "OCR_MCP_TRUSTED_PROXIES está vacía; todos los clientes llegarán con la IP del proxy y "
    "compartirán los límites por dirección"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ocr-mcp", description="Servidor MCP de OCR.")
    commands = parser.add_subparsers(dest="command")
    serve = commands.add_parser("serve", help="arranca el servidor (por defecto)")
    serve.add_argument(
        "--env-file", type=Path, help="archivo KEY=VALOR que se carga antes de leer el entorno"
    )
    commands.add_parser("hash-password", help="genera el hash de la contraseña del admin")
    args = parser.parse_args(argv)

    if args.command == "hash-password":
        return _hash_password()
    return _serve(getattr(args, "env_file", None))


def _serve(env_file: Path | None) -> int:
    import uvicorn

    from ocr_mcp.app import build

    try:
        if env_file is not None:
            _load_env_file(env_file)
        settings = Settings.from_env()
    except (ConfigError, OSError) as error:
        print(f"ocr-mcp: {error}", file=sys.stderr)
        return 2
    options: dict[str, object] = {"proxy_headers": True}
    if settings.tls_cert:
        options |= {"ssl_certfile": str(settings.tls_cert), "ssl_keyfile": str(settings.tls_key)}
    if settings.trusted_proxies:
        options["forwarded_allow_ips"] = settings.trusted_proxies
    elif settings.behind_untrusted_proxy and not os.environ.get("FORWARDED_ALLOW_IPS"):
        print(PROXY_WARNING, file=sys.stderr)
    uvicorn.run(build(settings), host=settings.host, port=settings.port, **options)
    return 0


def _hash_password() -> int:
    password = getpass.getpass("Contraseña del admin: ")
    if len(password) < MIN_PASSWORD:
        print(
            f"ocr-mcp: la contraseña necesita al menos {MIN_PASSWORD} caracteres", file=sys.stderr
        )
        return 2
    if getpass.getpass("Repítela: ") != password:
        print("ocr-mcp: las contraseñas no coinciden", file=sys.stderr)
        return 2
    print(hash_password(password))
    return 0


def _load_env_file(path: Path) -> None:
    """Carga líneas `KEY=VALOR` sin pisar variables ya definidas en el entorno."""
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        name, separator, value = line.partition("=")
        if not separator or not name.strip():
            raise ConfigError(f"{path}:{number}: se esperaba KEY=VALOR")
        os.environ.setdefault(name.strip(), value.strip().strip('"').strip("'"))


if __name__ == "__main__":
    raise SystemExit(main())
