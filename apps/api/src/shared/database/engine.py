from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from apps.api.src.shared.settings.config import settings

engine: AsyncEngine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
)
