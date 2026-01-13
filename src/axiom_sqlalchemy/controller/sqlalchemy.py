# ruff: noqa: W505
# mypy: disable-error-code="valid-type,type-arg"
"""Базовый контроллер sqlalchemy."""

from collections.abc import Callable
from typing import Any

from axiom_core.controller import BaseController
from axiom_sqlalchemy.database.postgres.base import Base


class SQLAlchemyController[ModelType: Base](BaseController):
    """Базовый класс для контроллера данных sqlalchemy."""

    async def processing_transaction(
        self,
        function: Callable,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Метод для обработки транзакции."""
        try:
            result = await function(self, *args, **kwargs)
            await self.repository.session.commit()
            if result is not None and function.__name__.lower() in ["update", "create"]:
                if isinstance(result, list | tuple | set):
                    for res in result:
                        await self.repository.session.refresh(res)
                else:
                    await self.repository.session.refresh(result)
        except Exception as exception:
            await self.repository.session.rollback()
            raise exception

        return result
