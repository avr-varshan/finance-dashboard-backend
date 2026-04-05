from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import RecordAuditLog


async def get_audit_logs(db: AsyncSession, record_id=None, changed_by=None, action=None, date_from=None, date_to=None, page=1, limit=20):
    query = select(RecordAuditLog)
    if record_id:
        query = query.where(RecordAuditLog.record_id == record_id)
    if changed_by:
        query = query.where(RecordAuditLog.changed_by == changed_by)
    if action:
        query = query.where(RecordAuditLog.action == action)
    if date_from:
        query = query.where(RecordAuditLog.changed_at >= date_from)
    if date_to:
        query = query.where(RecordAuditLog.changed_at <= date_to)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    pages = (total + limit - 1) // limit
    items = (await db.execute(query.order_by(RecordAuditLog.changed_at.desc()).offset((page-1)*limit).limit(limit))).scalars().all()
    return items, {"total": total, "page": page, "limit": limit, "pages": pages}
