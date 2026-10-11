"""
cortex.ai - Enterprise M365 Integration Microservice (Port 8005)
Provides Microsoft Office & Outlook capabilities:
- Outlook Email Drafts (Drafts only! Sending requires explicit human approval)
- Calendar Availability Queries
- Word (.docx) document generation
- PowerPoint (.pptx) presentation generation
"""

import os
import sys
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

src_dir = Path(__file__).resolve().parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from word_generator import generate_docx_document
from ppt_generator import generate_pptx_deck

app = FastAPI(
    title="cortex.ai M365 Connector API",
    description="Enterprise connector for Outlook drafts, calendar scheduling, Word (.docx) & PowerPoint (.pptx) document generation.",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json"
)

CONNECTOR_MODE = os.getenv("M365_CONNECTOR_MODE", "MOCK").upper()
STORAGE_DIR = Path(__file__).resolve().parent.parent / "generated_files"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# In-memory drafts store for MOCK mode
DRAFTS_STORE: Dict[str, Dict[str, Any]] = {}

class EmailDraftRequest(BaseModel):
    recipient_email: str = Field(..., description="Target email, e.g. manager@company.internal")
    subject: str = Field(..., description="Email subject line")
    body: str = Field(..., description="Drafted message body")
    cc: Optional[List[str]] = Field(default_factory=list)
    sender_id: Optional[str] = "current_user"

class EmailSendRequest(BaseModel):
    draft_id: str
    confirmed_by_user: bool = False

class CalendarQueryRequest(BaseModel):
    user_email: str
    target_date: Optional[str] = "today"

class WordDocRequest(BaseModel):
    title: str
    subtitle: Optional[str] = None
    author: Optional[str] = "cortex.ai Productivity Agent"
    sections: List[Dict[str, Any]] = Field(
        ...,
        description="List of sections with 'heading', 'content', and optional 'bullets'"
    )

class PowerPointRequest(BaseModel):
    deck_title: str
    deck_subtitle: Optional[str] = "cortex.ai Multi-Agent Intelligence"
    slides: List[Dict[str, Any]] = Field(
        ...,
        description="List of slide objects with 'title', 'bullets', and optional 'speaker_notes'"
    )

@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "service": "m365-connector",
        "port": 8005,
        "mode": CONNECTOR_MODE
    }

# ----------------- OUTLOOK -----------------

@app.post("/api/v1/outlook/drafts", tags=["Outlook"])
def create_email_draft(req: EmailDraftRequest):
    draft_id = f"draft-{str(uuid.uuid4())[:8]}"
    created_at = datetime.utcnow().isoformat()
    draft = {
        "draft_id": draft_id,
        "recipient_email": req.recipient_email,
        "cc": req.cc,
        "subject": req.subject,
        "body": req.body,
        "sender_id": req.sender_id,
        "created_at": created_at,
        "status": "DRAFT_SAVED",
        "requires_human_approval_to_send": True
    }
    DRAFTS_STORE[draft_id] = draft
    return draft

@app.post("/api/v1/outlook/send", tags=["Outlook"])
def send_email(req: EmailSendRequest):
    """Sending emails strictly requires human approval."""
    if not req.confirmed_by_user:
        return {
            "status": "PENDING_APPROVAL",
            "message": "Human approval required: Outgoing corporate emails cannot be sent autonomously.",
            "draft_id": req.draft_id
        }
    draft = DRAFTS_STORE.get(req.draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Email draft not found")
    draft["status"] = "SENT_SUCCESSFULLY"
    return draft

@app.get("/api/v1/outlook/calendar", tags=["Outlook"])
def get_calendar_availability(user_email: str, date: Optional[str] = None):
    # Deterministic availability calendar for demo
    return {
        "user_email": user_email,
        "date": date or datetime.utcnow().strftime("%Y-%m-%d"),
        "timezone": "UTC",
        "busy_slots": [
            {"start": "09:00", "end": "10:00", "title": "Platform Architecture Sync"},
            {"start": "14:00", "end": "15:00", "title": "1:1 with VP"}
        ],
        "available_slots": [
            {"start": "10:00", "end": "12:00"},
            {"start": "15:00", "end": "17:00"}
        ]
    }

# ----------------- WORD (.docx) -----------------

@app.post("/api/v1/word/generate", tags=["Word"])
def generate_word_document(req: WordDocRequest):
    doc_id = f"doc_{str(uuid.uuid4())[:8]}.docx"
    file_path = STORAGE_DIR / doc_id
    generate_docx_document(
        title=req.title,
        subtitle=req.subtitle,
        sections=req.sections,
        output_path=file_path,
        author=req.author
    )
    download_url = f"/api/v1/files/download/{doc_id}"
    return {
        "status": "DOCUMENT_CREATED",
        "file_name": doc_id,
        "file_type": "docx",
        "download_url": download_url,
        "local_path": str(file_path),
        "created_at": datetime.utcnow().isoformat()
    }

# ----------------- POWERPOINT (.pptx) -----------------

@app.post("/api/v1/powerpoint/generate", tags=["PowerPoint"])
def generate_powerpoint_presentation(req: PowerPointRequest):
    deck_id = f"presentation_{str(uuid.uuid4())[:8]}.pptx"
    file_path = STORAGE_DIR / deck_id
    generate_pptx_deck(
        deck_title=req.deck_title,
        deck_subtitle=req.deck_subtitle,
        slides=req.slides,
        output_path=file_path
    )
    download_url = f"/api/v1/files/download/{deck_id}"
    return {
        "status": "PRESENTATION_CREATED",
        "file_name": deck_id,
        "file_type": "pptx",
        "slide_count": len(req.slides) + 1,
        "download_url": download_url,
        "local_path": str(file_path),
        "created_at": datetime.utcnow().isoformat()
    }

# ----------------- FILE DOWNLOADS -----------------

@app.get("/api/v1/files/download/{file_name}", tags=["Files"])
def download_generated_file(file_name: str):
    file_path = STORAGE_DIR / file_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Requested generated file not found")
    media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document" if file_name.endswith(".docx") else "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    return FileResponse(path=file_path, filename=file_name, media_type=media_type)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8005, reload=True)
