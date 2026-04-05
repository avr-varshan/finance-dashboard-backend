from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict

from sqlalchemy import select, func, case, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.record import FinancialRecord, RecordType


def _format_amount(x):
    if x is None:
        return "₹0.00"
    return f"₹{Decimal(x):,.2f}"


async def summary(db: AsyncSession, period: str, role: str):
    now = datetime.utcnow().date()
    if period == "last_month":
        start = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
        end = now.replace(day=1) - timedelta(days=1)
    elif period == "all_time":
        start, end = None, None
    else:
        start = now.replace(day=1)
        end = now

    base = select(FinancialRecord)
    if start:
        base = base.where(FinancialRecord.date >= start)
    if end and period != "all_time":
        base = base.where(FinancialRecord.date <= end)

    total_income_q = select(func.coalesce(func.sum(FinancialRecord.amount), 0)).where(
        FinancialRecord.type == RecordType.income,
        FinancialRecord.is_deleted == False,
    )
    total_expense_q = select(func.coalesce(func.sum(FinancialRecord.amount), 0)).where(
        FinancialRecord.type == RecordType.expense,
        FinancialRecord.is_deleted == False,
    )

    inc = (await db.execute(total_income_q)).scalar_one() or Decimal(0)
    exp = (await db.execute(total_expense_q)).scalar_one() or Decimal(0)

    net = inc - exp

    trans_cnt = (await db.execute(select(func.count()).select_from(FinancialRecord).where(FinancialRecord.is_deleted == False))).scalar_one() or 0

    avg = (await db.execute(select(func.coalesce(func.avg(FinancialRecord.amount), 0)).where(FinancialRecord.is_deleted == False))).scalar_one() or Decimal(0)

    largest = (await db.execute(select(FinancialRecord).where(FinancialRecord.is_deleted == False).order_by(FinancialRecord.amount.desc()).limit(1))).scalars().first()

    last = (await db.execute(select(func.max(FinancialRecord.date)).where(FinancialRecord.is_deleted == False))).scalar_one()
    days_since = (datetime.utcnow().date() - last).days if last else None

    data = {
        "period": period,
        "total_income": _format_amount(inc),
        "total_expenses": _format_amount(exp),
        "net_balance": _format_amount(net),
        "transaction_count": int(trans_cnt),
        "income_count": int((await db.execute(select(func.count()).select_from(FinancialRecord).where(FinancialRecord.type == RecordType.income, FinancialRecord.is_deleted == False))).scalar_one() or 0),
        "expense_count": int((await db.execute(select(func.count()).select_from(FinancialRecord).where(FinancialRecord.type == RecordType.expense, FinancialRecord.is_deleted == False))).scalar_one() or 0),
        "avg_transaction_amount": _format_amount(avg),
        "largest_transaction": {
            "id": str(largest.id) if largest else None,
            "amount": _format_amount(largest.amount) if largest else "0.00",
            "type": largest.type.value if largest else None,
            "category": largest.category if largest else None,
            "date": largest.date.isoformat() if largest else None,
        },
        "days_since_last_entry": days_since if days_since is not None else 0,
    }

    if role != "viewer":
        data["mom_income_change_pct"] = 0.0
        data["mom_expense_change_pct"] = 0.0

    return data


async def category_breakdown(db: AsyncSession, period: str, record_type: str = None):
    q = select(
        FinancialRecord.category,
        func.coalesce(func.sum(FinancialRecord.amount), 0).label("total"),
        func.count(FinancialRecord.id).label("count"),
    ).where(FinancialRecord.is_deleted == False)

    if record_type:
        q = q.where(FinancialRecord.type == record_type)

    q = q.group_by(FinancialRecord.category).order_by(func.sum(FinancialRecord.amount).desc())

    rows = (await db.execute(q)).all()
    results = []
    total_all = sum([row.total for row in rows]) or Decimal(0)
    for row in rows:
        pct = (row.total / total_all * 100) if total_all else 0
        results.append({"category": row.category, "total": _format_amount(row.total), "count": row.count, "pct": round(float(pct),1)})

    return results


async def trends(db: AsyncSession, view: str):
    if view == "weekly":
        q = text("SELECT to_char(date_trunc('week', date), 'Mon DD') as label, coalesce(sum(amount) FILTER (WHERE type='income'),0) as income, coalesce(sum(amount) FILTER (WHERE type='expense'),0) as expenses, count(*) as transaction_count FROM financial_records WHERE is_deleted=false AND date >= now() - interval '8 weeks' GROUP BY date_trunc('week', date) ORDER BY date_trunc('week', date) DESC")
        rows = await db.execute(q)
        data = []
        for row in rows:
            data.append({"label": row.label, "income": _format_amount(row.income), "expenses": _format_amount(row.expenses), "net": _format_amount(Decimal(row.income) - Decimal(row.expenses)), "transaction_count": int(row.transaction_count)})
        return {"view": view, "data": data}
    else:
        q = text("SELECT to_char(date_trunc('month', date), 'Mon YYYY') as label, coalesce(sum(amount) FILTER (WHERE type='income'),0) as income, coalesce(sum(amount) FILTER (WHERE type='expense'),0) as expenses, count(*) as transaction_count FROM financial_records WHERE is_deleted=false AND date >= now() - interval '6 months' GROUP BY date_trunc('month', date) ORDER BY date_trunc('month', date) DESC")
        rows = await db.execute(q)
        data = []
        for row in rows:
            data.append({"label": row.label, "income": _format_amount(row.income), "expenses": _format_amount(row.expenses), "net": _format_amount(Decimal(row.income) - Decimal(row.expenses)), "transaction_count": int(row.transaction_count)})
        return {"view": view, "data": data}


async def recent(db: AsyncSession, limit: int = 10, role: str = None):
    limit = min(max(1, limit), 50)
    q = select(FinancialRecord).options(joinedload(FinancialRecord.created_by_user)).where(FinancialRecord.is_deleted == False).order_by(FinancialRecord.date.desc(), FinancialRecord.created_at.desc()).limit(limit)
    rows = (await db.execute(q)).scalars().unique().all()
    results = []
    for r in rows:
        result = {
            "id": str(r.id),
            "amount": _format_amount(r.amount),
            "type": r.type.value,
            "category": r.category,
            "date": r.date.isoformat(),
            "created_by_name": r.created_by_user.full_name if r.created_by_user else None,
            "created_at": r.created_at.isoformat(),
        }
        if role != "viewer":
            result["notes"] = r.notes
        results.append(result)
    return results


async def alerts(db: AsyncSession):
    now = datetime.utcnow().date()
    current_month_start = now.replace(day=1)

    # category spike simple implementation
    q_current = select(FinancialRecord.category, func.coalesce(func.sum(FinancialRecord.amount), 0).label("total")).where(
        FinancialRecord.type == RecordType.expense,
        FinancialRecord.is_deleted == False,
        FinancialRecord.date >= current_month_start,
    ).group_by(FinancialRecord.category)

    q_hist = select(FinancialRecord.category, func.coalesce(func.avg(FinancialRecord.amount), 0).label("avg")).where(
        FinancialRecord.type == RecordType.expense,
        FinancialRecord.is_deleted == False,
        FinancialRecord.date >= (current_month_start - timedelta(days=90)),
        FinancialRecord.date < current_month_start,
    ).group_by(FinancialRecord.category)

    cur_rows = (await db.execute(q_current)).all()
    hist_rows = {r.category: r.avg for r in (await db.execute(q_hist)).all()}

    alerts = []
    for row in cur_rows:
        avg = hist_rows.get(row.category, Decimal(0))
        if avg > 0 and row.total > avg * Decimal(1.5):
            spike_pct = float((row.total - avg) / avg * 100)
            severity = "high" if spike_pct >= 70 else "medium"
            alerts.append({
                "type": "category_spike",
                "severity": severity,
                "message": f"{row.category} expenses this month are {spike_pct:.1f}% above the 3-month average",
                "category": row.category,
                "current_amount": _format_amount(row.total),
                "average_amount": _format_amount(avg),
                "spike_pct": round(spike_pct, 1),
            })

    largest_row = (await db.execute(select(FinancialRecord).where(FinancialRecord.is_deleted == False, FinancialRecord.date >= current_month_start).order_by(FinancialRecord.amount.desc()).limit(1))).scalars().first()
    if largest_row:
        alerts.append({
            "type": "largest_transaction",
            "message": "Largest single transaction this month",
            "record": {
                "id": str(largest_row.id),
                "amount": _format_amount(largest_row.amount),
                "type": largest_row.type.value,
                "category": largest_row.category,
                "date": largest_row.date.isoformat(),
            },
        })
    else:
        alerts.append({
            "type": "no_data",
            "message": "No transactions in current month",
        })

    last = (await db.execute(select(func.max(FinancialRecord.date)).where(FinancialRecord.is_deleted == False))).scalar_one()
    if last:
        days = (now - last).days
        if days > 7:
            alerts.append({"type": "no_recent_activity", "message": "No transactions logged in the last 7 days", "days_since_last": days})

    return {"alerts": alerts, "generated_at": datetime.utcnow().isoformat()}
