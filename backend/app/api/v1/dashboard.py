from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.v1.transactions import serialize_transaction
from app.db.session import get_db
from app.models import User
from app.services.finance import dashboard_data, month_start, next_month, user_today

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
def get_dashboard(
    start: date | None = None,
    end: date | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    default_start = month_start(user_today(user))
    data = dashboard_data(
        db, user, start or default_start, end or next_month(default_start) - timedelta(days=1)
    )
    data["recent_transactions"] = [
        serialize_transaction(item).model_dump() for item in data["recent_transactions"]
    ]
    return data


@router.get("/reports/monthly")
def get_monthly_report(
    month: date | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    selected = month_start(month or user_today(user))
    data = dashboard_data(db, user, selected, next_month(selected) - timedelta(days=1))
    data["recent_transactions"] = [
        serialize_transaction(item).model_dump() for item in data["recent_transactions"]
    ]
    return data
