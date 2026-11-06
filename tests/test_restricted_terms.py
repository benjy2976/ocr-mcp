"""Ningún archivo versionado contiene términos prohibidos.

El repo es libre y no pertenece a ninguna institución (docs/convenciones.md).
La lista de términos vive fuera del repo, en el archivo que indica
`OCR_MCP_RESTRICTED_TERMS_FILE` (un término por línea; `#` comenta), para que
el repo no los nombre ni siquiera en esta prueba. Sin la variable, la prueba se
omite.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.test_documentation_independence import REPOSITORY, _text, _versioned_files

TERMS_VARIABLE = "OCR_MCP_RESTRICTED_TERMS_FILE"


def _restricted_terms() -> list[str]:
    location = os.environ.get(TERMS_VARIABLE, "").strip()
    if not location:
        pytest.skip(f"{TERMS_VARIABLE} no está definida")
    path = Path(location).expanduser().resolve()
    if path.is_relative_to(REPOSITORY):
        pytest.fail(f"{TERMS_VARIABLE} debe apuntar fuera del repo")
    terms = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        term = raw.strip()
        if term and not term.startswith("#"):
            terms.append(term.casefold())
    if not terms:
        pytest.fail(f"{path} no contiene términos")
    return terms


def test_versioned_files_contain_no_restricted_terms():
    terms = _restricted_terms()
    found = []
    for relative in _versioned_files():
        text = _text(relative)
        if text is None:
            continue
        for number, line in enumerate(text.casefold().splitlines(), start=1):
            for index, term in enumerate(terms, start=1):
                if term in line:
                    # Se informa el número del término, no el término: el reporte
                    # tampoco debe repetirlo.
                    found.append(f"{relative}:{number}: término {index} de la lista")
    assert not found, "Términos prohibidos en archivos versionados:\n" + "\n".join(found)
