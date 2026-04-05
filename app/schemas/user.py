from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Role(str, Enum):
    viewer = "viewer"
    analyst = "analyst"
    admin = "admin"


class UserBase(BaseModel):
    email: EmailStr = Field(..., example="admin@zorvyn.io")
    full_name: str = Field(..., example="Admin User")


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, example="Admin@123!")


class UserOut(UserBase):
    id: UUID
    role: Role
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    full_name: str = Field(..., example="New Name")


class UserRoleUpdate(BaseModel):
    role: Role


class UserStatusUpdate(BaseModel):
    is_active: bool
