"""Política de cuotas: límites por clave, uso del periodo y comprobación (decisión 0007).

Lógica pura, sin base de datos: quien llama aporta el uso actual. Los periodos
son días y meses UTC.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True)
class Limits:
    """Límites de una clave. `None` significa sin límite propio."""

    pages_per_day: int | None = None
    pages_per_month: int | None = None
    max_active_jobs: int | None = None

    @property
    def unlimited(self) -> bool:
        return (
            self.pages_per_day is None
            and self.pages_per_month is None
            and self.max_active_jobs is None
        )


@dataclass(frozen=True)
class Usage:
    pages_today: int
    pages_month: int
    active_jobs: int


class QuotaExceeded(Exception):
    """El pedido supera una cuota. El mensaje indica cuándo se renueva."""

    def __init__(self, message: str, renews_at: datetime | None):
        super().__init__(message)
        self.renews_at = renews_at


def day_start(now: datetime) -> datetime:
    return now.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)


def month_start(now: datetime) -> datetime:
    return day_start(now).replace(day=1)


def next_day(now: datetime) -> datetime:
    return day_start(now) + timedelta(days=1)


def next_month(now: datetime) -> datetime:
    start = month_start(now)
    return (
        start.replace(year=start.year + 1, month=1)
        if start.month == 12
        else start.replace(month=start.month + 1)
    )


def check(limits: Limits, usage: Usage, pages: int, now: datetime) -> None:
    """Lanza `QuotaExceeded` si enviar `pages` páginas más supera algún límite."""
    if limits.max_active_jobs is not None and usage.active_jobs >= limits.max_active_jobs:
        raise QuotaExceeded(
            f"Ya hay {usage.active_jobs} trabajos en curso, el máximo de esta clave. "
            "Espera a que alguno termine.",
            None,
        )
    if limits.pages_per_day is not None and usage.pages_today + pages > limits.pages_per_day:
        raise QuotaExceeded(
            f"El documento tiene {pages} páginas y quedan "
            f"{max(limits.pages_per_day - usage.pages_today, 0)} de la cuota diaria.",
            next_day(now),
        )
    if limits.pages_per_month is not None and usage.pages_month + pages > limits.pages_per_month:
        raise QuotaExceeded(
            f"El documento tiene {pages} páginas y quedan "
            f"{max(limits.pages_per_month - usage.pages_month, 0)} de la cuota mensual.",
            next_month(now),
        )


def check_global(public_pages_today: int, cap: int | None, pages: int, now: datetime) -> None:
    """Tope diario de la suma de todas las claves públicas."""
    if cap is not None and public_pages_today + pages > cap:
        raise QuotaExceeded(
            "El servicio público alcanzó su tope diario de páginas.",
            next_day(now),
        )
