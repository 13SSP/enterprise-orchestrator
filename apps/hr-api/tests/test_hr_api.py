import importlib.util
from pathlib import Path
from fastapi.testclient import TestClient

src_file = Path(__file__).resolve().parent.parent / "src" / "main.py"
spec = importlib.util.spec_from_file_location("hr_api_main", src_file)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
app = mod.app

client = TestClient(app)

def test_hr_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["service"] == "hr-api"

def test_list_departments():
    res = client.get("/api/v1/departments")
    assert res.status_code == 200
    assert len(res.json()) >= 3

def test_get_employee():
    res = client.get("/api/v1/employees/bob_ops")
    assert res.status_code == 200
    assert res.json()["first_name"] == "Bob"

def test_get_leave_balance():
    res = client.get("/api/v1/leaves/balances/bob_ops")
    assert res.status_code == 200
    assert res.json()["annual_pto_total"] == 20
