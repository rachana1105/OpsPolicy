"""Consistent structured error handling."""
from fastapi import Request
from fastapi.responses import JSONResponse


class OpsPolicyError(Exception):
    """Base error carrying a machine code, message and detail payload."""

    status_code: int = 400
    code: str = "OPSPOLICY_ERROR"

    def __init__(self, message: str, details: dict | None = None, code: str | None = None,
                 status_code: int | None = None):
        self.message = message
        self.details = details or {}
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code
        super().__init__(message)


class NotFoundError(OpsPolicyError):
    status_code = 404
    code = "NOT_FOUND"


class ValidationError(OpsPolicyError):
    status_code = 422
    code = "VALIDATION_ERROR"


class AuthError(OpsPolicyError):
    status_code = 401
    code = "UNAUTHENTICATED"


class ForbiddenError(OpsPolicyError):
    status_code = 403
    code = "FORBIDDEN"


class InvalidStateTransitionError(OpsPolicyError):
    status_code = 409
    code = "INVALID_STATE_TRANSITION"


class ConflictError(OpsPolicyError):
    status_code = 409
    code = "CONFLICT"


def error_body(code: str, message: str, details: dict, request_id: str) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "request_id": request_id,
        }
    }


async def opspolicy_error_handler(request: Request, exc: OpsPolicyError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(exc.code, exc.message, exc.details, request_id),
    )
