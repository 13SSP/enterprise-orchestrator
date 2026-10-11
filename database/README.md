# cortex.ai Database Sub-Project

This sub-project manages the Google Cloud Firestore schema, security rules, indexes, and sample seed data for `cortex.ai`.

## Collections
- `departments`: Enterprise business units and budgets.
- `employees`: User records, organizational roles, and skills.
- `salaries`: Sensitive compensation tiers and masked bank records.
- `leave_balances`: Annual PTO and sick leave allotments.
- `leave_records`: History of leave submissions and manager approvals.
- `jira_tickets`: IT engineering and support issue tracking.
- `expense_claims`: Travel and operations reimbursement requests.

## Running the Emulator
```bash
firebase emulators:start --only firestore,auth
```

## Seeding Sample Data
```bash
python seed_db.py
```
