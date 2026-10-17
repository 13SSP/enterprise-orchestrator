import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir / "cortex-ai" / "backend"))

import main
app = main.app

client = TestClient(app)

def test_duplicate_click_idempotency_protection():
    """Change 1: Verify rapid duplicate clicks with same client-request-id return cached response."""
    client_request_id = "req_test_dedup_001"
    payload = {
        "name": "Idempotent Pod Test",
        "description": "Testing rapid duplicate click protection",
        "workspace_type": "sdd",
        "visibility": "private"
    }
    
    # 1. First submission
    r1 = client.post(
        "/api/pods?persona=bob_ops",
        json=payload,
        headers={"x-client-request-id": client_request_id}
    )
    assert r1.status_code == 200
    d1 = r1.json()
    ws_id = d1["workspace"]["workspace_id"]
    
    # 2. Second rapid duplicate submission (simulating double click)
    r2 = client.post(
        "/api/pods?persona=bob_ops",
        json=payload,
        headers={"x-client-request-id": client_request_id}
    )
    assert r2.status_code == 200
    d2 = r2.json()
    
    # Must return exact same workspace id without creating a duplicate pod
    assert d2["workspace"]["workspace_id"] == ws_id
    assert d2.get("idempotent_replay") is True
    
    # Clean up
    client.delete(f"/api/pods/{ws_id}?persona=bob_ops")


def test_sdd_pod_lifecycle_and_spec_management():
    """Change 2: Verify SDD Pod creation, feature spec lifecycle states, and owner-only approval."""
    # 1. Create SDD Pod by Bob (owner) and invite Alice (contributor)
    r_create = client.post(
        "/api/pods?persona=bob_ops",
        json={
            "name": "E-Commerce SDD Pod",
            "description": "Spec-driven development pod for checkout microservice",
            "workspace_type": "sdd",
            "visibility": "private",
            "invited_employee_ids": ["alice_hr"]
        }
    )
    assert r_create.status_code == 200
    ws = r_create.json()["workspace"]
    ws_id = ws["workspace_id"]
    assert ws["pod_type"] == "sdd"
    
    try:
        # 2. Create feature spec in AI generation mode
        r_feat1 = client.post(
            f"/api/pods/{ws_id}/features?persona=bob_ops",
            json={
                "title": "Payment Gateway Integration",
                "description": "Stripe and PayPal multi-provider routing",
                "creation_mode": "ai_generated",
                "source_doc_text": "Need credit card tokens, idempotency keys, and 3D Secure verification.",
                "lifecycle_state": "draft"
            }
        )
        assert r_feat1.status_code == 200
        feat1 = r_feat1.json()["feature"]
        feat1_id = feat1["feature_id"]
        assert feat1["lifecycle_state"] == "draft"
        assert feat1["active_version"] == "v1.0"
        
        # 3. Create feature spec from requirement doc
        r_feat2 = client.post(
            f"/api/pods/{ws_id}/features?persona=alice_hr",
            json={
                "title": "Fraud Detection Rules",
                "description": "Velocity checks and geolocation rules",
                "creation_mode": "requirement_doc",
                "source_doc_text": "# Fraud Requirements\n- Max 3 cards per IP\n- Block high-risk BINs",
                "lifecycle_state": "draft",
                "acceptance_criteria": ["IP velocity limit enforced", "High risk BIN alerted"]
            }
        )
        assert r_feat2.status_code == 200
        feat2 = r_feat2.json()["feature"]
        feat2_id = feat2["feature_id"]
        
        # 4. Contributor (Alice) attempts to approve feature -> should be 403 Forbidden (Only Owner can approve)
        r_illegal_approve = client.put(
            f"/api/pods/{ws_id}/features/{feat1_id}?persona=alice_hr",
            json={"lifecycle_state": "approved"}
        )
        assert r_illegal_approve.status_code == 403
        
        # 5. Contributor can transition to in_review
        r_in_review = client.put(
            f"/api/pods/{ws_id}/features/{feat1_id}?persona=alice_hr",
            json={"lifecycle_state": "in_review"}
        )
        assert r_in_review.status_code == 200
        assert r_in_review.json()["feature"]["lifecycle_state"] == "in_review"
        
        # 6. Pod Owner (Bob) approves feature and bumps version
        r_owner_approve = client.put(
            f"/api/pods/{ws_id}/features/{feat1_id}?persona=bob_ops",
            json={
                "lifecycle_state": "approved",
                "bump_version": True,
                "raw_markdown": "# Payment Gateway Integration (v1.1)\n\nApproved architecture for Stripe integration."
            }
        )
        assert r_owner_approve.status_code == 200
        approved_feat = r_owner_approve.json()["feature"]
        assert approved_feat["lifecycle_state"] == "approved"
        assert approved_feat["active_version"] == "v1.1"
        assert len(approved_feat["versions"]) >= 1
        
        # 7. Grounded chat linked to feature
        r_chat = client.post(
            f"/api/pods/{ws_id}/chat",
            json={
                "prompt": "What payment providers are supported?",
                "persona": "alice_hr",
                "feature_id": feat1_id
            }
        )
        assert r_chat.status_code == 200
        chat_data = r_chat.json()
        assert "Payment Gateway Integration" in " ".join(chat_data.get("citations", []))

    finally:
        # Cleanup
        client.delete(f"/api/pods/{ws_id}?persona=bob_ops")


def test_prototype_local_storage_and_two_user_visibility_isolation():
    """Change 3: Verify local storage of prototypes and strict two-user visibility isolation."""
    # 1. Setup Pod with Bob (owner) and Alice (invited contributor)
    r_create = client.post(
        "/api/pods?persona=bob_ops",
        json={
            "name": "Local Privacy Isolation Pod",
            "description": "Verifying creator-only visibility of local prototype apps",
            "workspace_type": "sdd",
            "visibility": "private",
            "invited_employee_ids": ["alice_hr"]
        }
    )
    assert r_create.status_code == 200
    ws = r_create.json()["workspace"]
    ws_id = ws["workspace_id"]

    try:
        # 2. Bob builds a local prototype
        r_proto_local = client.post(
            f"/api/pods/{ws_id}/prototypes/build?persona=bob_ops",
            json={
                "name": "Bob Confidential Local Prototype",
                "description": "Local machine application with strict privacy",
                "storage_mode": "local",
                "tech_stack": "Python 3.11 / FastAPI / Pytest",
                "initial_prompt": "Build local order validator"
            }
        )
        assert r_proto_local.status_code == 200
        local_data = r_proto_local.json()
        proto_local = local_data["prototype"]
        proto_local_id = proto_local["prototype_id"]
        assert proto_local["storage_mode"] == "local"
        assert proto_local["creator_id"] == "bob_ops"
        # Files are returned in response payload for browser / companion local write
        assert "files" in local_data
        assert "main.py" in local_data["files"]

        # 3. Bob builds a cloud prototype (shared with pod contributors)
        r_proto_cloud = client.post(
            f"/api/pods/{ws_id}/prototypes/build?persona=bob_ops",
            json={
                "name": "Shared Cloud Prototype",
                "description": "Pod shared repository prototype",
                "storage_mode": "cloud",
                "tech_stack": "Python 3.11 / FastAPI / Pytest",
                "initial_prompt": "Build shared service"
            }
        )
        assert r_proto_cloud.status_code == 200
        proto_cloud_id = r_proto_cloud.json()["prototype"]["prototype_id"]

        # 4. BOB'S VIEW (Creator):
        # Bob queries list_prototypes -> sees BOTH local and cloud
        r_bob_protos = client.get(f"/api/pods/{ws_id}/prototypes?persona=bob_ops")
        assert r_bob_protos.status_code == 200
        bob_proto_ids = [p["prototype_id"] for p in r_bob_protos.json()["prototypes"]]
        assert proto_local_id in bob_proto_ids
        assert proto_cloud_id in bob_proto_ids

        # Bob queries pod details -> sees BOTH local and cloud in pod.prototypes
        r_bob_pod = client.get(f"/api/pods/{ws_id}?persona=bob_ops")
        assert r_bob_pod.status_code == 200
        bob_pod_proto_ids = [p["prototype_id"] for p in r_bob_pod.json()["prototypes"]]
        assert proto_local_id in bob_pod_proto_ids
        assert proto_cloud_id in bob_pod_proto_ids

        # 5. ALICE'S VIEW (Different user in the same pod):
        # Alice queries list_prototypes -> local prototype MUST BE PRUNED / ABSENT
        r_alice_protos = client.get(f"/api/pods/{ws_id}/prototypes?persona=alice_hr")
        assert r_alice_protos.status_code == 200
        alice_proto_ids = [p["prototype_id"] for p in r_alice_protos.json()["prototypes"]]
        assert proto_local_id not in alice_proto_ids, "CRITICAL: Local prototype leaked to non-creator Alice!"
        assert proto_cloud_id in alice_proto_ids, "Cloud prototype should be visible to contributor Alice"

        # Alice queries pod details -> local prototype MUST BE PRUNED from pod.prototypes
        r_alice_pod = client.get(f"/api/pods/{ws_id}?persona=alice_hr")
        assert r_alice_pod.status_code == 200
        alice_pod_proto_ids = [p["prototype_id"] for p in r_alice_pod.json()["prototypes"]]
        assert proto_local_id not in alice_pod_proto_ids, "CRITICAL: Local prototype leaked in pod details to Alice!"
        assert proto_cloud_id in alice_pod_proto_ids

        # 6. Alice attempts to delete Bob's local prototype -> 403 Forbidden
        r_alice_del = client.delete(f"/api/pods/{ws_id}/prototypes/{proto_local_id}?persona=alice_hr")
        assert r_alice_del.status_code == 403

        # 7. Bob deletes his local prototype -> 200 OK
        r_bob_del = client.delete(f"/api/pods/{ws_id}/prototypes/{proto_local_id}?persona=bob_ops")
        assert r_bob_del.status_code == 200

    finally:
        # Cleanup
        client.delete(f"/api/pods/{ws_id}?persona=bob_ops")
