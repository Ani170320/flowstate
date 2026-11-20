import uuid
from datetime import date
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

from app.schemas.auth import UserProfileResponse


class CalendarEventResponse(BaseModel):
    """Normalized event payload for Calendar rendering (representing either a Task or Project deadline/schedule)."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    entity_type: str  # "task" | "project"
    entity_id: uuid.UUID
    title: str
    key: Optional[str] = None
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    date: date
    status: str
    priority: Optional[str] = None
    color: Optional[str] = None
    project_id: Optional[uuid.UUID] = None
    project_name: Optional[str] = None
    assignee: Optional[UserProfileResponse] = None
    is_overdue: bool = False


class CalendarUpcomingItemResponse(BaseModel):
    """Urgent deadline countdown item."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    entity_type: str  # "task" | "project"
    key: Optional[str] = None
    title: str
    project_name: Optional[str] = None
    due_date: date
    days_remaining: int
    is_overdue: bool
    priority: str
    status: str
    assignee: Optional[UserProfileResponse] = None


class CalendarDayResponse(BaseModel):
    """Daily bucket of events."""
    date: date
    events_count: int
    events: List[CalendarEventResponse]


class CalendarViewResponse(BaseModel):
    """Comprehensive calendar window response supporting month, week, and day views."""
    view: str  # "month" | "week" | "day"
    start_date: date
    end_date: date
    reference_date: date
    total_events: int
    events: List[CalendarEventResponse]
    overdue_tasks_count: int
    days: Optional[List[CalendarDayResponse]] = None
