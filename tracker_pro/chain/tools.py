import json
from datetime import date, datetime, time, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from langchain_core.tools import tool
from pydantic import BaseModel, Field
from sqlalchemy import select

from tracker_pro.config import settings
from tracker_pro.database.db import SessionLocal
from tracker_pro.database.models import MealPlan, Task


class TaskCreateInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    scheduled_at: Optional[datetime] = None


class TaskListInput(BaseModel):
    task_date: Optional[date] = None
    include_completed: bool = True


class TaskIdInput(BaseModel):
    task_id: int = Field(gt=0)


class TaskUpdateInput(TaskIdInput):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    scheduled_at: Optional[datetime] = None


class MealPlanCreateInput(BaseModel):
    plan_date: date
    breakfast: str = Field(min_length=1)
    lunch: str = Field(min_length=1)
    dinner: str = Field(min_length=1)
    snacks: Optional[str] = None


class MealPlanDateInput(BaseModel):
    plan_date: date


class MealPlanIdInput(BaseModel):
    plan_id: int = Field(gt=0)


class MealPlanUpdateInput(MealPlanIdInput):
    plan_date: Optional[date] = None
    breakfast: Optional[str] = Field(default=None, min_length=1)
    lunch: Optional[str] = Field(default=None, min_length=1)
    dinner: Optional[str] = Field(default=None, min_length=1)
    snacks: Optional[str] = None


def _json(value):
    return json.dumps(value, ensure_ascii=False, default=str)


def _task_data(task: Task):
    return {"id": task.id, "title": task.title, "description": task.description,
            "scheduled_at": task.scheduled_at, "is_completed": task.is_completed}


def _meal_data(plan: MealPlan):
    return {"id": plan.id, "plan_date": plan.plan_date, "breakfast": plan.breakfast,
            "lunch": plan.lunch, "dinner": plan.dinner, "snacks": plan.snacks}


def build_user_tools(user_id: int):
    @tool("create_task", args_schema=TaskCreateInput)
    def create_task(title: str, description: Optional[str] = None, scheduled_at: Optional[datetime] = None) -> str:
        """Create a task for the authenticated user. Include scheduled_at as an ISO datetime when known."""
        if scheduled_at and scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=ZoneInfo(settings.app_timezone)).astimezone(timezone.utc)
        with SessionLocal.begin() as db:
            task = Task(user_id=user_id, title=title, description=description, scheduled_at=scheduled_at)
            db.add(task)
            db.flush()
            result = _task_data(task)
        return _json(result)

    @tool("get_tasks", args_schema=TaskListInput)
    def get_tasks(task_date: Optional[date] = None, include_completed: bool = True) -> str:
        """List this user's tasks, optionally for a local calendar date."""
        with SessionLocal() as db:
            query = select(Task).where(Task.user_id == user_id)
            if task_date:
                zone = ZoneInfo(settings.app_timezone)
                start = datetime.combine(task_date, time.min, tzinfo=zone).astimezone(timezone.utc)
                end = datetime.combine(task_date.fromordinal(task_date.toordinal() + 1), time.min, tzinfo=zone).astimezone(timezone.utc)
                query = query.where(Task.scheduled_at >= start, Task.scheduled_at < end)
            if not include_completed:
                query = query.where(Task.is_completed.is_(False))
            tasks = db.scalars(query.order_by(Task.scheduled_at, Task.id)).all()
            return _json([_task_data(task) for task in tasks])

    @tool("update_task", args_schema=TaskUpdateInput)
    def update_task(task_id: int, title: Optional[str] = None, description: Optional[str] = None,
                    scheduled_at: Optional[datetime] = None) -> str:
        """Update a task by its ID. First list tasks if the user did not specify an ID."""
        updates = {"title": title, "description": description, "scheduled_at": scheduled_at}
        updates = {key: value for key, value in updates.items() if value is not None}
        if scheduled_at and scheduled_at.tzinfo is None:
            updates["scheduled_at"] = scheduled_at.replace(tzinfo=ZoneInfo(settings.app_timezone)).astimezone(timezone.utc)
        with SessionLocal.begin() as db:
            task = db.scalar(select(Task).where(Task.id == task_id, Task.user_id == user_id))
            if task is None:
                return "Task not found"
            for key, value in updates.items():
                setattr(task, key, value)
            db.flush()
            result = _task_data(task)
        return _json(result)

    @tool("complete_task", args_schema=TaskIdInput)
    def complete_task(task_id: int) -> str:
        """Mark one of this user's tasks as completed by its ID."""
        with SessionLocal.begin() as db:
            task = db.scalar(select(Task).where(Task.id == task_id, Task.user_id == user_id))
            if task is None:
                return "Task not found"
            task.is_completed = True
            db.flush()
            result = _task_data(task)
        return _json(result)

    @tool("delete_task", args_schema=TaskIdInput)
    def delete_task(task_id: int) -> str:
        """Delete one of this user's tasks by its ID."""
        with SessionLocal.begin() as db:
            task = db.scalar(select(Task).where(Task.id == task_id, Task.user_id == user_id))
            if task is None:
                return "Task not found"
            db.delete(task)
        return "Task deleted"

    @tool("create_meal_plan", args_schema=MealPlanCreateInput)
    def create_meal_plan(plan_date: date, breakfast: str, lunch: str, dinner: str,
                         snacks: Optional[str] = None) -> str:
        """Save a meal plan for a date. Only call when the user asks to save/create a plan."""
        with SessionLocal.begin() as db:
            existing = db.scalar(select(MealPlan).where(MealPlan.user_id == user_id, MealPlan.plan_date == plan_date))
            if existing:
                return "A meal plan already exists for this date; update it if requested."
            plan = MealPlan(user_id=user_id, plan_date=plan_date, breakfast=breakfast,
                            lunch=lunch, dinner=dinner, snacks=snacks)
            db.add(plan)
            db.flush()
            result = _meal_data(plan)
        return _json(result)

    @tool("get_meal_plan", args_schema=MealPlanDateInput)
    def get_meal_plan(plan_date: date) -> str:
        """Retrieve this user's meal plan for a date."""
        with SessionLocal() as db:
            plan = db.scalar(select(MealPlan).where(MealPlan.user_id == user_id, MealPlan.plan_date == plan_date))
            return _json(_meal_data(plan) if plan else {"message": "No meal plan for this date"})

    @tool("update_meal_plan", args_schema=MealPlanUpdateInput)
    def update_meal_plan(plan_id: int, plan_date: Optional[date] = None, breakfast: Optional[str] = None,
                         lunch: Optional[str] = None, dinner: Optional[str] = None,
                         snacks: Optional[str] = None) -> str:
        """Update this user's meal plan by plan ID."""
        updates = {"plan_date": plan_date, "breakfast": breakfast, "lunch": lunch, "dinner": dinner, "snacks": snacks}
        updates = {key: value for key, value in updates.items() if value is not None}
        with SessionLocal.begin() as db:
            plan = db.scalar(select(MealPlan).where(MealPlan.id == plan_id, MealPlan.user_id == user_id))
            if plan is None:
                return "Meal plan not found"
            for key, value in updates.items():
                setattr(plan, key, value)
            db.flush()
            result = _meal_data(plan)
        return _json(result)

    @tool("delete_meal_plan", args_schema=MealPlanIdInput)
    def delete_meal_plan(plan_id: int) -> str:
        """Delete this user's meal plan by plan ID."""
        with SessionLocal.begin() as db:
            plan = db.scalar(select(MealPlan).where(MealPlan.id == plan_id, MealPlan.user_id == user_id))
            if plan is None:
                return "Meal plan not found"
            db.delete(plan)
        return "Meal plan deleted"

    return [create_task, get_tasks, update_task, complete_task, delete_task,
            create_meal_plan, get_meal_plan, update_meal_plan, delete_meal_plan]
