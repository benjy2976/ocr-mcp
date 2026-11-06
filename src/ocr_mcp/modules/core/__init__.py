"""Cliente de `ocr-core`. Ver `context.md`."""

from ocr_mcp.modules.core.client import (
    TERMINAL_STATES,
    CoreAuthError,
    CoreClient,
    CoreError,
    CoreMeta,
    CoreNotFound,
    CoreRejected,
    CoreUnavailable,
)

__all__ = [
    "TERMINAL_STATES",
    "CoreAuthError",
    "CoreClient",
    "CoreError",
    "CoreMeta",
    "CoreNotFound",
    "CoreRejected",
    "CoreUnavailable",
]
