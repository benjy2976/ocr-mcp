"""Reglas de organización del código (`docs/convenciones.md`, "Organización del código")."""

from __future__ import annotations

import ast
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "src" / "ocr_mcp"
MAX_LINES = 300


def _imports(path: Path) -> list[str]:
    names = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
            names.extend(f"{node.module}.{alias.name}" for alias in node.names)
        elif isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
    return names


def _python_files(folder: Path) -> list[Path]:
    return sorted(folder.rglob("*.py"))


def test_shared_depends_on_no_module():
    offending = [
        f"{path.relative_to(SOURCE)}: {name}"
        for path in _python_files(SOURCE / "shared")
        for name in _imports(path)
        if name.startswith(("ocr_mcp.modules", "ocr_mcp.app"))
    ]
    assert not offending, offending


def _exported(package: Path) -> set[str]:
    """Nombres del `__all__` del `__init__.py` de un módulo: su interfaz pública."""
    tree = ast.parse((package / "__init__.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets
        ):
            return {element.value for element in node.value.elts}
    return set()


def test_modules_use_each_other_only_through_their_public_interface():
    modules = SOURCE / "modules"
    offending = []
    for path in _python_files(modules):
        own = path.relative_to(modules).parts[0]
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and node.module:
                targets = [(node.module, alias.name) for alias in node.names]
            elif isinstance(node, ast.Import):
                targets = [(alias.name, None) for alias in node.names]
            else:
                continue
            for module, name in targets:
                parts = module.split(".")
                if parts[:2] != ["ocr_mcp", "modules"] or len(parts) < 3 or parts[2] == own:
                    continue
                # Solo `from ocr_mcp.modules.<otro> import <nombre exportado>`.
                if len(parts) > 3 or name not in _exported(modules / parts[2]):
                    offending.append(f"{path.relative_to(SOURCE)}: {module} {name or ''}".strip())
    assert not offending, offending


def test_no_source_file_grows_past_the_limit():
    long_files = [
        f"{path.relative_to(SOURCE)}: {lines}"
        for path in _python_files(SOURCE)
        if (lines := len(path.read_text(encoding="utf-8").splitlines())) > MAX_LINES
    ]
    assert not long_files, long_files


def test_every_module_has_its_context():
    missing = [
        folder.name
        for folder in (SOURCE / "modules").iterdir()
        if folder.is_dir() and folder.name != "__pycache__" and not (folder / "context.md").exists()
    ]
    assert not missing, missing
