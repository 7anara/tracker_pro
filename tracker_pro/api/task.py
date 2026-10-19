from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from tracker_pro.api.auth import get_current_user
from tracker_pro.config import settings
from tracker_pro.database.db import get_db
from tracker_pro.database.models import Task, User
from tracker_pro.schemas.task_schema import TaskCreateSchema, TaskOutSchema, TaskUpdateSchema


task_router = APIRouter(prefix="/tasks", tags=["Tasks"])


def _owned_task(db: Session, user_id: int, task_id: int) -> Task:
    task = db.scalar(select(Task).where(Task.id == task_id, Task.user_id == user_id))
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@task_router.post("/", response_model=TaskOutSchema, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreateSchema, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = Task(user_id=current_user.id, **payload.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@task_router.get("/", response_model=list[TaskOutSchema])
def get_tasks(
    task_date: date | None = Query(default=None, alias="date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Task).where(Task.user_id == current_user.id)
    if task_date is not None:
        local_zone = ZoneInfo(settings.app_timezone)
        start = datetime.combine(task_date, time.min, tzinfo=local_zone).astimezone(timezone.utc)
        end = (datetime.combine(task_date + timedelta(days=1), time.min, tzinfo=local_zone)).astimezone(timezone.utc)
        query = query.where(Task.scheduled_at >= start, Task.scheduled_at < end)
    return list(db.scalars(query.order_by(Task.scheduled_at, Task.id)).all())


@task_router.get("/{task_id}", response_model=TaskOutSchema)
def get_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return _owned_task(db, current_user.id, task_id)


@task_router.put("/{task_id}", response_model=TaskOutSchema)
def update_task(task_id: int, payload: TaskUpdateSchema, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = _owned_task(db, current_user.id, task_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, key, value)
    db.commit()
    db.refresh(task)
    return task


@task_router.post("/{task_id}/complete/", response_model=TaskOutSchema)
def complete_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = _owned_task(db, current_user.id, task_id)
    task.is_completed = True
    db.commit()
    db.refresh(task)
    return task


@task_router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db.delete(_owned_task(db, current_user.id, task_id))
    db.commit()
