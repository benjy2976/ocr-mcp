"""Core simulado: imita la API HTTP de `ocr-core` 0.7.0 que usa el servidor.

Exige el token del servidor, cuenta las páginas del PDF subido, respeta la
`idempotency_key` y genera artefactos con el mismo formato de marcas de página
que el core real. Ninguna prueba necesita un core real, red ni GPU.
"""

from __future__ import annotations

import io
import json

from pypdf import PdfReader
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

TOKEN = "token-del-core"


class FakeCore:
    def __init__(self) -> None:
        self.jobs: dict[str, dict] = {}
        self.by_key: dict[str, str] = {}
        self.uploads = 0
        self.deleted: list[str] = []
        self.status = "done"  # estado con el que termina cada trabajo nuevo
        self.max_upload_bytes = 5 * 1024 * 1024
        self.markdown = True
        self.reused_source = False
        self.app = Starlette(
            routes=[
                Route("/meta", self.meta, methods=["GET"]),
                Route("/jobs/upload", self.upload, methods=["POST"]),
                Route("/jobs/{job_id}", self.job, methods=["GET"]),
                Route("/jobs/{job_id}", self.delete, methods=["DELETE"]),
                Route("/jobs/{job_id}/artifacts/{name}", self.artifact, methods=["GET"]),
            ]
        )

    def _denied(self, request: Request) -> Response | None:
        if request.headers.get("authorization") != f"Bearer {TOKEN}":
            return JSONResponse({"detail": "authentication required"}, status_code=401)
        return None

    async def meta(self, request: Request) -> Response:
        if denied := self._denied(request):
            return denied
        schemas = {"md": "ocr.markdown.document.v1"} if self.markdown else {}
        return JSONResponse(
            {
                "version": "0.7.0",
                "client_id": "mcp",
                "max_upload_bytes": self.max_upload_bytes,
                "capabilities": {"auth": "bearer", "artifact_schemas": schemas},
            }
        )

    async def upload(self, request: Request) -> Response:
        if denied := self._denied(request):
            return denied
        if int(request.headers.get("content-length", "0")) > self.max_upload_bytes + 4096:
            return JSONResponse({"detail": "too large"}, status_code=413)
        async with request.form() as form:
            body = json.loads(str(form["request"]))
            data = await form["file"].read()
        key = body["idempotency_key"]
        if key in self.by_key:
            return JSONResponse({"job_id": self.by_key[key], "status": "queued"}, status_code=202)
        self.uploads += 1
        job_id = f"job-{self.uploads}"
        pages = len(PdfReader(io.BytesIO(data)).pages)
        self.by_key[key] = job_id
        self.jobs[job_id] = {
            "status": self.status,
            "pages": pages,
            "requested": sorted(body["artifacts"]),
            "title": (body.get("options") or {}).get("document_title"),
        }
        return JSONResponse({"job_id": job_id, "status": "queued"}, status_code=202)

    async def job(self, request: Request) -> Response:
        if denied := self._denied(request):
            return denied
        job = self.jobs.get(request.path_params["job_id"])
        if job is None:
            return JSONResponse({"detail": "not found"}, status_code=404)
        artifacts = {}
        for name in job["requested"]:
            if name == "pdf" and self.reused_source:
                artifacts[name] = {"written": False, "reused_source": True}
            else:
                artifacts[name] = {"written": True, "staged": True}
        payload = {
            "job_id": request.path_params["job_id"],
            "status": job["status"],
            "preflight": {"decision": "ocr"},
            "artifacts": artifacts if job["status"] == "done" else {},
        }
        if job["status"] == "failed":
            payload["error"] = "fallo simulado del motor"
        return JSONResponse(payload)

    async def artifact(self, request: Request) -> Response:
        if denied := self._denied(request):
            return denied
        job = self.jobs.get(request.path_params["job_id"])
        name = request.path_params["name"]
        if job is None or name not in job["requested"]:
            return JSONResponse({"detail": "not found"}, status_code=404)
        if name == "md":
            return Response(markdown(job["pages"], job["title"]), media_type="text/markdown")
        if name == "text":
            lines = [
                json.dumps({"page": n, "text": f"texto {n}"}) for n in range(1, job["pages"] + 1)
            ]
            return Response("\n".join(lines), media_type="application/x-ndjson")
        return Response(b"%PDF-1.4 buscable", media_type="application/pdf")

    async def delete(self, request: Request) -> Response:
        if denied := self._denied(request):
            return denied
        job_id = request.path_params["job_id"]
        if self.jobs.pop(job_id, None) is None:
            return JSONResponse({"detail": "not found"}, status_code=404)
        self.deleted.append(job_id)
        return Response(status_code=204)


def markdown(pages: int, title: str | None) -> str:
    """Mismo formato que el artefacto real: encabezado YAML, título y una marca por página.

    La página 2 sale de baja confianza.
    """
    low = "[2]" if pages >= 2 else "[]"
    lines = [
        "---",
        'schema: "ocr.markdown.document.v1"',
        f"page_count: {pages}",
        f"low_confidence_pages: {low}",
        "---",
        "",
        f"# {title or 'documento'}",
        "",
    ]
    for page in range(1, pages + 1):
        lines += [f"<!-- ocr-page: {page} -->", f"## Página {page}", ""]
        if page == 2:
            lines += ["<!-- ocr-quality: low-confidence -->", ""]
        lines += [f"Texto de la página {page}.", ""]
    return "\n".join(lines)
