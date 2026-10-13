"""
Calendar Event Models & Data Validation
"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, model_validator


class CalendarEvent(BaseModel):
    id: str = Field(..., description="Unique event identifier")
    title: str = Field(..., description="Meeting title or subject")
    start_time: str = Field(..., description="Start ISO-8601 UTC timestamp")
    end_time: str = Field(..., description="End ISO-8601 UTC timestamp")
    organizer_id: str = Field(..., description="Employee ID of organizer")
    attendee_ids: List[str] = Field(default_factory=list, description="List of participant IDs")
    room_id: Optional[str] = Field(None, description="Optional conference room ID")
    status: str = Field("confirmed", description="Event status: confirmed, cancelled")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    @model_validator(mode="after")
    def validate_time_boundaries(self):
        if not self.title.strip():
            raise ValueError("Event title cannot be empty")
        try:
            start_dt = datetime.fromisoformat(self.start_time.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(self.end_time.replace("Z", "+00:00"))
        except Exception as e:
            raise ValueError(f"Invalid ISO datetime format: {e}")
        if end_dt <= start_dt:
            raise ValueError("Event end_time must be strictly after start_time")
        return self


class TimeSlot(BaseModel):
    start_time: str
    end_time: str
    is_available: bool = True
