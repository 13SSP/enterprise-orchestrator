"""
Unit tests for Calendar Event Models
"""

import pytest
import sys
from pathlib import Path

src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from event_models import CalendarEvent


def test_valid_calendar_event():
    event = CalendarEvent(
        id="evt-101",
        title="Architecture Sync",
        start_time="2026-10-14T10:00:00Z",
        end_time="2026-10-14T11:00:00Z",
        organizer_id="bob_ops",
        attendee_ids=["priya_sharma", "alex_chen"],
        room_id="room-nebula-4"
    )
    assert event.id == "evt-101"
    assert event.title == "Architecture Sync"
    assert len(event.attendee_ids) == 2


def test_end_before_start_raises_validation_error():
    with pytest.raises(ValueError, match="end_time must be strictly after start_time"):
        CalendarEvent(
            id="evt-bad",
            title="Invalid Duration",
            start_time="2026-10-14T12:00:00Z",
            end_time="2026-10-14T11:00:00Z",
            organizer_id="bob_ops"
        )


def test_empty_title_raises_error():
    with pytest.raises(ValueError, match="title cannot be empty"):
        CalendarEvent(
            id="evt-bad-2",
            title="   ",
            start_time="2026-10-14T10:00:00Z",
            end_time="2026-10-14T11:00:00Z",
            organizer_id="bob_ops"
        )
