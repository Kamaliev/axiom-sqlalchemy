# ruff: noqa: D100, D101, D102
# mypy: disable-error-code="type-arg"

from contextvars import ContextVar, Token
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import Delete, Insert, Update

session_context: ContextVar[str] = ContextVar[str]("session_context")


def get_session_context() -> str:
    """Получение контекста сессии."""
    return session_context.get()


def set_session_context(session_id: str) -> Token:
    """Установление контекста сессии."""
    return session_context.set(session_id)


def reset_session_context(context: Token) -> None:
    """Переустановка контекста сессии."""
    session_context.reset(context)


class RoutingSession(Session):
    def __init__(
        self,
        engines: dict[str, AsyncEngine],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.engines = engines

    def get_bind(self, mapper=None, clause=None, **kw):  # type: ignore[no-untyped-def]
        if self._flushing or isinstance(clause, Update | Delete | Insert):
            return self.engines["writer"].sync_engine
        return self.engines["reader"].sync_engine
