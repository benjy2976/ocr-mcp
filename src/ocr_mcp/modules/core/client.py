"""Cliente HTTP de `ocr-core`, el único que conoce su API.

Sube el PDF por partes (multipart con `Content-Length`, sin cargarlo en
memoria), consulta trabajos, descarga artefactos y borra trabajos. Cada
llamada lleva `Authorization: Bearer <OCR_CORE_TOKEN>`; el token nunca se
registra ni aparece en un error.
"""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

MARKDOWN_SCHEMA = "ocr.markdown.document.v1"
TERMINAL_STATES = frozenset({"done", "failed", "blocked"})
CHUNK_BYTES = 1024 * 1024
META_TTL_SECONDS = 60


class CoreError(Exception):
    """Fallo al hablar con el core. El mensaje es apto para el usuario."""


class CoreAuthError(CoreError):
    """El core rechazó el token de este servidor (401)."""


class CoreUnavailable(CoreError):
    """El core no respondió o respondió con un error propio (5xx)."""


class CoreRejected(CoreError):
    """El core rechazó el pedido (4xx): el documento o los parámetros no sirven."""

    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.status_code = status_code


class CoreNotFound(CoreError):
    """El trabajo o el artefacto ya no existen en el core."""


@dataclass(frozen=True)
class CoreMeta:
    version: str
    max_upload_bytes: int | None
    markdown: bool


class CoreClient:
    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 30.0,
    ):
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=httpx.Timeout(timeout, read=300.0),
            transport=transport,
        )
        self._meta: tuple[float, CoreMeta] | None = None

    async def aclose(self) -> None:
        await self._client.aclose()

    async def meta(self, *, refresh: bool = False) -> CoreMeta:
        if not refresh and self._meta and time.monotonic() - self._meta[0] < META_TTL_SECONDS:
            return self._meta[1]
        data = (await self._request("GET", "/meta")).json()
        capabilities = data.get("capabilities") or {}
        schemas = capabilities.get("artifact_schemas") or {}
        limit = data.get("max_upload_bytes")
        meta = CoreMeta(
            version=str(data.get("version", "desconocida")),
            max_upload_bytes=limit if isinstance(limit, int) and limit > 0 else None,
            markdown=schemas.get("md") == MARKDOWN_SCHEMA,
        )
        self._meta = (time.monotonic(), meta)
        return meta

    async def submit(
        self,
        source: Path,
        *,
        artifacts: list[str],
        idempotency_key: str,
        options: dict[str, Any] | None = None,
    ) -> str:
        """Crea el trabajo y devuelve su `job_id` sin esperar el resultado."""
        body = _Multipart(
            source,
            {
                "artifacts": {name: {} for name in artifacts},
                "options": options or {},
                "idempotency_key": idempotency_key,
            },
        )
        response = await self._request(
            "POST",
            "/jobs/upload",
            content=body,
            headers={"Content-Type": body.content_type, "Content-Length": str(len(body))},
        )
        return str(response.json()["job_id"])

    async def job(self, job_id: str) -> dict[str, Any]:
        return (await self._request("GET", f"/jobs/{job_id}")).json()

    async def artifact_text(self, job_id: str, name: str) -> str:
        return (await self._request("GET", f"/jobs/{job_id}/artifacts/{name}")).text

    @asynccontextmanager
    async def artifact_stream(self, job_id: str, name: str) -> AsyncIterator[httpx.Response]:
        request = self._client.build_request("GET", f"/jobs/{job_id}/artifacts/{name}")
        try:
            response = await self._client.send(request, stream=True)
        except httpx.HTTPError as error:
            raise CoreUnavailable("No se pudo contactar con el core.") from error
        try:
            _raise_for_status(response)
            yield response
        finally:
            await response.aclose()

    async def delete(self, job_id: str) -> None:
        try:
            await self._request("DELETE", f"/jobs/{job_id}")
        except CoreNotFound:
            return

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            response = await self._client.request(method, path, **kwargs)
        except httpx.HTTPError as error:
            raise CoreUnavailable("No se pudo contactar con el core.") from error
        _raise_for_status(response)
        return response


def _raise_for_status(response: httpx.Response) -> None:
    status = response.status_code
    if status < 400:
        return
    if status == 401:
        raise CoreAuthError("El core rechazó el token de este servidor.")
    if status == 404:
        raise CoreNotFound("El trabajo o el artefacto ya no existen en el core.")
    if status == 413:
        raise CoreRejected("El PDF supera el tamaño máximo que acepta el core.", status)
    if status < 500:
        raise CoreRejected(f"El core rechazó el pedido ({status}).", status)
    raise CoreUnavailable(f"El core respondió con un error ({status}).")


class _Multipart:
    """Cuerpo multipart con los campos `request` y `file`, leído por bloques."""

    def __init__(self, source: Path, request: dict[str, Any]):
        boundary = uuid.uuid4().hex
        self.content_type = f"multipart/form-data; boundary={boundary}"
        self._source = source
        self._size = source.stat().st_size
        self._head = (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="request"\r\n'
            "Content-Type: application/json\r\n\r\n"
            f"{json.dumps(request, ensure_ascii=False)}\r\n"
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="file"; filename="documento.pdf"\r\n'
            "Content-Type: application/pdf\r\n\r\n"
        ).encode()
        self._tail = f"\r\n--{boundary}--\r\n".encode()

    def __len__(self) -> int:
        return len(self._head) + self._size + len(self._tail)

    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield self._head
        with self._source.open("rb") as handle:
            while chunk := handle.read(CHUNK_BYTES):
                yield chunk
        yield self._tail
