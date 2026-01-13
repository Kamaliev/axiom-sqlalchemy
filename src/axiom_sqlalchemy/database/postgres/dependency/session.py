# ruff: noqa: D105

"""Зависимости для базы данных postgres."""

from collections.abc import AsyncGenerator
from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_scoped_session


class PostgresSession:
    """FastAPI Depends для получения сессии Postgres(SQLAlchemy)."""

    def __init__(self, db_session: AsyncSession | async_scoped_session[AsyncSession]):
        self.db_session = db_session

    async def __call__(
        self,
    ) -> AsyncGenerator[AsyncSession | async_scoped_session[AsyncSession]]:
        """Работа с сессией в контексте request-a."""
        try:
            yield self.db_session
            await self.db_session.commit()
        except Exception:
            await self.db_session.rollback()
            raise
        finally:
            await self.db_session.close()

    async def __aenter__(self) -> AsyncSession | async_scoped_session[AsyncSession]:
        return self.db_session

    async def __aexit__(
        self,
        type_: type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if type_ is None:  # ошибок не было
            await self.db_session.commit()
        else:
            await self.db_session.rollback()
        await self.db_session.close()
