"""
Litestar Exception Handlers

Consistent error responses for /v2 API.
"""

from litestar import Request, Response
from litestar.exceptions import HTTPException, NotAuthorizedException, NotFoundException
from litestar.status_codes import HTTP_500_INTERNAL_SERVER_ERROR, HTTP_401_UNAUTHORIZED, HTTP_404_NOT_FOUND
from core.utils.logger import logger


def handle_not_authorized(request: Request, exc: NotAuthorizedException) -> Response:
    """Handle authentication errors."""
    return Response(
        content={"detail": str(exc.detail) if exc.detail else "Not authorized"},
        status_code=HTTP_401_UNAUTHORIZED,
    )


def handle_not_found(request: Request, exc: NotFoundException) -> Response:
    """Handle not found errors."""
    return Response(
        content={"detail": str(exc.detail) if exc.detail else "Not found"},
        status_code=HTTP_404_NOT_FOUND,
    )


def handle_http_exception(request: Request, exc: HTTPException) -> Response:
    """Handle HTTP exceptions."""
    return Response(
        content={"detail": str(exc.detail) if exc.detail else "Error"},
        status_code=exc.status_code,
    )


def handle_exception(request: Request, exc: Exception) -> Response:
    """Generic exception handler."""
    logger.error(f"[LITESTAR] Unhandled exception: {exc}", exc_info=True)
    return Response(
        content={"detail": "Internal server error"},
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
    )


exception_handlers = {
    NotAuthorizedException: handle_not_authorized,
    NotFoundException: handle_not_found,
    HTTPException: handle_http_exception,
    Exception: handle_exception,
}
