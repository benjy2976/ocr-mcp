"""Herramientas MCP y registro de trabajos. Ver `context.md`."""

from ocr_mcp.modules.jobs import ledger, markdown
from ocr_mcp.modules.jobs.tools import JobsDeps, register

__all__ = ["JobsDeps", "ledger", "markdown", "register"]
