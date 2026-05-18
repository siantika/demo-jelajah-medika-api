import uvicorn
from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.session import db_session_dependency
from app.shared.logging.logger import StructlogLogger, setup_logger
from app.shared.settings.config import settings

setup_logger(json_format=True, log_level="INFO")
logger = StructlogLogger("endpoint")

app = FastAPI(
    title="API Jelajah Medika",
    version="1.0.0",
    description="Backend for drug target interaction",
    contact={"name": "sian", "email": "pawesisiantika98@gmail.com"},
)


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
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
