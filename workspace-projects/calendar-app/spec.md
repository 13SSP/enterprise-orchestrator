# Enterprise Calendar Service Specification (v1.0)
## REQ-01: Calendar Event Model & Invariants
- Event title, start_time, end_time, organizer_id, attendee_ids, optional room_id.
- Invariant: end_time must be strictly after start_time.

## REQ-02: Conflict Detection & Room Booking Engine
- Detect overlapping intervals for organizers, attendees, and conference rooms.
- Raise BookingConflictError on collisions.

## REQ-03: REST API Calendar Controller
- Expose CRUD /api/v1/events and /api/v1/availability.
