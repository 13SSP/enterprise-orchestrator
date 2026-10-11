"""
cortex.ai - Expense Claims API Service (Port 8004)
Manages employee reimbursement claims and Document AI receipt extraction.
"""

import sys
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

root_dir = Path(__file__).resolve().parent.parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from database.firestore_client import db
from database.models import ExpenseClaim

app = FastAPI(
    title="cortex.ai Expense API",
    description="Microservice managing corporate expenses, travel reimbursements, and Document AI receipt parsing.",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json"
)

class SubmitClaimRequest(BaseModel):
    employee_id: str
    department_id: str = "dept-eng"
    amount: float
    currency: str = "USD"
    category: str = "TRAVEL"
    merchant: str
    description: str
    receipt_url: Optional[str] = None

class ReceiptParseRequest(BaseModel):
    receipt_image_base64: Optional[str] = None
    receipt_filename: str = "receipt.pdf"

class ReceiptParseResponse(BaseModel):
    merchant: str
    amount: float
    currency: str
    category: str
    tax_amount: float
    date: str
    confidence_score: float

@app.get("/health", tags=["System"])
def health_check():
    return {"status": "healthy", "service": "expense-api", "port": 8004}

@app.get("/api/v1/expenses/claims", response_model=List[ExpenseClaim], tags=["Expenses"])
def list_claims(employee_id: Optional[str] = None):
    col = db.collection("expense_claims")
    if employee_id:
        docs = col.where("employee_id", "==", employee_id).stream()
    else:
        docs = col.stream()
    return [ExpenseClaim(**d.to_dict()) for d in docs]

@app.get("/api/v1/expenses/claims/{claim_id}", response_model=ExpenseClaim, tags=["Expenses"])
def get_claim(claim_id: str):
    doc = db.collection("expense_claims").document(claim_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Expense claim not found")
    return ExpenseClaim(**doc.to_dict())

@app.post("/api/v1/expenses/claims", response_model=ExpenseClaim, tags=["Expenses"])
def submit_claim(req: SubmitClaimRequest):
    import random
    claim_id = f"EXP-2026-{random.randint(100, 999)}"
    now = datetime.utcnow().isoformat()
    claim = ExpenseClaim(
        claim_id=claim_id,
        employee_id=req.employee_id,
        department_id=req.department_id,
        amount=req.amount,
        currency=req.currency,
        category=req.category,
        merchant=req.merchant,
        description=req.description,
        receipt_url=req.receipt_url,
        status="PENDING_APPROVAL",
        approver_id=None,
        submitted_at=now,
        payout_date=None
    )
    db.collection("expense_claims").document(claim_id).set(claim.model_dump())
    return claim

@app.post("/api/v1/expenses/receipts/parse", response_model=ReceiptParseResponse, tags=["Document AI"])
def parse_receipt_document_ai(req: ReceiptParseRequest):
    """
    Parses receipt image or PDF via Google Cloud Document AI expense parser.
    Works in offline stub mode for local development.
    """
    # Deterministic Document AI entity extraction stub
    fname = req.receipt_filename.lower()
    if "delta" in fname or "flight" in fname:
        return ReceiptParseResponse(
            merchant="Delta Airlines",
            amount=250.0,
            currency="USD",
            category="TRAVEL",
            tax_amount=22.50,
            date="2026-10-05",
            confidence_score=0.98
        )
    elif "hotel" in fname or "marriott" in fname:
        return ReceiptParseResponse(
            merchant="Marriott Hotels",
            amount=380.0,
            currency="USD",
            category="TRAVEL",
            tax_amount=38.00,
            date="2026-10-06",
            confidence_score=0.96
        )
    return ReceiptParseResponse(
        merchant="Office Depot / Tech Supplies",
        amount=89.50,
        currency="USD",
        category="HARDWARE",
        tax_amount=7.16,
        date=datetime.utcnow().strftime("%Y-%m-%d"),
        confidence_score=0.92
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8004, reload=True)
