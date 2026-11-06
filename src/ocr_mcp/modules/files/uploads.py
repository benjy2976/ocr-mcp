"""Enlaces de subida de un solo uso y el PDF que reciben (decisión 0003).

Ciclo: `waiting` (enlace entregado) → `ready` (PDF recibido y validado) →
`used` (enviado al core; el archivo se borra). Un enlace vence a los
`link_ttl` segundos y pertenece a la clave que lo pidió. El archivo vive en
`<OCR_MCP_DATA_DIR>/uploads/<id>.pdf` solo mientras hace falta.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from ocr_mcp.shared.db import Database
from ocr_mcp.shared.security import new_id, new_secret, secret_hash

PDF_HEADER_WINDOW = 1024


class UploadError(Exception):
    """El enlace o el archivo no sirven. El mensaje es apto para el usuario."""


@dataclass(frozen=True)
class Upload:
    id: str
    key_id: str
    state: str
    bytes: int | None
    pages: int | None
    sha256: str | None
    expires_at: float


class Uploads:
    def __init__(self, db: Database, data_dir: Path, public_url: str, ttl: int):
        self.db = db
        self.folder = data_dir / "uploads"
        self.public_url = public_url
        self.ttl = ttl

    def path(self, upload_id: str) -> Path:
        return self.folder / f"{upload_id}.pdf"

    def create(self, key_id: str) -> tuple[Upload, str]:
        """Nuevo enlace de subida; devuelve el registro y la URL con su secreto."""
        self.cleanup()
        secret = new_secret()
        now = time.time()
        upload = Upload(new_id(), key_id, "waiting", None, None, None, now + self.ttl)
        with self.db.transaction() as connection:
            connection.execute(
                "INSERT INTO uploads (id, token_hash, key_id, state, expires_at, created_at) "
                "VALUES (?, ?, ?, 'waiting', ?, ?)",
                (upload.id, secret_hash(secret), key_id, upload.expires_at, now),
            )
        return upload, f"{self.public_url}/u/{secret}"

    def waiting(self, secret: str) -> Upload | None:
        row = self._row(
            "token_hash = ? AND state = 'waiting' AND expires_at >= ?",
            secret_hash(secret),
            time.time(),
        )
        return _upload(row) if row else None

    async def receive(
        self, secret: str, chunks: AsyncIterator[bytes], max_bytes: int | None
    ) -> Upload:
        """Guarda el PDF del enlace, lo valida y marca la subida como lista."""
        upload = self.waiting(secret)
        if upload is None:
            raise UploadError("El enlace de subida no existe, ya se usó o venció.")
        self.folder.mkdir(parents=True, exist_ok=True)
        target = self.path(upload.id)
        partial = target.with_suffix(".part")
        digest, size = hashlib.sha256(), 0
        try:
            with partial.open("wb") as handle:
                async for chunk in chunks:
                    size += len(chunk)
                    if max_bytes is not None and size > max_bytes:
                        raise UploadError(f"El PDF supera el tamaño máximo de {max_bytes} bytes.")
                    digest.update(chunk)
                    handle.write(chunk)
            if size == 0:
                raise UploadError("No se recibió ningún archivo.")
            pages = count_pages(partial)
            partial.replace(target)
        except BaseException:
            partial.unlink(missing_ok=True)
            raise
        with self.db.transaction() as connection:
            changed = connection.execute(
                "UPDATE uploads SET state = 'ready', bytes = ?, pages = ?, sha256 = ? "
                "WHERE id = ? AND state = 'waiting'",
                (size, pages, digest.hexdigest(), upload.id),
            ).rowcount
        if changed != 1:
            target.unlink(missing_ok=True)
            raise UploadError("El enlace de subida ya se usó.")
        return Upload(
            upload.id, upload.key_id, "ready", size, pages, digest.hexdigest(), upload.expires_at
        )

    def take(self, upload_id: str, key_id: str) -> Upload:
        """Subida lista de esta clave, para enviarla al core. Una ajena no existe."""
        row = self._row("id = ? AND key_id = ? AND expires_at >= ?", upload_id, key_id, time.time())
        if row is None:
            raise UploadError(
                "La subida no existe o venció. Pide otro enlace con `ocr_upload_link`."
            )
        if row["state"] == "waiting":
            raise UploadError("Todavía no se subió el PDF a ese enlace.")
        if row["state"] == "used":
            raise UploadError(
                "Esa subida ya se envió. Pide otro enlace para enviar otro documento."
            )
        return _upload(row)

    def finish(self, upload_id: str) -> None:
        with self.db.transaction() as connection:
            connection.execute("UPDATE uploads SET state = 'used' WHERE id = ?", (upload_id,))
        self.path(upload_id).unlink(missing_ok=True)

    def cleanup(self) -> None:
        """Borra subidas vencidas y archivos sin registro."""
        now = time.time()
        with self.db.transaction() as connection:
            connection.execute("DELETE FROM uploads WHERE expires_at < ?", (now - 86400,))
            alive = {
                row["id"]
                for row in connection.execute(
                    "SELECT id FROM uploads WHERE state = 'ready' AND expires_at >= ?", (now,)
                )
            }
        if self.folder.exists():
            for item in self.folder.iterdir():
                if item.stem not in alive:
                    item.unlink(missing_ok=True)

    def _row(self, where: str, *params: object):
        connection = self.db.connect()
        try:
            return connection.execute(f"SELECT * FROM uploads WHERE {where}", params).fetchone()
        finally:
            connection.close()


def count_pages(path: Path) -> int:
    """Valida que sea un PDF legible y sin cifrar, y devuelve sus páginas."""
    with path.open("rb") as handle:
        if b"%PDF-" not in handle.read(PDF_HEADER_WINDOW):
            raise UploadError("El archivo no es un PDF.")
    try:
        reader = PdfReader(path)
        if reader.is_encrypted:
            raise UploadError("El PDF está cifrado; el OCR necesita uno sin contraseña.")
        pages = len(reader.pages)
    except (PdfReadError, ValueError, KeyError, OSError) as error:
        raise UploadError("El PDF está dañado o no se puede leer.") from error
    if pages < 1:
        raise UploadError("El PDF no tiene páginas.")
    return pages


def _upload(row) -> Upload:
    return Upload(
        row["id"],
        row["key_id"],
        row["state"],
        row["bytes"],
        row["pages"],
        row["sha256"],
        row["expires_at"],
    )
