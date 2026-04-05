from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession


def normalize_pagination(page: int = 1, limit: int = 20, max_limit: int = 100):
    page = max(1, page)
    limit = max(1, min(limit, max_limit))
    return page, limit


async def paginate(query, page: int = 1, limit: int = 20, session: AsyncSession = None):
    page, limit = normalize_pagination(page, limit)
    count_q = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_q)).scalar_one()
    pages = (total + limit - 1) // limit
    results = (await session.execute(query.offset((page - 1) * limit).limit(limit))).scalars().all()
    return {
        "items": results,
        "pagination": {
            "total": total,
            "page": page,
            "limit": limit,
            "pages": pages,
        },
    }
