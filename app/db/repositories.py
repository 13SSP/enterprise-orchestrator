from typing import List, Optional, Dict, Any
from app.db.firestore_client import firestore_db
from app.db.models import (
    Department,
    Employee,
    Salary,
    LeaveRecord,
    LeaveBalance,
    JiraTicket,
    ExpenseClaim
)


class DepartmentRepository:
    COLLECTION_NAME = "departments"

    def __init__(self, db=firestore_db):
        self.db = db

    def get(self, department_id: str) -> Optional[Department]:
        doc = self.db.collection(self.COLLECTION_NAME).document(department_id).get()
        if doc.exists:
            return Department(**doc.to_dict())
        return None

    def list_all(self) -> List[Department]:
        docs = self.db.collection(self.COLLECTION_NAME).stream()
        return [Department(**d.to_dict()) for d in docs]

    def save(self, dept: Department) -> Department:
        self.db.collection(self.COLLECTION_NAME).document(dept.department_id).set(dept.model_dump())
        return dept

    def update(self, department_id: str, updates: Dict[str, Any]) -> Optional[Department]:
        ref = self.db.collection(self.COLLECTION_NAME).document(department_id)
        doc = ref.get()
        if not doc.exists:
            return None
        data = doc.to_dict()
        data.update(updates)
        ref.set(data)
        return Department(**data)

    def delete(self, department_id: str) -> bool:
        ref = self.db.collection(self.COLLECTION_NAME).document(department_id)
        if ref.get().exists:
            ref.delete()
            return True
        return False


class EmployeeRepository:
    COLLECTION_NAME = "employees"

    def __init__(self, db=firestore_db):
        self.db = db

    def get(self, employee_id: str) -> Optional[Employee]:
        doc = self.db.collection(self.COLLECTION_NAME).document(employee_id).get()
        if doc.exists:
            return Employee(**doc.to_dict())
        return None

    def get_by_email(self, email: str) -> Optional[Employee]:
        docs = list(self.db.collection(self.COLLECTION_NAME).where("email", "==", email).stream())
        if docs:
            return Employee(**docs[0].to_dict())
        return None

    def list_all(self) -> List[Employee]:
        docs = self.db.collection(self.COLLECTION_NAME).stream()
        return [Employee(**d.to_dict()) for d in docs]

    def list_by_department(self, department_id: str) -> List[Employee]:
        docs = self.db.collection(self.COLLECTION_NAME).where("department_id", "==", department_id).stream()
        return [Employee(**d.to_dict()) for d in docs]

    def save(self, emp: Employee) -> Employee:
        self.db.collection(self.COLLECTION_NAME).document(emp.employee_id).set(emp.model_dump())
        return emp

    def update(self, employee_id: str, updates: Dict[str, Any]) -> Optional[Employee]:
        ref = self.db.collection(self.COLLECTION_NAME).document(employee_id)
        doc = ref.get()
        if not doc.exists:
            return None
        data = doc.to_dict()
        data.update(updates)
        ref.set(data)
        return Employee(**data)

    def delete(self, employee_id: str) -> bool:
        ref = self.db.collection(self.COLLECTION_NAME).document(employee_id)
        if ref.get().exists:
            ref.delete()
            return True
        return False


class SalaryRepository:
    COLLECTION_NAME = "salaries"

    def __init__(self, db=firestore_db):
        self.db = db

    def get(self, salary_id: str) -> Optional[Salary]:
        doc = self.db.collection(self.COLLECTION_NAME).document(salary_id).get()
        if doc.exists:
            return Salary(**doc.to_dict())
        return None

    def get_by_employee_id(self, employee_id: str) -> Optional[Salary]:
        docs = list(self.db.collection(self.COLLECTION_NAME).where("employee_id", "==", employee_id).stream())
        if docs:
            return Salary(**docs[0].to_dict())
        return None

    def list_all(self) -> List[Salary]:
        docs = self.db.collection(self.COLLECTION_NAME).stream()
        return [Salary(**d.to_dict()) for d in docs]

    def save(self, salary: Salary) -> Salary:
        self.db.collection(self.COLLECTION_NAME).document(salary.salary_id).set(salary.model_dump())
        return salary

    def update(self, salary_id: str, updates: Dict[str, Any]) -> Optional[Salary]:
        ref = self.db.collection(self.COLLECTION_NAME).document(salary_id)
        doc = ref.get()
        if not doc.exists:
            return None
        data = doc.to_dict()
        data.update(updates)
        ref.set(data)
        return Salary(**data)


class LeaveRepository:
    COLLECTION_RECORDS = "leave_records"
    COLLECTION_BALANCES = "leave_balances"

    def __init__(self, db=firestore_db):
        self.db = db

    # Records
    def get_record(self, leave_id: str) -> Optional[LeaveRecord]:
        doc = self.db.collection(self.COLLECTION_RECORDS).document(leave_id).get()
        if doc.exists:
            return LeaveRecord(**doc.to_dict())
        return None

    def list_records(self, employee_id: Optional[str] = None) -> List[LeaveRecord]:
        if employee_id:
            docs = self.db.collection(self.COLLECTION_RECORDS).where("employee_id", "==", employee_id).stream()
        else:
            docs = self.db.collection(self.COLLECTION_RECORDS).stream()
        return [LeaveRecord(**d.to_dict()) for d in docs]

    def save_record(self, record: LeaveRecord) -> LeaveRecord:
        self.db.collection(self.COLLECTION_RECORDS).document(record.leave_id).set(record.model_dump())
        return record

    def update_record_status(self, leave_id: str, status: str, approved_by: Optional[str] = None) -> Optional[LeaveRecord]:
        ref = self.db.collection(self.COLLECTION_RECORDS).document(leave_id)
        doc = ref.get()
        if not doc.exists:
            return None
        data = doc.to_dict()
        data["status"] = status
        if approved_by:
            data["approved_by"] = approved_by
        ref.set(data)
        return LeaveRecord(**data)

    # Balances
    def get_balance(self, employee_id: str) -> Optional[LeaveBalance]:
        doc = self.db.collection(self.COLLECTION_BALANCES).document(f"bal-{employee_id}").get()
        if doc.exists:
            return LeaveBalance(**doc.to_dict())
        return None

    def save_balance(self, balance: LeaveBalance) -> LeaveBalance:
        self.db.collection(self.COLLECTION_BALANCES).document(balance.balance_id).set(balance.model_dump())
        return balance

    def list_all_balances(self) -> List[LeaveBalance]:
        docs = self.db.collection(self.COLLECTION_BALANCES).stream()
        return [LeaveBalance(**d.to_dict()) for d in docs]


class JiraRepository:
    COLLECTION_NAME = "jira_tickets"

    def __init__(self, db=firestore_db):
        self.db = db

    def get(self, ticket_key: str) -> Optional[JiraTicket]:
        doc = self.db.collection(self.COLLECTION_NAME).document(ticket_key).get()
        if doc.exists:
            return JiraTicket(**doc.to_dict())
        return None

    def list_all(self) -> List[JiraTicket]:
        docs = self.db.collection(self.COLLECTION_NAME).stream()
        return [JiraTicket(**d.to_dict()) for d in docs]

    def list_by_assignee(self, assignee_id: str) -> List[JiraTicket]:
        docs = self.db.collection(self.COLLECTION_NAME).where("assignee_id", "==", assignee_id).stream()
        return [JiraTicket(**d.to_dict()) for d in docs]

    def list_by_status(self, status: str) -> List[JiraTicket]:
        docs = self.db.collection(self.COLLECTION_NAME).where("status", "==", status).stream()
        return [JiraTicket(**d.to_dict()) for d in docs]

    def save(self, ticket: JiraTicket) -> JiraTicket:
        self.db.collection(self.COLLECTION_NAME).document(ticket.ticket_key).set(ticket.model_dump())
        return ticket

    def update_status(self, ticket_key: str, status: str) -> Optional[JiraTicket]:
        ref = self.db.collection(self.COLLECTION_NAME).document(ticket_key)
        doc = ref.get()
        if not doc.exists:
            return None
        data = doc.to_dict()
        data["status"] = status
        ref.set(data)
        return JiraTicket(**data)


class ClaimRepository:
    COLLECTION_NAME = "expense_claims"

    def __init__(self, db=firestore_db):
        self.db = db

    def get(self, claim_id: str) -> Optional[ExpenseClaim]:
        doc = self.db.collection(self.COLLECTION_NAME).document(claim_id).get()
        if doc.exists:
            return ExpenseClaim(**doc.to_dict())
        return None

    def list_all(self) -> List[ExpenseClaim]:
        docs = self.db.collection(self.COLLECTION_NAME).stream()
        return [ExpenseClaim(**d.to_dict()) for d in docs]

    def list_by_employee(self, employee_id: str) -> List[ExpenseClaim]:
        docs = self.db.collection(self.COLLECTION_NAME).where("employee_id", "==", employee_id).stream()
        return [ExpenseClaim(**d.to_dict()) for d in docs]

    def save(self, claim: ExpenseClaim) -> ExpenseClaim:
        self.db.collection(self.COLLECTION_NAME).document(claim.claim_id).set(claim.model_dump())
        return claim

    def update_status(self, claim_id: str, status: str, approver_id: Optional[str] = None) -> Optional[ExpenseClaim]:
        ref = self.db.collection(self.COLLECTION_NAME).document(claim_id)
        doc = ref.get()
        if not doc.exists:
            return None
        data = doc.to_dict()
        data["status"] = status
        if approver_id:
            data["approver_id"] = approver_id
        ref.set(data)
        return ExpenseClaim(**data)


# Instantiate repository singletons
department_repo = DepartmentRepository()
employee_repo = EmployeeRepository()
salary_repo = SalaryRepository()
leave_repo = LeaveRepository()
jira_repo = JiraRepository()
claim_repo = ClaimRepository()
