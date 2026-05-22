import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api_service.src.api import (
    router as job_management_router,
)
from apps.api_service.src.api.exception_handlers import register_exception_handlers
from apps.api_service.src.infra.job_queue_celery import (
    InProcessJobQueue,
)
from apps.api_service.src.infra.repositories.in_memory_prediction_job_repository import (
    InMemoryPredictionJobRepository,
)
from apps.api_service.src.infra.repositories.sqlalchemy_prediction_job_repository import (
    SQLAlchemyPredictionJobRepository,
)
from apps.api_service.src.infra.smiles_validator_default import (
    DomainSmilesValidator,
)
from apps.api_service.src.shared.database.session import db_session_dependency
from apps.api_service.src.shared.logging.logger_config import setup_logger
from apps.api_service.src.shared.logging.structlog_logger import StructlogLogger
from apps.api_service.src.shared.settings.config import settings

setup_logger(json_format=True, log_level="INFO")
logger = StructlogLogger("endpoint")


@asynccontextmanager
async def lifespan(app: FastAPI):
    backend = os.getenv("PREDICTION_REPOSITORY_BACKEND", "postgres").lower()
    if backend == "inmemory":
        app.state.prediction_repository = InMemoryPredictionJobRepository()
    else:
        app.state.prediction_repository = SQLAlchemyPredictionJobRepository(
            database_url=settings.database_url
        )
    app.state.job_queue = InProcessJobQueue()
    app.state.smiles_validator = DomainSmilesValidator()
    yield


app = FastAPI(
    title="API Jelajah Medika",
    version="1.0.0",
    description="Backend for drug target interaction",
    contact={"name": "sian", "email": "pawesisiantika98@gmail.com"},
    lifespan=lifespan,
)
register_exception_handlers(app)
app.include_router(job_management_router)


@app.get("/")
def home():
    logger.info("home_endpoint_called")
    return {"data": "server is running"}


@app.get("/health/db")
async def health_db(session: AsyncSession = Depends(db_session_dependency)):
    result = await session.execute(text("SELECT 1"))
    is_ok = result.scalar_one() == 1
    return {"database": "ok" if is_ok else "failed"}


if __name__ == "__main__":
    uvicorn.run("apps.api_service.src.main:app", host=settings.host, port=settings.port, reload=True)
