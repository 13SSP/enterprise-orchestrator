import sys
import importlib.util
from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

src_file = backend_dir / "main.py"
spec = importlib.util.spec_from_file_location("cortex_hub_main", src_file)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
app = mod.app

from database.firestore_client import db
from workspaces.manager import workspace_manager


def test_get_pods_success_returns_seeds():
    """Verify GET /api/pods returns HTTP 200 with seed pods."""
    with TestClient(app) as tc:
        res = tc.get("/api/pods?filter=all&persona=bob_ops")
        assert res.status_code == 200
        data = res.json()
        assert "workspaces" in data
        assert isinstance(data["workspaces"], list)
        
        pod_ids = [w.get("id") or w.get("workspace_id") for w in data["workspaces"]]
        assert "ws-calendar-app" in pod_ids
        assert "ws-eng-watercooler" in pod_ids


def test_get_pod_by_id_returns_valid_sdd_spec():
    """Verify GET /api/pods/{workspace_id} returns the full SDD spec."""
    with TestClient(app) as tc:
        res = tc.get("/api/pods/ws-calendar-app?persona=bob_ops")
        assert res.status_code == 200
        data = res.json()
        assert data.get("workspace_id") == "ws-calendar-app"
        assert data.get("workspace_type") == "sdd" or data.get("pod_type") == "sdd"
        assert "spec" in data
        assert "Enterprise Calendar" in data["spec"].get("title", "")


def test_pods_database_stream_exception_graceful_fallback():
    """
    Simulate Firestore error when streaming workspaces.
    Verify manager falls back to local disk and returns seed pods without crashing.
    """
    with patch.object(db, "collection", side_effect=RuntimeError("Firestore connection timeout")):
        workspaces = workspace_manager.list_workspaces(filter_type="all", current_user="bob_ops")
        assert isinstance(workspaces, list)
        pod_ids = [w.get("id") or w.get("workspace_id") for w in workspaces]
        assert "ws-calendar-app" in pod_ids
        assert "ws-eng-watercooler" in pod_ids


def test_pods_route_catches_unexpected_error_and_returns_valid_json():
    """
    Verify that even if workspace_manager raises an exception,
    /api/pods returns valid JSON response rather than plain text 500.
    """
    with patch("api.routes.workspace_manager.list_workspaces", side_effect=Exception("Critical system error")):
        with TestClient(app, raise_server_exceptions=False) as tc:
            res = tc.get("/api/pods?filter=all&persona=bob_ops")
            assert res.status_code == 200
            data = res.json()
            assert "workspaces" in data
            assert data["workspaces"] == []
            assert "error" in data


def test_global_exception_handler_returns_json_on_unhandled_500():
    """
    Verify that unhandled exceptions across the FastAPI app
    return a structured JSON object instead of raw HTML/text.
    """
    with patch("api.routes.workspace_manager.get_workspace", side_effect=ValueError("Boom")):
        with TestClient(app, raise_server_exceptions=False) as tc:
            res = tc.get("/api/pods/non-existent-pod-xyz")
            assert res.status_code == 500
            assert res.headers["content-type"].startswith("application/json")
            data = res.json()
            assert "detail" in data
            assert "error" in data

