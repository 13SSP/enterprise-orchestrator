"""
Calendar Conflict Detection and Scheduling Logic
"""

from typing import Dict, List, Optional
from datetime import datetime
from event_models import CalendarEvent


class BookingConflictError(Exception):
    """Raised when an event conflicts with an existing booking."""
    pass


class CalendarSchedulerService:
    def __init__(self):
        self._events: Dict[str, CalendarEvent] = {}

    def schedule_event(self, event: CalendarEvent) -> CalendarEvent:
        conflicts = self.check_conflicts(
            start_time=event.start_time,
            end_time=event.end_time,
            user_ids=[event.organizer_id] + event.attendee_ids,
            room_id=event.room_id
        )
        if conflicts:
            conflicting_titles = [c.title for c in conflicts]
            raise BookingConflictError(
                f"Scheduling conflict detected with existing event(s): {', '.join(conflicting_titles)}"
            )
        self._events[event.id] = event
        return event

    def get_event(self, event_id: str) -> Optional[CalendarEvent]:
        return self._events.get(event_id)

    def list_events(self, user_id: Optional[str] = None, room_id: Optional[str] = None) -> List[CalendarEvent]:
        results = []
        for e in self._events.values():
            if e.status != "confirmed":
                continue
            if user_id and (user_id != e.organizer_id and user_id not in e.attendee_ids):
                continue
            if room_id and e.room_id != room_id:
                continue
            results.append(e)
        return results

    def check_conflicts(
        self,
        start_time: str,
        end_time: str,
        user_ids: List[str],
        room_id: Optional[str] = None
    ) -> List[CalendarEvent]:
        s1 = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        e1 = datetime.fromisoformat(end_time.replace("Z", "+00:00"))

        conflicts = []
        for ev in self._events.values():
            if ev.status != "confirmed":
                continue
            s2 = datetime.fromisoformat(ev.start_time.replace("Z", "+00:00"))
            e2 = datetime.fromisoformat(ev.end_time.replace("Z", "+00:00"))

            # Overlap check: s1 < e2 and s2 < e1
            if s1 < e2 and s2 < e1:
                # Check user conflict
                overlap_users = set(user_ids) & set([ev.organizer_id] + ev.attendee_ids)
                if overlap_users:
                    conflicts.append(ev)
                    continue
                # Check room conflict
                if room_id and ev.room_id == room_id:
                    conflicts.append(ev)
        return conflicts

    def cancel_event(self, event_id: str) -> bool:
        if event_id in self._events:
            self._events[event_id].status = "cancelled"
            return True
        return False
