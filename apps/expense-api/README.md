# cortex.ai - Expense API Service
Runs on fixed port `8004`.

## Endpoints
- `GET /health`: Health status.
- `GET /openapi.json`: OpenAPI spec.
- `GET /api/v1/expenses/claims`: List claims (`?employee_id=`).
- `GET /api/v1/expenses/claims/{claim_id}`: Single claim record.
- `POST /api/v1/expenses/claims`: File an expense reimbursement.
- `POST /api/v1/expenses/receipts/parse`: Document AI automated receipt information extraction.
