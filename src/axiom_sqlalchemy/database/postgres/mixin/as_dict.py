# ruff: noqa: D100, D101, D102
# mypy: disable-error-code="attr-defined"
from typing import Any

from sqlalchemy import inspect


class AsDictMixin:
    def as_dict(
        self,
        exclude_none: bool = False,
        exclude_columns: list[str] | None = None,
    ) -> dict[str, Any]:
        data = {}
        for c in inspect(self).mapper.column_attrs:  # type: ignore[union-attr]
            attr = getattr(self, c.key)
            if exclude_columns:
                if c.key in exclude_columns:
                    continue
            if exclude_none:
                if attr is not None:
                    data[c.key] = attr
            else:
                data[c.key] = attr
        return data
