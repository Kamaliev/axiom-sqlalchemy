# mypy: disable-error-code="attr-defined"

from .as_dict import AsDictMixin
from .timestamp import TimestampMixin

__all__ = ["TimestampMixin", "AsDictMixin"]
