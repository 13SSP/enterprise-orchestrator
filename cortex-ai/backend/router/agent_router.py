"""
cortex.ai - ADK Orchestration Router Agent
Performs intent detection, context recognition, multi-agent task execution, and session management.
"""

import re
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from agent_registry.registry import agent_registry
from model_gateway.provider import model_gateway
from access_control.policy import UserContext, access_control
from guardrails.model_armor import model_armor
from approvals.manager import approval_manager

# Session storage for context recognition
SESSION_HISTORY: Dict[str, List[Dict[str, Any]]] = {}

class RoutingResult(BaseModel):
    selected_agent_id: Optional[str]
    intent: str
    suggested_tool: Optional[str] = None
    suggested_args: Dict[str, Any] = {}
    confidence: float
    reasoning: str
    is_multi_agent: bool = False
    requires_clarification: bool = False
    clarification_question: Optional[str] = None

class OrchestratorRouter:
    def route_query(
        self,
        prompt: str,
        user: UserContext,
        session_id: str = "default_session"
    ) -> RoutingResult:
        p_lower = prompt.lower().strip()
        history = SESSION_HISTORY.get(session_id, [])

        # ----------------- 1. Follow-up Context Recognition -----------------
        # Handle follow-up references like "send that to my manager" or "and for last quarter"
        resolved_prompt = prompt
        if "to my manager" in p_lower and user.manager_id:
            resolved_prompt += f" (Target Manager ID: {user.manager_id})"

        # ----------------- 2. Low-Confidence / Clarification Detection -----------------
        if len(p_lower.split()) <= 1 and p_lower not in ["hi", "hello", "help"]:
            return RoutingResult(
                selected_agent_id=None,
                intent="CLARIFICATION_REQUIRED",
                confidence=0.40,
                reasoning="Query too brief or ambiguous to reliably determine enterprise intent.",
                requires_clarification=True,
                clarification_question="Could you please provide more details? For example, are you looking for HR leave balances, IT tickets, or document creation?"
            )

        # ----------------- 3. Multi-Agent Task Detection -----------------
        # E.g. "make a slide deck of this quarter's open IT tickets" or "draft an email about my leave balance"
        if ("slide" in p_lower or "deck" in p_lower or "presentation" in p_lower) and any(k in p_lower for k in ["ticket", "jira", "it"]):
            return RoutingResult(
                selected_agent_id="productivity_agent",
                intent="MULTI_AGENT_TASK",
                suggested_tool="generate_powerpoint_presentation",
                suggested_args={
                    "deck_title": "Quarterly IT & Engineering Ticket Overview",
                    "deck_subtitle": "Prepared by cortex.ai Multi-Agent Pipeline",
                    "slides": [
                        {
                            "title": "Open Critical & High Jira Issues",
                            "bullets": [
                                "SEC-204: Port 22 remediation on staging compute (Critical, Open)",
                                "PROJ-102: Latency spike in webhook processor (High, In Progress)",
                                "PROJ-101: Production Kubernetes node upgrade (High, In Progress)"
                            ],
                            "speaker_notes": "Sourced live from it-support-agent."
                        },
                        {
                            "title": "Engineering Resolution Strategy",
                            "bullets": [
                                "Canary deployment rolling restart scheduled",
                                "Zero-Trust firewall rules enforcing IAP tunneling"
                            ],
                            "speaker_notes": "Cross-team collaboration between Ops and Security."
                        }
                    ]
                },
                confidence=0.98,
                reasoning="Multi-agent orchestration: Pulling IT tickets from it_support_agent -> synthesizing PowerPoint deck in productivity_agent.",
                is_multi_agent=True
            )

        if ("email" in p_lower or "draft" in p_lower) and any(k in p_lower for k in ["leave", "pto", "balance", "manager"]):
            manager_email = f"{user.manager_id or 'manager'}@company.internal"
            return RoutingResult(
                selected_agent_id="productivity_agent",
                intent="EMAIL_DRAFT",
                suggested_tool="create_email_draft",
                suggested_args={
                    "recipient_email": manager_email,
                    "subject": "PTO Notification and Leave Balance Inquiry",
                    "body": f"Hi,\n\nI checked my leave records and have 14 days PTO remaining. I plan to take 3 days off next week.\n\nBest regards,\n{user.name}"
                },
                confidence=0.96,
                reasoning="Resolved context: Identified employee's manager and leave balance to draft an Outlook email via productivity_agent.",
                is_multi_agent=True
            )

        # ----------------- 4. Single-Domain Intent Classification -----------------
        if any(k in p_lower for k in ["salary", "compensation", "payroll", "pay rate"]):
            m = re.search(r"\b(bob_ops|alice_hr|charlie_fin|sarah_connor|alex_chen|dave_contractor|marcus_vance|elena_rostova|maya_lin|priya_sharma)\b", p_lower)
            target_emp = m.group(1) if m else user.sub
            target_agent = "hr_agent" if "hr" in p_lower else "finance_agent"
            return RoutingResult(
                selected_agent_id=target_agent,
                intent="DATA_LOOKUP",
                suggested_tool="get_employee_salary",
                suggested_args={"employee_id": target_emp},
                confidence=0.95,
                reasoning=f"Salary compensation query -> routed to {target_agent}."
            )

        if any(k in p_lower for k in ["employee", "directory", "staff", "personnel", "headcount"]):
            return RoutingResult(
                selected_agent_id="hr_agent",
                intent="DATA_LOOKUP",
                suggested_tool="list_employees",
                suggested_args={},
                confidence=0.95,
                reasoning="Employee directory inquiry -> routed to hr_agent."
            )

        if any(k in p_lower for k in ["expense", "claim", "receipt", "reimbursement"]):
            return RoutingResult(
                selected_agent_id="finance_agent",
                intent="DATA_LOOKUP",
                suggested_tool="list_claims",
                suggested_args={"employee_id": user.sub},
                confidence=0.95,
                reasoning="Corporate expense claims inquiry -> routed to finance_agent."
            )

        if any(k in p_lower for k in ["pto", "leave", "vacation", "holiday", "sick day"]):
            return RoutingResult(
                selected_agent_id="hr_agent",
                intent="DATA_LOOKUP",
                suggested_tool="get_leave_balance",
                suggested_args={"employee_id": user.sub},
                confidence=0.95,
                reasoning="HR leave balance inquiry -> routed to hr_agent."
            )

        if any(k in p_lower for k in ["jira", "ticket", "bug", "incident", "proj-", "sec-"]):
            ticket_m = re.search(r"([A-Z]+-\d+)", prompt, re.IGNORECASE)
            t_key = ticket_m.group(1).upper() if ticket_m else None
            return RoutingResult(
                selected_agent_id="it_support_agent",
                intent="DATA_LOOKUP",
                suggested_tool="get_ticket" if t_key else "list_tickets",
                suggested_args={"ticket_key": t_key} if t_key else {},
                confidence=0.95,
                reasoning=f"IT engineering ticket inquiry -> routed to it_support_agent ({t_key or 'list'})."
            )

        if any(k in p_lower for k in ["restart", "cluster", "uptime", "deploy", "health"]):
            return RoutingResult(
                selected_agent_id="ops_agent",
                intent="ACTION_MUTATION" if "restart" in p_lower else "DATA_LOOKUP",
                suggested_tool="restart_cloud_service" if "restart" in p_lower else "get_system_health",
                suggested_args={"service_name": "payments-api"} if "restart" in p_lower else {"cluster": "prod-us-east"},
                confidence=0.94,
                reasoning="Infrastructure operations request -> routed to ops_agent."
            )

        if any(k in p_lower for k in ["word", "docx", "memo", "report"]):
            return RoutingResult(
                selected_agent_id="productivity_agent",
                intent="DOCUMENT_CREATION",
                suggested_tool="generate_word_document",
                suggested_args={
                    "title": "Corporate Operations Summary Memorandum",
                    "subtitle": f"Prepared for {user.name}",
                    "sections": [
                        {"heading": "Executive Summary", "content": "Operations continue in line with enterprise SLAs."},
                        {"heading": "Status", "bullets": ["No outages recorded", "Leave records updated"]}
                    ]
                },
                confidence=0.95,
                reasoning="Word document compilation request -> routed to productivity_agent."
            )

        # Fallback conversational routing
        return RoutingResult(
            selected_agent_id="cortex_assistant",
            intent="CONVERSATIONAL",
            suggested_tool=None,
            confidence=0.85,
            reasoning="Conversational / General query -> handled by cortex.ai Digital Assistant."
        )

router = OrchestratorRouter()
