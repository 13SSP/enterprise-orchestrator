import importlib.util
from pathlib import Path
from fastapi.testclient import TestClient

src_file = Path(__file__).resolve().parent.parent / "src" / "main.py"
spec = importlib.util.spec_from_file_location("expense_api_main", src_file)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
app = mod.app

client = TestClient(app)

def test_expense_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["service"] == "expense-api"

def test_get_claim():
    res = client.get("/api/v1/expenses/claims/EXP-2026-88")
    assert res.status_code == 200
    assert res.json()["amount"] == 250.0

def test_document_ai_receipt_parser():
    res = client.post("/api/v1/expenses/receipts/parse", json={"receipt_filename": "delta_ticket.pdf"})
    assert res.status_code == 200
    assert res.json()["merchant"] == "Delta Airlines"
    assert res.json()["amount"] == 250.0
