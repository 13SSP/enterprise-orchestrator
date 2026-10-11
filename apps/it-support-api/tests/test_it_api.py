import importlib.util
from pathlib import Path
from fastapi.testclient import TestClient

src_file = Path(__file__).resolve().parent.parent / "src" / "main.py"
spec = importlib.util.spec_from_file_location("it_api_main", src_file)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
app = mod.app

client = TestClient(app)

def test_it_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["service"] == "it-support-api"

def test_get_ticket():
    res = client.get("/api/v1/jira/tickets/PROJ-102")
    assert res.status_code == 200
    assert res.json()["priority"] == "HIGH"

def test_list_tickets():
    res = client.get("/api/v1/jira/tickets")
    assert res.status_code == 200
    assert len(res.json()) >= 6
