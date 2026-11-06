"""Claves de acceso, servidor OAuth incluido e inicio de sesión. Ver `context.md`."""

from ocr_mcp.modules.access import keys
from ocr_mcp.modules.access.keys import AccessKey
from ocr_mcp.modules.access.login import routes
from ocr_mcp.modules.access.oauth import SCOPE, AccessProvider

__all__ = ["SCOPE", "AccessKey", "AccessProvider", "keys", "routes"]
