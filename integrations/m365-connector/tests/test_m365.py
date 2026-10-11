import importlib.util
from pathlib import Path
from fastapi.testclient import TestClient

src_file = Path(__file__).resolve().parent.parent / "src" / "main.py"
spec = importlib.util.spec_from_file_location("m365_api_main", src_file)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
app = mod.app

client = TestClient(app)

def test_m365_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["service"] == "m365-connector"

def test_outlook_draft_creation():
    payload = {
        "recipient_email": "manager@company.internal",
        "subject": "PTO Notification",
        "body": "Hi, I have 14 PTO days remaining and plan to take next Monday off."
    }
    res = client.post("/api/v1/outlook/drafts", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "DRAFT_SAVED"
    assert data["requires_human_approval_to_send"] is True

def test_word_doc_generation():
    payload = {
        "title": "Quarterly Operations Review",
        "sections": [
            {"heading": "Executive Summary", "content": "All systems operating within SLA."},
            {"heading": "Key Metrics", "bullets": ["Uptime: 99.99%", "P99 Latency: 120ms"]}
        ]
    }
    res = client.post("/api/v1/word/generate", json=payload)
    assert res.status_code == 200
    assert res.json()["status"] == "DOCUMENT_CREATED"
    assert res.json()["file_type"] == "docx"

def test_powerpoint_deck_generation():
    payload = {
        "deck_title": "IT Ticket Incident Report",
        "slides": [
            {"title": "Open Critical Tickets", "bullets": ["SEC-204: Port 22 remediation", "PROJ-102: Latency spike"]},
            {"title": "Resolution Timelines", "bullets": ["Target SLA: 4 hours", "Status: In Progress"]}
        ]
    }
    res = client.post("/api/v1/powerpoint/generate", json=payload)
    assert res.status_code == 200
    assert res.json()["status"] == "PRESENTATION_CREATED"
    assert res.json()["slide_count"] == 3
