from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator

from tracker_pro.config import settings


def _normalize_scheduled_at(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=ZoneInfo(settings.app_timezone))
    return value.astimezone(timezone.utc)


class TaskCreateSchema(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    scheduled_at: datetime | None = None

    @field_validator("scheduled_at")
    @classmethod
    def normalize_scheduled_at(cls, value: datetime | None) -> datetime | None:
        return _normalize_scheduled_at(value)


class TaskUpdateSchema(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    scheduled_at: datetime | None = None
    is_completed: bool | None = None

    @field_validator("scheduled_at")
    @classmethod
    def normalize_scheduled_at(cls, value: datetime | None) -> datetime | None:
        return _normalize_scheduled_at(value)


class TaskOutSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    scheduled_at: datetime | None
    is_completed: bool
    created_at: datetime
    updated_at: datetime


class TaskDateFilter(BaseModel):
    date: date
