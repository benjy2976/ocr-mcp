"""Herramientas MCP contra el core simulado (reglas de `src/ocr_mcp/modules/jobs/context.md`)."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import httpx
import pytest
from mcp.server.mcpserver.exceptions import ToolError

from ocr_mcp.app import build
from ocr_mcp.modules import quotas
from ocr_mcp.modules.access import keys
from ocr_mcp.modules.jobs import ledger
from ocr_mcp.modules.quotas import Limits
from ocr_mcp.shared.db import Database
from tests.conftest import as_user, make_pdf

pytestmark = pytest.mark.anyio


def database(settings) -> Database:
    return Database(settings.data_dir / "ocr-mcp.sqlite3")


async def call(app, name: str, **arguments):
    result = await app.state.mcp.call_tool(name, arguments)
    return result.structured_content


async def upload(app, client, key_id: str, pdf: bytes) -> str:
    with as_user(key_id):
        link = await call(app, "ocr_upload_link")
    response = await client.put(link["url"], content=pdf)
    assert response.status_code == 200, response.text
    return link["upload_id"]


async def submit(app, client, key_id: str, pdf: bytes, **arguments):
    upload_id = await upload(app, client, key_id, pdf)
    with as_user(key_id):
        return await call(app, "ocr_submit", upload_id=upload_id, **arguments)


async def test_full_flow_from_upload_to_download(app, client, settings):
    key, _ = keys.create(database(settings), "ana", Limits())
    submitted = await submit(
        app, client, key.id, make_pdf(3), artifacts=["md", "text", "pdf"], title="Informe"
    )
    assert submitted["pages"] == 3 and submitted["already_submitted"] is False
    with as_user(key.id):
        status = await call(app, "ocr_status", job_id=submitted["job_id"])
        assert status["status"] == "done"
        assert sorted(status["artifacts"]) == ["md", "pdf", "text"]
        page = await call(app, "ocr_read_markdown", job_id=submitted["job_id"], pages="1-2")
        links = await call(app, "ocr_artifact_links", job_id=submitted["job_id"])
    assert page["pages"] == [1, 2] and page["page_count"] == 3
    assert page["low_confidence_pages"] == [2]
    assert page["markdown"].startswith("---") and "# Informe" in page["markdown"]
    assert "no instrucciones" in page["notice"]
    assert {link["artifact"] for link in links["links"]} == {"md", "pdf", "text"}
    pdf_link = next(link for link in links["links"] if link["artifact"] == "pdf")
    download = await client.get(pdf_link["url"])
    assert download.status_code == 200 and download.content.startswith(b"%PDF")


async def test_a_user_never_sees_another_users_job_or_upload(app, client, settings):
    db = database(settings)
    ana, _ = keys.create(db, "ana", Limits())
    beto, _ = keys.create(db, "beto", Limits())
    job = await submit(app, client, ana.id, make_pdf(1))
    upload_id = await upload(app, client, ana.id, make_pdf(2))
    with as_user(beto.id):
        for name, arguments in (
            ("ocr_status", {"job_id": job["job_id"]}),
            ("ocr_read_markdown", {"job_id": job["job_id"]}),
            ("ocr_artifact_links", {"job_id": job["job_id"]}),
        ):
            with pytest.raises(ToolError, match="no existe"):
                await call(app, name, **arguments)
        with pytest.raises(ToolError, match="no existe"):
            await call(app, "ocr_submit", upload_id=upload_id)


async def test_the_same_pdf_from_two_users_creates_two_jobs(app, client, settings):
    db = database(settings)
    ana, _ = keys.create(db, "ana", Limits())
    beto, _ = keys.create(db, "beto", Limits())
    pdf = make_pdf(2)
    first = await submit(app, client, ana.id, pdf)
    second = await submit(app, client, beto.id, pdf)
    assert first["job_id"] != second["job_id"]


async def test_an_identical_request_reuses_the_job_without_counting_twice(
    app, client, settings, fake_core
):
    db = database(settings)
    key, _ = keys.create(db, "ana", Limits(pages_per_day=3))
    pdf = make_pdf(3)
    first = await submit(app, client, key.id, pdf)
    again = await submit(app, client, key.id, pdf)
    assert again["job_id"] == first["job_id"] and again["already_submitted"] is True
    assert fake_core.uploads == 1
    assert ledger.usage(db, key.id, datetime.now(UTC)).pages_today == 3


async def test_quota_exceeded_explains_when_it_renews(app, client, settings):
    key, _ = keys.create(database(settings), "ana", Limits(pages_per_day=2))
    with pytest.raises(ToolError, match="cuota diaria.*Se renueva"):
        await submit(app, client, key.id, make_pdf(3))


async def test_a_failed_job_gives_its_pages_back_and_can_be_retried(
    app, client, settings, fake_core
):
    db = database(settings)
    key, _ = keys.create(db, "ana", Limits(pages_per_day=3))
    pdf = make_pdf(3)
    fake_core.status = "failed"
    job = await submit(app, client, key.id, pdf)
    with as_user(key.id):
        status = await call(app, "ocr_status", job_id=job["job_id"])
    assert status["status"] == "failed" and status["error"]
    assert ledger.usage(db, key.id, datetime.now(UTC)).pages_today == 0
    fake_core.status = "done"
    retried = await submit(app, client, key.id, pdf)
    assert retried["job_id"] != job["job_id"] and retried["already_submitted"] is False


async def test_jobs_in_progress_limit(app, client, settings, fake_core):
    key, _ = keys.create(database(settings), "ana", Limits(max_active_jobs=1))
    fake_core.status = "processing"
    await submit(app, client, key.id, make_pdf(1))
    with pytest.raises(ToolError, match="trabajos en curso"):
        await submit(app, client, key.id, make_pdf(2))


async def test_public_keys_share_a_global_daily_cap(app, client, settings):
    db = database(settings)
    quotas.public.save(db, quotas.PublicMode(enabled=True, global_pages_per_day=2))
    key, _ = keys.create(db, "pública", Limits(pages_per_day=10), public=True)
    with pytest.raises(ToolError, match="tope diario"):
        await submit(app, client, key.id, make_pdf(3))


async def test_urls_are_accepted_only_from_configured_prefixes(settings, fake_core):
    pdf = make_pdf(2)

    def remote(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=pdf)

    app = build(
        replace(settings, allowed_url_prefixes=("https://docs.ejemplo.org/publicos",)),
        core_transport=httpx.ASGITransport(app=fake_core.app),
        fetch_transport=httpx.MockTransport(remote),
    )
    key, _ = keys.create(database(settings), "ana", Limits())
    with as_user(key.id):
        with pytest.raises(ToolError, match="prefijos permitidos"):
            await call(app, "ocr_submit", url="https://interno.ejemplo.org/secreto.pdf")
        with pytest.raises(ToolError, match="prefijos permitidos"):
            await call(app, "ocr_submit", url="https://docs.ejemplo.org/publicos-falsos/a.pdf")
        job = await call(app, "ocr_submit", url="https://docs.ejemplo.org/publicos/a.pdf")
    assert job["pages"] == 2


async def test_markdown_requires_core_support(app, client, settings, fake_core):
    key, _ = keys.create(database(settings), "ana", Limits())
    fake_core.markdown = False
    with pytest.raises(ToolError, match="no genera Markdown"):
        await submit(app, client, key.id, make_pdf(1), artifacts=["md"])
    job = await submit(app, client, key.id, make_pdf(1), artifacts=["text"])
    assert job["artifacts"] == ["text"]


async def test_a_pdf_that_already_had_text_is_not_offered_again(app, client, settings, fake_core):
    key, _ = keys.create(database(settings), "ana", Limits())
    fake_core.reused_source = True
    job = await submit(app, client, key.id, make_pdf(1), artifacts=["pdf"])
    with as_user(key.id):
        links = await call(app, "ocr_artifact_links", job_id=job["job_id"])
    assert links["links"] == []
    assert "ya tenía texto" in links["unavailable"][0]["reason"]


async def test_a_deleted_key_can_no_longer_use_the_tools(app, settings):
    db = database(settings)
    key, _ = keys.create(db, "ana", Limits())
    keys.delete(db, key.id)
    with as_user(key.id), pytest.raises(ToolError, match="ya no es válida"):
        await call(app, "ocr_upload_link")


async def test_submit_needs_exactly_one_source(app, settings):
    key, _ = keys.create(database(settings), "ana", Limits())
    with as_user(key.id):
        with pytest.raises(ToolError, match="uno de los dos"):
            await call(app, "ocr_submit")
        with pytest.raises(ToolError, match="uno de los dos"):
            await call(app, "ocr_submit", upload_id="x", url="https://a.org/b.pdf")


async def test_usage_keeps_counts_but_never_titles_or_file_names(app, client, settings):
    db = database(settings)
    key, _ = keys.create(db, "ana", Limits())
    await submit(app, client, key.id, make_pdf(1), title="Expediente reservado de Fulano")
    connection = db.connect()
    try:
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(jobs)")}
        dump = "\n".join(connection.iterdump())
    finally:
        connection.close()
    assert columns == {
        "job_id", "key_id", "request_hash", "is_public", "pages", "bytes",
        "artifacts", "status", "refunded", "created_at", "finished_at",
    }  # fmt: skip
    assert "Fulano" not in dump and "documento.pdf" not in dump
