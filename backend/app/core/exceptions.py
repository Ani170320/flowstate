import logging
from typing import Any, Dict, Optional
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("flowstate.exceptions")


class AppException(Exception):
    """Base application exception for FLOWSTATE API."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details or {}


class NotFoundException(AppException):
    """Resource not found exception."""

    def __init__(
        self,
        message: str = "Resource not found",
        code: str = "NOT_FOUND",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            code=code,
            details=details,
        )


class BadRequestException(AppException):
    """Invalid client request exception."""

    def __init__(
        self,
        message: str = "Bad request",
        code: str = "BAD_REQUEST",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            code=code,
            details=details,
        )


class UnauthorizedException(AppException):
    """Authentication required or failed."""

    def __init__(
        self,
        message: str = "Unauthorized",
        code: str = "UNAUTHORIZED",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            code=code,
            details=details,
        )


class ForbiddenException(AppException):
    """Permission denied exception."""

    def __init__(
        self,
        message: str = "Forbidden",
        code: str = "FORBIDDEN",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            code=code,
            details=details,
        )


class DatabaseNotConfiguredException(AppException):
    """Raised when an operation requires the database, but DATABASE_URL is not set."""

    def __init__(
        self,
        message: str = "Database connection has not been configured yet.",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="DATABASE_NOT_CONFIGURED",
            details=details,
        )


class DatabaseConnectionException(AppException):
    """Raised when database connection cannot be established."""

    def __init__(
        self,
        message: str = "Failed to connect to database.",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="DATABASE_CONNECTION_ERROR",
            details=details,
        )


def register_exception_handlers(app: FastAPI) -> None:
    """Register centralized exception handlers for the FastAPI application."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        logger.warning(
            f"AppException: code={exc.code} status={exc.status_code} path={request.url.path} msg={exc.message}"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        logger.warning(f"Validation error on {request.url.path}: {exc.errors()}")
        formatted_errors = []
        for err in exc.errors():
            loc = " -> ".join(str(item) for item in err.get("loc", []))
            formatted_errors.append({
                "field": loc,
                "message": err.get("msg"),
                "type": err.get("type"),
            })
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Input validation failed.",
                    "details": {"validation_errors": formatted_errors},
                }
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        logger.warning(f"HTTPException: status={exc.status_code} path={request.url.path} detail={exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": f"HTTP_{exc.status_code}",
                    "message": exc.detail if isinstance(exc.detail, str) else "HTTP error",
                    "details": exc.detail if isinstance(exc.detail, dict) else {},
                }
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        # Crucial security requirement: Never leak credentials, DB strings or raw tracebacks to client
        logger.exception(f"Unhandled error on {request.url.path}: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred. Please try again later.",
                    "details": {},
                }
            },
        )
