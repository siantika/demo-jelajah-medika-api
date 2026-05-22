from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from apps.shared.domain.errors import PredictionJobNotFoundError
from apps.shared.domain.exceptions import InvalidValueObject


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(InvalidValueObject)
    async def invalid_value_object_handler(
        _request: Request, exc: InvalidValueObject
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)},
        )

    @app.exception_handler(PredictionJobNotFoundError)
    async def prediction_job_not_found_handler(
        _request: Request, exc: PredictionJobNotFoundError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc)},
        )
