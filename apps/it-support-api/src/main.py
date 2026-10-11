"""
cortex.ai - IT Support API Service (Port 8003)
Provides Jira ticket management, triage, and IT support incident operations.
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
from database.models import JiraTicket

app = FastAPI(
    title="cortex.ai IT Support API",
    description="Microservice managing Jira issue tracking, incident triage, and infrastructure tickets.",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json"
)

class CreateTicketRequest(BaseModel):
    title: str
    description: str
    issue_type: str = "TASK"
    priority: str = "MEDIUM"
    reporter_id: str
    assignee_id: Optional[str] = None
    department_id: str = "dept-eng"
    components: List[str] = []
    labels: List[str] = []

class UpdateStatusRequest(BaseModel):
    status: str

@app.get("/health", tags=["System"])
def health_check():
    return {"status": "healthy", "service": "it-support-api", "port": 8003}

@app.get("/api/v1/jira/tickets", response_model=List[JiraTicket], tags=["Jira"])
def list_tickets(
    status: Optional[str] = None,
    assignee_id: Optional[str] = None
):
    col = db.collection("jira_tickets")
    if status and assignee_id:
        docs = col.where("status", "==", status).where("assignee_id", "==", assignee_id).stream()
    elif status:
        docs = col.where("status", "==", status).stream()
    elif assignee_id:
        docs = col.where("assignee_id", "==", assignee_id).stream()
    else:
        docs = col.stream()
    return [JiraTicket(**d.to_dict()) for d in docs]

@app.get("/api/v1/jira/tickets/{ticket_key}", response_model=JiraTicket, tags=["Jira"])
def get_ticket(ticket_key: str):
    doc = db.collection("jira_tickets").document(ticket_key).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail=f"Jira ticket '{ticket_key}' not found")
    return JiraTicket(**doc.to_dict())

@app.post("/api/v1/jira/tickets", response_model=JiraTicket, tags=["Jira"])
def create_ticket(req: CreateTicketRequest):
    import random
    ticket_num = random.randint(300, 999)
    ticket_key = f"IT-{ticket_num}"
    now = datetime.utcnow().isoformat()
    ticket = JiraTicket(
        ticket_key=ticket_key,
        title=req.title,
        description=req.description,
        issue_type=req.issue_type,
        priority=req.priority,
        status="OPEN",
        reporter_id=req.reporter_id,
        assignee_id=req.assignee_id,
        department_id=req.department_id,
        components=req.components,
        labels=req.labels,
        created_at=now,
        updated_at=now
    )
    db.collection("jira_tickets").document(ticket_key).set(ticket.model_dump())
    return ticket

@app.patch("/api/v1/jira/tickets/{ticket_key}/status", response_model=JiraTicket, tags=["Jira"])
def update_ticket_status(ticket_key: str, req: UpdateStatusRequest):
    ref = db.collection("jira_tickets").document(ticket_key)
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Ticket not found")
    data = doc.to_dict()
    data["status"] = req.status
    data["updated_at"] = datetime.utcnow().isoformat()
    ref.set(data)
    return JiraTicket(**data)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8003, reload=True)
