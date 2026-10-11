import pytest
from app.db import (
    department_repo,
    employee_repo,
    salary_repo,
    leave_repo,
    jira_repo,
    claim_repo,
    Department,
    Employee,
    JiraTicket,
    ExpenseClaim
)

def test_departments_repository():
    depts = department_repo.list_all()
    assert len(depts) >= 5
    eng = department_repo.get("dept-eng")
    assert eng is not None
    assert eng.code == "ENG"
    assert eng.budget_allocated == 2500000.0

def test_employees_repository():
    emps = employee_repo.list_all()
    assert len(emps) >= 8
    bob = employee_repo.get("bob_ops")
    assert bob is not None
    assert bob.first_name == "Bob"
    assert bob.role == "devops_admin"
    
    by_email = employee_repo.get_by_email("bob.ops@company.internal")
    assert by_email is not None
    assert by_email.employee_id == "bob_ops"

def test_salaries_repository():
    sal = salary_repo.get_by_employee_id("bob_ops")
    assert sal is not None
    assert sal.base_salary == 165000.0
    assert sal.currency == "USD"
    assert sal.bank_account_masked.startswith("****")

def test_leave_repository():
    bal = leave_repo.get_balance("bob_ops")
    assert bal is not None
    assert bal.annual_pto_total == 20
    assert bal.annual_pto_used == 6
    assert bal.remaining_pto == 14

    records = leave_repo.list_records("bob_ops")
    assert len(records) >= 2

def test_jira_tickets_repository():
    tickets = jira_repo.list_all()
    assert len(tickets) >= 6
    ticket = jira_repo.get("PROJ-102")
    assert ticket is not None
    assert ticket.priority == "HIGH"
    assert ticket.assignee_id == "alex_chen"

    # Test status update
    updated = jira_repo.update_status("PROJ-102", "IN_PROGRESS")
    assert updated is not None
    assert updated.status == "IN_PROGRESS"

def test_expense_claims_repository():
    claims = claim_repo.list_all()
    assert len(claims) >= 4
    claim = claim_repo.get("EXP-2026-88")
    assert claim is not None
    assert claim.amount == 250.0
    assert claim.merchant == "Delta Airlines"
    assert claim.status == "APPROVED"
