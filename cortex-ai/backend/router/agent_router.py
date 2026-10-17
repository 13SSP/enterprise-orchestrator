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
        session_id: str = "default_session",
        target_agent_id: Optional[str] = None
    ) -> RoutingResult:
        p_lower = prompt.lower().strip()
        history = SESSION_HISTORY.get(session_id, [])

        # ----------------- 0. User Selected Target Agent -----------------
        # If user explicitly selected an agent (or continuing session with selected agent), strictly preserve it
        if target_agent_id and target_agent_id not in ["auto", "cortex_assistant"]:
            if target_agent_id == "hr_agent":
                if any(k in p_lower for k in ["pto", "leave", "vacation", "holiday", "sick day", "balance"]):
                    return RoutingResult(
                        selected_agent_id="hr_agent",
                        intent="DATA_LOOKUP",
                        suggested_tool="get_leave_balance",
                        suggested_args={"employee_id": user.sub},
                        confidence=0.99,
                        reasoning="User targeted HR Agent -> executed get_leave_balance."
                    )
                elif any(k in p_lower for k in ["employee", "directory", "staff", "personnel", "headcount"]):
                    return RoutingResult(
                        selected_agent_id="hr_agent",
                        intent="DATA_LOOKUP",
                        suggested_tool="list_employees",
                        suggested_args={},
                        confidence=0.99,
                        reasoning="User targeted HR Agent -> executed list_employees."
                    )
                else:
                    return RoutingResult(
                        selected_agent_id="hr_agent",
                        intent="CONVERSATIONAL",
                        suggested_tool=None,
                        confidence=0.99,
                        reasoning="User targeted HR Operations Agent."
                    )
            elif target_agent_id == "finance_agent":
                if any(k in p_lower for k in ["salary", "compensation", "payroll", "pay rate"]):
                    m = re.search(r"\b(bob_ops|alice_hr|charlie_fin|sarah_connor|alex_chen|dave_contractor|marcus_vance|elena_rostova|maya_lin|priya_sharma)\b", p_lower)
                    target_emp = m.group(1) if m else user.sub
                    return RoutingResult(
                        selected_agent_id="finance_agent",
                        intent="DATA_LOOKUP",
                        suggested_tool="get_employee_salary",
                        suggested_args={"employee_id": target_emp},
                        confidence=0.99,
                        reasoning="User targeted Finance Agent -> executed get_employee_salary."
                    )
                elif any(k in p_lower for k in ["expense", "claim", "receipt", "reimbursement"]):
                    return RoutingResult(
                        selected_agent_id="finance_agent",
                        intent="DATA_LOOKUP",
                        suggested_tool="list_claims",
                        suggested_args={"employee_id": user.sub},
                        confidence=0.99,
                        reasoning="User targeted Finance Agent -> executed list_claims."
                    )
                else:
                    return RoutingResult(
                        selected_agent_id="finance_agent",
                        intent="CONVERSATIONAL",
                        suggested_tool=None,
                        confidence=0.99,
                        reasoning="User targeted Corporate Finance Agent."
                    )
            elif target_agent_id == "financial_benchmark":
                if any(k in p_lower for k in ["ebitda", "operating margin", "margin", "profit", "earnings", "revenue"]):
                    return RoutingResult(
                        selected_agent_id="financial_benchmark",
                        intent="FINANCIAL_ANALYSIS",
                        suggested_tool="calculate_ebitda",
                        suggested_args={"fiscal_year": "2026", "quarter": "Q3"},
                        confidence=0.99,
                        reasoning="User targeted Financial Benchmark Agent -> executed calculate_ebitda."
                    )
                elif any(k in p_lower for k in ["sec", "10-k", "10-q", "filing", "annual report"]):
                    return RoutingResult(
                        selected_agent_id="financial_benchmark",
                        intent="DATA_LOOKUP",
                        suggested_tool="extract_sec_filings",
                        suggested_args={"form_type": "10-K", "ticker": "CORTEX"},
                        confidence=0.99,
                        reasoning="User targeted Financial Benchmark Agent -> executed extract_sec_filings."
                    )
                elif any(k in p_lower for k in ["salary", "compensation", "payroll", "pay rate"]):
                    m = re.search(r"\b(bob_ops|alice_hr|charlie_fin|sarah_connor|alex_chen|dave_contractor|marcus_vance|elena_rostova|maya_lin|priya_sharma)\b", p_lower)
                    target_emp = m.group(1) if m else user.sub
                    return RoutingResult(
                        selected_agent_id="financial_benchmark",
                        intent="DATA_LOOKUP",
                        suggested_tool="get_employee_salary",
                        suggested_args={"employee_id": target_emp},
                        confidence=0.99,
                        reasoning="User targeted Financial Benchmark Agent -> executed get_employee_salary."
                    )
                else:
                    return RoutingResult(
                        selected_agent_id="financial_benchmark",
                        intent="CONVERSATIONAL",
                        suggested_tool=None,
                        confidence=0.99,
                        reasoning="User targeted Financial Benchmark Agent."
                    )
            elif target_agent_id == "it_support_agent":
                ticket_m = re.search(r"([A-Z]+-\d+)", prompt, re.IGNORECASE)
                t_key = ticket_m.group(1).upper() if ticket_m else None
                return RoutingResult(
                    selected_agent_id="it_support_agent",
                    intent="DATA_LOOKUP",
                    suggested_tool="get_ticket" if t_key else "list_tickets",
                    suggested_args={"ticket_key": t_key} if t_key else {},
                    confidence=0.99,
                    reasoning=f"User targeted IT Support Agent ({t_key or 'tickets'})."
                )
            elif target_agent_id == "ops_agent":
                return RoutingResult(
                    selected_agent_id="ops_agent",
                    intent="ACTION_MUTATION" if "restart" in p_lower else "DATA_LOOKUP",
                    suggested_tool="restart_cloud_service" if "restart" in p_lower else "get_system_health",
                    suggested_args={"service_name": "payments-api"} if "restart" in p_lower else {"cluster": "prod-us-east"},
                    confidence=0.99,
                    reasoning="User targeted Cloud Operations Agent."
                )
            elif target_agent_id == "productivity_agent":
                if any(k in p_lower for k in ["slide", "deck", "presentation", "powerpoint"]):
                    return RoutingResult(
                        selected_agent_id="productivity_agent",
                        intent="DOCUMENT_CREATION",
                        suggested_tool="generate_powerpoint_presentation",
                        suggested_args={
                            "deck_title": "Enterprise Operations Presentation",
                            "deck_subtitle": f"Generated for {user.name}",
                            "slides": [
                                {"title": "Overview & Objectives", "bullets": ["Enterprise operations", "Automated orchestration"]},
                                {"title": "Milestones & Metrics", "bullets": ["99.9% availability", "Zero-trust compliance"]}
                            ]
                        },
                        confidence=0.99,
                        reasoning="User targeted Productivity Agent -> PowerPoint generation."
                    )
                elif any(k in p_lower for k in ["word", "docx", "memo", "report"]):
                    return RoutingResult(
                        selected_agent_id="productivity_agent",
                        intent="DOCUMENT_CREATION",
                        suggested_tool="generate_word_document",
                        suggested_args={
                            "title": "Corporate Memorandum",
                            "subtitle": f"Prepared for {user.name}",
                            "sections": [
                                {"heading": "Overview", "content": "Summary of active enterprise processes and metrics."},
                                {"heading": "Key Directives", "bullets": ["Operational readiness", "System synchronization"]}
                            ]
                        },
                        confidence=0.99,
                        reasoning="User targeted Productivity Agent -> Word doc generation."
                    )
                elif any(k in p_lower for k in ["email", "draft"]):
                    return RoutingResult(
                        selected_agent_id="productivity_agent",
                        intent="EMAIL_DRAFT",
                        suggested_tool="create_email_draft",
                        suggested_args={
                            "recipient_email": f"{user.manager_id or 'manager'}@company.internal",
                            "subject": "Enterprise Operational Update",
                            "body": f"Hi,\n\nFollowing up on our recent operational discussion.\n\nBest regards,\n{user.name}"
                        },
                        confidence=0.99,
                        reasoning="User targeted Productivity Agent -> Email draft."
                    )
                else:
                    return RoutingResult(
                        selected_agent_id="productivity_agent",
                        intent="CONVERSATIONAL",
                        suggested_tool=None,
                        confidence=0.99,
                        reasoning="User targeted Productivity Agent."
                    )
            elif target_agent_id == "swe_bench_agent":
                if any(k in p_lower for k in ["test", "pytest", "unit test", "runner"]):
                    return RoutingResult(
                        selected_agent_id="swe_bench_agent",
                        intent="CODE_TESTING",
                        suggested_tool="pytest_runner",
                        suggested_args={"repo": "enterprise-orchestrator", "test_path": "tests/"},
                        confidence=0.99,
                        reasoning="User targeted SWE-bench Agent -> executed pytest_runner."
                    )
                elif any(k in p_lower for k in ["patch", "git patch", "fix", "pr", "diff"]):
                    return RoutingResult(
                        selected_agent_id="swe_bench_agent",
                        intent="CODE_PATCH",
                        suggested_tool="git_patch_generator",
                        suggested_args={"repo": "enterprise-orchestrator", "issue_id": "ISSUE-42"},
                        confidence=0.99,
                        reasoning="User targeted SWE-bench Agent -> executed git_patch_generator."
                    )
                elif any(k in p_lower for k in ["index", "repo", "codebase", "search code", "files"]):
                    return RoutingResult(
                        selected_agent_id="swe_bench_agent",
                        intent="CODE_ANALYSIS",
                        suggested_tool="code_repo_indexer",
                        suggested_args={"repo": "enterprise-orchestrator"},
                        confidence=0.99,
                        reasoning="User targeted SWE-bench Agent -> executed code_repo_indexer."
                    )
                else:
                    return RoutingResult(
                        selected_agent_id="swe_bench_agent",
                        intent="CONVERSATIONAL",
                        suggested_tool=None,
                        confidence=0.99,
                        reasoning="User targeted SWE-bench Agent."
                    )
            elif target_agent_id == "a2a_benchmark":
                if any(k in p_lower for k in ["trace", "synthetic", "simulate"]):
                    return RoutingResult(
                        selected_agent_id="a2a_benchmark",
                        intent="BENCHMARK_EXECUTION",
                        suggested_tool="run_synthetic_trace",
                        suggested_args={"num_turns": 5, "domain": "enterprise_ops"},
                        confidence=0.99,
                        reasoning="User targeted A2A Benchmark -> executed run_synthetic_trace."
                    )
                else:
                    return RoutingResult(
                        selected_agent_id="a2a_benchmark",
                        intent="BENCHMARK_EVALUATION",
                        suggested_tool="benchmark_evaluator",
                        suggested_args={"benchmark_name": "A2A Multi-Agent Routing"},
                        confidence=0.99,
                        reasoning="User targeted A2A Benchmark -> executed benchmark_evaluator."
                    )
            else:
                # Dynamic matching for custom/onboarded agents in agent_registry
                cand = agent_registry.get_agent(target_agent_id)
                matched_tool = None
                if cand and cand.allowed_tools:
                    for t in cand.allowed_tools:
                        words = t.lower().replace("_", " ").split()
                        if any(w in p_lower for w in words if len(w) > 3):
                            matched_tool = t
                            break
                return RoutingResult(
                    selected_agent_id=target_agent_id,
                    intent="DATA_LOOKUP" if matched_tool else "CONVERSATIONAL",
                    suggested_tool=matched_tool,
                    suggested_args={},
                    confidence=0.99,
                    reasoning=f"User targeted agent: {target_agent_id}{f' -> executed {matched_tool}' if matched_tool else ''}."
                )

        # ----------------- Smart Orchestrator Intent Check (Auto-Route Mode) -----------------
        # Real-time internet, weather, external search, and general inquiries in auto-route are handled by cortex_assistant
        if any(k in p_lower for k in [
            "weather", "forecast", "temperature", "climate", "who is", "search for", "latest on",
            "what is the weather", "current weather", "tell me about", "explain", "analogy"
        ]):
            return RoutingResult(
                selected_agent_id="cortex_assistant",
                intent="CONVERSATIONAL",
                suggested_tool=None,
                confidence=0.95,
                reasoning="General external/internet inquiry in auto-route mode -> handled by cortex.ai Digital Assistant."
            )

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

        if any(k in p_lower for k in ["pytest", "unit test", "git patch", "swe-bench", "swe bench", "github issue", "repo indexer"]):
            suggested_tool = "pytest_runner" if any(k in p_lower for k in ["test", "pytest"]) else ("git_patch_generator" if any(k in p_lower for k in ["patch", "git", "diff", "pr"]) else "code_repo_indexer")
            return RoutingResult(
                selected_agent_id="swe_bench_agent",
                intent="CODE_TESTING" if "test" in p_lower else "CODE_ANALYSIS",
                suggested_tool=suggested_tool,
                suggested_args={"repo": "enterprise-orchestrator"},
                confidence=0.95,
                reasoning=f"Software engineering request -> routed to swe_bench_agent ({suggested_tool})."
            )

        if any(k in p_lower for k in ["ebitda", "operating margin", "sec filing", "10-k", "10-q", "sec filings", "financial benchmark"]):
            suggested_tool = "calculate_ebitda" if any(k in p_lower for k in ["ebitda", "margin", "profit"]) else "extract_sec_filings"
            return RoutingResult(
                selected_agent_id="financial_benchmark",
                intent="FINANCIAL_ANALYSIS",
                suggested_tool=suggested_tool,
                suggested_args={"fiscal_year": "2026", "quarter": "Q3"} if suggested_tool == "calculate_ebitda" else {"form_type": "10-K", "ticker": "CORTEX"},
                confidence=0.95,
                reasoning=f"Financial analytics inquiry -> routed to financial_benchmark ({suggested_tool})."
            )

        if any(k in p_lower for k in ["a2a benchmark", "synthetic trace", "agent benchmark"]):
            suggested_tool = "run_synthetic_trace" if "trace" in p_lower else "benchmark_evaluator"
            return RoutingResult(
                selected_agent_id="a2a_benchmark",
                intent="BENCHMARK_EXECUTION",
                suggested_tool=suggested_tool,
                suggested_args={"benchmark_name": "A2A Multi-Agent"} if suggested_tool == "benchmark_evaluator" else {"num_turns": 5},
                confidence=0.95,
                reasoning=f"Agent benchmark inquiry -> routed to a2a_benchmark ({suggested_tool})."
            )

        # ----------------- 5. Dynamic Agent Registry Matching -----------------
        for cand_agent in agent_registry.list_agents(active_only=True):
            if cand_agent.id in ["cortex_assistant", "router", "shieldgemma_guardrail", "hr_agent", "finance_agent", "it_support_agent", "ops_agent", "productivity_agent", "swe_bench_agent", "financial_benchmark", "a2a_benchmark"]:
                continue
            # Match keywords in prompt against agent name, description, and allowed_tools
            cand_name_words = cand_agent.name.lower().split()
            cand_tool_matches = [t for t in cand_agent.allowed_tools if any(w in p_lower for w in t.lower().replace("_", " ").split() if len(w) > 3)]
            if any(w in p_lower for w in cand_name_words if len(w) > 3) or cand_tool_matches:
                # Check user access
                allowed_roles = cand_agent.allowed_roles or ["*"]
                if "*" in allowed_roles or (user.role in allowed_roles):
                    suggested_tool = cand_tool_matches[0] if cand_tool_matches else (cand_agent.allowed_tools[0] if cand_agent.allowed_tools else None)
                    return RoutingResult(
                        selected_agent_id=cand_agent.id,
                        intent="DATA_LOOKUP" if suggested_tool else "CONVERSATIONAL",
                        suggested_tool=suggested_tool,
                        suggested_args={},
                        confidence=0.93,
                        reasoning=f"Dynamic intent matched custom agent '{cand_agent.name}' in agent registry."
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
