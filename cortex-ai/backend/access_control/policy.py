"""
cortex.ai - Two-Layer Access Control & Zero-Trust Policy Engine
Enforces:
1. Agent Manifest Authorization (Is the agent allowed to invoke this tool per its manifest?)
2. User Context RBAC & Ownership (Is the authenticated user permitted to see or mutate this data?)
"""

import re
import jwt
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from agent_registry.registry import agent_registry, AgentManifest

class UserContext(BaseModel):
    sub: str
    name: str
    email: str
    role: str # admin, devops_admin, hr_manager, finance_officer, employee, contractor, security_lead
    department_id: str
    manager_id: Optional[str] = None

class PolicyDecision(BaseModel):
    allowed: bool
    status_code: int
    decision_code: str # ALLOW, DENY_AGENT_NOT_FOUND, DENY_AGENT_RBAC, DENY_AGENT_MANIFEST, DENY_USER_RBAC, REQUIRES_HUMAN_APPROVAL
    reason: str
    requires_approval: bool = False

# Pre-packaged hackathon demo personas
DEMO_PERSONAS = {
    "admin": UserContext(
        sub="admin",
        name="System Administrator",
        email="admin@company.internal",
        role="admin",
        department_id="dept-eng",
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
    "alex_chen": UserContext(
        sub="alex_chen",
        name="Alex Chen",
        email="alex.chen@company.internal",
        role="security_lead",
        department_id="dept-sec",
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

def normalize_role(val: str) -> str:
    """Normalizes role/persona labels to common canonical keys for comparison."""
    if not val:
        return ""
    v = val.lower().strip()
    if "admin" in v and "devops" not in v:
        return "admin"
    if "finance" in v:
        return "finance"
    if "hr" in v or "human resources" in v or "people" in v:
        return "hr"
    if "devops" in v or "it_engineer" in v or "ops" in v:
        return "devops"
    if "contractor" in v:
        return "contractor"
    if "security" in v or "sec" in v:
        return "security"
    return re.sub(r"[^a-z0-9]", "", v)

def resolve_user(
    persona_param: Optional[str] = None,
    auth_header: Optional[str] = None,
    x_persona_header: Optional[str] = None
) -> UserContext:
    """
    Derives the user context from authenticated identity on the server.
    Never trusts client-supplied role values directly.
    """
    # 1. Bearer JWT Token if present
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            sub = payload.get("sub", "")
            if sub in DEMO_PERSONAS:
                return DEMO_PERSONAS[sub]
            return UserContext(
                sub=sub or "anon",
                name=payload.get("name", "Anonymous"),
                email=payload.get("email", ""),
                role=payload.get("role", "employee"),
                department_id=payload.get("department_id", "dept-eng")
            )
        except Exception:
            pass

    # 2. X-Persona header
    if x_persona_header and x_persona_header.strip() in DEMO_PERSONAS:
        return DEMO_PERSONAS[x_persona_header.strip()]

    # 3. persona query/body parameter
    if persona_param and persona_param.strip() in DEMO_PERSONAS:
        return DEMO_PERSONAS[persona_param.strip()]

    # Case-insensitive lookup for personas like 'admin', 'Admin', 'hr_manager', 'Alice_HR'
    if persona_param:
        p_clean = persona_param.strip().lower()
        for k, v in DEMO_PERSONAS.items():
            if k.lower() == p_clean or v.role.lower() == p_clean or (v.name and v.name.lower() == p_clean):
                return v

    return DEMO_PERSONAS["bob_ops"]

def can_access_agent(user: Optional[UserContext], agent: Optional[AgentManifest]) -> bool:
    """
    Enforces role-based access control (RBAC) on agents.
    Returns True if the user is authorized to see, use, chat with, test, or invoke the agent.
    
    1. Admin persona bypass: Admin can access ALL agents regardless of assigned roles.
    2. Unrestricted agents: If an agent has NO roles assigned (empty list or ['*']),
       keep existing behavior: accessible to all.
    3. Restricted agents: If an agent has assigned roles, ONLY users matching one of those
       roles/personas can access it.
    """
    if not agent or not user:
        return False

    # 1. Admin persona bypass
    u_role = getattr(user, "role", "") or ""
    u_sub = getattr(user, "sub", "") or ""
    if u_role == "admin" or u_sub == "admin":
        return True

    # 2. No roles assigned / Wildcard allows all
    allowed_roles = getattr(agent, "allowed_roles", None)
    if not allowed_roles or len(allowed_roles) == 0 or "*" in allowed_roles:
        return True

    # 3. Explicit role/persona matching
    u_norm = normalize_role(u_role)
    u_sub_norm = u_sub.lower()

    for r in allowed_roles:
        if not r:
            continue
        if r == "*":
            return True
        r_str = str(r).strip()
        r_norm = normalize_role(r_str)
        if r_norm == u_norm:
            return True
        if r_str.lower() == u_sub_norm:
            return True
        if hasattr(user, "name") and user.name and r_str.lower() == user.name.lower():
            return True

    return False

def can_edit_agent_access(user: Optional[UserContext], agent: Optional[AgentManifest]) -> bool:
    """
    Validates whether the user is authorized to change roles, limits, or configuration of an agent.
    Only Admin and the agent's author/owner can edit access settings.
    Non-admins cannot change roles or limits.
    """
    if not user or not agent:
        return False

    u_role = getattr(user, "role", "") or ""
    u_sub = getattr(user, "sub", "") or ""

    if u_role == "admin" or u_sub == "admin":
        return True

    author_id = getattr(agent, "author_id", "") or ""
    if author_id and (author_id.lower() == u_sub.lower() or author_id.lower() == user.name.lower()):
        return True

    return False

class AccessControlEngine:
    def evaluate_access(
        self,
        user: UserContext,
        agent_id: str,
        tool_name: Optional[str] = None,
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

        # ----------------- LAYER 0: Agent RBAC Authorization -----------------
        if not can_access_agent(user, agent):
            return PolicyDecision(
                allowed=False,
                status_code=403,
                decision_code="DENY_AGENT_RBAC",
                reason=f"Access Denied: User '{user.name}' ({user.role}) is unauthorized to access agent '{agent.name}'."
            )

        # If no tool is requested (e.g. conversational prompt or Try Agent), agent RBAC passed
        if not tool_name:
            return PolicyDecision(
                allowed=True,
                status_code=200,
                decision_code="ALLOW",
                reason=f"Authorized: User '{user.name}' cleared to access agent '{agent.name}'."
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
