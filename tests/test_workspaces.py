"""
Unit and Integration Tests for Workspace Hub and Autonomous SDD Engine
Verifies dynamic creation, Firestore persistence, Spec/Plan/Task management,
Chat grounded retrieval, and autonomous code execution.
"""

import sys
import shutil
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir / "cortex-ai" / "backend"))

import main
from workspaces.manager import workspace_manager


@pytest.fixture
def client():
    return TestClient(main.app)


def test_list_public_workspaces(client):
    res = client.get("/api/workspaces?filter=public")
    assert res.status_code == 200
    data = res.json()
    assert "workspaces" in data
    for ws in data["workspaces"]:
        assert ws["visibility"] == "public"


def test_list_shared_workspaces(client):
    res = client.get("/api/workspaces?filter=shared&persona=bob_ops")
    assert res.status_code == 200
    data = res.json()
    assert "workspaces" in data
    for ws in data["workspaces"]:
        assert ws["visibility"] == "private"


def test_sdd_workspace_strictly_private(client):
    payload = {
        "name": "Live SDD Service",
        "description": "Testing strict private SDD rule",
        "workspace_type": "sdd",
        "visibility": "public",  # Attempt to make it public
        "initial_prompt": "Build an enterprise customer order management system",
        "invited_employee_ids": ["alex_chen"]
    }
    res = client.post("/api/workspaces?persona=bob_ops", json=payload)
    assert res.status_code == 200
    ws = res.json()["workspace"]
    ws_id = ws["workspace_id"]
    try:
        assert ws["workspace_type"] == "sdd"
        assert ws["visibility"] == "private"  # Forced to private!
        assert ws["owner_id"] == "bob_ops"
        assert len(ws["spec"]["requirements"]) > 0
        assert len(ws["plan"]["data_models"]) > 0
        assert len(ws["tasks"]) > 0
    finally:
        client.delete(f"/api/workspaces/{ws_id}?persona=bob_ops")


def test_general_chat_public_and_private(client):
    # Public Chat Workspace
    res_pub = client.post("/api/workspaces?persona=bob_ops", json={
        "name": "Public Watercooler",
        "description": "Open company discussion",
        "workspace_type": "chat",
        "visibility": "public"
    })
    assert res_pub.status_code == 200
    pub_id = res_pub.json()["workspace"]["workspace_id"]
    assert res_pub.json()["workspace"]["visibility"] == "public"

    # Private Chat Workspace
    res_priv = client.post("/api/workspaces?persona=bob_ops", json={
        "name": "Private Exec Chat",
        "description": "Restricted discussion",
        "workspace_type": "chat",
        "visibility": "private",
        "invited_employee_ids": ["sarah_connor"]
    })
    assert res_priv.status_code == 200
    priv_id = res_priv.json()["workspace"]["workspace_id"]
    assert res_priv.json()["workspace"]["visibility"] == "private"

    # Clean up
    client.delete(f"/api/workspaces/{pub_id}?persona=bob_ops")
    client.delete(f"/api/workspaces/{priv_id}?persona=bob_ops")


def test_owner_invite_contributors(client):
    res = client.post("/api/workspaces?persona=bob_ops", json={
        "name": "Invite Test Workspace",
        "workspace_type": "sdd",
        "visibility": "private"
    })
    assert res.status_code == 200
    ws_id = res.json()["workspace"]["workspace_id"]

    try:
        # 1. Invite Priya and Maya
        res_invite = client.post(f"/api/workspaces/{ws_id}/invite?persona=bob_ops", json={
            "employee_ids": ["priya_sharma", "maya_lin"]
        })
        assert res_invite.status_code == 200
        members = res_invite.json()["workspace"]["members"]
        m_ids = [m["user_id"] for m in members]
        assert "bob_ops" in m_ids  # Owner preserved
        assert "priya_sharma" in m_ids
        assert "maya_lin" in m_ids

        # 2. Non-owner cannot remove contributor
        del_fail = client.delete(f"/api/pods/{ws_id}/contributors/maya_lin?persona=alice_hr")
        assert del_fail.status_code == 403

        # 3. Owner removes Maya
        del_res = client.delete(f"/api/pods/{ws_id}/contributors/maya_lin?persona=bob_ops")
        assert del_res.status_code == 200
        rem_members = [m["user_id"] for m in del_res.json()["workspace"]["members"]]
        assert "maya_lin" not in rem_members
        assert "priya_sharma" in rem_members
        assert "bob_ops" in rem_members
    finally:
        client.delete(f"/api/workspaces/{ws_id}?persona=bob_ops")


def test_workspace_scoped_chat_persistence(client):
    res = client.post("/api/workspaces?persona=bob_ops", json={
        "name": "Chat Persistence Workspace",
        "workspace_type": "chat",
        "visibility": "public",
        "system_instructions": "1. Always reply politely. 2. Safety first."
    })
    assert res.status_code == 200
    ws_id = res.json()["workspace"]["workspace_id"]

    try:
        chat_res = client.post(f"/api/workspaces/{ws_id}/chat", json={
            "prompt": "What are our safety guidelines?",
            "persona": "bob_ops"
        })
        assert chat_res.status_code == 200
        data = chat_res.json()
        assert "text" in data
        assert len(data["text"]) > 0

        # Verify message persisted in workspace detail
        get_res = client.get(f"/api/workspaces/{ws_id}")
        assert get_res.status_code == 200
        ws = get_res.json()
        assert len(ws.get("chat_messages", [])) >= 2  # user + assistant
    finally:
        client.delete(f"/api/workspaces/{ws_id}?persona=bob_ops")


def test_sdd_spec_plan_tasks_management(client):
    res = client.post("/api/workspaces?persona=bob_ops", json={
        "name": "Inventory App",
        "workspace_type": "sdd",
        "visibility": "private",
        "initial_prompt": "Create an automated warehouse inventory tracking service"
    })
    assert res.status_code == 200
    ws_id = res.json()["workspace"]["workspace_id"]

    try:
        # Update Spec
        spec_update_res = client.put(f"/api/workspaces/{ws_id}/spec?persona=bob_ops", json={
            "raw_markdown": "# Custom Inventory Tracking Specification",
            "requirements": [
                {"id": "REQ-INV-1", "title": "SKU Tracking", "description": "Must track SKU barcode and shelf location.", "priority": "P0", "acceptance_criteria": "Scans in < 200ms"}
            ]
        })
        assert spec_update_res.status_code == 200
        assert spec_update_res.json()["workspace"]["spec"]["requirements"][0]["id"] == "REQ-INV-1"

        # Update Plan
        plan_update_res = client.put(f"/api/workspaces/{ws_id}/plan?persona=bob_ops", json={
            "raw_markdown": "# Architecture Plan for Inventory",
            "data_models": [{"name": "ItemSKU", "fields": ["sku_code: str", "shelf: str"]}],
            "api_endpoints": [{"method": "GET", "path": "/api/sku/{code}", "summary": "Get SKU details"}]
        })
        assert plan_update_res.status_code == 200
        assert plan_update_res.json()["workspace"]["plan"]["raw_markdown"] == "# Architecture Plan for Inventory"

        # Add Task
        task_add_res = client.post(f"/api/workspaces/{ws_id}/tasks?persona=bob_ops", json={
            "title": "Build SKU Barcode scanner endpoint",
            "linked_req_id": "REQ-INV-1",
            "target_files": ["src/sku.py"],
            "test_file": "tests/test_sku.py"
        })
        assert task_add_res.status_code == 200
        assert any(t.get("linked_req_id") == "REQ-INV-1" for t in task_add_res.json()["workspace"]["tasks"])
    finally:
        client.delete(f"/api/workspaces/{ws_id}?persona=bob_ops")


def test_sdd_autonomous_repo_and_task_execution(client):
    res = client.post("/api/workspaces?persona=bob_ops", json={
        "name": "Calculators App",
        "workspace_type": "sdd",
        "visibility": "private",
        "initial_prompt": "Build a financial calculator service"
    })
    assert res.status_code == 200
    ws = res.json()["workspace"]
    ws_id = ws["workspace_id"]
    local_path = (ws.get("sdd_config") or {}).get("local_space_path")

    try:
        # 1. Init repository in local space
        init_res = client.post(f"/api/workspaces/{ws_id}/sdd/init-repo?persona=bob_ops")
        assert init_res.status_code == 200
        init_data = init_res.json()
        assert init_data["status"] == "success"
        assert "local_path" in init_data

        # 2. Implement task
        first_task_id = ws["tasks"][0].get("task_id") or ws["tasks"][0].get("id") or "TSK-101"
        task_res = client.post(f"/api/workspaces/{ws_id}/sdd/implement-task?task_id={first_task_id}&persona=bob_ops")
        assert task_res.status_code == 200
        task_data = task_res.json()
        assert task_data["status"] == "completed"
        assert task_data["commit_hash"] is not None
        assert len(task_data["steps"]) > 0

        # 3. Run Pytest suite
        test_run_res = client.post(f"/api/workspaces/{ws_id}/sdd/run-tests?persona=bob_ops")
        assert test_run_res.status_code == 200
        assert "tests" in test_run_res.json()
    finally:
        client.delete(f"/api/workspaces/{ws_id}?persona=bob_ops")
        if local_path and Path(local_path).exists():
            shutil.rmtree(local_path, ignore_errors=True)
