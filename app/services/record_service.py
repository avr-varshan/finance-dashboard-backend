from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import select, func, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.record import FinancialRecord, RecordType
from app.models.audit_log import RecordAuditLog, AuditAction
from app.models.user import User


def _format_amount(x):
    if x is None:
        return "₹0.00"
    return f"₹{Decimal(x):,.2f}"
from app.utils.errors import NotFoundError


async def create_record(db: AsyncSession, user: User, data):
    record = FinancialRecord(
        amount=data.amount,
        type=data.type,
        category=data.category,
        date=data.date,
        notes=data.notes,
        created_by=user.id,
        updated_by=None,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    audit = RecordAuditLog(
        record_id=record.id,
        action=AuditAction.created,
        changed_by=user.id,
        before_snapshot=None,
        after_snapshot={
            "id": str(record.id),
            "amount": _format_amount(record.amount),
            "type": record.type.value,
            "category": record.category,
            "date": record.date.isoformat(),
            "notes": record.notes,
        },
    )
    db.add(audit)
    await db.commit()

    return record


async def get_record(db: AsyncSession, record_id: str, current_user: User, include_deleted: bool = False):
    record = await db.get(FinancialRecord, record_id)
    if not record:
        raise NotFoundError("Record not found")
    if record.is_deleted and not (current_user.role.value == "admin" and include_deleted):
        raise NotFoundError("Record not found")

    return record


async def list_records(db: AsyncSession, current_user: User, filters: dict):
    query = select(FinancialRecord)
    if not (current_user.role.value == "admin" and filters.get("include_deleted")):
        query = query.where(FinancialRecord.is_deleted == False)

    if filters.get("type"):
        query = query.where(FinancialRecord.type == filters.get("type"))
    if filters.get("category"):
        query = query.where(FinancialRecord.category == filters.get("category"))
    if filters.get("date_from"):
        query = query.where(FinancialRecord.date >= filters.get("date_from"))
    if filters.get("date_to"):
        query = query.where(FinancialRecord.date <= filters.get("date_to"))
    if filters.get("amount_min"):
        query = query.where(FinancialRecord.amount >= Decimal(filters.get("amount_min")))
    if filters.get("amount_max"):
        query = query.where(FinancialRecord.amount <= Decimal(filters.get("amount_max")))
    if current_user.role.value == "admin" and filters.get("created_by"):
        query = query.where(FinancialRecord.created_by == filters.get("created_by"))
    if filters.get("search"):
        q = f"%{filters.get('search')}%"
        query = query.where(or_(FinancialRecord.notes.ilike(q), FinancialRecord.category.ilike(q)))

    sort_by = filters.get("sort_by", "date")
    order = filters.get("order", "desc")
    sort_column = {
        "date": FinancialRecord.date,
        "amount": FinancialRecord.amount,
        "created_at": FinancialRecord.created_at,
    }.get(sort_by, FinancialRecord.date)
    if order == "asc":
        query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(sort_column))

    # pagination will happen in router via helper
    return query


async def update_record(db: AsyncSession, record: FinancialRecord, user: User, data):
    before = {
        "id": str(record.id),
        "amount": _format_amount(record.amount),
        "type": record.type.value,
        "category": record.category,
        "date": record.date.isoformat(),
        "notes": record.notes,
    }

    for field in ["amount", "type", "category", "date", "notes"]:
        if hasattr(data, field) and getattr(data, field) is not None:
            setattr(record, field, getattr(data, field))
    record.updated_by = user.id
    record.updated_at = datetime.utcnow()
    db.add(record)
    await db.commit()
    await db.refresh(record)

    after = {
        "id": str(record.id),
        "amount": _format_amount(record.amount),
        "type": record.type.value,
        "category": record.category,
        "date": record.date.isoformat(),
        "notes": record.notes,
    }

    audit = RecordAuditLog(
        record_id=record.id,
        action=AuditAction.updated,
        changed_by=user.id,
        before_snapshot=before,
        after_snapshot=after,
    )
    db.add(audit)
    await db.commit()
    return record


async def delete_record(db: AsyncSession, record: FinancialRecord, user: User):
    record.is_deleted = True
    record.updated_by = user.id
    record.updated_at = datetime.utcnow()
    db.add(record)
    await db.commit()

    audit = RecordAuditLog(
        record_id=record.id,
        action=AuditAction.deleted,
        changed_by=user.id,
        before_snapshot=None,
        after_snapshot=None,
    )
    db.add(audit)
    await db.commit()

    return record
