import sys
import importlib.util
from pathlib import Path
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

from agent_registry.registry import agent_registry


@pytest.fixture(autouse=True)
def reset_finance_agent():
    """Ensure finance_agent starts and ends with clean state."""
    finance_agent = agent_registry.get_agent("finance_agent")
    orig_roles = list(finance_agent.allowed_roles) if finance_agent else ["*"]
    yield
    # Restore
    if finance_agent:
        agent_registry.update_access("finance_agent", allowed_roles=orig_roles, active=True)


def test_acceptance_1_finance_agent_restricted_to_finance_office():
    """
    1. Finance and Treasury agent with role = Finance Office:
       - Finance Office user: can see and use it, including 'Try agent' / direct chat.
       - HR Manager user: cannot see it in any list, gets 403 by direct URL/API call, and router never selects it.
       - Admin: can see and use it.
    """
    with TestClient(app) as tc:
        # Admin configures finance_agent to allowed_roles = ["Finance Office"]
        res_cfg = tc.put("/api/agents/finance_agent/access?persona=admin", json={
            "persona": "admin",
            "allowed_roles": ["Finance Office"],
            "allowed_teams": ["*"],
            "active": True
        })
        assert res_cfg.status_code == 200

        # A. Finance Office user (charlie_fin)
        res_list = tc.get("/api/agents?persona=charlie_fin")
        assert res_list.status_code == 200
        agents = res_list.json()["agents"]
        agent_ids = [a["id"] for a in agents]
        assert "finance_agent" in agent_ids, "Finance Office user must see finance_agent in list"

        res_direct = tc.get("/api/agents/finance_agent?persona=charlie_fin")
        assert res_direct.status_code == 200
        assert res_direct.json()["agent"]["id"] == "finance_agent"

        res_chat = tc.post("/api/chat", json={
            "prompt": "What is our quarterly EBITDA?",
            "persona": "charlie_fin",
            "target_agent_id": "finance_agent"
        })
        assert res_chat.status_code == 200
        assert res_chat.json()["handled_by"]["agent_id"] == "finance_agent"

        # B. HR Manager user (alice_hr)
        res_list_hr = tc.get("/api/agents?persona=alice_hr")
        assert res_list_hr.status_code == 200
        agents_hr = res_list_hr.json()["agents"]
        agent_ids_hr = [a["id"] for a in agents_hr]
        assert "finance_agent" not in agent_ids_hr, "HR Manager must NOT see finance_agent in list"

        res_direct_hr = tc.get("/api/agents/finance_agent?persona=alice_hr")
        assert res_direct_hr.status_code == 403, "HR Manager must receive 403 on direct lookup"

        res_chat_hr = tc.post("/api/chat", json={
            "prompt": "What is our quarterly EBITDA?",
            "persona": "alice_hr",
            "target_agent_id": "finance_agent"
        })
        assert res_chat_hr.status_code == 403, "HR Manager must receive 403 when directly targeting restricted agent"

        # C. Admin user (admin)
        res_list_admin = tc.get("/api/agents?persona=admin")
        assert res_list_admin.status_code == 200
        agents_admin = res_list_admin.json()["agents"]
        agent_ids_admin = [a["id"] for a in agents_admin]
        assert "finance_agent" in agent_ids_admin, "Admin must see finance_agent in list"

        res_direct_admin = tc.get("/api/agents/finance_agent?persona=admin")
        assert res_direct_admin.status_code == 200
        assert res_direct_admin.json()["agent"]["id"] == "finance_agent"

        res_chat_admin = tc.post("/api/chat", json={
            "prompt": "What is our quarterly EBITDA?",
            "persona": "admin",
            "target_agent_id": "finance_agent"
        })
        assert res_chat_admin.status_code == 200
        assert res_chat_admin.json()["handled_by"]["agent_id"] == "finance_agent"


def test_acceptance_2_admin_adds_role_takes_effect_immediately():
    """
    2. Admin changes the Finance agent's roles to include HR Manager:
       HR Manager can now see and use it immediately.
    """
    with TestClient(app) as tc:
        # Start restricted to Finance Office only
        tc.put("/api/agents/finance_agent/access?persona=admin", json={
            "persona": "admin",
            "allowed_roles": ["Finance Office"],
            "allowed_teams": ["*"],
            "active": True
        })

        # Pre-check: alice_hr cannot see or use it
        assert tc.get("/api/agents/finance_agent?persona=alice_hr").status_code == 403

        # Admin updates access limits to include HR Manager
        res_update = tc.put("/api/agents/finance_agent/access?persona=admin", json={
            "persona": "admin",
            "allowed_roles": ["Finance Office", "HR Manager"],
            "allowed_teams": ["*"],
            "active": True
        })
        assert res_update.status_code == 200

        # HR Manager can now immediately see it
        res_list = tc.get("/api/agents?persona=alice_hr")
        assert res_list.status_code == 200
        agent_ids = [a["id"] for a in res_list.json()["agents"]]
        assert "finance_agent" in agent_ids, "HR Manager should now see finance_agent"

        # HR Manager can now immediately access by direct ID
        res_direct = tc.get("/api/agents/finance_agent?persona=alice_hr")
        assert res_direct.status_code == 200
        assert res_direct.json()["agent"]["id"] == "finance_agent"

        # HR Manager can now use it in chat
        res_chat = tc.post("/api/chat", json={
            "prompt": "Review EBITDA metrics",
            "persona": "alice_hr",
            "target_agent_id": "finance_agent"
        })
        assert res_chat.status_code == 200
        assert res_chat.json()["handled_by"]["agent_id"] == "finance_agent"


def test_acceptance_3_non_admin_cannot_edit_agent_access():
    """
    3. A non-admin tries to edit an agent's roles or limits through direct API call:
       denied with 403.
    """
    with TestClient(app) as tc:
        # HR Manager tries to modify limits
        res_hr = tc.put("/api/agents/finance_agent/access?persona=alice_hr", json={
            "persona": "alice_hr",
            "allowed_roles": ["*"],
            "allowed_teams": ["*"],
            "active": True
        })
        assert res_hr.status_code == 403, "Non-admin HR Manager must be denied permission to edit access limits"

        # Finance Officer tries to modify limits
        res_fin = tc.put("/api/agents/finance_agent/access?persona=charlie_fin", json={
            "persona": "charlie_fin",
            "allowed_roles": ["*"],
            "allowed_teams": ["*"],
            "active": True
        })
        assert res_fin.status_code == 403, "Non-admin Finance Officer must be denied permission to edit access limits"


def test_acceptance_4_unassigned_agent_remains_accessible_to_all():
    """
    4. Agent with no roles assigned (empty list or wildcard):
       still visible and usable by all personas as before (backward compatibility).
    """
    with TestClient(app) as tc:
        # Set allowed_roles to wildcard
        tc.put("/api/agents/productivity_agent/access?persona=admin", json={
            "persona": "admin",
            "allowed_roles": ["*"],
            "allowed_teams": ["*"],
            "active": True
        })

        for persona in ["alice_hr", "charlie_fin", "bob_ops", "admin"]:
            res_list = tc.get(f"/api/agents?persona={persona}")
            assert res_list.status_code == 200
            ids = [a["id"] for a in res_list.json()["agents"]]
            assert "productivity_agent" in ids, f"Unassigned agent must be visible to persona {persona}"

            res_direct = tc.get(f"/api/agents/productivity_agent?persona={persona}")
            assert res_direct.status_code == 200


def test_acceptance_5_router_chat_confidentiality_no_leak():
    """
    5. Router/chat: an HR Manager asks a finance question.
       The restricted agent is not invoked and nothing about it is revealed in
       routing explanations or suggestions.
    """
    with TestClient(app) as tc:
        # Restrict finance_agent to Finance Office only
        tc.put("/api/agents/finance_agent/access?persona=admin", json={
            "persona": "admin",
            "allowed_roles": ["Finance Office"],
            "allowed_teams": ["*"],
            "active": True
        })

        # alice_hr asks a question in auto-route mode that normally routes to finance_agent
        res = tc.post("/api/chat", json={
            "prompt": "Please calculate the company quarterly EBITDA margin and forecast",
            "persona": "alice_hr",
            "target_agent_id": "auto"
        })
        assert res.status_code == 200
        data = res.json()
        handled_by = data.get("handled_by", {})

        # Verify finance_agent was NOT invoked
        assert handled_by.get("agent_id") != "finance_agent", "Restricted agent must not be invoked"
        assert "finance_agent" not in str(handled_by.get("reasoning", "")), "Restricted agent must not be revealed in reasoning"


def test_acceptance_6_stale_session_invalidation():
    """
    Verify changing limits takes immediate effect on multi-turn sessions (no stale cache or session bypass).
    """
    with TestClient(app) as tc:
        # First, allow Finance Office and HR Manager
        tc.put("/api/agents/finance_agent/access?persona=admin", json={
            "persona": "admin",
            "allowed_roles": ["Finance Office", "HR Manager"],
            "allowed_teams": ["*"],
            "active": True
        })

        session_id = "test-session-stale-123"

        # alice_hr chats in this session
        res1 = tc.post("/api/chat", json={
            "prompt": "Hello",
            "persona": "alice_hr",
            "session_id": session_id,
            "target_agent_id": "finance_agent"
        })
        assert res1.status_code == 200
        assert res1.json()["handled_by"]["agent_id"] == "finance_agent"

        # Now Admin restricts finance_agent to Finance Office ONLY
        tc.put("/api/agents/finance_agent/access?persona=admin", json={
            "persona": "admin",
            "allowed_roles": ["Finance Office"],
            "allowed_teams": ["*"],
            "active": True
        })

        # alice_hr sends a follow-up in the same session without specifying target_agent_id
        # The backend must invalidate the stale session target and NOT invoke finance_agent
        res2 = tc.post("/api/chat", json={
            "prompt": "What is our EBITDA?",
            "persona": "alice_hr",
            "session_id": session_id
        })
        assert res2.status_code == 200
        assert res2.json()["handled_by"]["agent_id"] != "finance_agent", "Stale session target must be invalidated"


def test_audit_logs_record_denials_and_limit_changes():
    """
    Log denied access attempts and role/limit changes (who, what, when) to the audit mechanism.
    """
    with TestClient(app) as tc:
        # Non-admin attempt generates audit entry
        tc.put("/api/agents/finance_agent/access?persona=alice_hr", json={
            "persona": "alice_hr",
            "allowed_roles": ["*"],
            "active": True
        })

        res_audit = tc.get("/api/audit")
        assert res_audit.status_code == 200
        events = res_audit.json()["events"]
        event_types = [e.get("event_type") for e in events]
        assert "AGENT_LIMIT_UPDATE_DENIED" in event_types, "Denied limit update must be recorded in audit log"
