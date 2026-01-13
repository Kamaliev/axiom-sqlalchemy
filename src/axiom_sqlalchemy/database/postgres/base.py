"""Базовая модель sqlalchemy."""

import re

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, declared_attr

from axiom_sqlalchemy.database.postgres.meta import meta


class Base(DeclarativeBase):
    """База для всех моделей sqlalchemy."""

    metadata: MetaData = meta  # type: ignore[misc]
    __abstract__: bool = True

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Дефолтное значение для __tablename__."""
        return to_snake(cls.__name__)


def to_snake(camel: str) -> str:
    """Convert a PascalCase, camelCase, or kebab-case string to snake_case.

    Args:
        camel: The string to convert.

    Returns:
        The converted string in snake_case.
    """
    # Handle the sequence of uppercase letters followed by a lowercase letter
    snake = re.sub(
        r"([A-Z]+)([A-Z][a-z])",
        lambda m: f"{m.group(1)}_{m.group(2)}",
        camel,
    )
    # Insert an underscore between a lowercase letter and an uppercase letter
    snake = re.sub(r"([a-z])([A-Z])", lambda m: f"{m.group(1)}_{m.group(2)}", snake)
    # Insert an underscore between a digit and an uppercase letter
    snake = re.sub(r"([0-9])([A-Z])", lambda m: f"{m.group(1)}_{m.group(2)}", snake)
    # Insert an underscore between a lowercase letter and a digit
    snake = re.sub(r"([a-z])([0-9])", lambda m: f"{m.group(1)}_{m.group(2)}", snake)
    # Replace hyphens with underscores to handle kebab-case
    snake = snake.replace("-", "_")
    return snake.lower()
