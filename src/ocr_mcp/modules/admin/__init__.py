"""Panel /admin: claves, cuotas, uso y modo público. Ver `context.md`."""

from ocr_mcp.modules.admin.routes import routes
from ocr_mcp.modules.admin.session import AdminSessions

__all__ = ["AdminSessions", "routes"]
