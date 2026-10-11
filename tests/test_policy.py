import pytest
from app.core.policy import policy_engine, DEMO_PERSONAS, UserContext
from app.core.registry import registry

def test_jwt_generation_and_decoding():
    user = DEMO_PERSONAS["devops_admin"]
    token = policy_engine.generate_jwt(user)
    assert token is not None

    decoded = policy_engine.decode_jwt(token)
    assert decoded is not None
    assert decoded.sub == user.sub
    assert "devops_admin" in decoded.roles

def test_agent_access_control():
    contractor = DEMO_PERSONAS["contractor_guest"]
    # Contractor only allowed hr_agent
    decision = policy_engine.can_user_call_agent(contractor, "it_agent")
    assert not decision.allowed
    assert "not granted access" in decision.reason

    decision_hr = policy_engine.can_user_call_agent(contractor, "hr_agent")
    assert decision_hr.allowed

def test_before_tool_callback_write_protection():
    devops = DEMO_PERSONAS["devops_admin"]
    # restart_cloud_service is write and requires confirmation
    decision = policy_engine.before_tool_callback(
        agent_id="it_agent",
        tool_name="restart_cloud_service",
        user=devops,
        tool_parameters={"service_name": "payments-api"},
        is_already_confirmed=False
    )
    assert decision.requires_confirmation
    assert decision.decision_code == "REQUIRES_CONFIRMATION"

def test_before_tool_callback_contractor_blocked():
    contractor = DEMO_PERSONAS["contractor_guest"]
    decision = policy_engine.before_tool_callback(
        agent_id="hr_agent",
        tool_name="submit_timeoff_request",
        user=contractor,
        tool_parameters={"start_date": "2026-11-01", "end_date": "2026-11-05"},
        is_already_confirmed=False
    )
    assert not decision.allowed
    assert decision.decision_code == "DENY_INSUFFICIENT_ROLE"

if __name__ == "__main__":
    test_jwt_generation_and_decoding()
    test_agent_access_control()
    test_before_tool_callback_write_protection()
    test_before_tool_callback_contractor_blocked()
    print("All policy tests passed successfully!")
