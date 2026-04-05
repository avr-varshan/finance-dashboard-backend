from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, Role
from app.schemas.user import UserCreate
from app.services.auth_service import get_password_hash
from app.utils.errors import ConflictError, NotFoundError


async def get_user_by_email(db: AsyncSession, email: str):
    q = select(User).where(User.email == email)
    res = await db.execute(q)
    return res.scalars().first()


async def get_user(db: AsyncSession, user_id: str):
    user = await db.get(User, user_id)
    if not user:
        raise NotFoundError("User not found")
    return user


async def create_user(db: AsyncSession, user_in: UserCreate, role: Role = Role.viewer):
    existing = await get_user_by_email(db, user_in.email)
    if existing:
        raise ConflictError("Email already registered")
    hashed = get_password_hash(user_in.password)
    user = User(email=user_in.email, hashed_password=hashed, full_name=user_in.full_name, role=role)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user_full_name(db: AsyncSession, user: User, full_name: str):
    user.full_name = full_name
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def list_users(db: AsyncSession, role: Role = None, is_active: bool = None, page=1, limit=20):
    query = select(User)
    if role:
        query = query.where(User.role == role)
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    pages = (total + limit - 1) // limit
    items = (await db.execute(query.offset((page - 1) * limit).limit(limit))).scalars().all()
    return items, {"total": total, "page": page, "limit": limit, "pages": pages}


async def update_user_role(db: AsyncSession, actor: User, target: User, role: Role):
    if actor.id == target.id:
        from app.utils.errors import SelfActionForbiddenError
        raise SelfActionForbiddenError("Admin cannot change own role")
    target.role = role
    db.add(target)
    await db.commit()
    await db.refresh(target)
    return target


async def update_user_status(db: AsyncSession, actor: User, target: User, is_active: bool):
    if actor.id == target.id:
        from app.utils.errors import SelfActionForbiddenError
        raise SelfActionForbiddenError("Admin cannot deactivate themselves")
    target.is_active = is_active
    db.add(target)
    await db.commit()
    await db.refresh(target)
    return target


async def get_user_activity(db: AsyncSession, user_id: str):
    from app.models.record import FinancialRecord
    from app.models.audit_log import RecordAuditLog

    q = select(
        func.count(FinancialRecord.id).label("total_records_created"),
        func.count(RecordAuditLog.id).label("total_records_updated"),
        func.max(RecordAuditLog.changed_at).label("last_active_at"),
    ).select_from(FinancialRecord).where(FinancialRecord.created_by == user_id)

    created = (await db.execute(q)).first()

    recent = await db.execute(
        select(func.count().label("records_this_month")).select_from(FinancialRecord).where(
            FinancialRecord.created_by == user_id,
            FinancialRecord.date >= func.date_trunc("month", func.now()),
        )
    )
    records_this_month = recent.scalar_one()

    return {
        "user_id": user_id,
        "full_name": (await get_user(db, user_id)).full_name,
        "total_records_created": created[0] if created else 0,
        "total_records_updated": created[1] if created else 0,
        "last_active_at": created[2] if created else None,
        "records_this_month": records_this_month,
    }
