"""Lectura del Markdown del core por tramos de páginas.

El artefacto marca cada página con `<!-- ocr-page: N -->` y las de baja
confianza con `<!-- ocr-quality: low-confidence -->`. El texto anterior a la
primera marca (el título) acompaña a la primera página.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

PAGE_MARK = re.compile(r"^<!-- ocr-page: (\d+) -->$", re.MULTILINE)
LOW_CONFIDENCE = "<!-- ocr-quality: low-confidence -->"
MAX_RANGE_PAGES = 500


@dataclass(frozen=True)
class MarkdownSlice:
    page_count: int
    pages: list[int]
    low_confidence_pages: list[int]
    truncated: bool
    markdown: str


def split_pages(markdown: str) -> tuple[str, dict[int, str]]:
    """Encabezado y texto de cada página, por número."""
    marks = list(PAGE_MARK.finditer(markdown))
    if not marks:
        return "", {1: markdown}
    header = markdown[: marks[0].start()]
    pages = {}
    for index, mark in enumerate(marks):
        end = marks[index + 1].start() if index + 1 < len(marks) else len(markdown)
        pages[int(mark.group(1))] = markdown[mark.start() : end]
    return header, pages


def parse_pages(spec: str, page_count: int) -> list[int]:
    """`"1-5,8"` → `[1, 2, 3, 4, 5, 8]`, dentro del documento y sin repetir."""
    selected: list[int] = []
    for part in spec.replace(" ", "").split(","):
        if not part:
            continue
        start_text, _, end_text = part.partition("-")
        if not start_text.isdigit() or (end_text and not end_text.isdigit()):
            raise ValueError(f'Rango de páginas inválido: {part!r}. Usa, por ejemplo, "1-5,8".')
        start, end = int(start_text), int(end_text or start_text)
        if start < 1 or end < start:
            raise ValueError(f"Rango de páginas inválido: {part!r}.")
        if end - start + 1 > MAX_RANGE_PAGES:
            raise ValueError(f"Un rango no puede pasar de {MAX_RANGE_PAGES} páginas.")
        for page in range(start, min(end, page_count) + 1):
            if page not in selected:
                selected.append(page)
    if not selected:
        raise ValueError(f"Ninguna página del rango existe: el documento tiene {page_count}.")
    return selected


def select(markdown: str, spec: str, max_chars: int) -> MarkdownSlice:
    header, pages = split_pages(markdown)
    wanted = parse_pages(spec, max(pages) if pages else 0)
    parts, returned, low, size, truncated = [], [], [], 0, False
    for page in wanted:
        text = pages.get(page)
        if text is None:
            continue
        if page == min(pages) and header.strip():
            text = header + text
        if returned and size + len(text) > max_chars:
            truncated = True
            break
        parts.append(text)
        returned.append(page)
        size += len(text)
        if LOW_CONFIDENCE in text:
            low.append(page)
    body = "".join(parts)
    if size > max_chars:
        body, truncated = body[:max_chars], True
    return MarkdownSlice(
        page_count=len(pages),
        pages=returned,
        low_confidence_pages=low,
        truncated=truncated,
        markdown=body,
    )
