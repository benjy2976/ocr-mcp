"""Enlaces de subida y descarga (reglas de `src/ocr_mcp/modules/files/context.md`)."""

from __future__ import annotations

import time

import pytest

from ocr_mcp.modules.access import keys
from ocr_mcp.modules.files import Downloads, UploadError, Uploads, allowed
from ocr_mcp.modules.quotas import Limits
from ocr_mcp.shared.db import Database
from tests.conftest import PUBLIC_URL, make_pdf

pytestmark = pytest.mark.anyio


@pytest.fixture
def db(app, settings) -> Database:
    return Database(settings.data_dir / "ocr-mcp.sqlite3")


@pytest.fixture
def uploads(db, settings) -> Uploads:
    return Uploads(db, settings.data_dir, PUBLIC_URL, ttl=60)


@pytest.fixture
def owner(db) -> str:
    return keys.create(db, "ana", Limits())[0].id


async def test_put_stores_a_valid_pdf_once(client, uploads, owner):
    upload, url = uploads.create(owner)
    response = await client.put(url, content=make_pdf(2))
    assert response.status_code == 200
    assert response.json()["pages"] == 2 and response.json()["upload_id"] == upload.id
    assert uploads.path(upload.id).exists()
    again = await client.put(url, content=make_pdf(1))
    assert again.status_code == 404


async def test_a_file_that_is_not_a_pdf_is_rejected_and_the_link_survives(client, uploads, owner):
    _, url = uploads.create(owner)
    response = await client.put(url, content=b"esto no es un pdf")
    assert response.status_code == 400 and "no es un PDF" in response.json()["error"]
    assert (await client.put(url, content=make_pdf(1))).status_code == 200


async def test_a_pdf_over_the_core_limit_is_rejected_before_storing(
    client, uploads, owner, fake_core
):
    fake_core.max_upload_bytes = 100
    upload, url = uploads.create(owner)
    response = await client.put(url, content=make_pdf(3))
    assert response.status_code == 413
    assert not uploads.path(upload.id).exists()


async def test_a_person_can_upload_with_the_browser_form(client, uploads, owner):
    upload, url = uploads.create(owner)
    form = await client.get(url)
    assert form.status_code == 200 and 'type="file"' in form.text
    sent = await client.post(url, files={"file": ("doc.pdf", make_pdf(2), "application/pdf")})
    assert sent.status_code == 200 and upload.id in sent.text
    assert (await client.get(url)).status_code == 404


async def test_an_expired_link_does_not_accept_files(client, db, settings, owner):
    expired = Uploads(db, settings.data_dir, PUBLIC_URL, ttl=-1)
    _, url = expired.create(owner)
    assert (await client.put(url, content=make_pdf(1))).status_code == 404


async def test_only_the_owner_can_take_an_upload(client, uploads, owner, db):
    upload, url = uploads.create(owner)
    await client.put(url, content=make_pdf(1))
    other = keys.create(db, "beto", Limits())[0].id
    with pytest.raises(UploadError, match="no existe"):
        uploads.take(upload.id, other)
    assert uploads.take(upload.id, owner).pages == 1


async def test_download_links_expire_and_unknown_ones_fail(client, db, owner):
    downloads = Downloads(db, PUBLIC_URL, ttl=-1)
    url, expires_at = downloads.create(owner, "job-1", "md")
    assert expires_at < time.time()
    assert (await client.get(url)).status_code == 404
    assert (await client.get(f"{PUBLIC_URL}/d/inventado")).status_code == 404


def test_url_prefixes_are_matched_by_path_segment():
    prefixes = ("https://docs.ejemplo.org/publicos",)
    assert allowed("https://docs.ejemplo.org/publicos/a.pdf", prefixes)
    assert not allowed("https://docs.ejemplo.org/publicos-otros/a.pdf", prefixes)
    assert not allowed("https://usuario:clave@docs.ejemplo.org/publicos/a.pdf", prefixes)
    assert not allowed("file:///etc/passwd", prefixes)
    assert not allowed("https://docs.ejemplo.org/publicos/a.pdf", ())
