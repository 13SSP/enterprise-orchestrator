import uuid
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, Field

from app.core.registry import registry, AgentManifest, ToolDefinition
from app.core.tool_builder import OpenAPIImporter, SAMPLE_DEV_OPS_SWAGGER
from app.core.policy import policy_engine, DEMO_PERSONAS, UserContext
from app.core.rag import rag_manager, KnowledgeDocument
from app.core.observability import observability
from app.core.orchestrator import orchestrator

router = APIRouter(prefix="/api")

# Pydantic Schemas for Requests
class ChatRequest(BaseModel):
    prompt: str
    persona: str = "devops_admin"
    token: Optional[str] = None
    confirmed_action_id: Optional[str] = None

class ConfirmActionRequest(BaseModel):
    confirmation_id: str
    action: str = Field("approve", description="'approve' or 'reject'")
    persona: str = "devops_admin"

class ImportSwaggerRequest(BaseModel):
    spec_content: Optional[str] = None
    spec_url: Optional[str] = None
    target_agent_id: Optional[str] = None

class GenerateAgentSwaggerRequest(BaseModel):
    spec_content: Optional[str] = None
    spec_url: Optional[str] = None
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    agent_description: Optional[str] = None
    system_prompt: Optional[str] = None
    owner_team: Optional[str] = "Engineering"
    author: Optional[str] = None
    author_id: Optional[str] = None
    icon: Optional[str] = "wrench"
    is_public: bool = True
    allowed_roles: List[str] = ["*"]
    allowed_teams: List[str] = ["*"]
    tool_overrides: Optional[Dict[str, Dict[str, Any]]] = None
    auto_register: bool = True

class UpdateAgentAccessRequest(BaseModel):
    is_public: bool = True
    allowed_roles: List[str] = ["*"]
    allowed_teams: List[str] = ["*"]

class UpdateToolAccessRequest(BaseModel):
    enabled: bool = True
    require_confirmation: bool = False
    allowed_roles: List[str] = ["*"]

class DocumentUploadRequest(BaseModel):
    title: str
    scope: str
    content: str
    tags: List[str] = []
    source_type: str = "document_ai_pdf"

def resolve_user(persona_key: str, token: Optional[str] = None) -> UserContext:
    if token:
        user = policy_engine.decode_jwt(token)
        if user:
            return user
    return policy_engine.get_persona_user(persona_key)

# ----------------- Chat & Orchestration -----------------

@router.post("/chat")
def handle_chat(req: ChatRequest):
    user = resolve_user(req.persona, req.token)
    response = orchestrator.execute_chat(
        prompt=req.prompt,
        user=user,
        confirmed_action_id=req.confirmed_action_id
    )
    return response

@router.post("/chat/confirm")
def handle_action_confirmation(req: ConfirmActionRequest):
    user = resolve_user(req.persona)
    if req.action.lower() == "approve":
        return orchestrator.execute_chat(
            prompt="[Action Confirmed by User]",
            user=user,
            confirmed_action_id=req.confirmation_id
        )
    else:
        return orchestrator.cancel_pending_action(req.confirmation_id, user)

# ----------------- Agent Onboarding & Registry -----------------

@router.get("/agents")
def list_agents(search: Optional[str] = None):
    agents = registry.list_agents()
    if search:
        s = search.lower().strip()
        agents = [
            a for a in agents 
            if s in a.name.lower() or s in a.description.lower() or s in a.owner_team.lower() or (a.author and s in a.author.lower())
        ]
    return {"agents": [a.model_dump() for a in agents]}

@router.post("/agents/generate-from-swagger")
def generate_agent_from_swagger(req: GenerateAgentSwaggerRequest):
    trace_id = str(uuid.uuid4())
    try:
        if req.spec_url:
            spec_data = OpenAPIImporter.fetch_from_url(req.spec_url)
        elif req.spec_content:
            spec_data = OpenAPIImporter.parse_spec_content(req.spec_content)
        else:
            raise HTTPException(status_code=400, detail="Either spec_content or spec_url must be provided.")

        manifest, tools, meta = OpenAPIImporter.generate_agent_and_tools(
            spec_data=spec_data,
            author=req.author,
            author_id=req.author_id,
            owner_team=req.owner_team,
            agent_id_override=req.agent_id,
            agent_name_override=req.agent_name,
            agent_description_override=req.agent_description,
            system_prompt_override=req.system_prompt,
            icon=req.icon or "wrench",
            is_public=req.is_public,
            allowed_roles=req.allowed_roles,
            allowed_teams=req.allowed_teams,
            tool_overrides=req.tool_overrides,
            auto_register=req.auto_register
        )

        observability.log_event(
            event_type="AGENT_CREATED_FROM_SWAGGER",
            severity="NOTICE",
            message=f"Agent '{manifest.name}' ({manifest.id}) auto-generated from OpenAPI spec with {len(manifest.allowed_tools)} tools",
            details={
                "agent": manifest.model_dump(),
                "tools_count": len(tools),
                "is_public": manifest.is_public,
                "allowed_roles": manifest.allowed_roles,
                "metadata": meta
            },
            trace_id=trace_id
        )

        return {
            "status": "success",
            "agent": manifest.model_dump(),
            "tools": [t.model_dump() for t in tools],
            "metadata": meta,
            "trace_id": trace_id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to generate agent from Swagger: {str(e)}")

@router.put("/agents/{agent_id}/access")
def update_agent_access(agent_id: str, req: UpdateAgentAccessRequest):
    agent = registry.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent.is_public = req.is_public
    agent.allowed_roles = req.allowed_roles
    agent.allowed_teams = req.allowed_teams
    registry.register_agent(agent)
    return {"status": "success", "agent": agent.model_dump()}

@router.put("/tools/{tool_name}/access")
def update_tool_access(tool_name: str, req: UpdateToolAccessRequest):
    tool = registry.get_tool(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    tool.enabled = req.enabled
    tool.require_confirmation = req.require_confirmation
    tool.allowed_roles = req.allowed_roles
    registry.register_tool(tool)
    return {"status": "success", "tool": tool.model_dump()}

@router.post("/agents/onboard")
def onboard_agent(manifest: AgentManifest):
    # Store in registry
    registered = registry.register_agent(manifest)
    
    # Log in observability
    trace_id = str(uuid.uuid4())
    observability.log_event(
        event_type="AGENT_ONBOARDED",
        severity="NOTICE",
        message=f"New agent '{manifest.name}' ({manifest.id}) onboarded by team '{manifest.owner_team}'",
        details=manifest.model_dump(),
        trace_id=trace_id,
        user={"sub": f"team_{manifest.owner_team.lower().replace(' ', '_')}"}
    )
    return {"status": "success", "agent": registered.model_dump(), "trace_id": trace_id}

@router.delete("/agents/{agent_id}")
def delete_agent(agent_id: str):
    success = registry.delete_agent(agent_id)
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"status": "deleted", "agent_id": agent_id}

@router.post("/agents/{agent_id}/toggle")
def toggle_agent(agent_id: str):
    agent = registry.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent.active = not agent.active
    registry.register_agent(agent)
    return {"status": "success", "agent_id": agent_id, "active": agent.active}

# ----------------- Swagger / OpenAPI Tool Builder -----------------

@router.get("/tools")
def list_tools(agent_id: Optional[str] = None):
    tools = registry.list_tools(agent_id=agent_id)
    return {"tools": [t.model_dump() for t in tools]}

@router.post("/tools/import-swagger")
def import_swagger(req: ImportSwaggerRequest):
    trace_id = str(uuid.uuid4())
    try:
        if req.spec_url:
            spec_data = OpenAPIImporter.fetch_from_url(req.spec_url)
        elif req.spec_content:
            spec_data = OpenAPIImporter.parse_spec_content(req.spec_content)
        else:
            raise HTTPException(status_code=400, detail="Either spec_content or spec_url must be provided.")

        tools, meta = OpenAPIImporter.import_spec(
            spec_data=spec_data,
            target_agent_id=req.target_agent_id,
            auto_register=True
        )

        observability.log_event(
            event_type="TOOL_REGISTERED",
            severity="NOTICE",
            message=f"Imported {len(tools)} tools from OpenAPI spec '{meta.get('title')}'",
            details={
                "tools": [t.name for t in tools],
                "target_agent": req.target_agent_id,
                "metadata": meta
            },
            trace_id=trace_id
        )

        return {
            "status": "success",
            "metadata": meta,
            "imported_tools": [t.model_dump() for t in tools],
            "trace_id": trace_id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to import OpenAPI spec: {str(e)}")

@router.get("/sample-specs")
def get_sample_specs():
    return {
        "devops_sample": SAMPLE_DEV_OPS_SWAGGER.strip(),
        "finance_sample": """openapi: 3.0.0
info:
  title: Enterprise ERP & Vendor Payment API
  version: 1.0.0
servers:
  - url: https://erp.internal.corp/api/v2
paths:
  /vendors/invoices:
    get:
      summary: Retrieve pending vendor invoices
      description: Returns list of accounts payable invoices awaiting payment.
      operationId: get_pending_invoices
      parameters:
        - name: vendor_name
          in: query
          schema:
            type: string
  /payments/approve:
    post:
      summary: Authorize corporate wire payment
      description: Dispatches high-value payment to banking gateway.
      operationId: approve_wire_transfer
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - invoice_id
                - amount
              properties:
                invoice_id:
                  type: string
                amount:
                  type: number
"""
    }

# ----------------- Identity & Personas -----------------

@router.get("/personas")
def get_personas():
    personas_data = {}
    for key, user in DEMO_PERSONAS.items():
        jwt_token = policy_engine.generate_jwt(user)
        personas_data[key] = {
            "user": user.model_dump(),
            "jwt": jwt_token
        }
    return {"personas": personas_data}

# ----------------- RAG Knowledge Stores -----------------

@router.get("/knowledge/documents")
def get_knowledge_documents(scope: Optional[str] = None):
    docs = rag_manager.list_documents(scope=scope)
    return {"documents": [d.model_dump() for d in docs]}

@router.get("/knowledge/scopes")
def get_knowledge_scopes():
    return {"scopes": rag_manager.list_scopes()}

@router.post("/knowledge/upload")
def upload_knowledge_document(req: DocumentUploadRequest):
    doc = KnowledgeDocument(
        title=req.title,
        scope=req.scope,
        content=req.content,
        tags=req.tags,
        source_type=req.source_type
    )
    saved = rag_manager.add_document(doc)
    trace_id = str(uuid.uuid4())
    observability.log_event(
        event_type="RAG_DOCUMENT_INGESTED",
        severity="INFO",
        message=f"Document '{doc.title}' ingested into scope '{doc.scope}' via {doc.source_type}",
        details=doc.model_dump(),
        trace_id=trace_id
    )
    return {"status": "success", "document": saved.model_dump(), "trace_id": trace_id}

# ----------------- Observability & Audit Trail -----------------

@router.get("/audit/logs")
def get_audit_logs(limit: int = 50, event_type: Optional[str] = None, trace_id: Optional[str] = None):
    logs = observability.get_logs(limit=limit, event_type=event_type, trace_id=trace_id)
    return {"logs": logs, "count": len(logs)}

@router.post("/audit/clear")
def clear_audit_logs():
    observability.clear()
    return {"status": "cleared"}
