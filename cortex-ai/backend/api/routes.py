"""
cortex.ai - Orchestration Gateway REST Routes
Provides endpoints for Chat, Human Approvals, Agent Registry, Tool Catalog, Model Gateway, and Audit Logs.
"""

import uuid
import json
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from agent_registry.registry import agent_registry, AgentManifest
from tool_registry.registry import tool_registry
from model_gateway.provider import model_gateway
from access_control.policy import DEMO_PERSONAS, UserContext, access_control
from guardrails.model_armor import model_armor
from approvals.manager import approval_manager, PendingAction
from router.agent_router import router, SESSION_HISTORY

router_api = APIRouter(prefix="/api")

AUDIT_LOGS: List[Dict[str, Any]] = []

def record_audit(event_type: str, severity: str, user: str, details: Dict[str, Any]):
    event = {
        "event_id": f"evt-{str(uuid.uuid4())[:8]}",
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "severity": severity,
        "user": user,
        "details": details
    }
    AUDIT_LOGS.append(event)
    return event

class ChatRequest(BaseModel):
    prompt: str
    persona: str = "bob_ops"
    session_id: str = "default_session"
    model: Optional[str] = None

class ConfirmActionRequest(BaseModel):
    confirmation_id: str
    action: str = Field("approve", description="'approve' or 'reject'")
    persona: str = "bob_ops"

@router_api.post("/chat", tags=["Chat"])
def handle_chat(req: ChatRequest):
    user = DEMO_PERSONAS.get(req.persona, DEMO_PERSONAS["bob_ops"])
    trace_id = f"trace-{str(uuid.uuid4())[:8]}"
    chosen_model = req.model or model_gateway.get_default_model()

    # 1. Model Armor Safety Screen (Prompt Injection)
    guard_check = model_armor.screen_prompt(req.prompt)
    if not guard_check.is_safe:
        record_audit("PROMPT_INJECTION_BLOCKED", "ALERT", user.sub, {
            "prompt": req.prompt,
            "threat": guard_check.threat_category,
            "details": guard_check.details
        })
        return {
            "reply": f"🛡️ **Security Alert - Model Armor Block**:\n\n{guard_check.details}\nYour request has been halted and logged.",
            "trace_id": trace_id,
            "handled_by": {
                "agent": "model_armor_guardrail",
                "tool": None,
                "reasoning": "Adversarial prompt injection pattern blocked.",
                "model": "model_armor"
            },
            "status": "BLOCKED_BY_GUARDRAIL"
        }

    # 2. Router Intent Detection & Context Recognition
    routing = router.route_query(req.prompt, user, req.session_id)
    if routing.requires_clarification:
        return {
            "reply": routing.clarification_question,
            "trace_id": trace_id,
            "handled_by": {
                "agent": "router",
                "tool": None,
                "reasoning": routing.reasoning,
                "model": chosen_model
            },
            "status": "CLARIFICATION_REQUIRED"
        }

    agent = agent_registry.get_agent(routing.selected_agent_id)
    if not agent:
        from agent_registry.registry import AgentManifest
        agent = AgentManifest(
            id="cortex_assistant",
            name="cortex.ai Digital Assistant",
            owner_team="Platform Core",
            description="Enterprise Digital Assistant & General AI Helper",
            preferred_model=chosen_model
        )
    tool_name = routing.suggested_tool
    tool_args = routing.suggested_args

    # 3. Two-Layer Access Control (Manifest + User RBAC)
    policy_decision = None
    if tool_name:
        policy_decision = access_control.evaluate_access(user, agent.id, tool_name, tool_args)
        
        # Log to audit trail
        record_audit(
            "POLICY_EVALUATION",
            "INFO" if policy_decision.allowed else "WARNING",
            user.sub,
            {
                "agent_id": agent.id,
                "tool_name": tool_name,
                "allowed": policy_decision.allowed,
                "decision_code": policy_decision.decision_code,
                "reason": policy_decision.reason
            }
        )

        if not policy_decision.allowed:
            return {
                "reply": f"🚫 **Access Denied (403)**\n\n{policy_decision.reason}\n\n*Agent `{agent.name}` attempted `{tool_name}` for user `{user.name}` ({user.role})*",
                "trace_id": trace_id,
                "handled_by": {
                    "agent": agent.name,
                    "tool": tool_name,
                    "reasoning": policy_decision.reason,
                    "model": chosen_model
                },
                "status": "DENIED",
                "policy_decision": policy_decision.model_dump()
            }

    # 4. Check Human-in-the-Loop Approval for sensitive actions
    if tool_name and any(k in tool_name for k in ["send", "adjust", "restart", "delete"]):
        pending = approval_manager.create_pending_action(
            action_type="SENSITIVE_MUTATION",
            agent_id=agent.id,
            tool_name=tool_name,
            parameters=tool_args,
            requested_by=user.sub,
            summary=f"Run sensitive operation '{tool_name}' with parameters: {json.dumps(tool_args)}"
        )
        return {
            "reply": (
                f"⚠️ **Human Approval Required**\n\n"
                f"**Agent**: `{agent.name}`\n"
                f"**Operation**: `{tool_name}`\n"
                f"**Parameters**: `{json.dumps(tool_args)}`\n\n"
                f"Please review and approve this action in the interface."
            ),
            "trace_id": trace_id,
            "handled_by": {
                "agent": agent.name,
                "tool": tool_name,
                "reasoning": "Sensitive mutation requires human approval.",
                "model": chosen_model
            },
            "status": "PENDING_APPROVAL",
            "pending_approval": pending.model_dump()
        }

    # 5. Execute Tool or Generate Response
    tool_result = None
    download_card = None
    email_draft_card = None

    def _get_m365():
        import importlib.util
        root_dir = Path(__file__).resolve().parent.parent.parent.parent
        m365_path = root_dir / "integrations" / "m365-connector" / "src" / "main.py"
        spec = importlib.util.spec_from_file_location("m365_conn_main", m365_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    if tool_name == "generate_powerpoint_presentation":
        m365 = _get_m365()
        ppt_res = m365.generate_powerpoint_presentation(m365.PowerPointRequest(**tool_args))
        download_card = {
            "file_name": ppt_res["file_name"],
            "file_type": "pptx",
            "download_url": ppt_res["download_url"],
            "slide_count": ppt_res["slide_count"],
            "title": tool_args.get("deck_title", "PowerPoint Presentation")
        }
        tool_result = ppt_res
        reply = (
            f"📊 **Presentation Generated Successfully** by `{agent.name}`:\n\n"
            f"**File**: `{ppt_res['file_name']}` ({ppt_res['slide_count']} slides)\n"
            f"**Topic**: {tool_args.get('deck_title')}\n\n"
            f"Download your presentation using the card below."
        )

    elif tool_name == "generate_word_document":
        m365 = _get_m365()
        doc_res = m365.generate_word_document(m365.WordDocRequest(**tool_args))
        download_card = {
            "file_name": doc_res["file_name"],
            "file_type": "docx",
            "download_url": doc_res["download_url"],
            "title": tool_args.get("title", "Word Document")
        }
        tool_result = doc_res
        reply = f"📝 **Word Document Compiled Successfully** by `{agent.name}`:\n\n**File**: `{doc_res['file_name']}`"

    elif tool_name == "create_email_draft":
        m365 = _get_m365()
        draft_res = m365.create_email_draft(m365.EmailDraftRequest(**tool_args))
        email_draft_card = draft_res
        
        # Trigger human approval before actual sending
        pending = approval_manager.create_pending_action(
            action_type="EMAIL_SEND",
            agent_id=agent.id,
            tool_name="send_email",
            parameters={"draft_id": draft_res["draft_id"]},
            requested_by=user.sub,
            summary=f"Send drafted Outlook email to '{draft_res['recipient_email']}' regarding '{draft_res['subject']}'"
        )
        reply = (
            f"✉️ **Outlook Email Draft Created** by `{agent.name}`:\n\n"
            f"**To**: `{draft_res['recipient_email']}`\n"
            f"**Subject**: {draft_res['subject']}\n"
            f"**Body**:\n> {draft_res['body'].replace(chr(10), chr(10) + '> ')}\n\n"
            f"🔒 *In accordance with security policy, emails are never sent automatically. Click **Approve & Send** below to disburse.*"
        )
        return {
            "reply": reply,
            "trace_id": trace_id,
            "handled_by": {
                "agent": agent.name,
                "tool": "create_email_draft",
                "reasoning": routing.reasoning,
                "model": chosen_model
            },
            "status": "DRAFT_SAVED",
            "email_draft": email_draft_card,
            "pending_approval": pending.model_dump()
        }

    elif tool_name == "get_leave_balance":
        from database.firestore_client import db
        doc = db.collection("leave_balances").document(f"bal-{user.sub}").get()
        bal_data = doc.to_dict() if doc.exists else {"annual_pto_total": 20, "annual_pto_used": 6, "remaining_pto": 14}
        rem = bal_data.get("annual_pto_total", 20) - bal_data.get("annual_pto_used", 0)
        reply = (
            f"🌴 **Leave Balance for {user.name}**:\n\n"
            f"- **Annual PTO Total**: {bal_data.get('annual_pto_total', 20)} days\n"
            f"- **Consumed PTO**: {bal_data.get('annual_pto_used', 6)} days\n"
            f"- **Remaining Available PTO**: **{rem} days**\n"
            f"- **Sick Leave Allotment**: 10 days"
        )
        tool_result = bal_data

    elif tool_name == "get_ticket":
        from database.firestore_client import db
        ticket_key = tool_args.get("ticket_key", "PROJ-102")
        doc = db.collection("jira_tickets").document(ticket_key).get()
        t_data = doc.to_dict() if doc.exists else {"ticket_key": ticket_key, "title": "Payment webhook latency", "status": "IN_PROGRESS", "priority": "HIGH"}
        reply = (
            f"🎫 **Jira Ticket Details [{ticket_key}]**:\n\n"
            f"- **Title**: {t_data.get('title')}\n"
            f"- **Priority**: `{t_data.get('priority')}`\n"
            f"- **Status**: `{t_data.get('status')}`\n"
            f"- **Assignee**: `{t_data.get('assignee_id', 'Unassigned')}`\n"
            f"- **Description**: {t_data.get('description', '')}"
        )
        tool_result = t_data

    elif tool_name == "get_employee_salary":
        from database.firestore_client import db
        doc = db.collection("salaries").document(f"sal-{tool_args.get('employee_id', user.sub)}").get()
        sal_data = doc.to_dict() if doc.exists else {"base_salary": 165000.0, "currency": "USD", "bank_account_masked": "****4821"}
        reply = (
            f"💰 **Confidential Salary Record**:\n\n"
            f"- **Employee**: `{sal_data.get('employee_id')}`\n"
            f"- **Base Salary**: **${sal_data.get('base_salary'):,.2f} {sal_data.get('currency')}**\n"
            f"- **Disbursement Account**: `{sal_data.get('bank_account_masked')}`\n"
            f"- **Bonus Target**: {sal_data.get('bonus_target_pct', 0)}%"
        )
        tool_result = sal_data

    else:
        # Conversational generation using Model Gateway
        system_inst = (
            "You are cortex.ai, an intelligent enterprise AI assistant and digital workplace integration hub. "
            "Answer general questions (weather, general knowledge, creative writing, explanations, code) "
            "naturally, conversationally, and accurately. "
            "For organizational operations, you can also connect to HR, IT Jira, Finance, Ops, and Microsoft 365 tools."
        )
        model_res = model_gateway.generate(
            prompt=req.prompt,
            preferred_model=chosen_model,
            fallback_models=agent.fallback_models,
            system_instruction=system_inst
        )
        reply = model_res.get("text") or f"Hello {user.name}! I am **{agent.name}** ({agent.owner_team}).\n\nHow can I help you today?"
        chosen_model = model_res.get("model", chosen_model)

    # Screen response through Model Armor for PII masking
    screened_reply = model_armor.screen_response(reply)

    return {
        "reply": screened_reply,
        "trace_id": trace_id,
        "handled_by": {
            "agent": agent.name,
            "agent_id": agent.id,
            "tool": tool_name,
            "reasoning": routing.reasoning,
            "model": chosen_model
        },
        "status": "SUCCESS",
        "tool_result": tool_result,
        "download_card": download_card,
        "email_draft": email_draft_card,
        "policy_decision": policy_decision.model_dump() if policy_decision else None
    }

@router_api.post("/chat/confirm", tags=["Approvals"])
def confirm_action(req: ConfirmActionRequest):
    approved = req.action.lower() == "approve"
    action = approval_manager.resolve_action(req.confirmation_id, approved, req.persona)
    if not action:
        raise HTTPException(status_code=404, detail="Confirmation ID not found")
    
    user = DEMO_PERSONAS.get(req.persona, DEMO_PERSONAS["bob_ops"])
    record_audit(
        "HUMAN_WRITE_CONFIRMATION",
        "NOTICE",
        user.sub,
        {"confirmation_id": req.confirmation_id, "decision": action.status, "action": action.tool_name}
    )

    if approved:
        return {
            "status": "APPROVED_AND_EXECUTED",
            "message": f"Operation '{action.tool_name}' was approved by {user.name} and successfully executed.",
            "action": action.model_dump()
        }
    return {
        "status": "REJECTED_AND_CANCELLED",
        "message": f"Operation '{action.tool_name}' was rejected and halted.",
        "action": action.model_dump()
    }

class SwaggerGenerateRequest(BaseModel):
    agent_name: str = Field(..., description="Display name for the agent")
    agent_id: Optional[str] = None
    author: Optional[str] = "Enterprise Developer"
    author_id: Optional[str] = "bob_ops"
    owner_team: Optional[str] = "Operations"
    allowed_roles: Optional[List[str]] = None
    base_url: Optional[str] = "http://127.0.0.1:8000"
    swagger_json: Optional[str] = None
    url: Optional[str] = None

class AgentAccessUpdateRequest(BaseModel):
    allowed_roles: Optional[List[str]] = None
    allowed_teams: Optional[List[str]] = None
    active: Optional[bool] = None

class ToolAccessUpdateRequest(BaseModel):
    allowed_roles: Optional[List[str]] = None
    enabled: Optional[bool] = None
    requires_human_approval: Optional[bool] = None

@router_api.get("/agents", tags=["Registry"])
def list_agents(
    q: Optional[str] = None,
    scope: Optional[str] = None,
    persona: Optional[str] = "bob_ops"
):
    user = DEMO_PERSONAS.get(persona, DEMO_PERSONAS.get("bob_ops"))
    dept_map = {
        "dept-eng": "Operations",
        "dept-hr": "HR Operations",
        "dept-fin": "Corporate Finance",
        "dept-sec": "Security"
    }
    user_team = dept_map.get(getattr(user, "department_id", ""), "") if user else None
    user_id = user.sub if user else persona
    agents = agent_registry.search_agents(
        query=q,
        scope=scope,
        persona_id=user_id,
        persona_team=user_team
    )
    return {"agents": [a.model_dump() for a in agents]}

@router_api.post("/agents/onboard", tags=["Registry"])
def onboard_agent(manifest: AgentManifest):
    reg = agent_registry.register_agent(manifest)
    return {"status": "onboarded", "agent": reg.model_dump()}

@router_api.post("/agents/generate-from-swagger", tags=["Registry"])
def generate_agent_from_swagger(req: SwaggerGenerateRequest):
    from tool_factory.generator import tool_factory
    spec = {}
    if req.swagger_json:
        try:
            spec = json.loads(req.swagger_json)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON in swagger_json: {str(e)}")
    elif req.url:
        try:
            r = httpx.get(req.url, timeout=10.0)
            spec = r.json()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to fetch OpenAPI spec from URL: {str(e)}")
    else:
        raise HTTPException(status_code=400, detail="Must provide swagger_json or url")

    res = tool_factory.generate_agent_and_tools(
        openapi_dict=spec,
        agent_name=req.agent_name,
        agent_id=req.agent_id,
        author=req.author or "Enterprise Developer",
        author_id=req.author_id or "bob_ops",
        owner_team=req.owner_team or "Operations",
        allowed_roles=req.allowed_roles or ["*"],
        base_url=req.base_url or "http://127.0.0.1:8000"
    )
    return res

@router_api.put("/agents/{agent_id}/access", tags=["Registry"])
def update_agent_access(agent_id: str, req: AgentAccessUpdateRequest):
    res = agent_registry.update_access(
        agent_id=agent_id,
        allowed_roles=req.allowed_roles,
        allowed_teams=req.allowed_teams,
        active=req.active
    )
    if not res:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"status": "updated", "agent": res.model_dump()}

@router_api.delete("/agents/{agent_id}", tags=["Registry"])
def delete_agent(agent_id: str):
    success = agent_registry.delete_agent(agent_id)
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"status": "deleted", "agent_id": agent_id}

@router_api.put("/tools/{tool_name}/access", tags=["Tool Registry"])
def update_tool_access(tool_name: str, req: ToolAccessUpdateRequest):
    res = tool_registry.update_access(
        tool_name=tool_name,
        allowed_roles=req.allowed_roles,
        enabled=req.enabled,
        requires_human_approval=req.requires_human_approval
    )
    if not res:
        raise HTTPException(status_code=404, detail="Tool not found")
    return {"status": "updated", "tool": res.model_dump()}


@router_api.get("/tools", tags=["Tool Registry"])
def list_tools():
    return {"tools": [t.model_dump() for t in tool_registry.list_tools()]}

@router_api.get("/models", tags=["Model Gateway"])
def list_models():
    return {
        "models": model_gateway.get_available_models(),
        "default_model": model_gateway.get_default_model(),
        "active_models": list(model_gateway.providers.keys())
    }

@router_api.get("/audit", tags=["Observability"])
def get_audit_trail():
    return {"events": AUDIT_LOGS[-50:]}

@router_api.get("/prompts", tags=["Prompt Library"])
def list_prompt_library():
    from prompts.library import get_prompt_library
    return get_prompt_library()


# ==========================================
# WORKSPACES & SDD AUTONOMOUS ENGINE ROUTES
# ==========================================

from workspaces.manager import workspace_manager


class CreateWorkspaceRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    workspace_type: str = Field("chat", description="'chat' or 'sdd'")
    visibility: str = Field("public", description="'public' or 'private'")
    invited_employee_ids: List[str] = Field(default_factory=list)
    system_instructions: Optional[str] = None
    sdd_config: Optional[Dict[str, Any]] = None
    initial_prompt: Optional[str] = None


class WorkspaceInviteRequest(BaseModel):
    employee_ids: List[str]


class SDDRulesUpdateRequest(BaseModel):
    architecture_principles: List[str]
    coding_standards: List[str] = Field(default_factory=list)


class WorkspaceInstructionsRequest(BaseModel):
    system_instructions: str


class WorkspaceChatRequest(BaseModel):
    prompt: str
    persona: str = "bob_ops"


class UpdateSpecRequest(BaseModel):
    raw_markdown: str
    requirements: List[Dict[str, Any]] = Field(default_factory=list)


class AIGenerateSpecRequest(BaseModel):
    prompt: str


class UpdatePlanRequest(BaseModel):
    raw_markdown: str
    data_models: List[Dict[str, Any]] = Field(default_factory=list)
    api_endpoints: List[Dict[str, Any]] = Field(default_factory=list)


class AIGeneratePlanRequest(BaseModel):
    prompt: str


class UpdateTasksRequest(BaseModel):
    tasks: List[Dict[str, Any]]


class AddTaskRequest(BaseModel):
    task_id: Optional[str] = None
    title: str
    description: Optional[str] = ""
    linked_req_id: Optional[str] = None
    target_files: List[str] = Field(default_factory=list)
    test_file: Optional[str] = None


@router_api.get("/employees", tags=["Workspaces"])
def list_company_employees():
    return {"employees": workspace_manager.list_employees()}


@router_api.get("/workspaces", tags=["Workspaces"])
@router_api.get("/pods", tags=["Pods"])
def list_workspaces(filter: str = "public", persona: str = "bob_ops", search: str = ""):
    workspaces = workspace_manager.list_workspaces(filter_type=filter, current_user=persona, search=search)
    return {"workspaces": workspaces, "filter": filter, "count": len(workspaces)}


@router_api.post("/workspaces", tags=["Workspaces"])
@router_api.post("/pods", tags=["Pods"])
def create_workspace(req: CreateWorkspaceRequest, persona: str = "bob_ops"):
    payload = req.model_dump()
    new_ws = workspace_manager.create_workspace(payload, current_user_id=persona)
    record_audit(
        event_type="WORKSPACE_CREATED",
        severity="INFO",
        user=persona,
        details={"workspace_id": new_ws["workspace_id"], "name": new_ws["name"], "type": new_ws["workspace_type"]}
    )
    return {"status": "created", "workspace": new_ws}


@router_api.get("/workspaces/{workspace_id}", tags=["Workspaces"])
@router_api.get("/pods/{workspace_id}", tags=["Pods"])
def get_workspace_details(workspace_id: str):
    ws = workspace_manager.get_workspace(workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return ws


@router_api.delete("/workspaces/{workspace_id}", tags=["Workspaces"])
@router_api.delete("/pods/{workspace_id}", tags=["Pods"])
def delete_workspace(workspace_id: str, persona: str = "bob_ops"):
    try:
        success = workspace_manager.delete_workspace(workspace_id, current_user=persona)
        if not success:
            raise HTTPException(status_code=404, detail="Workspace not found")
        return {"status": "deleted", "workspace_id": workspace_id}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))


@router_api.post("/workspaces/{workspace_id}/invite", tags=["Workspaces"])
@router_api.post("/pods/{workspace_id}/invite", tags=["Pods"])
def invite_workspace_contributors(workspace_id: str, req: WorkspaceInviteRequest, persona: str = "bob_ops"):
    try:
        updated_ws = workspace_manager.invite_contributors(workspace_id, req.employee_ids, requester_id=persona)
        return {"status": "updated", "workspace": updated_ws}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@router_api.put("/workspaces/{workspace_id}/instructions", tags=["Workspaces"])
@router_api.put("/pods/{workspace_id}/instructions", tags=["Pods"])
def update_workspace_instructions(workspace_id: str, req: WorkspaceInstructionsRequest, persona: str = "bob_ops"):
    try:
        updated_ws = workspace_manager.update_instructions(workspace_id, req.system_instructions, requester_id=persona)
        return {"status": "updated", "workspace": updated_ws}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@router_api.put("/workspaces/{workspace_id}/sdd/rules", tags=["Workspaces"])
@router_api.put("/pods/{workspace_id}/sdd/rules", tags=["Pods"])
def update_sdd_rules(workspace_id: str, req: SDDRulesUpdateRequest, persona: str = "bob_ops"):
    try:
        updated_ws = workspace_manager.update_sdd_rules(
            workspace_id,
            principles=req.architecture_principles,
            standards=req.coding_standards,
            user_id=persona
        )
        return {"status": "updated", "workspace": updated_ws}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


# SPECIFICATION APIS (PERSISTED IN FIRESTORE)
@router_api.put("/workspaces/{workspace_id}/spec", tags=["Workspaces"])
@router_api.put("/pods/{workspace_id}/spec", tags=["Pods"])
def update_spec(workspace_id: str, req: UpdateSpecRequest, persona: str = "bob_ops"):
    try:
        updated = workspace_manager.update_spec(workspace_id, req.raw_markdown, req.requirements, user_id=persona)
        return {"status": "updated", "workspace": updated}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router_api.post("/workspaces/{workspace_id}/spec/ai-generate", tags=["Workspaces"])
@router_api.post("/pods/{workspace_id}/spec/ai-generate", tags=["Pods"])
def ai_generate_spec(workspace_id: str, req: AIGenerateSpecRequest, persona: str = "bob_ops"):
    try:
        updated = workspace_manager.ai_generate_spec(workspace_id, req.prompt, user_id=persona)
        return {"status": "generated", "workspace": updated}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ARCHITECTURE PLAN APIS (PERSISTED IN FIRESTORE)
@router_api.put("/workspaces/{workspace_id}/plan", tags=["Workspaces"])
@router_api.put("/pods/{workspace_id}/plan", tags=["Pods"])
def update_plan(workspace_id: str, req: UpdatePlanRequest, persona: str = "bob_ops"):
    try:
        updated = workspace_manager.update_plan(workspace_id, req.raw_markdown, req.data_models, req.api_endpoints, user_id=persona)
        return {"status": "updated", "workspace": updated}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router_api.post("/workspaces/{workspace_id}/plan/ai-generate", tags=["Workspaces"])
@router_api.post("/pods/{workspace_id}/plan/ai-generate", tags=["Pods"])
def ai_generate_plan(workspace_id: str, req: AIGeneratePlanRequest, persona: str = "bob_ops"):
    try:
        updated = workspace_manager.ai_generate_plan(workspace_id, req.prompt, user_id=persona)
        return {"status": "generated", "workspace": updated}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# TASKS APIS (PERSISTED IN FIRESTORE)
@router_api.put("/workspaces/{workspace_id}/tasks", tags=["Workspaces"])
@router_api.put("/pods/{workspace_id}/tasks", tags=["Pods"])
def update_tasks(workspace_id: str, req: UpdateTasksRequest, persona: str = "bob_ops"):
    try:
        updated = workspace_manager.update_tasks(workspace_id, req.tasks, user_id=persona)
        return {"status": "updated", "workspace": updated}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router_api.post("/workspaces/{workspace_id}/tasks", tags=["Workspaces"])
@router_api.post("/pods/{workspace_id}/tasks", tags=["Pods"])
def add_task(workspace_id: str, req: AddTaskRequest, persona: str = "bob_ops"):
    try:
        updated = workspace_manager.add_task(workspace_id, req.model_dump(), user_id=persona)
        return {"status": "added", "workspace": updated}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router_api.post("/workspaces/{workspace_id}/tasks/ai-breakdown", tags=["Workspaces"])
@router_api.post("/pods/{workspace_id}/tasks/ai-breakdown", tags=["Pods"])
def ai_breakdown_tasks(workspace_id: str, persona: str = "bob_ops"):
    try:
        updated = workspace_manager.ai_breakdown_tasks(workspace_id, user_id=persona)
        return {"status": "breakdown_complete", "workspace": updated}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# AUTONOMOUS EXECUTION ENGINES
@router_api.post("/workspaces/{workspace_id}/sdd/init-repo", tags=["Workspaces"])
@router_api.post("/pods/{workspace_id}/sdd/init-repo", tags=["Pods"])
def init_sdd_repo(workspace_id: str, persona: str = "bob_ops"):
    try:
        res = workspace_manager.init_or_clone_repo(workspace_id, requester_id=persona)
        record_audit(
            event_type="SDD_REPO_INITIALIZED",
            severity="INFO",
            user=persona,
            details={"workspace_id": workspace_id, "local_path": res.get("local_path")}
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router_api.post("/workspaces/{workspace_id}/sdd/implement-task", tags=["Workspaces"])
@router_api.post("/pods/{workspace_id}/sdd/implement-task", tags=["Pods"])
def implement_sdd_task(workspace_id: str, task_id: str = "TSK-101", persona: str = "bob_ops"):
    try:
        res = workspace_manager.implement_task(workspace_id, task_id=task_id, requester_id=persona)
        record_audit(
            event_type="SDD_TASK_IMPLEMENTED",
            severity="INFO",
            user=persona,
            details={"workspace_id": workspace_id, "task_id": task_id, "commit_hash": res.get("commit_hash")}
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router_api.post("/workspaces/{workspace_id}/sdd/run-tests", tags=["Workspaces"])
@router_api.post("/pods/{workspace_id}/sdd/run-tests", tags=["Pods"])
def run_sdd_tests(workspace_id: str, persona: str = "bob_ops"):
    try:
        return workspace_manager.run_tests(workspace_id, requester_id=persona)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router_api.post("/workspaces/{workspace_id}/chat", tags=["Workspaces"])
@router_api.post("/pods/{workspace_id}/chat", tags=["Pods"])
def chat_in_workspace(workspace_id: str, req: WorkspaceChatRequest):
    try:
        res = workspace_manager.send_chat_message(workspace_id, prompt=req.prompt, persona=req.persona)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==========================================
# SYSTEM FILE EXPLORER & FOLDER PICKER ROUTES
# ==========================================
from system_utils import open_folder_in_os, pick_folder_dialog


class OpenFolderRequest(BaseModel):
    path: str


class PickFolderRequest(BaseModel):
    initial_dir: Optional[str] = None


@router_api.post("/system/open-folder", tags=["System"])
def open_system_folder(req: OpenFolderRequest):
    folder_path = req.path.strip()
    if not folder_path:
        raise HTTPException(status_code=400, detail="Path cannot be empty")
    try:
        opened_path = open_folder_in_os(folder_path)
        return {"status": "opened", "path": opened_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to open folder: {str(e)}")


@router_api.post("/system/pick-folder", tags=["System"])
def pick_system_folder(req: Optional[PickFolderRequest] = None):
    initial_dir = req.initial_dir if req else None
    selected = pick_folder_dialog(initial_dir=initial_dir)
    return {"status": "ok", "path": selected}




