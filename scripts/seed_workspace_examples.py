"""
Seed runner for Workspaces:
1. One General Chat Workspace ("Engineering Team Discussion")
2. One Spec-Driven Development (SDD) Workspace ("Enterprise Calendar Service")
3. Scaffolds local repo for Calendar Service at workspace-projects/calendar-app
"""

import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(root_dir / "cortex-ai" / "backend"))

from database.firestore_client import db

def seed_calendar_local_repo(repo_path: Path):
    repo_path.mkdir(parents=True, exist_ok=True)
    src_dir = repo_path / "src"
    src_dir.mkdir(exist_ok=True)
    tests_dir = repo_path / "tests"
    tests_dir.mkdir(exist_ok=True)

    (src_dir / "__init__.py").write_text("", encoding="utf-8")
    (tests_dir / "__init__.py").write_text("", encoding="utf-8")

    # 1. Spec & Principles docs
    (repo_path / "spec.md").write_text("""# Enterprise Calendar Service Specification (v1.0)
## REQ-01: Calendar Event Model & Invariants
- Event title, start_time, end_time, organizer_id, attendee_ids, optional room_id.
- Invariant: end_time must be strictly after start_time.

## REQ-02: Conflict Detection & Room Booking Engine
- Detect overlapping intervals for organizers, attendees, and conference rooms.
- Raise BookingConflictError on collisions.

## REQ-03: REST API Calendar Controller
- Expose CRUD /api/v1/events and /api/v1/availability.
""", encoding="utf-8")

    (repo_path / "principles.md").write_text("""# SDD Principles - Enterprise Calendar Service
1. Stateless Event Scheduling & Interval Collision Engine
2. Pydantic v2 Schema Validation for All ISO Datetimes
3. Deterministic Timezone Normalization to UTC
4. Automated Pytest Coverage for Booking Invariants
""", encoding="utf-8")

    (repo_path / "README.md").write_text("""# Enterprise Calendar Service
High-performance spec-driven calendar and meeting scheduling service.
Developed via Cortex.ai Spec-Driven Development (SDD).
""", encoding="utf-8")

    # 2. Code: event_models.py
    (src_dir / "event_models.py").write_text('''"""
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
''', encoding="utf-8")

    # 3. Tests: test_event_models.py
    (tests_dir / "test_event_models.py").write_text('''"""
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
''', encoding="utf-8")

    # 4. Code: scheduler_service.py
    (src_dir / "scheduler_service.py").write_text('''"""
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
''', encoding="utf-8")

    # 5. Tests: test_scheduler_service.py
    (tests_dir / "test_scheduler_service.py").write_text('''"""
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
''', encoding="utf-8")

    # 6. Initialize git repository
    try:
        git_dir = repo_path / ".git"
        if not git_dir.exists():
            subprocess.run(["git", "init"], cwd=str(repo_path), check=True, capture_output=True)
            subprocess.run(["git", "add", "."], cwd=str(repo_path), check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "chore(sdd): initialize calendar-app repository"], cwd=str(repo_path), capture_output=True)
            subprocess.run(["git", "commit", "--allow-empty", "-m", "feat(TSK-101): implement CalendarEvent model and time boundary validations"], cwd=str(repo_path), capture_output=True)
            subprocess.run(["git", "commit", "--allow-empty", "-m", "feat(TSK-102): implement scheduler service and room collision engine"], cwd=str(repo_path), capture_output=True)
    except Exception as e:
        print(f"Git init notice: {e}")

    # 7. Run pytest to verify all tests pass
    env = dict(**dict(subprocess.os.environ))
    env["PYTHONPATH"] = f"{str(src_dir)};{str(repo_path)}"
    res = subprocess.run([sys.executable, "-m", "pytest", "tests", "-v"], cwd=str(repo_path), env=env, capture_output=True, text=True)
    print("Calendar local test execution:\n", res.stdout)
    assert res.returncode == 0, f"Tests failed: {res.stdout}\n{res.stderr}"

    # Get short commit hash
    rev_p = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(repo_path), capture_output=True, text=True)
    return rev_p.stdout.strip() if rev_p.returncode == 0 else "c4a179b"


def seed_workspaces():
    print("Seeding General Chat & Calendar App SDD workspaces...")

    # 1. Normal General Chat Workspace
    ws_chat = {
        "workspace_id": "ws-eng-watercooler",
        "id": "ws-eng-watercooler",
        "name": "Engineering Team Discussion",
        "description": "General open discussion workspace for engineering topics, architectural brainstorming, and team announcements.",
        "workspace_type": "chat",
        "visibility": "public",
        "owner_id": "bob_ops",
        "owner_name": "Bob Martinez",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "system_instructions": "You are the Cortex Engineering copilot. Support engineering team discussions on architecture, microservices, and development practices.",
        "members": [
            {"user_id": "bob_ops", "user_name": "Bob Martinez", "role": "owner", "joined_at": datetime.utcnow().isoformat()},
            {"user_id": "priya_sharma", "user_name": "Priya Sharma", "role": "contributor", "joined_at": datetime.utcnow().isoformat()},
            {"user_id": "alex_chen", "user_name": "Alex Chen", "role": "contributor", "joined_at": datetime.utcnow().isoformat()},
            {"user_id": "charlie_fin", "user_name": "Charlie Zhao", "role": "contributor", "joined_at": datetime.utcnow().isoformat()},
            {"user_id": "alice_hr", "user_name": "Alice Henderson", "role": "contributor", "joined_at": datetime.utcnow().isoformat()}
        ],
        "documents": [
            {"id": "doc-eng-guidelines", "title": "Engineering Standards & Best Practices v2", "url": "/docs/engineering-standards.md"},
            {"id": "doc-api-standards", "title": "Cloud Microservices & API Security Standards", "url": "/docs/api-standards.md"}
        ],
        "prompts": [
            {"title": "Architecture Review Checklist", "content": "Review this design against microservices best practices."}
        ],
        "chat_messages": [
            {
                "id": "msg-001",
                "sender_id": "priya_sharma",
                "sender_name": "Priya Sharma",
                "role": "user",
                "content": "Hey team, are we standardizing on FastAPI and Pydantic v2 for our upcoming Q4 microservices?",
                "citations": [],
                "timestamp": datetime.utcnow().isoformat()
            },
            {
                "id": "msg-002",
                "sender_id": "cortex-ai",
                "sender_name": "Engineering Copilot",
                "role": "assistant",
                "content": "Yes! All backend microservices are standardized on Python 3.11 with FastAPI and Pydantic v2 schemas for strict boundary validation and auto-generated OpenAPI contracts.",
                "citations": ["Engineering Standards & Best Practices v2"],
                "timestamp": datetime.utcnow().isoformat()
            },
            {
                "id": "msg-003",
                "sender_id": "bob_ops",
                "sender_name": "Bob Martinez",
                "role": "user",
                "content": "Sounds great. What is our required test coverage and pytest standard before promoting to staging?",
                "citations": [],
                "timestamp": datetime.utcnow().isoformat()
            },
            {
                "id": "msg-004",
                "sender_id": "cortex-ai",
                "sender_name": "Engineering Copilot",
                "role": "assistant",
                "content": "Understood! According to Section 4.2 of our Engineering Standards & Best Practices v2, automated test coverage is strictly enforced via CI pipelines, targeting minimum 85% branch coverage on domain models and conflict detection logic. Pytest suites must execute with zero external network dependencies.",
                "citations": ["Engineering Standards & Best Practices v2"],
                "timestamp": datetime.utcnow().isoformat()
            },
            {
                "id": "msg-005",
                "sender_id": "alex_chen",
                "sender_name": "Alex Chen",
                "role": "user",
                "content": "What is our policy regarding logging sensitive employee PII or tokens in our service logs?",
                "citations": [],
                "timestamp": datetime.utcnow().isoformat()
            },
            {
                "id": "msg-006",
                "sender_id": "cortex-ai",
                "sender_name": "Engineering Copilot",
                "role": "assistant",
                "content": "Per Cloud Microservices & API Security Standards: Never log plain PII (SSNs, compensation details, bank credentials) or auth tokens. All stdout log streams must format as structured JSON for Google Cloud Logging, and sensitive parameters must pass through Model Armor masking filters.",
                "citations": ["Cloud Microservices & API Security Standards"],
                "timestamp": datetime.utcnow().isoformat()
            }
        ],
        "sdd_config": None,
        "spec": None,
        "plan": None,
        "tasks": [],
        "execution_logs": []
    }

    db.collection("workspaces").document(ws_chat["workspace_id"]).set(ws_chat)
    print("  + Created General Chat workspace: Engineering Team Discussion")

    # 2. SDD Calendar App Workspace
    repo_path = root_dir / "workspace-projects" / "calendar-app"
    commit_hash = seed_calendar_local_repo(repo_path)

    ws_sdd = {
        "workspace_id": "ws-calendar-app",
        "id": "ws-calendar-app",
        "name": "Enterprise Calendar Service",
        "description": "Spec-driven development workspace for a high-performance team calendar, event scheduling, and room booking service.",
        "workspace_type": "sdd",
        "visibility": "private",
        "owner_id": "bob_ops",
        "owner_name": "Bob Martinez",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "system_instructions": "You are the specialized AI architect for Enterprise Calendar Service. Ground all responses in the approved specification and scheduling invariants.",
        "members": [
            {"user_id": "bob_ops", "user_name": "Bob Martinez", "role": "owner", "joined_at": datetime.utcnow().isoformat()},
            {"user_id": "priya_sharma", "user_name": "Priya Sharma", "role": "contributor", "joined_at": datetime.utcnow().isoformat()},
            {"user_id": "alex_chen", "user_name": "Alex Chen", "role": "contributor", "joined_at": datetime.utcnow().isoformat()}
        ],
        "sdd_config": {
            "local_space_path": str(repo_path).replace("\\", "/"),
            "git_action": "init",
            "git_status": "active",
            "commit_hash": commit_hash,
            "tech_stack": "Python 3.11 / FastAPI / Pydantic v2 / Pytest",
            "active_spec_version": "v1.0",
            "approval_status": "approved",
            "architecture_principles": [
                "Stateless Event Scheduling & Interval Collision Engine",
                "Pydantic v2 Schema Validation for All ISO Datetimes",
                "Deterministic Timezone Normalization to UTC",
                "Automated Pytest Coverage for Booking Invariants"
            ],
            "coding_standards": [
                "100% Strict Type Annotations conforming to PEP 8",
                "Immutable Datetime Models with Zero Side-Effects",
                "Async FastAPI Route Handlers with RFC-7807 Error Responses"
            ]
        },
        "spec": {
            "title": "Enterprise Calendar & Scheduling Specification",
            "version": "v1.0",
            "status": "approved",
            "raw_markdown": """# Enterprise Calendar & Scheduling Specification (v1.0)

## Overview
High-concurrency microservice managing calendar event scheduling, attendee coordination, and room collision prevention across corporate offices.

## REQ-01: Calendar Event Model & Invariants
- Event title, start_time, end_time, organizer_id, attendee_ids, and optional room_id.
- Invariant: end_time must be strictly greater than start_time.
- Acceptance Criteria: Given valid timestamps, model is instantiated; end_time <= start_time raises ValidationError.

## REQ-02: Conflict Detection & Room Booking Engine
- Detect overlapping time intervals for organizers, attendees, and conference rooms.
- Raise BookingConflictError on collisions.
- Acceptance Criteria: Double-booking the same person or room within overlapping intervals is rejected.

## REQ-03: REST API Calendar Controller
- Expose CRUD /api/v1/events and /api/v1/availability.
- Acceptance Criteria: Returns HTTP 200/201 on success, HTTP 409 Conflict on overlapping bookings.
""",
            "requirements": [
                {
                    "id": "REQ-01",
                    "title": "Calendar Event Model & Scheduling Validation",
                    "description": "Enforce data integrity, non-empty titles, and end_time > start_time validation.",
                    "acceptance_criteria": "Given valid timestamps, CalendarEvent instantiates successfully; reversed intervals raise ValueError."
                },
                {
                    "id": "REQ-02",
                    "title": "Conflict Detection & Availability Query Engine",
                    "description": "Interval intersection engine for attendees and conference rooms.",
                    "acceptance_criteria": "Overlapping bookings for user or room raise BookingConflictError."
                },
                {
                    "id": "REQ-03",
                    "title": "REST API Calendar Controller",
                    "description": "FastAPI router exposing /api/v1/events and /api/v1/availability.",
                    "acceptance_criteria": "Returns HTTP 201 Created on booking, HTTP 409 on schedule conflict."
                }
            ]
        },
        "plan": {
            "title": "Calendar Service Architecture & Contract Design",
            "version": "v1.0",
            "raw_markdown": """# Technical Architecture: Enterprise Calendar Service

## 1. System Pattern
Layered Clean Architecture:
- Domain Models: CalendarEvent, TimeSlot
- Core Service: CalendarSchedulerService with interval collision detection
- Controller: FastAPI APIRouter

## 2. API Contract
- GET /api/v1/events: Query scheduled events by user or room
- POST /api/v1/events: Create event with conflict check
- POST /api/v1/availability: Query free slots
""",
            "data_models": [
                {"name": "CalendarEvent", "fields": ["id: str", "title: str", "start_time: str", "end_time: str", "organizer_id: str", "attendee_ids: List[str]", "room_id: Optional[str]"]},
                {"name": "TimeSlot", "fields": ["start_time: str", "end_time: str", "is_available: bool"]}
            ],
            "api_endpoints": [
                {"path": "/api/v1/events", "method": "GET", "summary": "Query events by attendee or room"},
                {"path": "/api/v1/events", "method": "POST", "summary": "Schedule new meeting event"},
                {"path": "/api/v1/availability", "method": "POST", "summary": "Query free/busy slots"}
            ],
            "decisions": [
                "ADR-01: Timezone Normalization to UTC at API Boundary",
                "ADR-02: In-memory Interval Collision Tree for Microsecond Conflict Checks"
            ]
        },
        "tasks": [
            {
                "task_id": "TSK-101",
                "title": "Implement CalendarEvent Model & Invariants",
                "description": "Create Pydantic v2 entity with strict start < end validation",
                "linked_req_id": "REQ-01",
                "target_files": ["src/event_models.py"],
                "test_file": "tests/test_event_models.py",
                "status": "completed",
                "last_commit_hash": commit_hash,
                "last_test_output": "3 passed in 0.04s",
                "completed_at": datetime.utcnow().isoformat()
            },
            {
                "task_id": "TSK-102",
                "title": "Implement Conflict Detection Engine",
                "description": "Implement interval collision logic for users and conference rooms",
                "linked_req_id": "REQ-02",
                "target_files": ["src/scheduler_service.py"],
                "test_file": "tests/test_scheduler_service.py",
                "status": "completed",
                "last_commit_hash": commit_hash,
                "last_test_output": "3 passed in 0.05s",
                "completed_at": datetime.utcnow().isoformat()
            },
            {
                "task_id": "TSK-103",
                "title": "Implement FastAPI Calendar Router",
                "description": "Create FastAPI endpoints for events and availability",
                "linked_req_id": "REQ-03",
                "target_files": ["src/calendar_api.py"],
                "test_file": "tests/test_calendar_api.py",
                "status": "pending",
                "last_commit_hash": None,
                "last_test_output": None,
                "completed_at": None
            }
        ],
        "features": [
            {
                "feature_id": "feat-cal-01",
                "title": "Calendar Event Model & Scheduling Validation",
                "description": "Pydantic v2 data models enforcing strict ISO-8601 UTC timestamps, non-empty event titles, and mandatory end_time > start_time validation.",
                "creation_mode": "ai_generated",
                "active_version": "v1.1",
                "lifecycle_state": "approved",
                "source_doc_text": "Need data models with strict time boundaries and attendee list validation.",
                "acceptance_criteria": [
                    "Given valid ISO-8601 timestamps, CalendarEvent model instantiates successfully.",
                    "Given end_time <= start_time, raises ValueError('Event end_time must be strictly after start_time').",
                    "Given empty or whitespace title, raises ValueError('Event title cannot be empty')."
                ],
                "raw_markdown": "# Calendar Event Model & Invariants (v1.1)\n\n## Data Schema\n- `id: str` (UUID)\n- `title: str` (non-empty)\n- `start_time: str` (ISO UTC)\n- `end_time: str` (ISO UTC)\n- `organizer_id: str`\n- `attendee_ids: List[str]`\n- `room_id: Optional[str]`\n\n## Validation Invariants\n- `end_time` must be strictly after `start_time`.",
                "requirements": [
                    {
                        "id": "REQ-01",
                        "title": "Calendar Event Model & Invariants",
                        "description": "Enforce data integrity, non-empty titles, and end_time > start_time validation.",
                        "acceptance_criteria": "Given valid timestamps, CalendarEvent instantiates successfully; reversed intervals raise ValueError."
                    }
                ],
                "created_by": "bob_ops",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "versions": [
                    {"version": "v1.0", "lifecycle_state": "in_review", "updated_by": "alice_hr", "timestamp": "2026-10-14T09:00:00Z"},
                    {"version": "v1.1", "lifecycle_state": "approved", "updated_by": "bob_ops", "timestamp": "2026-10-14T10:00:00Z"}
                ]
            },
            {
                "feature_id": "feat-cal-02",
                "title": "Interval Collision & Room Conflict Engine",
                "description": "Microsecond interval intersection math (s1 < e2 and s2 < e1) detecting double-booking collisions for attendees and shared conference rooms.",
                "creation_mode": "requirement_doc",
                "active_version": "v1.0",
                "lifecycle_state": "approved",
                "source_doc_text": "# Collision Engine Requirements\n- Intersect intervals s1 < e2 and s2 < e1\n- Block double booking of attendees or rooms\n- Raise BookingConflictError",
                "acceptance_criteria": [
                    "Overlapping meetings for any attendee raises BookingConflictError with conflicting meeting titles.",
                    "Overlapping meetings for the same conference room raises BookingConflictError.",
                    "Non-overlapping intervals or cancelled meetings permit booking without conflict."
                ],
                "raw_markdown": "# Interval Collision & Room Booking Engine (v1.0)\n\n## Math Formula\nOverlap condition: `(start1 < end2) and (start2 < end1)`\n\n## Collision Behavior\n- Evaluates organizers, attendees, and room_id.\n- Excludes events where status == 'cancelled'.",
                "requirements": [
                    {
                        "id": "REQ-02",
                        "title": "Conflict Detection & Room Booking Engine",
                        "description": "Interval intersection engine for attendees and conference rooms.",
                        "acceptance_criteria": "Overlapping bookings for user or room raise BookingConflictError."
                    }
                ],
                "created_by": "priya_sharma",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "versions": [
                    {"version": "v1.0", "lifecycle_state": "approved", "updated_by": "bob_ops", "timestamp": "2026-10-15T11:00:00Z"}
                ]
            },
            {
                "feature_id": "feat-cal-03",
                "title": "REST API Calendar Controller & Availability Engine",
                "description": "FastAPI endpoints exposing /api/v1/events and /api/v1/availability with RFC-7807 problem details.",
                "creation_mode": "ai_generated",
                "active_version": "v1.0",
                "lifecycle_state": "in_review",
                "source_doc_text": "REST API router exposing CRUD calendar endpoints and availability queries.",
                "acceptance_criteria": [
                    "POST /api/v1/events returns HTTP 201 Created on valid booking.",
                    "POST /api/v1/events returns HTTP 409 Conflict with collision details on double booking.",
                    "POST /api/v1/availability returns available time slots for attendee list."
                ],
                "raw_markdown": "# REST API Calendar Controller (v1.0)\n\n## Endpoints\n- `GET /api/v1/events`: List events for user or room\n- `POST /api/v1/events`: Create event (checks collisions)\n- `POST /api/v1/availability`: Query free time slots",
                "requirements": [
                    {
                        "id": "REQ-03",
                        "title": "REST API Calendar Controller",
                        "description": "FastAPI router exposing /api/v1/events and /api/v1/availability.",
                        "acceptance_criteria": "Returns HTTP 201 Created on booking, HTTP 409 on schedule conflict."
                    }
                ],
                "created_by": "alex_chen",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "versions": [
                    {"version": "v1.0", "lifecycle_state": "in_review", "updated_by": "alex_chen", "timestamp": "2026-10-16T14:00:00Z"}
                ]
            }
        ],
        "prototypes": [
            {
                "prototype_id": "proto-calendar-app",
                "pod_id": "ws-calendar-app",
                "title": "Calendar Service Engine",
                "name": "Calendar Service Engine",
                "description": "Autonomous FastAPI microservice implementing event validation, room collision prevention, and interval overlap engine.",
                "feature_id": "feat-cal-02",
                "linked_feature_id": "feat-cal-02",
                "linked_spec_version": "v1.0",
                "storage_mode": "cloud",
                "local_path": str(repo_path).replace("\\", "/"),
                "tech_stack": "Python 3.11 / FastAPI / Pydantic v2 / Pytest",
                "creator_id": "bob_ops",
                "creator_name": "Bob Martinez",
                "status": "online",
                "cloud_hosted": True,
                "test_output": "6 passed in 0.21s - 100% acceptance criteria satisfied",
                "files": ["src/event_models.py", "src/scheduler_service.py", "tests/test_event_models.py", "tests/test_scheduler_service.py"],
                "created_at": datetime.utcnow().isoformat()
            }
        ],
        "documents": [],
        "prompts": [],
        "chat_messages": [
            {
                "id": "msg-cal-1",
                "sender_id": "priya_sharma",
                "sender_name": "Priya Sharma",
                "role": "user",
                "content": "What is the acceptance criteria for scheduling conflict detection?",
                "citations": [],
                "linked_feature_id": "feat-cal-02",
                "timestamp": datetime.utcnow().isoformat()
            },
            {
                "id": "msg-cal-2",
                "sender_id": "cortex-ai",
                "sender_name": "Calendar Copilot",
                "role": "assistant",
                "content": "According to **REQ-02: Conflict Detection & Room Booking Engine**, the system checks interval overlaps using the invariant formula `(start1 < end2 AND start2 < end1)`. If any attendee or the selected conference room already has a confirmed meeting during that window, a `BookingConflictError` is raised and the booking is rejected.\n\nKey Invariants:\n1. Double-booking any attendee across overlapping intervals is rejected.\n2. Room collisions are blocked regardless of meeting organizer.\n3. Cancelled events are excluded from collision evaluation.",
                "citations": ["REQ-02: Conflict Detection & Availability Query Engine", "Feature: Interval Collision & Room Conflict Engine (v1.0)"],
                "linked_feature_id": "feat-cal-02",
                "timestamp": datetime.utcnow().isoformat()
            },
            {
                "id": "msg-cal-3",
                "sender_id": "alex_chen",
                "sender_name": "Alex Chen",
                "role": "user",
                "content": "What validation happens if someone attempts to schedule an event where end_time is earlier than or equal to start_time?",
                "citations": [],
                "linked_feature_id": "feat-cal-01",
                "timestamp": datetime.utcnow().isoformat()
            },
            {
                "id": "msg-cal-4",
                "sender_id": "cortex-ai",
                "sender_name": "Calendar Copilot",
                "role": "assistant",
                "content": "Under **REQ-01: Calendar Event Model & Invariants** (enforced in `src/event_models.py` via Pydantic v2 `@model_validator`), `end_time` must be strictly greater than `start_time` in normalized UTC ISO-8601 format.\n\nIf `end_dt <= start_dt`, the model immediately raises `ValueError('Event end_time must be strictly after start_time')`. Zero-duration or negative-duration meetings are impossible at the domain model boundary.",
                "citations": ["REQ-01: Calendar Event Model & Invariants", "Feature: Calendar Event Model & Scheduling Validation (v1.1)"],
                "linked_feature_id": "feat-cal-01",
                "timestamp": datetime.utcnow().isoformat()
            },
            {
                "id": "msg-cal-5",
                "sender_id": "bob_ops",
                "sender_name": "Bob Martinez",
                "role": "user",
                "content": "What HTTP status code and error schema should our REST controller return when a room collision occurs?",
                "citations": [],
                "linked_feature_id": "feat-cal-03",
                "timestamp": datetime.utcnow().isoformat()
            },
            {
                "id": "msg-cal-6",
                "sender_id": "cortex-ai",
                "sender_name": "Calendar Copilot",
                "role": "assistant",
                "content": "Per **REQ-03: REST API Calendar Controller** and our ADR-02 guidelines:\n- **HTTP Status**: Returns `HTTP 409 Conflict`.\n- **Error Schema**: Complies with RFC-7807 Problem Details containing `error: 'BookingConflictError'`, the colliding `event_id`, and `conflicting_titles`.\n- Successful bookings return `HTTP 201 Created` with the persisted event payload.",
                "citations": ["REQ-03: REST API Calendar Controller", "Feature: REST API Calendar Controller & Availability Engine (v1.0)"],
                "linked_feature_id": "feat-cal-03",
                "timestamp": datetime.utcnow().isoformat()
            }
        ],
        "execution_logs": [
            {
                "task_id": "TSK-101",
                "commit_hash": commit_hash,
                "status": "completed",
                "timestamp": datetime.utcnow().isoformat(),
                "steps": [
                    {"msg": f"[GIT] Initialized repository at {repo_path}", "level": "info"},
                    {"msg": "[SDD AGENT] Grounded in Spec REQ-01: Calendar Event Model & Invariants", "level": "info"},
                    {"msg": "[CODEGEN] Generated src/event_models.py (35 lines)", "level": "info"},
                    {"msg": "[TESTGEN] Generated tests/test_event_models.py (45 lines)", "level": "info"},
                    {"msg": "[VERIFY] Running pytest tests/test_event_models.py: 3 passed", "level": "success"},
                    {"msg": f"[GIT COMMIT] {commit_hash} - feat(TSK-101): implement CalendarEvent model and time boundary validations", "level": "success"}
                ]
            },
            {
                "task_id": "TSK-102",
                "commit_hash": commit_hash,
                "status": "completed",
                "timestamp": datetime.utcnow().isoformat(),
                "steps": [
                    {"msg": "[SDD AGENT] Grounded in Spec REQ-02: Conflict Detection & Room Booking Engine", "level": "info"},
                    {"msg": "[CODEGEN] Generated src/scheduler_service.py (78 lines)", "level": "info"},
                    {"msg": "[TESTGEN] Generated tests/test_scheduler_service.py (62 lines)", "level": "info"},
                    {"msg": "[VERIFY] Running pytest tests/test_scheduler_service.py: 3 passed", "level": "success"},
                    {"msg": f"[GIT COMMIT] {commit_hash} - feat(TSK-102): implement scheduler service and room collision engine", "level": "success"}
                ]
            }
        ]
    }

    db.collection("workspaces").document(ws_sdd["workspace_id"]).set(ws_sdd)
    print("  + Created SDD workspace: Enterprise Calendar Service (ws-calendar-app)")
    print("Seeding complete!")

if __name__ == "__main__":
    seed_workspaces()
