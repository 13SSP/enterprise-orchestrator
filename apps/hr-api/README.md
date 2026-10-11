# cortex.ai - HR API Service
Runs on fixed port `8001`.

## Endpoints
- `GET /health`: Health status.
- `GET /openapi.json`: OpenAPI 3.0 specification.
- `GET /api/v1/departments`: List all departments.
- `GET /api/v1/employees`: List employees (supports `?department_id=`).
- `GET /api/v1/employees/{id}`: Detailed employee profile.
- `GET /api/v1/leaves/balances/{id}`: Look up employee PTO balances.
- `POST /api/v1/leaves/requests`: Submit a leave request.

## Local Execution
```bash
uvicorn src.main:app --port 8001
```
