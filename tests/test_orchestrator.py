from app.core.orchestrator import orchestrator
from app.core.policy import DEMO_PERSONAS
from app.core.registry import registry, AgentManifest

def test_intent_routing_and_execution():
    devops = DEMO_PERSONAS["devops_admin"]
    
    # 1. Read tool prompt
    res = orchestrator.execute_chat("Check status of Jira ticket PROJ-102", devops)
    assert res["action_taken"] == "TOOL_EXECUTED"
    assert res["routing"]["selected_agent_id"] == "it_agent"
    assert "PROJ-102" in str(res["tool_executed"])

    # 2. Write tool prompt (should require confirmation)
    res_write = orchestrator.execute_chat("Restart payments-api in cloud cluster", devops)
    assert res_write["action_taken"] == "CONFIRMATION_REQUIRED"
    assert "pending_confirmation" in res_write
    conf_id = res_write["pending_confirmation"]["confirmation_id"]

    # 3. Resume write tool with confirmation
    res_confirmed = orchestrator.execute_chat("[Confirm]", devops, confirmed_action_id=conf_id)
    assert res_confirmed["action_taken"] == "WRITE_APPROVED_EXECUTED"
    assert "RESTARTED_SUCCESSFULLY" in str(res_confirmed["tool_executed"])

    # 4. RAG knowledge prompt
    hr_user = DEMO_PERSONAS["hr_manager"]
    res_rag = orchestrator.execute_chat("What is our 2026 PTO and leave policy?", hr_user)
    assert res_rag["action_taken"] == "RAG_RETRIEVAL"
    assert "rag_sources" in res_rag

def test_dynamic_agent_onboarding_in_orchestrator():
    # Onboard dynamic agent at runtime
    new_agent = AgentManifest(
        id="analytics_test_agent",
        name="Data Analytics Agent",
        description="Handles SQL queries, BigQuery analytics, and dashboard metrics.",
        owner_team="Data Platform",
        system_prompt="You are the Data Analytics Agent.",
        allowed_tools=["get_budget_overview"],
        knowledge_scopes=["finance_guidelines"],
        agent_type="local_adk",
        active=True
    )
    registry.register_agent(new_agent)

    # Route request to newly onboarded agent with an authorized user
    user = DEMO_PERSONAS["finance_officer"].model_copy(deep=True)
    user.allowed_agent_ids.append("analytics_test_agent")
    route_res = orchestrator.route_prompt("Run BigQuery analytics for data dashboard metrics", user, "test-trace")
    assert route_res["selected_agent_id"] == "analytics_test_agent"

if __name__ == "__main__":
    test_intent_routing_and_execution()
    test_dynamic_agent_onboarding_in_orchestrator()
    print("All orchestrator tests passed successfully!")
