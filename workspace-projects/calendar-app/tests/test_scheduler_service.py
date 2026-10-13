"""
Unit tests for Calendar Scheduling Service & Collision Engine
"""

import pytest
import sys
from pathlib import Path

src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from event_models import CalendarEvent
from scheduler_service import CalendarSchedulerService, BookingConflictError


def test_schedule_event_and_retrieve():
    svc = CalendarSchedulerService()
    evt = CalendarEvent(
        id="evt-201",
        title="Sprint Planning",
        start_time="2026-10-15T09:00:00Z",
        end_time="2026-10-15T10:00:00Z",
        organizer_id="bob_ops",
        attendee_ids=["alex_chen"]
    )
    saved = svc.schedule_event(evt)
    assert saved.id == "evt-201"
    assert len(svc.list_events(user_id="bob_ops")) == 1


def test_user_scheduling_conflict_raises_error():
    svc = CalendarSchedulerService()
    evt1 = CalendarEvent(
        id="evt-202",
        title="Design Review",
        start_time="2026-10-15T14:00:00Z",
        end_time="2026-10-15T15:00:00Z",
        organizer_id="priya_sharma",
        attendee_ids=["alex_chen"]
    )
    svc.schedule_event(evt1)

    # Overlapping meeting for alex_chen
    evt2 = CalendarEvent(
        id="evt-203",
        title="1-on-1 Catchup",
        start_time="2026-10-15T14:30:00Z",
        end_time="2026-10-15T15:30:00Z",
        organizer_id="bob_ops",
        attendee_ids=["alex_chen"]
    )
    with pytest.raises(BookingConflictError, match="Design Review"):
        svc.schedule_event(evt2)


def test_room_scheduling_conflict_raises_error():
    svc = CalendarSchedulerService()
    evt1 = CalendarEvent(
        id="evt-204",
        title="All Hands",
        start_time="2026-10-16T11:00:00Z",
        end_time="2026-10-16T12:00:00Z",
        organizer_id="alice_hr",
        attendee_ids=[],
        room_id="room-aurora"
    )
    svc.schedule_event(evt1)

    # Different people, same room at same time
    evt2 = CalendarEvent(
        id="evt-205",
        title="Budget Meeting",
        start_time="2026-10-16T11:15:00Z",
        end_time="2026-10-16T11:45:00Z",
        organizer_id="charlie_fin",
        attendee_ids=[],
        room_id="room-aurora"
    )
    with pytest.raises(BookingConflictError, match="All Hands"):
        svc.schedule_event(evt2)
