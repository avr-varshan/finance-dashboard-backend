from fastapi import HTTPException, status


class APIException(HTTPException):
    def __init__(self, status_code: int, code: str, message: str, details=None):
        self.status_code = status_code
        self.detail = {
            "error": True,
            "code": code,
            "message": message,
            "request_id": "",
            "details": details,
        }


class UnauthorizedError(APIException):
    def __init__(self, message="Unauthorized", details=None):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, code="UNAUTHORIZED", message=message, details=details)


class ForbiddenError(APIException):
    def __init__(self, message="Forbidden", details=None):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, code="FORBIDDEN", message=message, details=details)


class NotFoundError(APIException):
    def __init__(self, message="Not found", details=None):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, code="NOT_FOUND", message=message, details=details)


class ConflictError(APIException):
    def __init__(self, message="Conflict", details=None):
        super().__init__(status_code=status.HTTP_409_CONFLICT, code="CONFLICT", message=message, details=details)


class ValidationError(APIException):
    def __init__(self, message="Validation error", details=None):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, code="VALIDATION_ERROR", message=message, details=details)


class InvalidCredentialsError(APIException):
    def __init__(self, message="Invalid credentials", details=None):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, code="INVALID_CREDENTIALS", message=message, details=details)


class TokenExpiredError(APIException):
    def __init__(self, message="Token expired", details=None):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, code="TOKEN_EXPIRED", message=message, details=details)


class TokenRevokedError(APIException):
    def __init__(self, message="Token revoked", details=None):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, code="TOKEN_REVOKED", message=message, details=details)


class WeakPasswordError(ValidationError):
    def __init__(self, message="Weak password", details=None):
        super().__init__(message=message, details=details)


class SelfActionForbiddenError(ForbiddenError):
    def __init__(self, message="Self-action forbidden", details=None):
        super().__init__(message=message, details=details)
