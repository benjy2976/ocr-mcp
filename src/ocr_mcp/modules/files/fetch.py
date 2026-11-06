"""Descarga de un PDF por URL, solo desde los prefijos que configura quien opera (decisión 0003).

La lista está vacía por defecto, así que esta vía queda apagada: el servidor no
puede usarse para alcanzar direcciones internas (SSRF). No sigue redirecciones,
que podrían salir de los prefijos permitidos.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from urllib.parse import urlsplit

import httpx

from ocr_mcp.modules.files.uploads import Upload, UploadError, Uploads


def allowed(url: str, prefixes: tuple[str, ...]) -> bool:
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or parts.username or parts.password:
        return False
    return any(url == prefix or url.startswith(prefix + "/") for prefix in prefixes)


async def fetch_into_upload(
    url: str,
    *,
    key_id: str,
    uploads: Uploads,
    prefixes: tuple[str, ...],
    max_bytes: int | None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> Upload:
    """Descarga la URL a una subida nueva de `key_id`, con las mismas validaciones que el enlace."""
    if not allowed(url, prefixes):
        raise UploadError("Esa URL no está entre los prefijos permitidos por este servidor.")
    _, link = uploads.create(key_id)
    secret = link.rsplit("/", 1)[1]
    async with httpx.AsyncClient(
        follow_redirects=False, timeout=60.0, transport=transport
    ) as client:
        try:
            async with client.stream("GET", url) as response:
                if response.status_code != 200:
                    raise UploadError(f"La URL respondió {response.status_code}.")
                upload = await uploads.receive(secret, _chunks(response), max_bytes)
        except httpx.HTTPError as error:
            raise UploadError("No se pudo descargar la URL.") from error
    return upload


async def _chunks(response: httpx.Response) -> AsyncIterator[bytes]:
    async for chunk in response.aiter_bytes():
        yield chunk
