"""Corte del Markdown por páginas."""

from __future__ import annotations

import pytest

from ocr_mcp.modules.jobs.markdown import parse_pages, select
from tests.fakes.core import markdown


def test_ranges_are_ordered_unique_and_clipped():
    assert parse_pages("1-3,2,7", 5) == [1, 2, 3]
    assert parse_pages(" 4 , 1 ", 5) == [4, 1]
    for spec in ("", "0", "3-1", "a", "1-x"):
        with pytest.raises(ValueError):
            parse_pages(spec, 5)


def test_the_title_goes_with_the_first_page_and_low_confidence_is_flagged():
    piece = select(markdown(4, "Acta"), "2-3", 10_000)
    assert piece.pages == [2, 3] and piece.page_count == 4
    assert piece.low_confidence_pages == [2]
    assert "# Acta" not in piece.markdown and "schema:" not in piece.markdown
    first = select(markdown(4, "Acta"), "1", 10_000).markdown
    assert first.startswith("---") and "# Acta" in first


def test_long_text_is_cut_at_page_boundaries():
    piece = select(markdown(50, None), "1-50", 300)
    assert piece.truncated and 1 <= len(piece.pages) < 50
    single = select("x" * 1000, "1", 100)
    assert single.truncated and len(single.markdown) == 100
