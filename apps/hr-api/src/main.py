"""
cortex.ai - HR API Service (Port 8001)
Provides endpoints for departments, employees, leave balances, and leave records.
"""

import sys
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel

# Add project root to path
root_dir = Path(__file__).resolve().parent.parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from database.firestore_client import db
from database.models import Department, Employee, LeaveBalance, LeaveRecord

app = FastAPI(
    title="cortex.ai HR API",
    description="Domain microservice for human resources, personnel records, and leave management.",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json"
)

class LeaveApplicationRequest(BaseModel):
    employee_id: str
    leave_type: str = "ANNUAL_PTO"
    start_date: str
    end_date: str
    days_count: int
    reason: str

@app.get("/health", tags=["System"])
def health_check():
    return {"status": "healthy", "service": "hr-api", "port": 8001}

@app.get("/api/v1/departments", response_model=List[Department], tags=["Departments"])
def list_departments():
    docs = db.collection("departments").stream()
    return [Department(**d.to_dict()) for d in docs]

@app.get("/api/v1/departments/{department_id}", response_model=Department, tags=["Departments"])
def get_department(department_id: str):
    doc = db.collection("departments").document(department_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Department not found")
    return Department(**doc.to_dict())

@app.get("/api/v1/employees", response_model=List[Employee], tags=["Employees"])
def list_employees(department_id: Optional[str] = None):
    if department_id:
        docs = db.collection("employees").where("department_id", "==", department_id).stream()
    else:
        docs = db.collection("employees").stream()
    return [Employee(**d.to_dict()) for d in docs]

@app.get("/api/v1/employees/{employee_id}", response_model=Employee, tags=["Employees"])
def get_employee(employee_id: str):
    doc = db.collection("employees").document(employee_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Employee not found")
    return Employee(**doc.to_dict())

@app.get("/api/v1/leaves/balances/{employee_id}", response_model=LeaveBalance, tags=["Leaves"])
def get_leave_balance(employee_id: str):
    doc = db.collection("leave_balances").document(f"bal-{employee_id}").get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Leave balance not found for employee")
    return LeaveBalance(**doc.to_dict())

@app.get("/api/v1/leaves/records", response_model=List[LeaveRecord], tags=["Leaves"])
def list_leave_records(employee_id: Optional[str] = None):
    if employee_id:
        docs = db.collection("leave_records").where("employee_id", "==", employee_id).stream()
    else:
        docs = db.collection("leave_records").stream()
    return [LeaveRecord(**d.to_dict()) for d in docs]

@app.post("/api/v1/leaves/requests", response_model=LeaveRecord, tags=["Leaves"])
def submit_leave_request(req: LeaveApplicationRequest):
    import uuid
    from datetime import datetime
    leave_id = f"leave-{str(uuid.uuid4())[:8]}"
    record = LeaveRecord(
        leave_id=leave_id,
        employee_id=req.employee_id,
        leave_type=req.leave_type,
        start_date=req.start_date,
        end_date=req.end_date,
        days_count=req.days_count,
        reason=req.reason,
        status="PENDING",
        approved_by=None,
        applied_at=datetime.utcnow().isoformat()
    )
    db.collection("leave_records").document(leave_id).set(record.model_dump())
    return record

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
