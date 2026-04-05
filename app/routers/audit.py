from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import require_role
from app.models.user import Role, User
from app.schemas.common import SuccessResponse
from app.services.audit_service import get_audit_logs
from app.database import get_db

router = APIRouter()


@router.get("/audit-log", response_model=SuccessResponse, description="Audit log listing")
async def audit_log(
    record_id: str = Query(None),
    changed_by: str = Query(None),
    action: str = Query(None),
    date_from: str = Query(None),
    date_to: str = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_role(Role.admin)),
    db: AsyncSession = Depends(get_db),
):
    items, pagination = await get_audit_logs(db, record_id=record_id, changed_by=changed_by, action=action, date_from=date_from, date_to=date_to, page=page, limit=limit)
    return SuccessResponse(data=items)
