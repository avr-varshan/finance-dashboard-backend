from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import require_role, get_current_user
from app.models.user import Role, User
from app.schemas.common import SuccessResponse
from app.services.dashboard_service import summary, category_breakdown, trends, recent, alerts
from app.database import get_db

router = APIRouter()


@router.get("/summary", response_model=SuccessResponse, description="Dashboard summary")
async def dashboard_summary(period: str = Query("current_month"), current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    data = await summary(db, period, current_user.role.value)
    return SuccessResponse(data=data)


@router.get("/categories", response_model=SuccessResponse, description="Dashboard categories breakdown")
async def dashboard_categories(period: str = Query("current_month"), type: str = Query(None), current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    income = await category_breakdown(db, period, record_type="income")
    expense = await category_breakdown(db, period, record_type="expense")
    return SuccessResponse(data={"income_breakdown": income, "expense_breakdown": expense, "top_expense_category": (expense[0]["category"] if expense else None), "top_income_category": (income[0]["category"] if income else None)})


@router.get("/trends", response_model=SuccessResponse, description="Dashboard trends")
async def dashboard_trends(view: str = Query("monthly"), current_user: User = Depends(require_role(Role.analyst, Role.admin)), db: AsyncSession = Depends(get_db)):
    data = await trends(db, view)
    return SuccessResponse(data=data)


@router.get("/recent", response_model=SuccessResponse, description="Dashboard recent transactions")
async def dashboard_recent(limit: int = Query(10, ge=1, le=50), current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    data = await recent(db, limit, current_user.role.value)
    return SuccessResponse(data=data)


@router.get("/alerts", response_model=SuccessResponse, description="Dashboard anomaly alerts")
async def dashboard_alerts(current_user: User = Depends(require_role(Role.analyst, Role.admin)), db: AsyncSession = Depends(get_db)):
    data = await alerts(db)
    return SuccessResponse(data=data)
