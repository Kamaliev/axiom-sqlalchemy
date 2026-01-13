# ruff: noqa: D100, D101, D102
# mypy: disable-error-code="type-arg"


from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_scoped_session,
    async_sessionmaker,
)

from axiom_sqlalchemy.database.postgres.session import (
    RoutingSession,
    get_session_context,
)


def get_async_sessionmaker(engines: dict) -> async_sessionmaker:
    """
    :param engines: async engines
    :return: async sessionmaker
    """
    return async_sessionmaker(
        class_=AsyncSession,
        sync_session_class=RoutingSession,
        expire_on_commit=False,
        engines=engines,
    )


def get_db_session(factory: async_sessionmaker) -> AsyncSession | async_scoped_session:
    """
    :param factory: async session factory
    :return: async session
    """
    return async_scoped_session(
        session_factory=factory,
        scopefunc=get_session_context,
    )
