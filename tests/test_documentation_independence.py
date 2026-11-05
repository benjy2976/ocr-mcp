"""La documentación versionada no depende de los planes de trabajo.

Los planes viven fuera de git (ver "Planes de trabajo y bitácoras" en
AGENTS.md). Estas pruebas fallan si un archivo versionado cita un plan
concreto, si algún plan quedó versionado o si `planes/` deja de estar ignorado.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest

REPOSITORY = Path(__file__).resolve().parents[1]
SELF = Path(__file__).resolve().relative_to(REPOSITORY).as_posix()
WALK_SKIPPED_DIRS = {".git", ".venv", "__pycache__", "planes", "node_modules", ".pytest_cache"}

PLAN_CITATIONS = (
    re.compile(r"\b[A-Z][A-Z0-9_]*_(?:PLAN|ROADMAP)\.md\b"),
    # Una carpeta de plan concreta; la política genérica `planes/<AAAA-MM>-<slug>/` sí se permite.
    re.compile(r"planes/\d{4}-\d{2}-"),
    re.compile(r"(?<![\w/])bitacoras/"),
)


def _git_tracked_files() -> list[str] | None:
    try:
        output = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=REPOSITORY,
            capture_output=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    tracked = [name for name in output.decode("utf-8").split("\0") if name]
    # Un repo recién creado, sin nada en el índice, se revisa recorriendo el árbol.
    return tracked or None


def _versioned_files() -> list[str]:
    tracked = _git_tracked_files()
    if tracked is not None:
        return tracked
    files = []
    for root, dirs, names in os.walk(REPOSITORY):
        dirs[:] = [name for name in dirs if name not in WALK_SKIPPED_DIRS]
        files.extend(
            (Path(root) / name).relative_to(REPOSITORY).as_posix() for name in names
        )
    return files


def _text(relative: str) -> str | None:
    path = REPOSITORY / relative
    if not path.is_file():
        return None
    data = path.read_bytes()
    if b"\0" in data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def test_versioned_files_do_not_cite_work_plans():
    citations = []
    for relative in _versioned_files():
        if relative == SELF:
            continue
        text = _text(relative)
        if text is None:
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            for pattern in PLAN_CITATIONS:
                match = pattern.search(line)
                if match:
                    citations.append(f"{relative}:{number}: {match.group(0)}")
    assert not citations, (
        "La documentación versionada no puede citar planes de trabajo. Cosechar ese "
        "contenido (decisión, documento vigente o iniciativa) y citar eso:\n"
        + "\n".join(citations)
    )


def test_no_work_plan_is_versioned():
    tracked = _git_tracked_files()
    if tracked is None:
        pytest.skip("git no está disponible o el índice está vacío")
    versioned_plans = [name for name in tracked if name.startswith("planes/")]
    assert not versioned_plans, f"Planes versionados: {versioned_plans}"


def test_plans_folder_is_git_ignored():
    lines = (REPOSITORY / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "/planes/" in lines
