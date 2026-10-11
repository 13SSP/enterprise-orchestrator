"""
Database Seeding Script for Enterprise AI Orchestrator
Seeds departments, employees, salaries, leaves, jira tickets, and expense claims
into Google Cloud Firestore / Firebase.
"""

import sys
import os
import json
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from app.db import (
    firestore_db,
    department_repo,
    employee_repo,
    salary_repo,
    leave_repo,
    jira_repo,
    claim_repo,
    SEED_DEPARTMENTS,
    SEED_EMPLOYEES,
    SEED_SALARIES,
    SEED_LEAVE_BALANCES,
    SEED_LEAVE_RECORDS,
    SEED_JIRA_TICKETS,
    SEED_EXPENSE_CLAIMS
)

def seed_database():
    print("=" * 60)
    print("🏢 ENTERPRISE DATABASE INITIALIZATION & SEEDING")
    print("=" * 60)
    
    status = firestore_db.get_status()
    print(f"🔥 Database Mode:       {status['mode']}")
    print(f"📁 Storage / Project:   {status['project_id']}")
    print(f"🌐 Google Cloud Live:   {status['is_live_google_cloud']}")
    print("-" * 60)

    # 1. Departments
    print(f"📦 Seeding Departments ({len(SEED_DEPARTMENTS)} records)...")
    for dept in SEED_DEPARTMENTS:
        department_repo.save(dept)
        print(f"   ✓ [{dept.code}] {dept.name} (${dept.budget_allocated:,.0f})")

    # 2. Employees
    print(f"\n👥 Seeding Employees ({len(SEED_EMPLOYEES)} records)...")
    for emp in SEED_EMPLOYEES:
        employee_repo.save(emp)
        print(f"   ✓ [{emp.employee_id}] {emp.full_name} ({emp.title})")

    # 3. Salaries
    print(f"\n💰 Seeding Compensation & Salaries ({len(SEED_SALARIES)} records)...")
    for sal in SEED_SALARIES:
        salary_repo.save(sal)
        print(f"   ✓ [{sal.employee_id}] ${sal.base_salary:,.0f} {sal.currency} ({sal.pay_frequency})")

    # 4. Leave Balances
    print(f"\n🌴 Seeding Leave Balances ({len(SEED_LEAVE_BALANCES)} records)...")
    for bal in SEED_LEAVE_BALANCES:
        leave_repo.save_balance(bal)
        print(f"   ✓ [{bal.employee_id}] PTO Total: {bal.annual_pto_total}d | Used: {bal.annual_pto_used}d | Remaining: {bal.remaining_pto}d")

    # 5. Leave Records
    print(f"\n📅 Seeding Leave History & Requests ({len(SEED_LEAVE_RECORDS)} records)...")
    for rec in SEED_LEAVE_RECORDS:
        leave_repo.save_record(rec)
        print(f"   ✓ [{rec.leave_id}] {rec.employee_id}: {rec.leave_type} ({rec.days_count} days) -> Status: {rec.status}")

    # 6. Jira Tickets
    print(f"\n🎫 Seeding Jira Issues & Tickets ({len(SEED_JIRA_TICKETS)} records)...")
    for ticket in SEED_JIRA_TICKETS:
        jira_repo.save(ticket)
        print(f"   ✓ [{ticket.ticket_key}] [{ticket.priority}] {ticket.title} -> {ticket.status}")

    # 7. Expense Claims
    print(f"\n💳 Seeding Expense Claims ({len(SEED_EXPENSE_CLAIMS)} records)...")
    for claim in SEED_EXPENSE_CLAIMS:
        claim_repo.save(claim)
        print(f"   ✓ [{claim.claim_id}] {claim.employee_id}: ${claim.amount:,.2f} at {claim.merchant} -> {claim.status}")

    print("\n" + "=" * 60)
    print("✅ DATABASE SEEDING COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print(f"Total Collections Created: 7")
    print(f"Total Records Seeded:     {len(SEED_DEPARTMENTS) + len(SEED_EMPLOYEES) + len(SEED_SALARIES) + len(SEED_LEAVE_BALANCES) + len(SEED_LEAVE_RECORDS) + len(SEED_JIRA_TICKETS) + len(SEED_EXPENSE_CLAIMS)}")
    print("=" * 60)

if __name__ == "__main__":
    seed_database()
