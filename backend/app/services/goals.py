from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Goal, User
from app.schemas.finance import GoalCreate, GoalUpdate


def owned_goal(db: Session, user: User, goal_id: UUID) -> Goal:
    goal = db.scalar(select(Goal).where(Goal.id == goal_id, Goal.user_id == user.id))
    if not goal:
        raise HTTPException(status_code=404, detail="Meta não encontrada")
    return goal


def sync_goal_status(goal: Goal) -> None:
    if goal.status == "archived":
        return
    goal.status = "completed" if goal.current_amount >= goal.target_amount else "active"


def create_goal(db: Session, user: User, payload: GoalCreate) -> Goal:
    goal = Goal(user_id=user.id, **payload.model_dump())
    sync_goal_status(goal)
    db.add(goal)
    db.flush()
    return goal


def update_goal(db: Session, user: User, goal_id: UUID, payload: GoalUpdate) -> Goal:
    goal = owned_goal(db, user, goal_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(goal, key, value)
    sync_goal_status(goal)
    db.flush()
    return goal


def archive_goal(db: Session, user: User, goal_id: UUID) -> Goal:
    goal = owned_goal(db, user, goal_id)
    goal.status = "archived"
    db.flush()
    return goal
