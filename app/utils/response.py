from app.schemas.common import ErrorResponse, SuccessResponse


def success_response(data=None, message: str = "OK") -> SuccessResponse:
    return SuccessResponse(success=True, data=data, message=message)


def error_response(code: str, message: str, request_id: str, details=None) -> ErrorResponse:
    return ErrorResponse(error=True, code=code, message=message, request_id=request_id, details=details)
