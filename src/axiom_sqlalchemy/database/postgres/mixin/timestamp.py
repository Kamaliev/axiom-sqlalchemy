# ruff: noqa: D100, D101, D102
# mypy: disable-error-code="no-untyped-def,arg-type"
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    @declared_attr
    def created_at(cls) -> Mapped[datetime]:
        return mapped_column(
            DateTime(timezone=True),
            default=func.now(),
            server_default=func.now(),
            nullable=False,
        )

    @declared_attr
    def updated_at(cls) -> Mapped[datetime]:
        return mapped_column(
            DateTime(timezone=True),
            default=func.now(),
            onupdate=func.now(),
            server_default=func.now(),
            server_onupdate=func.now(),
            nullable=False,
        )
