from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from apps.shared.src.infra.db.config import resolve_database_url

_engines: dict[str, AsyncEngine] = {}


def get_engine(database_url: str | None = None) -> AsyncEngine:
    url = database_url or resolve_database_url()
    engine = _engines.get(url)
    if engine is None:
        engine = create_async_engine(url, pool_pre_ping=True)
        _engines[url] = engine
    return engine


async def close_engine(database_url: str | None = None) -> None:
    if database_url is not None:
        engine = _engines.pop(database_url, None)
        if engine is not None:
            await engine.dispose()
        return

    # close all cached engines
    urls = list(_engines.keys())
    for url in urls:
        engine = _engines.pop(url, None)
        if engine is not None:
            await engine.dispose()
