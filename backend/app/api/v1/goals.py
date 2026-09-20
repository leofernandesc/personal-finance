from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Goal, User
from app.schemas.finance import GoalCreate, GoalResponse, GoalUpdate
from app.services.goals import archive_goal as archive_goal_service
from app.services.goals import create_goal, update_goal

router = APIRouter(prefix="/goals", tags=["goals"])


@router.get("", response_model=list[GoalResponse])
def list_goals(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return list(
        db.scalars(select(Goal).where(Goal.user_id == user.id).order_by(Goal.created_at.desc()))
    )


@router.post("", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
def add_goal(
    payload: GoalCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    goal = create_goal(db, user, payload)
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
    goal = update_goal(db, user, goal_id, payload)
    db.commit()
    db.refresh(goal)
    return goal


@router.delete("/{goal_id}")
def remove_goal(
    goal_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    archive_goal_service(db, user, goal_id)
    db.commit()
    return {"message": "Meta arquivada"}
