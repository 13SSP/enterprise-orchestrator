import jwt
import time
from typing import Dict, List, Any, Optional, Tuple
from pydantic import BaseModel
from app.config import settings
from app.core.registry import registry, AgentManifest, ToolDefinition
from app.core.observability import observability

class UserContext(BaseModel):
    sub: str
    name: str
    email: str
    team: str
    roles: List[str]
    allowed_agent_ids: List[str] = ["*"]

class PolicyDecision(BaseModel):
    allowed: bool
    requires_confirmation: bool = False
    decision_code: str  # "ALLOW", "DENY_AGENT_ACCESS", "DENY_TOOL_PERMISSION", "REQUIRES_CONFIRMATION"
    reason: str
    rule_name: str
    confirmation_payload: Optional[Dict[str, Any]] = None

# Pre-packaged personas for demo & hackathon evaluation
DEMO_PERSONAS = {
    "devops_admin": UserContext(
        sub="bob_ops",
        name="Bob Martinez",
        email="bob.ops@company.internal",
        team="Engineering",
        roles=["employee", "devops_admin", "it_engineer"],
        allowed_agent_ids=["it_agent", "hr_agent", "security_remote_agent"]
    ),
    "hr_manager": UserContext(
        sub="alice_hr",
        name="Alice Henderson",
        email="alice.hr@company.internal",
        team="Human Resources",
        roles=["employee", "hr_manager"],
        allowed_agent_ids=["hr_agent", "it_agent"]
    ),
    "finance_officer": UserContext(
        sub="charlie_fin",
        name="Charlie Zhao",
        email="charlie.fin@company.internal",
        team="Finance",
        roles=["employee", "finance_officer"],
        allowed_agent_ids=["finance_agent", "hr_agent"]
    ),
    "contractor_guest": UserContext(
        sub="dave_contractor",
        name="Dave Miller (Contractor)",
        email="dave.external@partner.com",
        team="External Vendor",
        roles=["contractor"],
        allowed_agent_ids=["hr_agent"]  # Restricted: only HR, cannot call IT or Finance or Write tools
    )
}

# Agent Dedicated Service Account mapping (Tier 3: API Gateway / Least-Privilege IAM)
AGENT_SERVICE_ACCOUNTS = {
    "it_agent": {
        "service_account": "sa-cloud-ops@hackathon-corp.iam.gserviceaccount.com",
        "iam_roles": ["roles/container.developer", "roles/monitoring.viewer"],
        "secret_ref": "projects/12345/secrets/jira-cloud-token/versions/latest"
    },
    "hr_agent": {
        "service_account": "sa-people-ops@hackathon-corp.iam.gserviceaccount.com",
        "iam_roles": ["roles/workday.directoryReader"],
        "secret_ref": "projects/12345/secrets/workday-creds/versions/latest"
    },
    "finance_agent": {
        "service_account": "sa-netsuite-api@hackathon-corp.iam.gserviceaccount.com",
        "iam_roles": ["roles/netsuite.readOnly", "roles/expenses.approver"],
        "secret_ref": "projects/12345/secrets/netsuite-oauth-key/versions/latest"
    },
    "security_remote_agent": {
        "service_account": "sa-secops-scanner@hackathon-corp.iam.gserviceaccount.com",
        "iam_roles": ["roles/securityReviewer"],
        "secret_ref": "projects/12345/secrets/secops-jwt-cert/versions/latest"
    }
}

class PolicyEngine:
    """
    Tier 1: JWT Authentication & Claims.
    Tier 2: ADK Policy Layer with before_tool_callback and Per-Agent Tool Filtering.
    Tier 3: API Gateway & IAM boundary validation.
    """

    def generate_jwt(self, user: UserContext) -> str:
        payload = {
            "sub": user.sub,
            "name": user.name,
            "email": user.email,
            "team": user.team,
            "roles": user.roles,
            "allowed_agent_ids": user.allowed_agent_ids,
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600 * 24,
            "iss": "identity-platform.hackathon.internal"
        }
        return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")

    def decode_jwt(self, token: str) -> Optional[UserContext]:
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
            return UserContext(
                sub=payload.get("sub", "anon"),
                name=payload.get("name", "Anonymous"),
                email=payload.get("email", ""),
                team=payload.get("team", ""),
                roles=payload.get("roles", []),
                allowed_agent_ids=payload.get("allowed_agent_ids", ["*"])
            )
        except Exception as e:
            print(f"[PolicyEngine] JWT decode error: {e}")
            return None

    def get_persona_user(self, persona_key: str) -> UserContext:
        return DEMO_PERSONAS.get(persona_key, DEMO_PERSONAS["devops_admin"])

    # Tier 2 Policy: Agent level access
    def can_user_call_agent(self, user: UserContext, agent_id: str, trace_id: str = "") -> PolicyDecision:
        agent = registry.get_agent(agent_id)
        if not agent:
            decision = PolicyDecision(
                allowed=False,
                decision_code="DENY_AGENT_NOT_FOUND",
                reason=f"Agent '{agent_id}' does not exist in registry.",
                rule_name="AgentExistenceCheck"
            )
            observability.log_policy_evaluation(trace_id, user.model_dump(), agent_id, None, "DENIED", decision.reason, decision.rule_name)
            return decision

        if not agent.active:
            decision = PolicyDecision(
                allowed=False,
                decision_code="DENY_AGENT_INACTIVE",
                reason=f"Agent '{agent.name}' is currently deactivated.",
                rule_name="AgentLifecycleCheck"
            )
            observability.log_policy_evaluation(trace_id, user.model_dump(), agent_id, None, "DENIED", decision.reason, decision.rule_name)
            return decision

        # Check Agent Visibility & Access Control (RBAC & Team Limits)
        if not agent.is_public:
            if "*" not in agent.allowed_roles and not any(r in agent.allowed_roles for r in user.roles):
                decision = PolicyDecision(
                    allowed=False,
                    decision_code="DENY_AGENT_ROLE_RESTRICTED",
                    reason=f"Access Denied: Agent '{agent.name}' is restricted to roles {agent.allowed_roles}. Current user has: {user.roles}.",
                    rule_name="AgentRoleAccessCheck"
                )
                observability.log_policy_evaluation(trace_id, user.model_dump(), agent_id, None, "DENIED", decision.reason, decision.rule_name)
                return decision

            if "*" not in agent.allowed_teams and user.team not in agent.allowed_teams:
                decision = PolicyDecision(
                    allowed=False,
                    decision_code="DENY_AGENT_TEAM_RESTRICTED",
                    reason=f"Access Denied: Agent '{agent.name}' is restricted to teams {agent.allowed_teams}. User belongs to '{user.team}'.",
                    rule_name="AgentTeamAccessCheck"
                )
                observability.log_policy_evaluation(trace_id, user.model_dump(), agent_id, None, "DENIED", decision.reason, decision.rule_name)
                return decision

        # Check allowed_agent_ids
        if "*" not in user.allowed_agent_ids and agent_id not in user.allowed_agent_ids:
            decision = PolicyDecision(
                allowed=False,
                decision_code="DENY_AGENT_ACCESS",
                reason=f"User '{user.name}' ({user.team}) is not granted access to agent '{agent.name}'.",
                rule_name="UserAgentScopeAllowlist"
            )
            observability.log_policy_evaluation(trace_id, user.model_dump(), agent_id, None, "DENIED", decision.reason, decision.rule_name)
            return decision

        decision = PolicyDecision(
            allowed=True,
            decision_code="ALLOW",
            reason=f"User has valid credentials to access agent '{agent.name}'.",
            rule_name="UserAgentScopeAllowlist"
        )
        observability.log_policy_evaluation(trace_id, user.model_dump(), agent_id, None, "ALLOWED", decision.reason, decision.rule_name)
        return decision

    # Tier 2 Policy: Per-Agent Tool Filter (Agent never sees tools it isn't allowed to use)
    def filter_visible_tools(self, user: UserContext, agent: AgentManifest) -> List[ToolDefinition]:
        """
        Ensures prompt injection cannot discover or call unauthorized tools.
        Returns ONLY tools authorized for both the Agent and the User.
        """
        all_agent_tools = registry.list_tools(agent_id=agent.id)
        visible: List[ToolDefinition] = []

        for tool in all_agent_tools:
            # 1. Skip disabled tools
            if not getattr(tool, "enabled", True):
                continue

            # 2. Check per-tool allowed_roles
            if hasattr(tool, "allowed_roles") and "*" not in tool.allowed_roles:
                if not any(r in tool.allowed_roles for r in user.roles):
                    continue

            # 3. Check if user has basic role privileges for sensitive/write tools
            if tool.is_write:
                # Contractors cannot view/run any write operations
                if "contractor" in user.roles and not any(r in ["devops_admin", "hr_manager", "finance_officer"] for r in user.roles):
                    continue

                # DevOps write operations require devops_admin or it_engineer
                if "it" in tool.tags and not any(r in ["devops_admin", "it_engineer"] for r in user.roles):
                    continue

                # Finance write operations require finance_officer
                if "finance" in tool.tags and "finance_officer" not in user.roles:
                    continue

            visible.append(tool)

        return visible

    # ADK before_tool_callback implementation
    def before_tool_callback(
        self,
        agent_id: str,
        tool_name: str,
        user: UserContext,
        tool_parameters: Dict[str, Any],
        trace_id: str = "",
        is_already_confirmed: bool = False
    ) -> PolicyDecision:
        """
        ADK Callback invoked before any tool execution.
        Verifies permissions, allowlist, and triggers human write confirmation.
        """
        agent = registry.get_agent(agent_id)
        if not agent:
            decision = PolicyDecision(
                allowed=False,
                decision_code="DENY_AGENT_NOT_FOUND",
                reason=f"Agent '{agent_id}' does not exist.",
                rule_name="ADKBeforeTool_AgentCheck"
            )
            observability.log_policy_evaluation(trace_id, user.model_dump(), agent_id, tool_name, "DENIED", decision.reason, decision.rule_name)
            return decision

        # 1. Agent Tool Allowlist Check (Prevents Prompt Injections from calling foreign tools)
        if tool_name not in agent.allowed_tools:
            decision = PolicyDecision(
                allowed=False,
                decision_code="DENY_TOOL_NOT_IN_AGENT_ALLOWLIST",
                reason=f"Security Violation: Tool '{tool_name}' is not in allowed_tools for '{agent.name}'. Prompt injection attempt intercepted.",
                rule_name="ADK_AgentToolAllowlistEnforcer"
            )
            observability.log_policy_evaluation(trace_id, user.model_dump(), agent_id, tool_name, "DENIED", decision.reason, decision.rule_name)
            return decision

        tool = registry.get_tool(tool_name)
        if not tool:
            decision = PolicyDecision(
                allowed=False,
                decision_code="DENY_TOOL_NOT_FOUND",
                reason=f"Tool definition '{tool_name}' not registered.",
                rule_name="ToolExistenceCheck"
            )
            observability.log_policy_evaluation(trace_id, user.model_dump(), agent_id, tool_name, "DENIED", decision.reason, decision.rule_name)
            return decision

        # 2. Tool Enabled Check
        if not getattr(tool, "enabled", True):
            decision = PolicyDecision(
                allowed=False,
                decision_code="DENY_TOOL_DISABLED",
                reason=f"Tool '{tool_name}' is currently disabled in the Tool Registry.",
                rule_name="ToolStateCheck"
            )
            observability.log_policy_evaluation(trace_id, user.model_dump(), agent_id, tool_name, "DENIED", decision.reason, decision.rule_name)
            return decision

        # 3. Tool Role Limit Check
        if hasattr(tool, "allowed_roles") and "*" not in tool.allowed_roles:
            if not any(r in tool.allowed_roles for r in user.roles):
                decision = PolicyDecision(
                    allowed=False,
                    decision_code="DENY_INSUFFICIENT_ROLE",
                    reason=f"Access Denied: Tool '{tool_name}' requires roles {tool.allowed_roles}. Current user roles: {user.roles}.",
                    rule_name="ToolRoleLimitCheck"
                )
                observability.log_policy_evaluation(trace_id, user.model_dump(), agent_id, tool_name, "DENIED", decision.reason, decision.rule_name)
                return decision

        # 4. Role-Based Access Control (RBAC)
        if tool.is_write:
            if "contractor" in user.roles:
                decision = PolicyDecision(
                    allowed=False,
                    decision_code="DENY_INSUFFICIENT_ROLE",
                    reason=f"Access Denied: Contractor persona cannot execute write/mutation tool '{tool_name}'.",
                    rule_name="RBAC_WriteProtection"
                )
                observability.log_policy_evaluation(trace_id, user.model_dump(), agent_id, tool_name, "DENIED", decision.reason, decision.rule_name)
                return decision

            if "it" in tool.tags and not any(r in ["devops_admin", "it_engineer"] for r in user.roles):
                decision = PolicyDecision(
                    allowed=False,
                    decision_code="DENY_INSUFFICIENT_ROLE",
                    reason=f"Access Denied: Role 'devops_admin' required to execute '{tool_name}'.",
                    rule_name="RBAC_DevOpsProtection"
                )
                observability.log_policy_evaluation(trace_id, user.model_dump(), agent_id, tool_name, "DENIED", decision.reason, decision.rule_name)
                return decision

        # 3. Write Operation Human Confirmation Check
        if tool.require_confirmation and not is_already_confirmed:
            decision = PolicyDecision(
                allowed=False,
                requires_confirmation=True,
                decision_code="REQUIRES_CONFIRMATION",
                reason=f"Write operation '{tool_name}' requires human-in-the-loop authorization before mutation.",
                rule_name="HumanInTheLoop_WritePolicy",
                confirmation_payload={
                    "agent_id": agent_id,
                    "tool_name": tool_name,
                    "parameters": tool_parameters,
                    "description": tool.description,
                    "user_sub": user.sub,
                }
            )
            observability.log_policy_evaluation(trace_id, user.model_dump(), agent_id, tool_name, "REQUIRES_CONFIRMATION", decision.reason, decision.rule_name)
            return decision

        # Passed all policy checks
        decision = PolicyDecision(
            allowed=True,
            decision_code="ALLOW",
            reason=f"Tool '{tool_name}' cleared all policy rules.",
            rule_name="PolicyGatePassed"
        )
        observability.log_policy_evaluation(trace_id, user.model_dump(), agent_id, tool_name, "ALLOWED", decision.reason, decision.rule_name)
        return decision

    # Tier 3: API Gateway & Least-Privilege IAM Verification
    def get_agent_gateway_context(self, agent_id: str) -> Dict[str, Any]:
        return AGENT_SERVICE_ACCOUNTS.get(agent_id, {
            "service_account": f"sa-{agent_id}@hackathon-corp.iam.gserviceaccount.com",
            "iam_roles": ["roles/leastPrivilege.consumer"],
            "secret_ref": "projects/12345/secrets/default-gateway-key/versions/latest"
        })

policy_engine = PolicyEngine()
