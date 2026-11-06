"""Rutas de los enlaces (decisión 0003). No usan OAuth: el secreto del enlace es la credencial.

- `PUT /u/{secreto}`: un agente con terminal sube el PDF (`curl -T documento.pdf <enlace>`).
- `GET /u/{secreto}` y `POST /u/{secreto}`: una persona elige el archivo en un formulario.
- `GET /d/{secreto}`: descarga de un artefacto, reenviada desde el core por partes.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path

from starlette.datastructures import UploadFile
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse
from starlette.routing import Route

from ocr_mcp.modules.core import CoreClient, CoreError, CoreNotFound
from ocr_mcp.modules.files.downloads import Downloads
from ocr_mcp.modules.files.uploads import Upload, UploadError, Uploads
from ocr_mcp.shared.web import render

TEMPLATES = Path(__file__).parent / "templates"
CHUNK_BYTES = 1024 * 1024
MULTIPART_OVERHEAD = 64 * 1024
EXTENSIONS = {"pdf": "pdf", "text": "jsonl", "md": "md"}
MEDIA_TYPES = {
    "pdf": "application/pdf",
    "text": "application/x-ndjson",
    "md": "text/markdown; charset=utf-8",
}


def routes(
    uploads: Uploads,
    downloads: Downloads,
    core: CoreClient,
    upload_limit: Callable[[], Awaitable[int | None]],
) -> list[Route]:
    """`upload_limit` es una corrutina que devuelve el tamaño máximo vigente, o `None`."""

    async def put(request: Request) -> Response:
        secret = request.path_params["secret"]
        try:
            limit = await upload_limit()
            _reject_declared_size(request, limit, 0)
            upload = await uploads.receive(secret, request.stream(), limit)
        except UploadError as error:
            return JSONResponse({"error": str(error)}, status_code=_status(error))
        except CoreError as error:
            return JSONResponse({"error": str(error)}, status_code=503)
        return JSONResponse(_summary(upload))

    async def form(request: Request) -> Response:
        if uploads.waiting(request.path_params["secret"]) is None:
            return _message(
                "Enlace no disponible", "El enlace de subida no existe, ya se usó o venció.", 404
            )
        return render(TEMPLATES, "upload.html")

    async def post(request: Request) -> Response:
        secret = request.path_params["secret"]
        try:
            limit = await upload_limit()
            _reject_declared_size(request, limit, MULTIPART_OVERHEAD)
            async with request.form(max_files=1, max_fields=1) as data:
                file = data.get("file")
                if not isinstance(file, UploadFile):
                    raise UploadError("No se recibió ningún archivo.")
                upload = await uploads.receive(secret, _read(file), limit)
        except UploadError as error:
            return render(TEMPLATES, "upload.html", _status(error), error=str(error))
        except CoreError as error:
            return render(TEMPLATES, "upload.html", 503, error=str(error))
        return render(TEMPLATES, "uploaded.html", upload=upload)

    async def download(request: Request) -> Response:
        found = downloads.resolve(request.path_params["secret"])
        if found is None:
            return _message(
                "Enlace no disponible", "El enlace de descarga no existe o venció.", 404
            )
        try:
            await core.job(found.job_id)  # falla antes de abrir la respuesta si ya no existe
        except CoreNotFound:
            return _message("Artefacto no disponible", "El trabajo ya no está en el core.", 410)
        except CoreError as error:
            return _message("Core no disponible", str(error), 503)
        filename = f"ocr-{found.job_id}.{EXTENSIONS[found.artifact]}"
        return StreamingResponse(
            _artifact(core, found.job_id, found.artifact),
            media_type=MEDIA_TYPES[found.artifact],
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "no-store",
            },
        )

    return [
        Route("/u/{secret}", put, methods=["PUT"]),
        Route("/u/{secret}", form, methods=["GET"]),
        Route("/u/{secret}", post, methods=["POST"]),
        Route("/d/{secret}", download, methods=["GET"]),
    ]


def _reject_declared_size(request: Request, limit: int | None, overhead: int) -> None:
    declared = request.headers.get("content-length", "")
    if limit is not None and declared.isdigit() and int(declared) > limit + overhead:
        raise UploadError(f"El PDF supera el tamaño máximo de {limit} bytes.")


async def _read(file: UploadFile) -> AsyncIterator[bytes]:
    while chunk := await file.read(CHUNK_BYTES):
        yield chunk


async def _artifact(core: CoreClient, job_id: str, name: str) -> AsyncIterator[bytes]:
    async with core.artifact_stream(job_id, name) as response:
        async for chunk in response.aiter_bytes():
            yield chunk


def _summary(upload: Upload) -> dict[str, object]:
    return {
        "upload_id": upload.id,
        "pages": upload.pages,
        "bytes": upload.bytes,
        "next": "Llama a ocr_submit con este upload_id.",
    }


def _status(error: UploadError) -> int:
    text = str(error)
    if "tamaño máximo" in text:
        return 413
    if "no existe" in text or "ya se usó" in text:
        return 404
    return 400


def _message(title: str, message: str, status: int) -> Response:
    return render(TEMPLATES, "message.html", status, title=title, message=message)
