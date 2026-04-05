import csv
import io
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.user import Role, User
from app.schemas.common import SuccessResponse
from app.schemas.record import RecordCreate, RecordOut, RecordUpdate
from app.services.record_service import create_record, get_record, list_records, update_record, delete_record, _format_amount
from app.utils.pagination import paginate

router = APIRouter()


@router.get("", response_model=SuccessResponse, description="List financial records")
async def get_records(
    type: str = Query(None),
    category: str = Query(None),
    date_from: str = Query(None),
    date_to: str = Query(None),
    amount_min: float = Query(None),
    amount_max: float = Query(None),
    created_by: str = Query(None),
    search: str = Query(None),
    include_deleted: bool = Query(False),
    sort_by: str = Query("date"),
    order: str = Query("desc"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Restrict filters for viewers
    if current_user.role.value == "viewer":
        created_by = None
        search = None
        include_deleted = False

    filters = {
        "type": type,
        "category": category,
        "date_from": date_from,
        "date_to": date_to,
        "amount_min": amount_min,
        "amount_max": amount_max,
        "created_by": created_by,
        "search": search,
        "include_deleted": include_deleted,
        "sort_by": sort_by,
        "order": order,
    }
    query = await list_records(db, current_user, filters)
    page_data = await paginate(query, page=page, limit=limit, session=db)
    return SuccessResponse(data=[RecordOut.from_orm_with_role(r, current_user.role.value) for r in page_data["items"]], message="OK")


@router.post("", response_model=SuccessResponse, description="Create a financial record")
async def post_record(payload: RecordCreate, current_user: User = Depends(require_role(Role.analyst, Role.admin)), db: AsyncSession = Depends(get_db)):
    rec = await create_record(db, current_user, payload)
    return SuccessResponse(data=RecordOut.from_orm(rec))


@router.get("/categories", response_model=SuccessResponse, description="Get distinct categories")
async def get_categories(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.models.record import FinancialRecord

    rows = (await db.execute(select(FinancialRecord.category).distinct().where(FinancialRecord.is_deleted == False))).scalars().all()
    return SuccessResponse(data=rows)


@router.get("/export", response_model=None, description="Export records as CSV")
async def export_records(
    type: str = Query(None),
    category: str = Query(None),
    date_from: str = Query(None),
    date_to: str = Query(None),
    amount_min: float = Query(None),
    amount_max: float = Query(None),
    created_by: str = Query(None),
    search: str = Query(None),
    include_deleted: bool = Query(False),
    sort_by: str = Query("date"),
    order: str = Query("desc"),
    current_user: User = Depends(require_role(Role.analyst, Role.admin)),
    db: AsyncSession = Depends(get_db),
):
    filters = {
        "type": type,
        "category": category,
        "date_from": date_from,
        "date_to": date_to,
        "amount_min": amount_min,
        "amount_max": amount_max,
        "created_by": created_by,
        "search": search,
        "include_deleted": include_deleted,
        "sort_by": sort_by,
        "order": order,
    }
    query = await list_records(db, current_user, filters)
    rows = (await db.execute(query)).scalars().all()

    def stream():
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["id", "amount", "type", "category", "date", "notes", "created_by", "created_at"])
        for r in rows:
            writer.writerow([str(r.id), _format_amount(r.amount), r.type.value, r.category, r.date.isoformat(), r.notes or "", str(r.created_by), r.created_at.isoformat()])
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)

    headers = {"Content-Disposition": "attachment; filename=records_export_.csv"}
    return StreamingResponse(stream(), media_type="text/csv", headers=headers)


@router.get("/{record_id}", response_model=SuccessResponse, description="Get record by ID")
async def read_record(record_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db), include_deleted: bool = Query(False)):
    rec = await get_record(db, record_id, current_user, include_deleted=include_deleted)
    return SuccessResponse(data=RecordOut.from_orm(rec))


@router.patch("/{record_id}", response_model=SuccessResponse, description="Update record")
async def patch_record(record_id: str, payload: RecordUpdate, current_user: User = Depends(require_role(Role.admin)), db: AsyncSession = Depends(get_db)):
    rec = await get_record(db, record_id, current_user, include_deleted=True)
    rec = await update_record(db, rec, current_user, payload)
    return SuccessResponse(data=RecordOut.from_orm(rec))


@router.delete("/{record_id}", response_model=SuccessResponse, description="Soft delete record")
async def delete_record_route(record_id: str, current_user: User = Depends(require_role(Role.admin)), db: AsyncSession = Depends(get_db)):
    rec = await get_record(db, record_id, current_user, include_deleted=True)
    await delete_record(db, rec, current_user)
    return SuccessResponse(message="Record deleted")


@router.get("/{record_id}/history", response_model=SuccessResponse, description="Get record audit history")
async def history(record_id: str, current_user: User = Depends(require_role(Role.analyst, Role.admin)), db: AsyncSession = Depends(get_db)):
    from app.models.audit_log import RecordAuditLog
    from sqlalchemy import select

    rows = (await db.execute(select(RecordAuditLog).where(RecordAuditLog.record_id == record_id).order_by(RecordAuditLog.changed_at.desc()))).scalars().all()
    data = []
    for r in rows:
        data.append({
            "action": r.action.value,
            "changed_by": str(r.changed_by),
            "before_snapshot": r.before_snapshot,
            "after_snapshot": r.after_snapshot,
            "changed_at": r.changed_at.isoformat(),
        })
    return SuccessResponse(data=data)
