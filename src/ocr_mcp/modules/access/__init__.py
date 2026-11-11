"""Claves de acceso, OAuth incluido, inicio de sesión y claves públicas. Ver `context.md`."""

from starlette.routing import Route

from ocr_mcp.modules.access import keys, login, public_keys
from ocr_mcp.modules.access.keys import AccessKey
from ocr_mcp.modules.access.oauth import SCOPE, AccessProvider
from ocr_mcp.shared.db import Database

__all__ = ["SCOPE", "AccessKey", "AccessProvider", "keys", "routes"]


def routes(db: Database, provider: AccessProvider) -> list[Route]:
    """Rutas propias del módulo: inicio de sesión de OAuth y `/public/key`."""
    return [*login.routes(db, provider), *public_keys.routes(db, provider.settings)]
