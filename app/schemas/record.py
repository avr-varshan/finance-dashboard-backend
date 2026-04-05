from datetime import date as date_type, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, validator


class RecordType(str, Enum):
    income = "income"
    expense = "expense"


class RecordCreate(BaseModel):
    amount: Decimal = Field(..., gt=0, example="1250.50")
    type: RecordType = Field(..., example="income")
    category: str = Field(..., example="Salary")
    date: date_type = Field(..., example="2025-01-10")
    notes: Optional[str] = Field(None, example="Monthly salary")

    @validator("date")
    def date_not_future(cls, v: date_type):
        from datetime import date as _date

        if v > _date.today():
            raise ValueError("Date cannot be in the future")
        return v


class RecordUpdate(BaseModel):
    amount: Optional[Decimal] = Field(None, gt=0, example="1500.00")
    type: Optional[RecordType] = Field(None, example="expense")
    category: Optional[str] = Field(None, example="Rent")
    date: Optional[date_type] = Field(None, example="2025-02-01")
    notes: Optional[str] = Field(None, example="Updated notes")

    @validator("date")
    def date_not_future(cls, v: Optional[date_type]):
        from datetime import date as _date

        if v and v > _date.today():
            raise ValueError("Date cannot be in the future")
        return v


class RecordFilter(BaseModel):
    type: Optional[RecordType]
    category: Optional[str]
    date_from: Optional[date_type]
    date_to: Optional[date_type]
    amount_min: Optional[Decimal]
    amount_max: Optional[Decimal]
    created_by: Optional[str]
    search: Optional[str]
    include_deleted: Optional[bool] = False
    sort_by: Optional[str] = "date"
    order: Optional[str] = "desc"
    page: Optional[int] = 1
    limit: Optional[int] = 20


class RecordOut(BaseModel):
    id: UUID
    amount: Decimal
    type: RecordType
    category: str
    date: date_type
    notes: Optional[str]
    is_deleted: bool
    created_by: UUID
    updated_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_with_role(cls, record, role: str):
        data = cls.from_orm(record).model_dump()
        if role in ["viewer", "analyst"]:
            data["notes"] = None
        return cls(**data)
