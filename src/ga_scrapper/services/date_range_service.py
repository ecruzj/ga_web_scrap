from __future__ import annotations
from datetime import date, timedelta
from typing import Iterator


def iter_dates(start: date, end: date) -> Iterator[date]:
    """
    Generates every day from start to end (inclusive).
    """
    if end < start:
        raise ValueError("end date must be >= start date")

    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)