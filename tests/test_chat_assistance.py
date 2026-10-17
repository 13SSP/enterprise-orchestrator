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

def test_real_time_internet_grounding_weather_and_search():
    with TestClient(app) as tc:
        session_id = f"test-weather-{uuid.uuid4().hex[:8]}"
        res = tc.post("/api/chat", json={
            "prompt": "what is weather in Pune",
            "persona": "bob_ops",
            "session_id": session_id,
            "agent_id": "auto"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "SUCCESS"
        assert data["handled_by"]["agent_id"] == "cortex_assistant"
        assert data["handled_by"]["is_enterprise_agent"] is False
        assert "Enterprise Agent Used" not in data["reply"]
        assert "Pune" in data["reply"]
        # Verify weather breakdown elements
        reply_lower = data["reply"].lower()
        assert any(k in reply_lower for k in ["temperature", "high", "low", "humidity", "outlook", "weather", "°c"])
        db.collection("chat_sessions").document(session_id).delete()

def test_target_agent_persistence_across_multiple_chat_turns():
    with TestClient(app) as tc:
        session_id = f"test-persist-{uuid.uuid4().hex[:8]}"
        # Turn 1: User targeted HR agent with initial question
        res1 = tc.post("/api/chat", json={
            "prompt": "Check my remaining PTO leave balance",
            "persona": "bob_ops",
            "session_id": session_id,
            "agent_id": "hr_agent",
            "model": "offline/stub"
        })
        assert res1.status_code == 200
        d1 = res1.json()
        assert d1["handled_by"]["agent_id"] == "hr_agent"
        assert d1["handled_by"]["is_enterprise_agent"] is True

        # Turn 2: Follow-up question in the same chat session (even if agent_id is omitted or auto)
        res2 = tc.post("/api/chat", json={
            "prompt": "what is todays date",
            "persona": "bob_ops",
            "session_id": session_id,
            "agent_id": "auto",
            "model": "offline/stub"
        })
        assert res2.status_code == 200
        d2 = res2.json()
        # Verify agent does NOT change to a different agent on subsequent chats in this session
        assert d2["handled_by"]["agent_id"] == "hr_agent"
        assert d2["handled_by"]["is_enterprise_agent"] is True
        db.collection("chat_sessions").document(session_id).delete()

def test_enterprise_knowledge_base_rag_retrieval():
    with TestClient(app) as tc:
        session_id = f"test-rag-{uuid.uuid4().hex[:8]}"
        res = tc.post("/api/chat", json={
            "prompt": "what is the primary caregiver parental leave in the policy handbook?",
            "persona": "bob_ops",
            "session_id": session_id,
            "model": "offline/stub"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "SUCCESS"
        # RAG retrieves section from HR handbook
        assert any(k in data["reply"].lower() for k in ["parental", "caregiver", "leave", "weeks", "policy", "handbook"])
        db.collection("chat_sessions").document(session_id).delete()

def test_model_selection_and_switching_in_chat():
    with TestClient(app) as tc:
        # 1. Verify models endpoint lists working active models
        m_res = tc.get("/api/models")
        assert m_res.status_code == 200
        m_data = m_res.json()
        model_ids = [m["id"] for m in m_data.get("models", [])]
        assert "google/gemini-3.7-flash" in model_ids
        assert "google/gemini-flash-lite-latest" in model_ids
        assert "google/gemini-3.5-flash-lite" in model_ids
        assert "google/gemini-3.1-flash-lite" in model_ids
        assert m_data.get("default_model") == "google/gemini-3.7-flash"

        session_id = f"test-model-{uuid.uuid4().hex[:8]}"

        # 2. First chat turn with offline/stub
        turn1 = tc.post("/api/chat", json={
            "prompt": "Explain quantum computing briefly",
            "persona": "bob_ops",
            "session_id": session_id,
            "model": "offline/stub"
        })
        assert turn1.status_code == 200
        d1 = turn1.json()
        assert d1["handled_by"]["model"] == "offline/stub"

        # 3. Second chat turn in same session switched to a different model
        turn2 = tc.post("/api/chat", json={
            "prompt": "Give a one-sentence follow-up",
            "persona": "bob_ops",
            "session_id": session_id,
            "model": "google/gemini-flash-lite-latest"
        })
        assert turn2.status_code == 200
        d2 = turn2.json()
        assert "gemini-flash-lite-latest" in d2["handled_by"]["model"] or "google/" in d2["handled_by"]["model"]

        # 4. Verify session record in DB persists the selected model
        doc = db.collection("chat_sessions").document(session_id).get()
        assert doc.exists is True
        assert doc.to_dict().get("model") is not None

        db.collection("chat_sessions").document(session_id).delete()

def test_optimized_swe_bench_and_benchmark_agent_selection():
    with TestClient(app) as tc:
        session_id = f"test-swe-{uuid.uuid4().hex[:8]}"

        # 1. Target SWE-bench Agent for code testing
        res_swe = tc.post("/api/chat", json={
            "prompt": "Run unit tests and pytest runner on repository",
            "persona": "bob_ops",
            "session_id": session_id,
            "agent_id": "swe_bench_agent",
            "model": "offline/stub"
        })
        assert res_swe.status_code == 200
        d_swe = res_swe.json()
        assert d_swe["handled_by"]["agent_id"] == "swe_bench_agent"
        assert d_swe["handled_by"]["tool"] == "pytest_runner"
        assert d_swe["handled_by"]["is_enterprise_agent"] is True
        assert "Pytest Runner Results" in d_swe["reply"]

        # 2. Target Financial Benchmark for EBITDA calculation
        res_fin = tc.post("/api/chat", json={
            "prompt": "Calculate corporate EBITDA margin for Q3",
            "persona": "charlie_fin",
            "session_id": session_id,
            "agent_id": "financial_benchmark",
            "model": "offline/stub"
        })
        assert res_fin.status_code == 200
        d_fin = res_fin.json()
        assert d_fin["handled_by"]["agent_id"] == "financial_benchmark"
        assert d_fin["handled_by"]["tool"] == "calculate_ebitda"
        assert d_fin["handled_by"]["is_enterprise_agent"] is True
        assert "EBITDA" in d_fin["reply"]

        db.collection("chat_sessions").document(session_id).delete()

def test_auto_routing_to_specialist_benchmark_and_code_agents():
    with TestClient(app) as tc:
        session_id = f"test-autoroute-{uuid.uuid4().hex[:8]}"

        # Auto-route code test query to swe_bench_agent
        res_code = tc.post("/api/chat", json={
            "prompt": "Run pytest suite on backend repository",
            "persona": "bob_ops",
            "session_id": session_id,
            "agent_id": "auto",
            "model": "offline/stub"
        })
        assert res_code.status_code == 200
        d_code = res_code.json()
        assert d_code["handled_by"]["agent_id"] == "swe_bench_agent"
        assert d_code["handled_by"]["tool"] == "pytest_runner"
        assert d_code["handled_by"]["is_enterprise_agent"] is True

        db.collection("chat_sessions").document(session_id).delete()

def test_explicit_agent_switching_across_session_turns():
    with TestClient(app) as tc:
        session_id = f"test-switch-{uuid.uuid4().hex[:8]}"

        # Turn 1: Start targeted session with hr_agent
        turn1 = tc.post("/api/chat", json={
            "prompt": "Check my leave balance",
            "persona": "bob_ops",
            "session_id": session_id,
            "agent_id": "hr_agent",
            "model": "offline/stub"
        })
        assert turn1.status_code == 200
        assert turn1.json()["handled_by"]["agent_id"] == "hr_agent"

        # Turn 2: Explicitly switch target agent to finance_agent
        turn2 = tc.post("/api/chat", json={
            "prompt": "List corporate expense claims",
            "persona": "bob_ops",
            "session_id": session_id,
            "agent_id": "finance_agent",
            "target_agent_id": "finance_agent",
            "model": "offline/stub"
        })
        assert turn2.status_code == 200
        d2 = turn2.json()
        assert d2["handled_by"]["agent_id"] == "finance_agent"
        assert d2["handled_by"]["tool"] == "list_claims"

        # Turn 3: Explicitly switch target agent to auto
        turn3 = tc.post("/api/chat", json={
            "prompt": "what is weather in Pune",
            "persona": "bob_ops",
            "session_id": session_id,
            "agent_id": "auto",
            "target_agent_id": "auto"
        })
        assert turn3.status_code == 200
        d3 = turn3.json()
        assert d3["handled_by"]["agent_id"] == "cortex_assistant"
        assert d3["handled_by"]["is_enterprise_agent"] is False

        db.collection("chat_sessions").document(session_id).delete()

def test_domain_agent_tool_execution():
    with TestClient(app) as tc:
        session_id = f"test-tools-{uuid.uuid4().hex[:8]}"

        # 1. HR Agent: list_employees
        res_hr = tc.post("/api/chat", json={
            "prompt": "Show company employee directory",
            "persona": "alice_hr",
            "session_id": session_id,
            "agent_id": "hr_agent",
            "target_agent_id": "hr_agent",
            "model": "offline/stub"
        })
        assert res_hr.status_code == 200
        d_hr = res_hr.json()
        assert d_hr["handled_by"]["tool"] == "list_employees"
        assert "Employee Directory" in d_hr["reply"]

        # 2. Ops Agent: get_system_health
        res_ops = tc.post("/api/chat", json={
            "prompt": "Check cluster system health and uptime",
            "persona": "bob_ops",
            "session_id": session_id,
            "agent_id": "ops_agent",
            "target_agent_id": "ops_agent",
            "model": "offline/stub"
        })
        assert res_ops.status_code == 200
        d_ops = res_ops.json()
        assert d_ops["handled_by"]["tool"] == "get_system_health"
        assert "HEALTHY" in d_ops["reply"]

        # 3. IT Support Agent: list_tickets
        res_it = tc.post("/api/chat", json={
            "prompt": "List open Jira engineering tickets",
            "persona": "bob_ops",
            "session_id": session_id,
            "agent_id": "it_support_agent",
            "target_agent_id": "it_support_agent",
            "model": "offline/stub"
        })
        assert res_it.status_code == 200
        d_it = res_it.json()
        assert d_it["handled_by"]["tool"] == "list_tickets"
        assert "Active Engineering Jira Tickets" in d_it["reply"]

        db.collection("chat_sessions").document(session_id).delete()



