from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apps.shared.src.infra.db.engine import close_engine, get_engine


_session_factories: dict[str, async_sessionmaker[AsyncSession]] = {}


def get_session_factory(database_url: str | None = None) -> async_sessionmaker[AsyncSession]:
    engine = get_engine(database_url)
    key = str(engine.url)
    factory = _session_factories.get(key)
    if factory is None:
        factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
        _session_factories[key] = factory
    return factory


@asynccontextmanager
async def get_db_session(database_url: str | None = None) -> AsyncIterator[AsyncSession]:
    session = get_session_factory(database_url)()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def db_session_dependency() -> AsyncIterator[AsyncSession]:
    async with get_db_session() as session:
        yield session


async def close_db_engine(database_url: str | None = None) -> None:
    await close_engine(database_url)
