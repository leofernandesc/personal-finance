from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Goal, User
from app.schemas.finance import GoalCreate, GoalResponse, GoalUpdate

router = APIRouter(prefix="/goals", tags=["goals"])


def owned_goal(db: Session, user: User, goal_id: UUID) -> Goal:
    goal = db.scalar(select(Goal).where(Goal.id == goal_id, Goal.user_id == user.id))
    if not goal:
        raise HTTPException(status_code=404, detail="Meta não encontrada")
    return goal


@router.get("", response_model=list[GoalResponse])
def list_goals(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return list(
        db.scalars(select(Goal).where(Goal.user_id == user.id).order_by(Goal.created_at.desc()))
    )


@router.post("", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
def add_goal(
    payload: GoalCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    goal = Goal(user_id=user.id, **payload.model_dump())
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


@router.patch("/{goal_id}", response_model=GoalResponse)
def edit_goal(
    goal_id: UUID,
    payload: GoalUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    goal = owned_goal(db, user, goal_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(goal, key, value)
    db.commit()
    db.refresh(goal)
    return goal


@router.delete("/{goal_id}")
def archive_goal(
    goal_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    goal = owned_goal(db, user, goal_id)
    goal.status = "archived"
    db.commit()
    return {"message": "Meta arquivada"}
