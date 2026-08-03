"""A UTC datetime column type that stores and compares consistently.

Motivation: SQLAlchemy's SQLite datetime binds query parameters with a space
separator ("2026-08-03 15:58:57") but stores values via ``datetime.isoformat()``
with a "T" separator ("2026-08-03T15:58:57"). String comparison of the two then
breaks range queries like ``expires_at <= now`` — the worker never sees expired
grants. This type normalises both directions to naive UTC with a space
separator, so range comparisons are correct on SQLite and unchanged on
PostgreSQL (which uses native timestamp storage).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.types import TypeDecorator


def to_naive_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


class UTCDateTime(TypeDecorator):
    """Naive-UTC datetime, stored space-separated on SQLite for stable ordering."""

    impl = DateTime
    cache_ok = True

    def load_dialect_impl(self, dialect):
        # On SQLite, store as TEXT with a space separator (matching how SQLite
        # binds datetime parameters) so lexical ordering equals chronological
        # ordering. On other backends, use the native DateTime.
        if dialect.name == "sqlite":
            return dialect.type_descriptor(String(32))
        return dialect.type_descriptor(DateTime())

    def process_bind_param(self, value, dialect):
        value = to_naive_utc(value)
        if value is None:
            return None
        if dialect.name == "sqlite":
            return value.strftime("%Y-%m-%d %H:%M:%S.%f")
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "sqlite" and isinstance(value, str):
            # Accept both space and T separators when reading legacy rows.
            normalised = value.replace("T", " ")
            try:
                return datetime.strptime(normalised, "%Y-%m-%d %H:%M:%S.%f")
            except ValueError:
                return datetime.strptime(normalised, "%Y-%m-%d %H:%M:%S")
        return value
