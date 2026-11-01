"""Shared helpers for the ORM models."""
from datetime import datetime, timezone

from sqlalchemy.dialects.mysql import LONGTEXT

from ..extensions import db

TABLE_OPTIONS = {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}

# TEXT holds 64 KB on MySQL; chapters can be much longer.
LongText = db.Text().with_variant(LONGTEXT(), "mysql")


def table_args(*constraints):
    """Table constraints plus the utf8mb4 options every table needs."""
    return (*constraints, TABLE_OPTIONS)


def utcnow() -> datetime:
    """Naive UTC timestamp (MySQL DATETIME columns carry no timezone)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
