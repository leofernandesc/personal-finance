from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Category, User
from app.schemas.finance import CategoryCreate, CategoryResponse, CategoryUpdate
from app.services.finance import create_category, update_category

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryResponse])
def list_categories(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return list(
        db.scalars(select(Category).where(Category.user_id == user.id).order_by(Category.name))
    )


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def add_category(
    payload: CategoryCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    category = create_category(db, user, payload)
    db.commit()
    db.refresh(category)
    return category


@router.patch("/{category_id}", response_model=CategoryResponse)
def edit_category(
    category_id: UUID,
    payload: CategoryUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    category = update_category(db, user, category_id, payload)
    db.commit()
    db.refresh(category)
    return category
