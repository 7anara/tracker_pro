from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tracker_pro.api.auth import get_current_user
from tracker_pro.database.db import get_db
from tracker_pro.database.models import MealPlan, User
from tracker_pro.schemas.meal_schema import MealPlanCreateSchema, MealPlanOutSchema, MealPlanUpdateSchema


meal_router = APIRouter(prefix="/meal-plans", tags=["Meal Plans"])


def _owned_plan(db: Session, user_id: int, plan_id: int) -> MealPlan:
    plan = db.scalar(select(MealPlan).where(MealPlan.id == plan_id, MealPlan.user_id == user_id))
    if plan is None:
        raise HTTPException(status_code=404, detail="Meal plan not found")
    return plan


@meal_router.post("/", response_model=MealPlanOutSchema, status_code=status.HTTP_201_CREATED)
def create_meal_plan(payload: MealPlanCreateSchema, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    plan = MealPlan(user_id=current_user.id, **payload.model_dump())
    db.add(plan)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A meal plan already exists for this date")
    db.refresh(plan)
    return plan


@meal_router.get("/", response_model=list[MealPlanOutSchema])
def get_meal_plans(
    plan_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(MealPlan).where(MealPlan.user_id == current_user.id)
    if plan_date is not None:
        query = query.where(MealPlan.plan_date == plan_date)
    return list(db.scalars(query.order_by(MealPlan.plan_date.desc())).all())


@meal_router.get("/{plan_id}", response_model=MealPlanOutSchema)
def get_meal_plan(plan_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return _owned_plan(db, current_user.id, plan_id)


@meal_router.put("/{plan_id}", response_model=MealPlanOutSchema)
def update_meal_plan(plan_id: int, payload: MealPlanUpdateSchema, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    plan = _owned_plan(db, current_user.id, plan_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(plan, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A meal plan already exists for this date")
    db.refresh(plan)
    return plan


@meal_router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meal_plan(plan_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db.delete(_owned_plan(db, current_user.id, plan_id))
    db.commit()
