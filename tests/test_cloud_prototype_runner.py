"""
Unit and integration tests for Cloud Prototype Runner and Headless System Utils:
- Verification of FastAPI execution endpoints on cloud prototypes
- In-memory/cloud sandbox Pytest execution
- Real ZIP bundle creation and file streaming
- Graceful behavior of headless file explorer / picker in Google Cloud Run
- Strict visibility isolation for prototypes
"""

import sys
from pathlib import Path
import io
import zipfile
import pytest
from fastapi.testclient import TestClient

root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "cortex-ai" / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import main
app = main.app
from workspaces.manager import workspace_manager
from system_utils import pick_folder_dialog, open_folder_in_os


client = TestClient(app)


def test_headless_system_utils_safe_in_cloud(monkeypatch):
    """Verifies pick_folder_dialog and open_folder_in_os are safe in headless cloud environments."""
    monkeypatch.setenv("CI", "true")
    res = pick_folder_dialog()
    assert isinstance(res, str)
    assert res == ""

    # open_folder_in_os handles path safely without throwing
    res_open = open_folder_in_os("workspace-projects/test-folder")
    assert "test-folder" in res_open


def test_cloud_prototype_creation_and_file_persistence():
    """Verifies prototypes store complete file_contents for cloud execution."""
    ws = workspace_manager.create_workspace({
        "name": "Cloud Calculator Pod",
        "description": "SDD Pod for Cloud Calculator",
        "workspace_type": "sdd",
        "sdd_config": {
            "local_space_path": "workspace-projects/cloud-calc",
            "git_action": "init"
        }
    }, current_user_id="bob_ops")
    ws_id = ws["workspace_id"]

    proto_res = client.post(
        f"/api/pods/{ws_id}/prototypes/build?persona=bob_ops",
        json={
            "name": "Division Engine",
            "description": "Division Calculator with Pydantic validation and decimal precision",
            "storage_mode": "local",
            "tech_stack": "Python 3.11 / FastAPI / Pytest",
            "task_id": "TSK-CALC-01"
        }
    )
    assert proto_res.status_code == 200
    data = proto_res.json()
    proto = data["prototype"]
    proto_id = proto["prototype_id"]

    assert proto["name"] == "Division Engine"
    assert "main.py" in proto["file_contents"]
    assert "test_main.py" in proto["file_contents"]
    assert "spec.md" in proto["file_contents"]
    assert "README.md" in proto["file_contents"]


def test_cloud_prototype_live_execution():
    """Verifies POST /api/pods/{ws_id}/prototypes/{proto_id}/execute executes real code in cloud sandbox."""
    ws = workspace_manager.create_workspace({
        "name": "Math Pod",
        "workspace_type": "sdd",
        "sdd_config": {"local_space_path": "workspace-projects/math-pod"}
    }, current_user_id="bob_ops")
    ws_id = ws["workspace_id"]

    build_res = client.post(
        f"/api/pods/{ws_id}/prototypes/build?persona=bob_ops",
        json={
            "name": "Division Service",
            "description": "Division calculator microservice",
            "storage_mode": "local"
        }
    )
    proto_id = build_res.json()["prototype"]["prototype_id"]

    # 1. Execute GET / (info endpoint)
    exec_root = client.post(
        f"/api/pods/{ws_id}/prototypes/{proto_id}/execute?persona=bob_ops",
        json={"method": "GET", "endpoint": "/"}
    )
    assert exec_root.status_code == 200
    root_data = exec_root.json()
    assert root_data["status"] == "success"
    assert root_data["http_status"] == 200
    assert root_data["response"]["status"] == "online"
    assert root_data["cloud_host"] == "Google Cloud Run"
    assert root_data["latency_ms"] >= 0

    # 2. Execute POST /calculate with valid parameters
    exec_calc = client.post(
        f"/api/pods/{ws_id}/prototypes/{proto_id}/execute?persona=bob_ops",
        json={
            "method": "POST",
            "endpoint": "/calculate",
            "payload": {"numerator": 100.0, "denominator": 4.0, "precision": 2}
        }
    )
    assert exec_calc.status_code == 200
    calc_data = exec_calc.json()
    assert calc_data["status"] == "success", f"Calc data was: {calc_data}"
    assert calc_data["http_status"] == 200
    assert calc_data["response"]["quotient"] == 25.0

    # 3. Execute POST /calculate with Division by Zero - handles validation error
    exec_err = client.post(
        f"/api/pods/{ws_id}/prototypes/{proto_id}/execute?persona=bob_ops",
        json={
            "method": "POST",
            "endpoint": "/calculate",
            "payload": {"numerator": 10.0, "denominator": 0.0}
        }
    )
    assert exec_err.status_code == 200
    err_data = exec_err.json()
    # Pydantic validator rejects denominator=0 with HTTP 422 (or 400)
    assert err_data["http_status"] in (400, 422)


def test_cloud_prototype_pytest_runner():
    """Verifies POST /api/pods/{ws_id}/prototypes/{proto_id}/test runs pytest in cloud sandbox."""
    ws = workspace_manager.create_workspace({
        "name": "Pytest Test Pod",
        "workspace_type": "sdd"
    }, current_user_id="bob_ops")
    ws_id = ws["workspace_id"]

    build_res = client.post(
        f"/api/pods/{ws_id}/prototypes/build?persona=bob_ops",
        json={
            "name": "Auth App",
            "description": "User authentication and registration service",
            "storage_mode": "local"
        }
    )
    proto_id = build_res.json()["prototype"]["prototype_id"]

    test_res = client.post(f"/api/pods/{ws_id}/prototypes/{proto_id}/test?persona=bob_ops")
    assert test_res.status_code == 200
    test_data = test_res.json()
    assert test_data["status"] == "passed"
    assert test_data["passed"] is True
    assert test_data["returncode"] == 0
    assert "passed" in test_data["output"]


def test_cloud_prototype_zip_download_and_files():
    """Verifies GET download zip and GET files return full source code."""
    ws = workspace_manager.create_workspace({
        "name": "Zip Test Pod",
        "workspace_type": "sdd"
    }, current_user_id="bob_ops")
    ws_id = ws["workspace_id"]

    build_res = client.post(
        f"/api/pods/{ws_id}/prototypes/build?persona=bob_ops",
        json={
            "name": "E-Commerce App",
            "description": "Orders and cart service",
            "storage_mode": "local"
        }
    )
    proto_id = build_res.json()["prototype"]["prototype_id"]

    # 1. Test GET /files
    files_res = client.get(f"/api/pods/{ws_id}/prototypes/{proto_id}/files?persona=bob_ops")
    assert files_res.status_code == 200
    f_data = files_res.json()
    assert "main.py" in f_data["files"]
    assert "CommerceManager" in f_data["files"]["main.py"]

    # 2. Test GET /download (ZIP archive)
    dl_res = client.get(f"/api/pods/{ws_id}/prototypes/{proto_id}/download?persona=bob_ops")
    assert dl_res.status_code == 200
    assert dl_res.headers["content-type"] == "application/zip"
    assert "attachment" in dl_res.headers["content-disposition"]

    # Unpack and verify zip contents
    buf = io.BytesIO(dl_res.content)
    with zipfile.ZipFile(buf, "r") as zf:
        names = zf.namelist()
        assert "main.py" in names
        assert "test_main.py" in names
        main_text = zf.read("main.py").decode("utf-8")
        assert "CommerceManager" in main_text


def test_cloud_prototype_visibility_permission_enforcement():
    """Verifies local prototypes in cloud cannot be executed or downloaded by other users."""
    ws = workspace_manager.create_workspace({
        "name": "Isolated Pod",
        "workspace_type": "sdd"
    }, current_user_id="bob_ops")
    ws_id = ws["workspace_id"]

    build_res = client.post(
        f"/api/pods/{ws_id}/prototypes/build?persona=bob_ops",
        json={
            "name": "Bob Secret Tool",
            "description": "Private devops tool",
            "storage_mode": "local"
        }
    )
    proto_id = build_res.json()["prototype"]["prototype_id"]

    # Alice (different user) cannot execute Bob's local prototype
    alice_exec = client.post(
        f"/api/pods/{ws_id}/prototypes/{proto_id}/execute?persona=alice_hr",
        json={"method": "GET", "endpoint": "/"}
    )
    assert alice_exec.status_code in (400, 403)

    # Alice cannot download Bob's local prototype
    alice_dl = client.get(f"/api/pods/{ws_id}/prototypes/{proto_id}/download?persona=alice_hr")
    assert alice_dl.status_code in (400, 403)
