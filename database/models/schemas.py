"""
cortex.ai - Unified Database Models
Pydantic model definitions for enterprise Firestore collections.
"""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime
import uuid



class Department(BaseModel):
    department_id: str = Field(..., description="Unique department identifier, e.g. dept-eng")
    name: str = Field(..., description="Department name, e.g. Engineering")
    code: str = Field(..., description="Department short code, e.g. ENG")
    head_employee_id: Optional[str] = Field(None, description="Employee ID of department head")
    budget_allocated: float = Field(0.0, description="Annual allocated budget in USD")
    budget_spent: float = Field(0.0, description="Current spent budget in USD")
    currency: str = Field("USD", description="Currency code")
    location: str = Field("Remote / HQ", description="Office or building location")
    description: str = Field("", description="Overview of department charter")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class Employee(BaseModel):
    employee_id: str = Field(..., description="Unique employee identifier, e.g. emp-101 or username")
    first_name: str
    last_name: str
    email: str
    department_id: str = Field(..., description="Foreign key reference to Department")
    role: str = Field(..., description="System RBAC role: admin, devops_admin, hr_manager, employee, contractor")
    title: str = Field(..., description="Job title, e.g. Staff DevOps Engineer")
    manager_id: Optional[str] = Field(None, description="Employee ID of direct manager")
    status: str = Field("ACTIVE", description="ACTIVE, ON_LEAVE, or TERMINATED")
    employment_type: str = Field("FULL_TIME", description="FULL_TIME, PART_TIME, or CONTRACTOR")
    skills: List[str] = Field(default_factory=list, description="Primary technical or functional competencies")
    date_of_joining: str = Field(..., description="ISO date of hire")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class Salary(BaseModel):
    salary_id: str = Field(..., description="Unique compensation record identifier, e.g. sal-101")
    employee_id: str = Field(..., description="Employee reference ID")
    base_salary: float = Field(..., description="Annual or monthly base pay")
    currency: str = Field("USD", description="Currency ISO code")
    pay_frequency: str = Field("ANNUAL", description="ANNUAL, BI_WEEKLY, or MONTHLY")
    bonus_target_pct: float = Field(0.0, description="Target performance bonus percentage")
    effective_date: str = Field(..., description="Effective date of this salary tier")
    bank_account_masked: str = Field("****0000", description="Masked disbursement account")
    tax_id_masked: str = Field("***-**-0000", description="Masked tax ID for compliance")
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class LeaveRecord(BaseModel):
    leave_id: str = Field(..., description="Leave request ID, e.g. leave-2026-001")
    employee_id: str = Field(..., description="Employee who submitted the leave")
    leave_type: str = Field("ANNUAL_PTO", description="ANNUAL_PTO, SICK_LEAVE, CASUAL, PARENTAL, UNPAID")
    start_date: str = Field(..., description="Start date YYYY-MM-DD")
    end_date: str = Field(..., description="End date YYYY-MM-DD")
    days_count: int = Field(..., description="Total business days requested")
    reason: str = Field(..., description="Purpose or description of the leave")
    status: str = Field("PENDING", description="PENDING, APPROVED, REJECTED, CANCELLED")
    approved_by: Optional[str] = Field(None, description="Manager employee ID who approved or rejected")
    applied_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class LeaveBalance(BaseModel):
    balance_id: str = Field(..., description="Balance tracking ID, e.g. bal-emp-101")
    employee_id: str = Field(..., description="Target employee ID")
    year: int = Field(2026, description="Fiscal calendar year")
    annual_pto_total: int = Field(20, description="Total allocated PTO days")
    annual_pto_used: int = Field(0, description="PTO days already consumed")
    annual_pto_pending: int = Field(0, description="PTO days pending approval")
    sick_leave_total: int = Field(10, description="Total sick leave days allocated")
    sick_leave_used: int = Field(0, description="Sick days consumed")
    rollover_days: int = Field(0, description="Days rolled over from previous year")

    @property
    def remaining_pto(self) -> int:
        return max(0, self.annual_pto_total + self.rollover_days - self.annual_pto_used - self.annual_pto_pending)

    @property
    def remaining_sick_leave(self) -> int:
        return max(0, self.sick_leave_total - self.sick_leave_used)


class JiraTicket(BaseModel):
    ticket_key: str = Field(..., description="Jira issue key, e.g. PROJ-102 or SEC-204")
    title: str = Field(..., description="Summary title of the issue")
    description: str = Field("", description="Detailed problem statement or acceptance criteria")
    issue_type: str = Field("TASK", description="BUG, TASK, STORY, INCIDENT, FEATURE")
    priority: str = Field("MEDIUM", description="LOW, MEDIUM, HIGH, CRITICAL")
    status: str = Field("OPEN", description="OPEN, IN_PROGRESS, REVIEW, RESOLVED, CLOSED")
    reporter_id: str = Field(..., description="Employee ID or username of reporter")
    assignee_id: Optional[str] = Field(None, description="Employee ID or username of assignee")
    department_id: str = Field(..., description="Target department managing this ticket")
    components: List[str] = Field(default_factory=list, description="Target subsystems, e.g. ['payments', 'api']")
    labels: List[str] = Field(default_factory=list, description="Categorization tags")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ExpenseClaim(BaseModel):
    claim_id: str = Field(..., description="Expense claim reference ID, e.g. EXP-2026-88")
    employee_id: str = Field(..., description="Claimant employee ID")
    department_id: str = Field(..., description="Department budget to charge")
    amount: float = Field(..., description="Monetary claim value")
    currency: str = Field("USD", description="Currency code")
    category: str = Field("TRAVEL", description="TRAVEL, MEALS, SOFTWARE, HARDWARE, TRAINING, OFFICE")
    merchant: str = Field(..., description="Vendor or provider name, e.g. Delta Airlines")
    description: str = Field("", description="Business justification")
    receipt_url: Optional[str] = Field(None, description="Attached cloud storage receipt link")
    status: str = Field("PENDING_APPROVAL", description="DRAFT, SUBMITTED, PENDING_APPROVAL, APPROVED, REJECTED, PAID")
    approver_id: Optional[str] = Field(None, description="Manager or finance approver ID")
    submitted_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    payout_date: Optional[str] = Field(None, description="Target or actual reimbursement disbursement date")


class WorkspaceMember(BaseModel):
    user_id: str
    user_name: str
    role: str = Field("contributor", description="'owner' or 'contributor'")
    joined_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class SDDTask(BaseModel):
    task_id: str = Field(..., description="Unique task key, e.g. TSK-101")
    title: str = Field(..., description="Task title")
    description: str = Field("", description="Task scope and deliverables")
    linked_req_id: Optional[str] = Field(None, description="Linked specification requirement key, e.g. REQ-01")
    target_files: List[str] = Field(default_factory=list, description="Target implementation files, e.g. ['src/models.py']")
    test_file: Optional[str] = Field(None, description="Test suite path, e.g. 'tests/test_models.py'")
    status: str = Field("pending", description="'pending', 'in_progress', 'completed', 'failed'")
    last_commit_hash: Optional[str] = None
    last_test_output: Optional[str] = None
    completed_at: Optional[str] = None


class SDDSpec(BaseModel):
    title: str = Field("Application Requirements Specification", description="Spec title")
    version: str = Field("v1.0", description="Spec revision")
    status: str = Field("approved", description="'draft' or 'approved'")
    raw_markdown: str = Field("", description="Authoritative specification markdown content")
    requirements: List[Dict[str, Any]] = Field(default_factory=list, description="Extracted requirement items [id, title, acceptance_criteria]")


class SDDPlan(BaseModel):
    title: str = Field("Technical Architecture & Plan", description="Plan title")
    version: str = Field("v1.0", description="Plan revision")
    raw_markdown: str = Field("", description="Architecture design, data models, and API contracts markdown")
    data_models: List[Dict[str, Any]] = Field(default_factory=list, description="Entity schemas and relational models")
    api_endpoints: List[Dict[str, Any]] = Field(default_factory=list, description="OpenAPI / REST route contracts")
    decisions: List[str] = Field(default_factory=list, description="Architecture Decision Records (ADRs)")


class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    sender_id: str
    sender_name: str
    role: str = Field("user", description="'user' or 'assistant'")
    content: str
    citations: List[str] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class SDDConfig(BaseModel):
    local_space_path: str = Field(..., description="Local working directory path for repo cloning and autonomous execution")
    git_action: str = Field("init", description="'init' or 'clone'")
    git_remote_url: Optional[str] = None
    tech_stack: str = Field("Python 3.11 / FastAPI / Pytest")
    architecture_principles: List[str] = Field(default_factory=list)
    coding_standards: List[str] = Field(default_factory=list)
    active_spec_version: str = Field("v1.0")
    approval_status: str = Field("approved")



SpecLifecycleState = Literal["draft", "in_review", "approved", "deprecated"]
StorageMode = Literal["local", "cloud"]


class SpecVersion(BaseModel):
    version_id: str = Field(default_factory=lambda: f"v{datetime.utcnow().strftime('%Y%m%d%H%M%S')}")
    version_tag: str = Field("v1.0", description="Semantic version tag, e.g. v1.0, v1.1")
    raw_markdown: str = Field("", description="Authoritative specification markdown content")
    requirements: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    created_by: str = Field("system", description="Author who created this revision")
    change_summary: str = Field("", description="Summary of changes in this version")


class FeatureSpec(BaseModel):
    feature_id: str = Field(default_factory=lambda: f"feat-{str(uuid.uuid4())[:8]}")
    title: str = Field(..., description="Feature title")
    description: str = Field("", description="Overview of feature scope")
    lifecycle_state: SpecLifecycleState = Field("draft")
    active_version: str = Field("v1.0")
    source_type: Literal["ai", "doc", "manual"] = Field("manual")
    raw_markdown: str = Field("", description="Current active specification markdown")
    requirements: List[Dict[str, Any]] = Field(default_factory=list)
    versions: List[SpecVersion] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    created_by: str = Field("bob_ops")
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class PrototypeApp(BaseModel):
    prototype_id: str = Field(default_factory=lambda: f"proto-{str(uuid.uuid4())[:8]}")
    pod_id: str = Field(..., description="ID of the parent POD")
    title: str = Field(..., description="Application or Prototype title")
    description: str = Field("", description="Prototype summary")
    linked_feature_id: Optional[str] = Field(None, description="Linked FeatureSpec ID")
    linked_spec_version: Optional[str] = Field("v1.0", description="Linked spec version")
    storage_mode: StorageMode = Field("local", description="Where the prototype is stored: 'local' machine or 'cloud'")
    local_path: Optional[str] = Field(None, description="Local machine directory path (visible ONLY to creator)")
    creator_id: str = Field(..., description="Authenticated user ID who created this prototype")
    creator_name: str = Field("Bob Martinez")
    status: Literal["building", "ready", "test_passed", "test_failed"] = Field("ready")
    test_output: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    files: List[str] = Field(default_factory=list, description="Relative file paths in prototype")


class Workspace(BaseModel):
    workspace_id: str = Field(..., description="Unique workspace ID, e.g. ws-my-app")
    name: str = Field(..., description="Workspace title")
    description: str = Field("", description="Purpose or scope of workspace")
    workspace_type: str = Field("chat", description="'chat' or 'sdd'")
    pod_type: str = Field("chat", description="Canonical pod type: 'chat' or 'sdd'")
    visibility: str = Field("private", description="'public' or 'private'")
    owner_id: str = Field(..., description="Employee ID of owner who created it")
    owner_name: str = Field(..., description="Full name of owner")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    system_instructions: str = Field("", description="Persistent workspace system prompt")
    members: List[WorkspaceMember] = Field(default_factory=list)
    sdd_config: Optional[SDDConfig] = None
    spec: Optional[SDDSpec] = None
    plan: Optional[SDDPlan] = None
    tasks: List[SDDTask] = Field(default_factory=list)
    features: List[FeatureSpec] = Field(default_factory=list)
    prototypes: List[PrototypeApp] = Field(default_factory=list)
    documents: List[Dict[str, Any]] = Field(default_factory=list)
    prompts: List[Dict[str, Any]] = Field(default_factory=list)
    chat_messages: List[ChatMessage] = Field(default_factory=list)
    chat_sessions: List[str] = Field(default_factory=list)
    execution_logs: List[Dict[str, Any]] = Field(default_factory=list)



