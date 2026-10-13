import json
import os
import uuid
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from app.config import settings

class AgentManifest(BaseModel):
    id: str = Field(..., description="Unique agent identifier (e.g. it_agent, hr_agent)")
    name: str = Field(..., description="Human readable name of the agent")
    description: str = Field(..., description="Semantic description of capabilities used by Gemini Router")
    owner_team: str = Field(..., description="Owner department or team (e.g. IT, HR, Finance, DevOps)")
    author: Optional[str] = Field(default=None, description="Display name of creator or owner")
    author_id: Optional[str] = Field(default=None, description="Author persona user ID (e.g. bob_ops)")
    icon: Optional[str] = Field(default="wrench", description="Icon key: wrench, chart, shield, docs, cart, user, bot, code")
    system_prompt: str = Field(..., description="Instructions and persona for the agent")
    allowed_tools: List[str] = Field(default_factory=list, description="Names of tools this agent is authorized to use")
    knowledge_scopes: List[str] = Field(default_factory=list, description="RAG datastore scopes this agent can query")
    agent_type: str = Field(default="local_adk", description="'local_adk' or 'remote_a2a'")
    remote_endpoint: Optional[str] = Field(default=None, description="URL endpoint if registered as remote A2A agent")
    active: bool = Field(default=True, description="Whether agent is active")
    is_public: bool = Field(default=True, description="Whether agent is accessible to all enterprise users")
    allowed_roles: List[str] = Field(default_factory=lambda: ["*"], description="Roles authorized to invoke this agent")
    allowed_teams: List[str] = Field(default_factory=lambda: ["*"], description="Teams authorized to invoke this agent")
    created_at: Optional[str] = None

class ToolDefinition(BaseModel):
    name: str = Field(..., description="Unique tool identifier / function name")
    description: str = Field(..., description="Human-readable description for Gemini routing")
    method: str = Field(default="GET", description="HTTP method: GET, POST, PUT, DELETE")
    path: str = Field(default="/", description="API endpoint path")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="JSON Schema for arguments")
    is_write: bool = Field(default=False, description="Whether operation mutates state")
    require_confirmation: bool = Field(default=False, description="Requires human approval before execution")
    target_url: Optional[str] = Field(default=None, description="Base URL of backend service")
    tags: List[str] = Field(default_factory=list, description="Categories or team tags")
    owner_agent: Optional[str] = Field(default=None, description="Agent this tool belongs to")
    enabled: bool = Field(default=True, description="Whether tool is active and callable")
    allowed_roles: List[str] = Field(default_factory=lambda: ["*"], description="Roles permitted to execute this specific tool")

class RegistryManager:
    """
    Central Agent & Tool Registry.
    Compatible with Firestore document storage patterns with local persistence.
    Dynamically loads and unloads ADK sub-agents at runtime.
    """
    def __init__(self):
        self.agents_file = os.path.join(settings.DATA_DIR, "agents_registry.json")
        self.tools_file = os.path.join(settings.DATA_DIR, "tools_registry.json")
        self._agents: Dict[str, AgentManifest] = {}
        self._tools: Dict[str, ToolDefinition] = {}
        self._load_or_initialize()

    def _load_or_initialize(self):
        if os.path.exists(self.agents_file):
            try:
                with open(self.agents_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        agent = AgentManifest(**item)
                        self._agents[agent.id] = agent
                # Merge any missing default benchmark agents
                self._merge_default_agents()
            except Exception as e:
                print(f"[Registry] Error loading agents: {e}, reinitializing defaults")
                self._init_default_agents()
        else:
            self._init_default_agents()

        if os.path.exists(self.tools_file):
            try:
                with open(self.tools_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        tool = ToolDefinition(**item)
                        self._tools[tool.name] = tool
            except Exception as e:
                print(f"[Registry] Error loading tools: {e}, reinitializing defaults")
                self._init_default_tools()
        else:
            self._init_default_tools()

    def _save_agents(self):
        with open(self.agents_file, "w", encoding="utf-8") as f:
            json.dump([agent.model_dump() for agent in self._agents.values()], f, indent=2)

    def _save_tools(self):
        with open(self.tools_file, "w", encoding="utf-8") as f:
            json.dump([tool.model_dump() for tool in self._tools.values()], f, indent=2)

    def _merge_default_agents(self):
        default_list = self._get_default_agents_list()
        updated = False
        for def_agent in default_list:
            if def_agent.id not in self._agents:
                self._agents[def_agent.id] = def_agent
                updated = True
            else:
                curr = self._agents[def_agent.id]
                # Populate missing metadata if not present
                if not curr.author and def_agent.author:
                    curr.author = def_agent.author
                    curr.author_id = def_agent.author_id
                    curr.icon = def_agent.icon
                    updated = True
        if updated:
            self._save_agents()

    def _get_default_agents_list(self) -> List[AgentManifest]:
        return [
            AgentManifest(
                id="usage_pricing_agent",
                name="Usage Pricing Insights Agent",
                description="Strategic knowledge assistant that synthesises internal thinking, documentation, and decisions on consumption and usage-based pricing to help build scalable models.",
                owner_team="Product Strategy",
                author="Adam Furness",
                author_id="adam_pricing",
                icon="chart",
                system_prompt="You are the Usage Pricing Insights Agent. Synthesise strategic pricing documentation and consumption data.",
                allowed_tools=["get_budget_overview"],
                knowledge_scopes=["finance_guidelines"],
                agent_type="local_adk",
                active=True,
                is_public=True,
                allowed_roles=["*"],
                allowed_teams=["*"],
            ),
            AgentManifest(
                id="ela_feedback_analyst",
                name="ELA customer feedback analyst",
                description="Analyzes Gong calls, customer sentiment, and feedback trends for ELA accounts to inform product retention strategies.",
                owner_team="Customer Success",
                author="Sarah Croft",
                author_id="sarah_cs",
                icon="docs",
                system_prompt="You are the ELA Customer Feedback Analyst. Parse Gong transcript summaries and customer feedback.",
                allowed_tools=[],
                knowledge_scopes=["benefits_handbook"],
                agent_type="local_adk",
                active=True,
                is_public=True,
                allowed_roles=["*"],
                allowed_teams=["*"],
            ),
            AgentManifest(
                id="policy_bot",
                name="Policy Bot",
                description="Agent to assist with compliance policy inquiries, security controls, and regulatory audit queries.",
                owner_team="Governance",
                author="Francisco Barciella",
                author_id="francisco_gov",
                icon="shield",
                system_prompt="You are the Policy Bot. Assist with compliance checks and corporate governance policies.",
                allowed_tools=["scan_security_posture"],
                knowledge_scopes=["security_standards"],
                agent_type="local_adk",
                active=False,
                is_public=True,
                allowed_roles=["*"],
                allowed_teams=["*"],
            ),
            AgentManifest(
                id="commerce_intake_agent",
                name="Commerce Intake Agent",
                description="Streamlines B2B checkout intake, vendor procurement orders, and merchant billing contract verification.",
                owner_team="Commercial Ops",
                author="Jai Ganesh Kamalakannan",
                author_id="jai_ops",
                icon="cart",
                system_prompt="You are the Commerce Intake Agent. Assist with corporate purchase intakes and contract approvals.",
                allowed_tools=["check_expense_status"],
                knowledge_scopes=["finance_guidelines"],
                agent_type="local_adk",
                active=True,
                is_public=True,
                allowed_roles=["*"],
                allowed_teams=["*"],
            ),
            AgentManifest(
                id="it_agent",
                name="IT & Cloud Ops Agent",
                description="Handles IT infrastructure queries, Jira issue lookups, system restart requests, cloud server status, and developer workspace operations.",
                owner_team="Engineering",
                author="Bob Martinez",
                author_id="bob_ops",
                icon="wrench",
                system_prompt="You are the IT & Operations Agent. Assist users with technical queries, infrastructure checks, and Jira tickets. For destructive or write operations, always explain what will be changed.",
                allowed_tools=["get_system_health", "lookup_jira_issue", "restart_cloud_service"],
                knowledge_scopes=["it_runbooks", "cloud_architecture"],
                agent_type="local_adk",
                active=True,
                is_public=True,
                allowed_roles=["devops_admin", "it_engineer", "employee"],
                allowed_teams=["Engineering"],
            ),
            AgentManifest(
                id="hr_agent",
                name="HR & People Operations Agent",
                description="Assists employees with PTO balance queries, company benefits, employee directory searches, internal leave policies, and onboarding questions.",
                owner_team="Human Resources",
                author="Alice Henderson",
                author_id="alice_hr",
                icon="user",
                system_prompt="You are the HR Assistant. Provide helpful, confidential, and accurate information on benefits, time off, and company policies.",
                allowed_tools=["check_pto_balance", "lookup_employee", "submit_timeoff_request"],
                knowledge_scopes=["hr_policies", "benefits_handbook"],
                agent_type="local_adk",
                active=True,
                is_public=True,
                allowed_roles=["*"],
                allowed_teams=["*"],
            ),
            AgentManifest(
                id="finance_agent",
                name="Finance & Expenses Agent",
                description="Handles corporate expense report inquiries, reimbursement status, departmental budget checks, and financial compliance questions.",
                owner_team="Finance",
                author="Charlie Zhao",
                author_id="charlie_fin",
                icon="cart",
                system_prompt="You are the Finance & Expenses Specialist. Assist with budget lookups and expense reports accurately.",
                allowed_tools=["check_expense_status", "get_budget_overview", "submit_expense_claim"],
                knowledge_scopes=["finance_guidelines", "procurement_policy"],
                agent_type="local_adk",
                active=True,
                is_public=False,
                allowed_roles=["finance_officer", "devops_admin"],
                allowed_teams=["Finance", "Engineering"],
            ),
            AgentManifest(
                id="ticket_manager_review",
                name="Ticket Manager Review",
                description="Analyzes Jira tickets and provides key insights on sprint health, SLA tracking, and ticket escalation bottlenecks.",
                owner_team="Engineering",
                author="Christiane Delazeri",
                author_id="christiane_eng",
                icon="wrench",
                system_prompt="You are the Ticket Manager Review agent.",
                allowed_tools=["lookup_jira_issue"],
                knowledge_scopes=["it_runbooks"],
                agent_type="local_adk",
                active=False,
                is_public=True,
                allowed_roles=["*"],
                allowed_teams=["*"],
            ),
            AgentManifest(
                id="file_creator_agent",
                name="file creator",
                description="Agent to help create downloadable files, spreadsheets, and document templates for enterprise teams.",
                owner_team="General",
                author="Eurley Balentina",
                author_id="eurley_dev",
                icon="docs",
                system_prompt="You are the file creator agent. Generate structured report documents and download templates.",
                allowed_tools=[],
                knowledge_scopes=[],
                agent_type="local_adk",
                active=True,
                is_public=True,
                allowed_roles=["*"],
                allowed_teams=["*"],
            ),
            AgentManifest(
                id="security_remote_agent",
                name="SecOps Remote Agent (A2A)",
                description="Remote Agent running over Agent-to-Agent (A2A) protocol for enterprise security audits, vulnerability scanning, and IAM compliance reviews.",
                owner_team="Security Ops",
                author="Francisco Barciella",
                author_id="francisco_gov",
                icon="shield",
                system_prompt="You are the SecOps A2A Agent. Conduct security posture checks and firewall rule reviews.",
                allowed_tools=["scan_security_posture"],
                knowledge_scopes=["security_standards"],
                agent_type="remote_a2a",
                remote_endpoint="https://secops.internal.corp/a2a/v1/agent",
                active=True,
                is_public=False,
                allowed_roles=["devops_admin", "it_engineer"],
                allowed_teams=["Engineering", "Security Ops"],
            ),
        ]

    def _init_default_agents(self):
        default_agents = self._get_default_agents_list()
        self._agents = {a.id: a for a in default_agents}
        self._save_agents()

    def _init_default_tools(self):
        default_tools = [
            ToolDefinition(
                name="get_system_health",
                description="Check real-time health, CPU, memory, and uptime of cloud services.",
                method="GET",
                path="/api/v1/ops/health",
                parameters={"type": "object", "properties": {"cluster": {"type": "string", "description": "Cluster name, e.g. prod-us-east"}}},
                is_write=False,
                require_confirmation=False,
                tags=["it", "infrastructure"],
                owner_agent="it_agent"
            ),
            ToolDefinition(
                name="lookup_jira_issue",
                description="Retrieve details, assignee, status, and comments of a Jira issue ticket.",
                method="GET",
                path="/api/v1/jira/issue",
                parameters={"type": "object", "properties": {"issue_key": {"type": "string", "description": "e.g. PROJ-102"}}, "required": ["issue_key"]},
                is_write=False,
                require_confirmation=False,
                tags=["it", "jira"],
                owner_agent="it_agent"
            ),
            ToolDefinition(
                name="restart_cloud_service",
                description="Initiate a graceful rolling restart of a designated cloud production service.",
                method="POST",
                path="/api/v1/ops/restart",
                parameters={"type": "object", "properties": {"service_name": {"type": "string", "description": "Name of service to restart"}}, "required": ["service_name"]},
                is_write=True,
                require_confirmation=True,
                tags=["it", "ops", "write"],
                owner_agent="it_agent"
            ),
            ToolDefinition(
                name="check_pto_balance",
                description="Look up remaining paid time off (PTO), sick days, and holiday allowance for an employee.",
                method="GET",
                path="/api/v1/hr/pto",
                parameters={"type": "object", "properties": {"employee_id": {"type": "string", "description": "Employee ID or current user"}}},
                is_write=False,
                require_confirmation=False,
                tags=["hr", "pto"],
                owner_agent="hr_agent"
            ),
            ToolDefinition(
                name="lookup_employee",
                description="Search the company employee directory by name, role, or team.",
                method="GET",
                path="/api/v1/hr/directory",
                parameters={"type": "object", "properties": {"query": {"type": "string", "description": "Name or title"}}},
                is_write=False,
                require_confirmation=False,
                tags=["hr", "directory"],
                owner_agent="hr_agent"
            ),
            ToolDefinition(
                name="submit_timeoff_request",
                description="Submit a formal vacation or leave request for managerial approval.",
                method="POST",
                path="/api/v1/hr/timeoff/submit",
                parameters={"type": "object", "properties": {"start_date": {"type": "string"}, "end_date": {"type": "string"}, "reason": {"type": "string"}}, "required": ["start_date", "end_date"]},
                is_write=True,
                require_confirmation=True,
                tags=["hr", "write"],
                owner_agent="hr_agent"
            ),
            ToolDefinition(
                name="check_expense_status",
                description="Check current status, approval phase, and payout date of an expense reimbursement claim.",
                method="GET",
                path="/api/v1/finance/expenses/status",
                parameters={"type": "object", "properties": {"report_id": {"type": "string", "description": "e.g. EXP-2026-88"}}, "required": ["report_id"]},
                is_write=False,
                require_confirmation=False,
                tags=["finance"],
                owner_agent="finance_agent"
            ),
            ToolDefinition(
                name="get_budget_overview",
                description="Retrieve current fiscal year allocated vs spent budget for a specified department.",
                method="GET",
                path="/api/v1/finance/budget",
                parameters={"type": "object", "properties": {"department": {"type": "string", "description": "e.g. Engineering, Marketing"}}, "required": ["department"]},
                is_write=False,
                require_confirmation=False,
                tags=["finance"],
                owner_agent="finance_agent"
            ),
            ToolDefinition(
                name="submit_expense_claim",
                description="Submit a new expense reimbursement request with merchant and dollar amount.",
                method="POST",
                path="/api/v1/finance/expenses/claim",
                parameters={"type": "object", "properties": {"amount": {"type": "number"}, "merchant": {"type": "string"}, "category": {"type": "string"}}, "required": ["amount", "merchant"]},
                is_write=True,
                require_confirmation=True,
                tags=["finance", "write"],
                owner_agent="finance_agent"
            ),
            ToolDefinition(
                name="scan_security_posture",
                description="Remote SecOps check to audit cloud VPC security groups and exposed endpoints.",
                method="GET",
                path="/api/v1/secops/posture",
                parameters={"type": "object", "properties": {"target_env": {"type": "string", "description": "staging or prod"}}},
                is_write=False,
                require_confirmation=False,
                tags=["security"],
                owner_agent="security_remote_agent"
            ),
        ]
        self._tools = {t.name: t for t in default_tools}
        self._save_tools()

    # Agent Management API
    def register_agent(self, manifest: AgentManifest) -> AgentManifest:
        self._agents[manifest.id] = manifest
        self._save_agents()
        return manifest

    def get_agent(self, agent_id: str) -> Optional[AgentManifest]:
        return self._agents.get(agent_id)

    def list_agents(self, active_only: bool = False) -> List[AgentManifest]:
        if active_only:
            return [a for a in self._agents.values() if a.active]
        return list(self._agents.values())

    def delete_agent(self, agent_id: str) -> bool:
        if agent_id in self._agents:
            del self._agents[agent_id]
            self._save_agents()
            return True
        return False

    # Tool Management API
    def register_tool(self, tool: ToolDefinition) -> ToolDefinition:
        self._tools[tool.name] = tool
        self._save_tools()
        return tool

    def get_tool(self, tool_name: str) -> Optional[ToolDefinition]:
        return self._tools.get(tool_name)

    def list_tools(self, agent_id: Optional[str] = None) -> List[ToolDefinition]:
        if agent_id:
            agent = self.get_agent(agent_id)
            if not agent:
                return []
            return [t for t in self._tools.values() if t.name in agent.allowed_tools]
        return list(self._tools.values())

    def delete_tool(self, tool_name: str) -> bool:
        if tool_name in self._tools:
            del self._tools[tool_name]
            self._save_tools()
            return True
        return False

registry = RegistryManager()
