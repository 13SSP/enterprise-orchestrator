"""
cortex.ai - Human-in-the-Loop Approval Manager
Enforces human verification before performing sensitive mutations:
- Submitting / approving leave requests
- Expense reimbursement payouts
- Sending corporate Outlook emails
"""

import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class PendingAction(BaseModel):
    confirmation_id: str
    action_type: str # EMAIL_SEND, LEAVE_MUTATION, EXPENSE_PAYOUT, INFRA_RESTART
    agent_id: str
    tool_name: str
    parameters: Dict[str, Any]
    requested_by: str
    summary: str
    status: str = "PENDING_APPROVAL" # PENDING_APPROVAL, APPROVED, REJECTED
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class ApprovalManager:
    def __init__(self):
        self._pending: Dict[str, PendingAction] = {}

    def create_pending_action(
        self,
        action_type: str,
        agent_id: str,
        tool_name: str,
        parameters: Dict[str, Any],
        requested_by: str,
        summary: str
    ) -> PendingAction:
        conf_id = f"conf-{str(uuid.uuid4())[:8]}"
        action = PendingAction(
            confirmation_id=conf_id,
            action_type=action_type,
            agent_id=agent_id,
            tool_name=tool_name,
            parameters=parameters,
            requested_by=requested_by,
            summary=summary
        )
        self._pending[conf_id] = action
        return action

    def get_action(self, confirmation_id: str) -> Optional[PendingAction]:
        return self._pending.get(confirmation_id)

    def list_pending(self) -> List[PendingAction]:
        return [a for a in self._pending.values() if a.status == "PENDING_APPROVAL"]

    def resolve_action(self, confirmation_id: str, approved: bool, user_sub: str) -> Optional[PendingAction]:
        action = self._pending.get(confirmation_id)
        if not action:
            return None
        action.status = "APPROVED" if approved else "REJECTED"
        return action

approval_manager = ApprovalManager()
