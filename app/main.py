import uvicorn
from fastapi import FastAPI

from app.api.shared.config import settings

app = FastAPI(
    title="API Jelajah Medika",
    version="1.0.0",
    description="Backend for drug target interaction",
    contact={"name": "sian", "email": "pawesisiantika98@gmail.com"},
)


@app.get("/")
def home():
    return {"data": "server is running"}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
