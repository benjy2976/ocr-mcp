"""Los enlaces y las rutas que cita la documentación existen.

Falla si un enlace Markdown relativo, una ruta `docs/...` citada desde
cualquier archivo versionado, el nombre de un documento entre comillas
invertidas o una ruta relativa entre comillas invertidas (`../x.md`) deja de
resolver.
"""

from __future__ import annotations

import re
from pathlib import Path

from tests.test_documentation_independence import REPOSITORY, _text, _versioned_files

SELF = Path(__file__).resolve().relative_to(REPOSITORY).as_posix()
# Copias literales del estándar de memoria viva: sus ejemplos son genéricos y
# no son rutas de este repo. Se mantienen iguales a las de la skill.
EXCLUDED_PREFIXES = ("docs/memoria-viva/",)
# Fuentes condicionales: el protocolo las cita antes de que nazcan, al cruzar su
# umbral (docs/guia_IA.md, "Fuentes condicionales todavía inexistentes").
CONDITIONAL_DOCS = {"docs/api.md", "docs/cli.md", "docs/modelo-datos.md", "docs/frontend.md"}

MARKDOWN_LINK = re.compile(r"\]\(([^)\s]+)\)")
EXTERNAL_TARGET = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|#|/)")
DOCS_PATH = re.compile(r"(?<![\w/.-])docs/[A-Za-z0-9_./-]*[A-Za-z0-9_/-]")
# Solo nombres con forma de documento: `INICIATIVAS.md` o `0002-modo-local-stdio.md`,
# no `plan.md`.
BARE_DOCUMENT = re.compile(r"`([A-Z][A-Z0-9_]*\.md|[a-z0-9]+(?:-[a-z0-9]+)+\.md)`")
BARE_DOCUMENT_SCOPE = ("docs/", "AGENTS.md", "README.md")
RELATIVE_PATH = re.compile(r"`((?:\.\.?/)+[^`\s<>*]+)`")


def _checked_files() -> list[str]:
    return [
        relative
        for relative in _versioned_files()
        if relative != SELF and not relative.startswith(EXCLUDED_PREFIXES)
    ]


def _resolver():
    """Existe si es un archivo versionado o una carpeta que contiene alguno."""
    known = set(_versioned_files())
    for name in list(known):
        known.update(parent.as_posix() for parent in Path(name).parents)

    def exists(relative: str) -> bool:
        return relative.rstrip("/") in known

    return exists


def _normalized(base: str, target: str) -> str | None:
    parts: list[str] = []
    for part in (Path(base).parent / target).as_posix().split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if not parts:
                return None
            parts.pop()
        else:
            parts.append(part)
    return "/".join(parts)


def test_relative_markdown_links_resolve():
    exists = _resolver()
    broken = []
    for relative in _checked_files():
        if not relative.endswith(".md"):
            continue
        text = _text(relative)
        if text is None:
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            for match in MARKDOWN_LINK.finditer(line):
                target = match.group(1).split("#", 1)[0]
                if not target or EXTERNAL_TARGET.match(target):
                    continue
                resolved = _normalized(relative, target)
                if resolved is None or not exists(resolved):
                    broken.append(f"{relative}:{number}: {match.group(1)}")
    assert not broken, "Enlaces Markdown rotos:\n" + "\n".join(broken)


def test_cited_docs_paths_exist():
    exists = _resolver()
    missing = []
    for relative in _checked_files():
        text = _text(relative)
        if text is None:
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            for match in DOCS_PATH.finditer(line):
                if match.group(0) not in CONDITIONAL_DOCS and not exists(match.group(0)):
                    missing.append(f"{relative}:{number}: {match.group(0)}")
    assert not missing, "Rutas docs/ que no existen:\n" + "\n".join(missing)


def test_bare_document_names_exist():
    basenames = {Path(name).name for name in _versioned_files()}
    unknown = []
    for relative in _checked_files():
        if not (relative.startswith(BARE_DOCUMENT_SCOPE[0]) or relative in BARE_DOCUMENT_SCOPE[1:]):
            continue
        text = _text(relative)
        if text is None:
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            for match in BARE_DOCUMENT.finditer(line):
                if match.group(1) not in basenames:
                    unknown.append(f"{relative}:{number}: {match.group(1)}")
    assert not unknown, (
        "Nombres de documento que no corresponden a ningún archivo versionado "
        "(citarlos con su ruta completa):\n" + "\n".join(unknown)
    )


def test_relative_backticked_paths_resolve():
    exists = _resolver()
    broken = []
    for relative in _checked_files():
        if not relative.endswith(".md"):
            continue
        text = _text(relative)
        if text is None:
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            for match in RELATIVE_PATH.finditer(line):
                resolved = _normalized(relative, match.group(1))
                if resolved is None or not exists(resolved):
                    broken.append(f"{relative}:{number}: {match.group(1)}")
    assert not broken, "Rutas relativas entre comillas invertidas rotas:\n" + "\n".join(broken)
