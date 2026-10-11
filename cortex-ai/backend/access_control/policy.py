"""
cortex.ai - Two-Layer Access Control & Zero-Trust Policy Engine
Enforces:
1. Agent Manifest Authorization (Is the agent allowed to invoke this tool per its manifest?)
2. User Context RBAC & Ownership (Is the authenticated user permitted to see or mutate this data?)
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from agent_registry.registry import agent_registry

class UserContext(BaseModel):
    sub: str
    name: str
    email: str
    role: str # admin, devops_admin, hr_manager, finance_officer, employee, contractor
    department_id: str
    manager_id: Optional[str] = None

class PolicyDecision(BaseModel):
    allowed: bool
    status_code: int
    decision_code: str # ALLOW, DENY_AGENT_MANIFEST, DENY_USER_RBAC, REQUIRES_HUMAN_APPROVAL
    reason: str
    requires_approval: bool = False

# Pre-packaged hackathon demo personas
DEMO_PERSONAS = {
    "bob_ops": UserContext(
        sub="bob_ops",
        name="Bob Martinez",
        email="bob.ops@company.internal",
        role="devops_admin",
        department_id="dept-eng",
        manager_id="sarah_connor"
    ),
    "alice_hr": UserContext(
        sub="alice_hr",
        name="Alice Henderson",
        email="alice.hr@company.internal",
        role="hr_manager",
        department_id="dept-hr",
        manager_id=None
    ),
    "charlie_fin": UserContext(
        sub="charlie_fin",
        name="Charlie Zhao",
        email="charlie.fin@company.internal",
        role="finance_officer",
        department_id="dept-fin",
        manager_id=None
    ),
    "sarah_connor": UserContext(
        sub="sarah_connor",
        name="Sarah Connor",
        email="s.connor@company.internal",
        role="admin",
        department_id="dept-eng",
        manager_id=None
    ),
    "dave_contractor": UserContext(
        sub="dave_contractor",
        name="Dave Miller",
        email="dave.external@partner.com",
        role="contractor",
        department_id="dept-eng",
        manager_id="bob_ops"
    )
}

class AccessControlEngine:
    def evaluate_access(
        self,
        user: UserContext,
        agent_id: str,
        tool_name: str,
        tool_args: Optional[Dict[str, Any]] = None
    ) -> PolicyDecision:
        tool_args = tool_args or {}
        agent = agent_registry.get_agent(agent_id)
        if not agent:
            return PolicyDecision(
                allowed=False,
                status_code=404,
                decision_code="DENY_AGENT_NOT_FOUND",
                reason=f"Agent '{agent_id}' does not exist in registry."
            )

        # ----------------- LAYER A: Agent Manifest Authorization -----------------
        if tool_name not in agent.allowed_tools:
            return PolicyDecision(
                allowed=False,
                status_code=403,
                decision_code="DENY_AGENT_MANIFEST",
                reason=f"Security Policy: Agent '{agent_id}' is NOT authorized to execute '{tool_name}' per its declarative manifest."
            )

        # ----------------- LAYER B: User Identity & RBAC Authorization -----------------
        # Salary / Compensation inspection restrictions
        if "salary" in tool_name or "salaries" in tool_name:
            target_emp = tool_args.get("employee_id")
            if tool_name == "list_all_salaries":
                if user.role not in ["admin", "finance_officer"]:
                    return PolicyDecision(
                        allowed=False,
                        status_code=403,
                        decision_code="DENY_USER_RBAC",
                        reason=f"Access Denied: User '{user.name}' ({user.role}) is unauthorized to inspect enterprise salary rolls."
                    )
            elif tool_name == "get_employee_salary":
                # Allowed if user is admin, finance, or viewing their own salary
                if user.role not in ["admin", "finance_officer"] and target_emp != user.sub:
                    return PolicyDecision(
                        allowed=False,
                        status_code=403,
                        decision_code="DENY_USER_RBAC",
                        reason=f"Access Denied: User '{user.name}' cannot inspect salary data for other employees ('{target_emp}')."
                    )

        # Restricted contractor restrictions
        if user.role == "contractor":
            if any(k in tool_name for k in ["restart", "adjust", "delete", "payout", "send"]):
                return PolicyDecision(
                    allowed=False,
                    status_code=403,
                    decision_code="DENY_USER_RBAC",
                    reason=f"Access Denied: External contractor '{user.name}' is prohibited from running privileged mutation tools."
                )

        return PolicyDecision(
            allowed=True,
            status_code=200,
            decision_code="ALLOW",
            reason=f"Authorized: Agent '{agent_id}' allowed by manifest; user '{user.name}' ({user.role}) cleared by RBAC policy."
        )

access_control = AccessControlEngine()
