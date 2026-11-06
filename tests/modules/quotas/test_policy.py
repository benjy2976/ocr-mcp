"""Política de cuotas (reglas de `src/ocr_mcp/modules/quotas/context.md`)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ocr_mcp.modules.quotas import (
    Limits,
    PublicMode,
    QuotaExceeded,
    Usage,
    check,
    check_global,
    public,
)
from ocr_mcp.modules.quotas.policy import next_month
from ocr_mcp.shared.db import Database

NOW = datetime(2026, 12, 31, 23, 30, tzinfo=UTC)


def test_without_limits_everything_passes():
    check(Limits(), Usage(10_000, 10_000, 50), 500, NOW)


def test_daily_monthly_and_active_limits():
    with pytest.raises(QuotaExceeded) as daily:
        check(Limits(pages_per_day=10), Usage(8, 8, 0), 3, NOW)
    assert daily.value.renews_at == datetime(2027, 1, 1, tzinfo=UTC)
    with pytest.raises(QuotaExceeded, match="mensual"):
        check(Limits(pages_per_month=10), Usage(0, 9, 0), 2, NOW)
    with pytest.raises(QuotaExceeded, match="en curso"):
        check(Limits(max_active_jobs=1), Usage(0, 0, 1), 1, NOW)
    check(Limits(pages_per_day=10), Usage(7, 7, 0), 3, NOW)


def test_the_month_after_december_is_january():
    assert next_month(NOW) == datetime(2027, 1, 1, tzinfo=UTC)


def test_the_global_public_cap():
    check_global(90, None, 50, NOW)
    with pytest.raises(QuotaExceeded, match="tope diario"):
        check_global(90, 100, 11, NOW)


def test_public_mode_is_off_by_default_and_needs_a_page_limit(tmp_path):
    db = Database(tmp_path / "base.sqlite3")
    db.migrate()
    assert public.load(db).enabled is False
    with pytest.raises(ValueError):
        public.save(db, PublicMode(enabled=True, limits=Limits(max_active_jobs=1)))
    public.save(db, PublicMode(enabled=True, global_pages_per_day=None))
    assert public.load(db).enabled and public.load(db).global_pages_per_day is None
