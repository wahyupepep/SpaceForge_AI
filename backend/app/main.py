import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import settings
from app.core.errors import ApplicationError
from app.core.logging import RequestLoggingMiddleware, configure_logging
from app.schemas.error import ErrorDetail, ErrorResponse


def create_app() -> FastAPI:
    configure_logging()
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    application.add_middleware(
        RequestLoggingMiddleware, max_body_bytes=settings.max_request_body_bytes
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.exception_handler(ApplicationError)
    async def application_error_handler(request: Request, exc: ApplicationError) -> JSONResponse:
        logging.getLogger("spaceforge.error").warning(
            "application_error",
            extra={
                "request_id": getattr(request.state, "request_id", None),
                "method": request.method,
                "path": request.url.path,
                "status_code": exc.status_code,
                "error_code": exc.code,
            },
        )
        payload = ErrorResponse(
            error=ErrorDetail(code=exc.code, message=exc.message, details=exc.details)
        )
        return JSONResponse(status_code=exc.status_code, content=jsonable_encoder(payload))

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logging.getLogger("spaceforge.error").warning(
            "request_validation_error",
            extra={
                "request_id": getattr(request.state, "request_id", None),
                "method": request.method,
                "path": request.url.path,
                "status_code": 422,
                "error_code": "VALIDATION_ERROR",
            },
        )
        payload = ErrorResponse(
            error=ErrorDetail(
                code="VALIDATION_ERROR",
                message="Request validation failed.",
                details=exc.errors(),
            )
        )
        return JSONResponse(status_code=422, content=jsonable_encoder(payload))

    @application.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logging.getLogger("spaceforge.error").exception(
            "unhandled_error",
            extra={
                "request_id": getattr(request.state, "request_id", None),
                "method": request.method,
                "path": request.url.path,
                "status_code": 500,
                "error_code": "INTERNAL_SERVER_ERROR",
                "error_type": type(exc).__name__,
            },
        )
        payload = ErrorResponse(
            error=ErrorDetail(
                code="INTERNAL_SERVER_ERROR",
                message="An unexpected server error occurred.",
            )
        )
        return JSONResponse(status_code=500, content=jsonable_encoder(payload))

    application.include_router(api_router)
    return application


app = create_app()
