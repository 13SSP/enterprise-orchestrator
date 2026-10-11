"""
cortex.ai - Unified Database Models
Pydantic model definitions for enterprise Firestore collections.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


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
