from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class MealPlanCreateSchema(BaseModel):
    plan_date: date
    breakfast: str = Field(min_length=1)
    lunch: str = Field(min_length=1)
    dinner: str = Field(min_length=1)
    snacks: str | None = None


class MealPlanUpdateSchema(BaseModel):
    plan_date: date | None = None
    breakfast: str | None = Field(default=None, min_length=1)
    lunch: str | None = Field(default=None, min_length=1)
    dinner: str | None = Field(default=None, min_length=1)
    snacks: str | None = None


class MealPlanOutSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plan_date: date
    breakfast: str
    lunch: str
    dinner: str
    snacks: str | None
    created_at: datetime
    updated_at: datetime
