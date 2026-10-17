import sys
import uuid
import importlib.util
from pathlib import Path
from fastapi.testclient import TestClient

root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

backend_dir = root_dir / "cortex-ai" / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

src_file = backend_dir / "main.py"
spec = importlib.util.spec_from_file_location("cortex_hub_main", src_file)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
app = mod.app

from database.firestore_client import db

def test_chat_context_storage_and_multi_turn_history():
    with TestClient(app) as tc:
        session_id = f"test-session-{uuid.uuid4().hex[:8]}"
        
        # Turn 1: Ask about HR leave balance
        turn1_res = tc.post("/api/chat", json={
            "prompt": "What is my leave balance?",
            "persona": "bob_ops",
            "session_id": session_id
        })
        assert turn1_res.status_code == 200
        turn1_data = turn1_res.json()
        assert turn1_data["status"] == "SUCCESS"
        assert "Leave Balance for Bob Martinez" in turn1_data["reply"]
        assert turn1_data["session_id"] == session_id
        # Check enterprise agent mention
        assert "Enterprise Agent Used" in turn1_data["reply"]
        assert turn1_data["handled_by"]["is_enterprise_agent"] is True

        # Check that session was stored in Firebase DB
        doc = db.collection("chat_sessions").document(session_id).get()
        assert doc.exists is True
        s_data = doc.to_dict()
        assert len(s_data["messages"]) == 2
        assert s_data["messages"][0]["role"] == "user"
        assert s_data["messages"][1]["role"] == "assistant"

        # Turn 2: Follow-up in the same session
        turn2_res = tc.post("/api/chat", json={
            "prompt": "Can you summarize that in 1 sentence?",
            "persona": "bob_ops",
            "session_id": session_id,
            "model": "offline/stub"
        })
        assert turn2_res.status_code == 200
        turn2_data = turn2_res.json()
        assert turn2_data["session_id"] == session_id

        # Verify session has now 4 messages in Firebase DB
        doc2 = db.collection("chat_sessions").document(session_id).get()
        s_data2 = doc2.to_dict()
        assert len(s_data2["messages"]) == 4

        # Clean up
        db.collection("chat_sessions").document(session_id).delete()

def test_target_agent_selection():
    with TestClient(app) as tc:
        session_id = f"test-agent-select-{uuid.uuid4().hex[:8]}"
        
        # Explicitly select finance_agent
        res = tc.post("/api/chat", json={
            "prompt": "Check salary compensation details",
            "persona": "charlie_fin",
            "session_id": session_id,
            "agent_id": "finance_agent"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["handled_by"]["agent_id"] == "finance_agent"
        assert data["handled_by"]["is_enterprise_agent"] is True
        assert "Enterprise Agent Used" in data["reply"]

        # Clean up
        db.collection("chat_sessions").document(session_id).delete()

def test_context_document_upload_in_chat():
    with TestClient(app) as tc:
        session_id = f"test-doc-upload-{uuid.uuid4().hex[:8]}"
        
        res = tc.post("/api/chat", json={
            "prompt": "What does the attached policy document specify regarding remote working hours?",
            "persona": "bob_ops",
            "session_id": session_id,
            "model": "offline/stub",
            "context_documents": [
                {
                    "name": "remote_work_policy.txt",
                    "content": "Employees may work remotely between 9 AM and 6 PM in their local timezone with core hours from 10 AM to 3 PM.",
                    "size": 115
                }
            ]
        })
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "SUCCESS"

        # Verify context document is saved in session messages in Firebase DB
        doc = db.collection("chat_sessions").document(session_id).get()
        assert doc.exists is True
        s_data = doc.to_dict()
        user_msg = s_data["messages"][0]
        assert "documents" in user_msg
        assert user_msg["documents"][0]["name"] == "remote_work_policy.txt"

        # Clean up
        db.collection("chat_sessions").document(session_id).delete()

def test_document_download_url_and_endpoint():
    with TestClient(app) as tc:
        # Generate word document
        res = tc.post("/api/chat", json={
            "prompt": "Create a word document summary memo",
            "persona": "bob_ops",
            "model": "offline/stub"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["download_card"] is not None
        down_url = data["download_card"]["download_url"]
        
        # Verify no localhost in URL
        assert "localhost" not in down_url
        assert "127.0.0.1" not in down_url
        assert down_url.startswith("/api/files/download/")

        # Test download endpoint directly on backend
        file_name = data["download_card"]["file_name"]
        dl_res = tc.get(f"/api/files/download/{file_name}")
        assert dl_res.status_code == 200
        assert dl_res.headers["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

def test_chat_history_api():
    with TestClient(app) as tc:
        test_session_id = f"test-hist-{uuid.uuid4().hex[:8]}"
        
        # Create a session via /api/chat
        tc.post("/api/chat", json={
            "prompt": "Hello test assistant query",
            "persona": "alice_hr",
            "session_id": test_session_id,
            "model": "offline/stub"
        })

        # List chat history
        hist_res = tc.get("/api/chat/history?persona=alice_hr")
        assert hist_res.status_code == 200
        sessions = hist_res.json()["sessions"]
        found = [s for s in sessions if s["session_id"] == test_session_id]
        assert len(found) > 0

        # Retrieve specific session
        sess_res = tc.get(f"/api/chat/sessions/{test_session_id}")
        assert sess_res.status_code == 200
        sess_data = sess_res.json()
        assert sess_data["session_id"] == test_session_id
        assert len(sess_data["messages"]) >= 2

        # Delete session
        del_res = tc.delete(f"/api/chat/sessions/{test_session_id}")
        assert del_res.status_code == 200
        assert del_res.json()["status"] == "DELETED"

        # Verify deletion
        assert tc.get(f"/api/chat/sessions/{test_session_id}").status_code == 404
