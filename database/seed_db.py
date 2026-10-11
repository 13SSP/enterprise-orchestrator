"""
cortex.ai - Database Seed Runner
Populates Firestore Emulator or local storage with sample enterprise records.
"""

import sys
import os
from pathlib import Path

# Support UTF-8 terminal encoding on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from database.firestore_client import db
from database.seeds import (
    DEPARTMENTS,
    EMPLOYEES,
    SALARIES,
    LEAVE_BALANCES,
    LEAVE_RECORDS,
    JIRA_TICKETS,
    EXPENSE_CLAIMS,
)

def run_seed():
    print("=" * 60)
    print("cortex.ai - Firestore Seeding Engine")
    print("=" * 60)
    status = db.get_status()
    print(f"Target Mode:   {status['mode']}")
    print(f"Project ID:    {status['project_id']}")
    print("-" * 60)

    # 1. Departments
    print(f"Seeding Departments ({len(DEPARTMENTS)} records)...")
    for d in DEPARTMENTS:
        db.collection("departments").document(d.department_id).set(d.model_dump())
        print(f"  + [{d.code}] {d.name}")

    # 2. Employees
    print(f"\nSeeding Employees ({len(EMPLOYEES)} records)...")
    for e in EMPLOYEES:
        db.collection("employees").document(e.employee_id).set(e.model_dump())
        print(f"  + [{e.employee_id}] {e.full_name} ({e.title})")

    # 3. Salaries
    print(f"\nSeeding Salaries ({len(SALARIES)} records)...")
    for s in SALARIES:
        db.collection("salaries").document(s.salary_id).set(s.model_dump())
        print(f"  + [{s.employee_id}] ${s.base_salary:,.0f} {s.currency}")

    # 4. Leave Balances
    print(f"\nSeeding Leave Balances ({len(LEAVE_BALANCES)} records)...")
    for b in LEAVE_BALANCES:
        db.collection("leave_balances").document(b.balance_id).set(b.model_dump())
        print(f"  + [{b.employee_id}] Remaining PTO: {b.remaining_pto} days")

    # 5. Leave Records
    print(f"\nSeeding Leave Records ({len(LEAVE_RECORDS)} records)...")
    for r in LEAVE_RECORDS:
        db.collection("leave_records").document(r.leave_id).set(r.model_dump())
        print(f"  + [{r.leave_id}] {r.employee_id} -> {r.leave_type} ({r.status})")

    # 6. Jira Tickets
    print(f"\nSeeding Jira Tickets ({len(JIRA_TICKETS)} records)...")
    for t in JIRA_TICKETS:
        db.collection("jira_tickets").document(t.ticket_key).set(t.model_dump())
        print(f"  + [{t.ticket_key}] [{t.priority}] {t.title}")

    # 7. Expense Claims
    print(f"\nSeeding Expense Claims ({len(EXPENSE_CLAIMS)} records)...")
    for c in EXPENSE_CLAIMS:
        db.collection("expense_claims").document(c.claim_id).set(c.model_dump())
        print(f"  + [{c.claim_id}] {c.employee_id} -> ${c.amount:,.2f} ({c.status})")

    total = len(DEPARTMENTS) + len(EMPLOYEES) + len(SALARIES) + len(LEAVE_BALANCES) + len(LEAVE_RECORDS) + len(JIRA_TICKETS) + len(EXPENSE_CLAIMS)
    print("\n" + "=" * 60)
    print(f"SUCCESS: Seeded {total} records across 7 collections into Firestore!")
    print("=" * 60)

if __name__ == "__main__":
    run_seed()
