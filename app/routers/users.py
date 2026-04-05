from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.user import Role, User
from app.schemas.common import SuccessResponse, PaginatedResponse
from app.schemas.user import UserOut, UserUpdate, UserRoleUpdate, UserStatusUpdate
from app.services.user_service import update_user_full_name, list_users, get_user, update_user_role, update_user_status, get_user_activity

router = APIRouter()


@router.get("/me", response_model=SuccessResponse, description="Get own profile")
async def read_me(current_user: User = Depends(get_current_user)):
    return SuccessResponse(data=UserOut.from_orm(current_user))


@router.patch("/me", response_model=SuccessResponse, description="Update own profile")
async def update_me(payload: UserUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user = await update_user_full_name(db, current_user, payload.full_name)
    return SuccessResponse(data=UserOut.from_orm(user))


@router.get("", response_model=SuccessResponse, description="List users")
async def get_users(role: Role = Query(None), is_active: bool = Query(None), page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100), current_user: User = Depends(require_role(Role.admin)), db: AsyncSession = Depends(get_db)):
    items, pagination = await list_users(db, role=role, is_active=is_active, page=page, limit=limit)
    return SuccessResponse(data=[UserOut.from_orm(item) for item in items], message="OK")


@router.get("/{user_id}", response_model=SuccessResponse, description="Get user by ID")
async def get_user_by_id(user_id: str, current_user: User = Depends(require_role(Role.admin)), db: AsyncSession = Depends(get_db)):
    user = await get_user(db, user_id)
    return SuccessResponse(data=UserOut.from_orm(user))


@router.patch("/{user_id}/role", response_model=SuccessResponse, description="Change user role")
async def change_role(user_id: str, payload: UserRoleUpdate, current_user: User = Depends(require_role(Role.admin)), db: AsyncSession = Depends(get_db)):
    target = await get_user(db, user_id)
    updated = await update_user_role(db, current_user, target, payload.role)
    return SuccessResponse(data=UserOut.from_orm(updated))


@router.patch("/{user_id}/status", response_model=SuccessResponse, description="Change user status")
async def change_status(user_id: str, payload: UserStatusUpdate, current_user: User = Depends(require_role(Role.admin)), db: AsyncSession = Depends(get_db)):
    target = await get_user(db, user_id)
    updated = await update_user_status(db, current_user, target, payload.is_active)
    return SuccessResponse(data=UserOut.from_orm(updated))


@router.get("/{user_id}/activity", response_model=SuccessResponse, description="User activity summary")
async def user_activity(user_id: str, current_user: User = Depends(require_role(Role.admin)), db: AsyncSession = Depends(get_db)):
    activity = await get_user_activity(db, user_id)
    return SuccessResponse(data=activity)
