"""Cliente del core (reglas de `src/ocr_mcp/modules/core/context.md`)."""

from __future__ import annotations

import httpx
import pytest

from ocr_mcp.modules.core import (
    CoreAuthError,
    CoreClient,
    CoreNotFound,
    CoreRejected,
    CoreUnavailable,
)
from tests.conftest import make_pdf
from tests.fakes.core import TOKEN, FakeCore

pytestmark = pytest.mark.anyio


def client_for(app, token: str = TOKEN) -> CoreClient:
    return CoreClient("http://core.test", token, transport=httpx.ASGITransport(app=app))


async def test_upload_streams_the_pdf_and_reads_artifacts(tmp_path):
    core = FakeCore()
    source = tmp_path / "doc.pdf"
    source.write_bytes(make_pdf(3))
    client = client_for(core.app)
    meta = await client.meta()
    assert meta.markdown and meta.max_upload_bytes == core.max_upload_bytes
    job_id = await client.submit(source, artifacts=["md"], idempotency_key="k1")
    assert core.jobs[job_id]["pages"] == 3
    assert (await client.job(job_id))["status"] == "done"
    assert "<!-- ocr-page: 3 -->" in await client.artifact_text(job_id, "md")
    await client.delete(job_id)
    await client.delete(job_id)  # borrar algo que ya no existe no es un error
    await client.aclose()


async def test_core_errors_are_translated_without_the_token(tmp_path):
    core = FakeCore()
    with pytest.raises(CoreAuthError) as denied:
        await client_for(core.app, token="otro").meta()
    assert TOKEN not in str(denied.value) and "otro" not in str(denied.value)
    client = client_for(core.app)
    with pytest.raises(CoreNotFound):
        await client.job("no-existe")
    core.max_upload_bytes = 10
    source = tmp_path / "doc.pdf"
    source.write_bytes(make_pdf(60))  # supera el margen que el core simulado deja al multipart
    with pytest.raises(CoreRejected, match="tamaño máximo"):
        await client.submit(source, artifacts=["md"], idempotency_key="k")


async def test_an_unreachable_core_is_reported_as_unavailable():
    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("sin conexión")

    client = CoreClient("http://core.test", TOKEN, transport=httpx.MockTransport(down))
    with pytest.raises(CoreUnavailable):
        await client.meta()
