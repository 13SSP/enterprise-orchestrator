import importlib.util
from pathlib import Path
from fastapi.testclient import TestClient

src_file = Path(__file__).resolve().parent.parent / "src" / "main.py"
spec = importlib.util.spec_from_file_location("payroll_api_main", src_file)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
app = mod.app

client = TestClient(app)

def test_payroll_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["service"] == "payroll-api"

def test_get_salary_authorized_finance():
    res = client.get("/api/v1/salaries/bob_ops", headers={"X-Caller-Role": "finance_officer"})
    assert res.status_code == 200
    assert res.json()["base_salary"] == 165000.0

def test_get_salary_unauthorized_denied():
    res = client.get("/api/v1/salaries/bob_ops", headers={"X-Caller-Role": "hr_manager", "X-Caller-ID": "alice_hr"})
    assert res.status_code == 403
