import logging
import time
from typing import Any, Optional
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import configure_logging, log_event
from app.core.request_context import request_id_from
from app.db.session import get_db_session
from app.errors import DomainError

logger = logging.getLogger("app")


def error_response(
    *,
    request: Request,
    status_code: int,
    code: str,
    message: str,
    fields: Optional[dict[str, str]] = None,
) -> JSONResponse:
    error: dict[str, Any] = {
        "code": code,
        "message": message,
        "request_id": request_id_from(request) or str(uuid4()),
    }
    if fields:
        error["fields"] = fields
    return JSONResponse(status_code=status_code, content={"error": error})


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    app = FastAPI(title="Car Dealership Inventory API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    @app.middleware("http")
    async def add_request_context(request: Request, call_next: Any) -> Any:
        incoming = request.headers.get("X-Request-ID")
        try:
            request_id = str(UUID(incoming)) if incoming else str(uuid4())
        except ValueError:
            request_id = str(uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        log_event(
            logger,
            "request.completed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
            user_id=getattr(request.state, "user_id", None),
        )
        return response

    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        return error_response(
            request=request,
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            fields=exc.fields,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        fields = {
            ".".join(str(part) for part in error["loc"] if part != "body"): error["msg"]
            for error in exc.errors()
        }
        return error_response(
            request=request,
            status_code=422,
            code="validation_error",
            message="Request validation failed.",
            fields=fields,
        )

    @app.exception_handler(HTTPException)
    async def handle_http_error(request: Request, exc: HTTPException) -> JSONResponse:
        status_codes = {
            401: ("unauthorized", "Authentication is required."),
            403: ("forbidden", "You do not have permission to perform this action."),
            404: ("not_found", "The requested resource does not exist."),
            405: ("method_not_allowed", "The request method is not allowed."),
        }
        code, message = status_codes.get(exc.status_code, ("http_error", "The request failed."))
        return error_response(
            request=request, status_code=exc.status_code, code=code, message=message
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        log_event(
            logger, "request.failed", request_id=request_id_from(request), error=type(exc).__name__
        )
        return error_response(
            request=request,
            status_code=500,
            code="internal_error",
            message="An unexpected error occurred.",
        )

    @app.get("/health", tags=["operations"])
    def health_check(session: Session = Depends(get_db_session)) -> dict[str, str]:  # noqa: B008
        try:
            session.execute(text("SELECT 1"))
        except SQLAlchemyError as exc:
            raise DomainError(503, "service_unavailable", "Database is unavailable.") from exc
        return {"status": "ok"}

    return app


app = create_app()
