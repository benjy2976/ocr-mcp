"""Enlaces de subida y descarga, y URL permitidas. Ver `context.md`."""

from ocr_mcp.modules.files.downloads import ARTIFACTS, Downloads
from ocr_mcp.modules.files.fetch import allowed, fetch_into_upload
from ocr_mcp.modules.files.routes import routes
from ocr_mcp.modules.files.uploads import Upload, UploadError, Uploads, count_pages

__all__ = [
    "ARTIFACTS",
    "Downloads",
    "Upload",
    "UploadError",
    "Uploads",
    "allowed",
    "count_pages",
    "fetch_into_upload",
    "routes",
]
