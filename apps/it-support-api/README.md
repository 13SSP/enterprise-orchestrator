# cortex.ai - IT Support API Service
Runs on fixed port `8003`.

## Endpoints
- `GET /health`: Health status.
- `GET /openapi.json`: OpenAPI spec.
- `GET /api/v1/jira/tickets`: List Jira tickets (`?status=`, `?assignee_id=`).
- `GET /api/v1/jira/tickets/{ticket_key}`: Single Jira issue details.
- `POST /api/v1/jira/tickets`: File an incident or task ticket.
- `PATCH /api/v1/jira/tickets/{ticket_key}/status`: Update ticket lifecycle status.
