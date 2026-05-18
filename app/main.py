import uvicorn
from fastapi import FastAPI

from app.api.shared.logging.logger import StructlogLogger, setup_logger
from app.api.shared.settings.config import settings

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


if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
