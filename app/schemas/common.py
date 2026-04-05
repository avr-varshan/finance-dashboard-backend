from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field
from pydantic.generics import GenericModel

T = TypeVar("T")


class SuccessResponse(BaseModel):
    success: bool = True
    data: Any = None
    message: str = "OK"


class PaginatedResponse(GenericModel, Generic[T]):
    success: bool = True
    data: list[T]
    pagination: dict = Field(..., example={"total": 0, "page": 1, "limit": 20, "pages": 0})
    message: str = "OK"


class ErrorResponse(BaseModel):
    error: bool = True
    code: str
    message: str
    request_id: str
    details: Any = None
