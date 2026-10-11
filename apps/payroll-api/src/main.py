"""
cortex.ai - Payroll API Service (Port 8002)
Protected domain microservice for sensitive employee compensation, salaries, and disbursement accounts.
"""

import sys
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel

root_dir = Path(__file__).resolve().parent.parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from database.firestore_client import db
from database.models import Salary

app = FastAPI(
    title="cortex.ai Payroll API",
    description="Confidential payroll & compensation management microservice. Restricted to finance officers and administrative roles.",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json"
)

class SalaryAdjustmentRequest(BaseModel):
    employee_id: str
    new_base_salary: float
    bonus_target_pct: Optional[float] = None
    reason: str

@app.get("/health", tags=["System"])
def health_check():
    return {"status": "healthy", "service": "payroll-api", "port": 8002}

@app.get("/api/v1/salaries", response_model=List[Salary], tags=["Payroll"])
def list_all_salaries(
    x_caller_role: Optional[str] = Header(None, alias="X-Caller-Role"),
    x_caller_id: Optional[str] = Header(None, alias="X-Caller-ID")
):
    """Restricted to admin and finance_officer roles."""
    if x_caller_role and x_caller_role not in ["admin", "finance_officer"]:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Only finance officers or platform admins may inspect enterprise salaries."
        )
    docs = db.collection("salaries").stream()
    return [Salary(**d.to_dict()) for d in docs]

@app.get("/api/v1/salaries/{employee_id}", response_model=Salary, tags=["Payroll"])
def get_employee_salary(
    employee_id: str,
    x_caller_role: Optional[str] = Header(None, alias="X-Caller-Role"),
    x_caller_id: Optional[str] = Header(None, alias="X-Caller-ID")
):
    """Accessible by finance_officer, admin, or the employee themselves."""
    if x_caller_role and x_caller_role not in ["admin", "finance_officer"]:
        if x_caller_id and x_caller_id != employee_id:
            raise HTTPException(
                status_code=403,
                detail=f"Access Denied: Caller '{x_caller_id}' cannot view salary for '{employee_id}'."
            )
    doc = db.collection("salaries").document(f"sal-{employee_id}").get()
    if not doc.exists:
        # Fallback check by employee_id field
        docs = list(db.collection("salaries").where("employee_id", "==", employee_id).stream())
        if docs:
            return Salary(**docs[0].to_dict())
        raise HTTPException(status_code=404, detail="Salary record not found for employee")
    return Salary(**doc.to_dict())

@app.post("/api/v1/salaries/adjust", response_model=Salary, tags=["Payroll"])
def adjust_salary(
    req: SalaryAdjustmentRequest,
    x_caller_role: Optional[str] = Header(None, alias="X-Caller-Role")
):
    if x_caller_role and x_caller_role not in ["admin", "finance_officer"]:
        raise HTTPException(status_code=403, detail="Forbidden: Unauthorized to adjust employee salaries.")
    
    sal_id = f"sal-{req.employee_id}"
    ref = db.collection("salaries").document(sal_id)
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Salary record does not exist")
    data = doc.to_dict()
    data["base_salary"] = req.new_base_salary
    if req.bonus_target_pct is not None:
        data["bonus_target_pct"] = req.bonus_target_pct
    ref.set(data)
    return Salary(**data)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
