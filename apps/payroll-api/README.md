# cortex.ai - Payroll API Service
Runs on fixed port `8002`.

## Role-Restricted Endpoints
- `GET /health`: Health status.
- `GET /openapi.json`: OpenAPI spec.
- `GET /api/v1/salaries`: Full salary rolls (requires `finance_officer` or `admin`).
- `GET /api/v1/salaries/{employee_id}`: Single salary record (finance, admin, or self).
- `POST /api/v1/salaries/adjust`: Adjust employee salary compensation.
