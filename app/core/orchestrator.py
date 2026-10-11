import os
import time
import uuid
import json
import re
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from app.config import settings
from app.core.registry import registry, AgentManifest, ToolDefinition
from app.core.policy import policy_engine, UserContext, PolicyDecision
from app.core.rag import rag_manager
from app.core.observability import observability

# In-memory store for pending human-in-the-loop write confirmations
PENDING_CONFIRMATIONS: Dict[str, Dict[str, Any]] = {}

class Orchestrator:
    """
    Core ADK Orchestrator and Gemini Router Agent.
    Orchestrates routing across dynamic team agents, executes ADK policy gates,
    enforces per-agent tool filtering, handles RAG retrieval and write confirmation cycles.
    """

    def __init__(self):
        self._gemini_client = None
        if settings.GEMINI_API_KEY:
            try:
                from google import genai
                self._gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
                print("[Orchestrator] Initialized Google GenAI Gemini client.")
            except Exception as e:
                print(f"[Orchestrator] Warning: could not init Gemini client: {e}")

    def route_prompt(
        self,
        prompt: str,
        user: UserContext,
        trace_id: str
    ) -> Dict[str, Any]:
        """
        Determines target agent, confidence, intent, and candidate tool parameters.
        Uses Gemini if available, or high-accuracy domain semantic parser.
        """
        all_agents = registry.list_agents(active_only=True)
        # Filter agents accessible to user
        accessible_agents = [
            a for a in all_agents 
            if ("*" in user.allowed_agent_ids or a.id in user.allowed_agent_ids)
        ]

        if not accessible_agents:
            observability.log_routing(
                trace_id=trace_id,
                user=user.model_dump(),
                prompt=prompt,
                selected_agent=None,
                confidence=0.0,
                reasoning="No agents available for current user's role/team.",
                intent="out_of_scope",
                candidate_agents=[]
            )
            return {
                "selected_agent_id": None,
                "confidence": 0.0,
                "intent": "out_of_scope",
                "reasoning": "User does not have access to any registered agents.",
                "candidate_agents": [],
                "suggested_tool": None,
                "suggested_args": {}
            }

        candidate_ids = [a.id for a in accessible_agents]

        # 1. Attempt routing with Gemini if valid Google AI Studio API key configured
        if self._gemini_client and settings.GEMINI_API_KEY.startswith("AIzaSy"):
            try:
                agent_catalog = []
                for a in accessible_agents:
                    visible_tools = [t.name for t in policy_engine.filter_visible_tools(user, a)]
                    agent_catalog.append({
                        "id": a.id,
                        "name": a.name,
                        "description": a.description,
                        "owner_team": a.owner_team,
                        "available_tools": visible_tools,
                        "knowledge_scopes": a.knowledge_scopes
                    })

                system_instruction = (
                    "You are the Enterprise Orchestrator Router. Select the single best agent "
                    "to handle the user's request based on the catalog. Respond ONLY in valid JSON with format: "
                    '{"selected_agent_id": "<id>", "confidence": 0.95, "intent": "tool_call|knowledge_retrieval|conversational", '
                    '"reasoning": "<brief>", "suggested_tool": "<tool_name or null>", "suggested_args": {}}'
                )
                gemini_prompt = f"Catalog: {json.dumps(agent_catalog)}\n\nUser Prompt: {prompt}"

                response = self._gemini_client.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=gemini_prompt,
                    config={"response_mime_type": "application/json", "system_instruction": system_instruction}
                )
                parsed = json.loads(response.text)
                selected_id = parsed.get("selected_agent_id")
                if selected_id in candidate_ids:
                    observability.log_routing(
                        trace_id=trace_id,
                        user=user.model_dump(),
                        prompt=prompt,
                        selected_agent=selected_id,
                        confidence=float(parsed.get("confidence", 0.9)),
                        reasoning=f"Gemini: {parsed.get('reasoning', '')}",
                        intent=parsed.get("intent", "conversational"),
                        candidate_agents=candidate_ids
                    )
                    return {
                        "selected_agent_id": selected_id,
                        "confidence": float(parsed.get("confidence", 0.9)),
                        "intent": parsed.get("intent", "conversational"),
                        "reasoning": parsed.get("reasoning", "Selected by Gemini Router"),
                        "candidate_agents": candidate_ids,
                        "suggested_tool": parsed.get("suggested_tool"),
                        "suggested_args": parsed.get("suggested_args", {})
                    }
            except Exception as e:
                print(f"[Orchestrator] Gemini routing fallback due to: {e}")

        # 2. Intelligent Built-in Semantic Evaluator (works offline / keyless)
        p_lower = prompt.lower()
        scored_agents = []

        for agent in accessible_agents:
            score = 0.1
            reasons = []

            # Check keyword affinity
            agent_text = f"{agent.name} {agent.description} {agent.owner_team} {' '.join(agent.allowed_tools)} {' '.join(agent.knowledge_scopes)}".lower()
            
            # Domain matching rules
            if any(k in p_lower for k in ["jira", "ticket", "restart", "deploy", "server", "cluster", "health", "ops", "kubernetes", "incident", "cpu", "uptime"]):
                if "it" in agent.id or "ops" in agent.owner_team.lower():
                    score += 0.7
                    reasons.append("Matched IT & Operations keywords")

            if any(k in p_lower for k in ["pto", "vacation", "leave", "time off", "holiday", "sick", "employee", "benefits", "hr", "workday", "handbook"]):
                if "hr" in agent.id or "human" in agent.owner_team.lower():
                    score += 0.7
                    reasons.append("Matched HR & People Operations keywords")

            if any(k in p_lower for k in ["expense", "reimbursement", "budget", "finance", "receipt", "payout", "cost", "dollar", "fiscal"]):
                if "finance" in agent.id or "finance" in agent.owner_team.lower():
                    score += 0.7
                    reasons.append("Matched Finance & Expenses keywords")

            if any(k in p_lower for k in ["security", "vulnerability", "firewall", "vpc", "posture", "secops", "cve"]):
                if "security" in agent.id or "sec" in agent.owner_team.lower():
                    score += 0.7
                    reasons.append("Matched Security Ops keywords")

            # Word token overlap
            prompt_tokens = set(re.findall(r"\w+", p_lower))
            overlap = prompt_tokens.intersection(set(re.findall(r"\w+", agent_text)))
            score += len(overlap) * 0.08

            scored_agents.append((agent, score, ", ".join(reasons) or "General capability alignment"))

        scored_agents.sort(key=lambda x: x[1], reverse=True)
        top_agent, top_score, reason = scored_agents[0]

        # Determine Intent
        intent = "conversational"
        suggested_tool = None
        suggested_args = {}

        # Check if query targets a tool
        visible_tools = policy_engine.filter_visible_tools(user, top_agent)
        for tool in visible_tools:
            tool_tokens = tool.name.split("_")
            if any(tok in p_lower for tok in tool_tokens if len(tok) > 3) or (tool.name.replace("_", " ") in p_lower):
                intent = "tool_call"
                suggested_tool = tool.name
                # Extract simple args
                if "jira" in tool.name:
                    m = re.search(r"([A-Z]+-\d+)", prompt, re.IGNORECASE)
                    suggested_args = {"issue_key": m.group(1).upper() if m else "PROJ-102"}
                elif "restart" in tool.name:
                    suggested_args = {"service_name": "payments-api"}
                elif "rollback" in tool.name:
                    suggested_args = {"service_name": "auth-service", "target_version": "v1.4.2"}
                elif "pto" in tool.name:
                    suggested_args = {"employee_id": user.sub}
                elif "expense" in tool.name:
                    suggested_args = {"report_id": "EXP-2026-88", "amount": 250.0, "merchant": "Delta Airlines"}
                break

        # Check if query matches knowledge retrieval
        if not suggested_tool:
            if any(k in p_lower for k in ["policy", "how many", "what is", "how do i", "guidelines", "rules", "runbook", "standard"]):
                intent = "knowledge_retrieval"

        confidence = min(0.98, max(0.65, top_score))

        observability.log_routing(
            trace_id=trace_id,
            user=user.model_dump(),
            prompt=prompt,
            selected_agent=top_agent.id,
            confidence=confidence,
            reasoning=f"Intent Router: {reason}",
            intent=intent,
            candidate_agents=candidate_ids
        )

        return {
            "selected_agent_id": top_agent.id,
            "confidence": confidence,
            "intent": intent,
            "reasoning": f"Domain intent matched agent '{top_agent.name}': {reason}",
            "candidate_agents": candidate_ids,
            "suggested_tool": suggested_tool,
            "suggested_args": suggested_args
        }

    def execute_chat(
        self,
        prompt: str,
        user: UserContext,
        confirmed_action_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main end-to-end orchestration flow:
        Router -> Policy Check -> RAG / Tool Execution -> Observability -> Response
        """
        trace_id = str(uuid.uuid4())
        start_time = time.time()

        # Handle resume from write confirmation approval
        if confirmed_action_id and confirmed_action_id in PENDING_CONFIRMATIONS:
            return self._resume_confirmed_action(confirmed_action_id, user, trace_id)

        # 1. Routing phase
        routing = self.route_prompt(prompt, user, trace_id)
        selected_agent_id = routing.get("selected_agent_id")

        if not selected_agent_id:
            return {
                "trace_id": trace_id,
                "reply": "I am unable to route your request because your user account is not assigned to any active agents.",
                "routing": routing,
                "action_taken": "NONE",
                "policy_decision": {"allowed": False, "reason": "No accessible agents"},
                "duration_ms": round((time.time() - start_time) * 1000, 1)
            }

        agent = registry.get_agent(selected_agent_id)

        # 2. Tier 2 Policy: Verify User can call this agent
        agent_access_decision = policy_engine.can_user_call_agent(user, selected_agent_id, trace_id)
        if not agent_access_decision.allowed:
            return {
                "trace_id": trace_id,
                "reply": f"⛔ **Access Denied**: {agent_access_decision.reason}\n\n*Policy Rule Enforced: `{agent_access_decision.rule_name}`*",
                "routing": routing,
                "agent_info": agent.model_dump() if agent else None,
                "action_taken": "POLICY_BLOCKED",
                "policy_decision": agent_access_decision.model_dump(),
                "duration_ms": round((time.time() - start_time) * 1000, 1)
            }

        gateway_context = policy_engine.get_agent_gateway_context(selected_agent_id)

        # 3. Handle Remote A2A Agent
        if agent.agent_type == "remote_a2a":
            return self._handle_remote_a2a(prompt, agent, user, routing, gateway_context, trace_id, start_time)

        # 4. Handle Knowledge Retrieval (RAG)
        if routing["intent"] == "knowledge_retrieval" or (not routing.get("suggested_tool") and agent.knowledge_scopes):
            rag_results = rag_manager.search_knowledge(
                query=prompt,
                allowed_scopes=agent.knowledge_scopes,
                top_k=2,
                trace_id=trace_id,
                user=user.model_dump()
            )
            if rag_results:
                docs_formatted = "\n\n".join([f"**From `{r['title']}` ({r['scope']}):**\n{r['content']}" for r in rag_results])
                reply = (
                    f"Hello {user.name}, I consulted our internal knowledge base via **Vertex AI Search** scoped to `{', '.join(agent.knowledge_scopes)}`:\n\n"
                    f"{docs_formatted}\n\n"
                    f"*Answered by {agent.name} with verified data-store isolation.*"
                )
                return {
                    "trace_id": trace_id,
                    "reply": reply,
                    "routing": routing,
                    "agent_info": agent.model_dump(),
                    "action_taken": "RAG_RETRIEVAL",
                    "rag_sources": rag_results,
                    "gateway_context": gateway_context,
                    "policy_decision": agent_access_decision.model_dump(),
                    "duration_ms": round((time.time() - start_time) * 1000, 1)
                }

        # 5. Handle Tool Execution
        tool_name = routing.get("suggested_tool")
        if tool_name:
            tool_args = routing.get("suggested_args", {})
            # Run ADK before_tool_callback
            policy_check = policy_engine.before_tool_callback(
                agent_id=agent.id,
                tool_name=tool_name,
                user=user,
                tool_parameters=tool_args,
                trace_id=trace_id,
                is_already_confirmed=False
            )

            # Check if write operation requires Human-In-The-Loop Confirmation
            if policy_check.requires_confirmation:
                conf_id = str(uuid.uuid4())[:8]
                PENDING_CONFIRMATIONS[conf_id] = {
                    "confirmation_id": conf_id,
                    "agent_id": agent.id,
                    "tool_name": tool_name,
                    "parameters": tool_args,
                    "prompt": prompt,
                    "user_sub": user.sub,
                    "created_at": time.time(),
                }
                observability.log_write_confirmation(
                    trace_id=trace_id,
                    user=user.model_dump(),
                    confirmation_id=conf_id,
                    tool_name=tool_name,
                    status="PENDING",
                    details=tool_args
                )
                tool_def = registry.get_tool(tool_name)
                return {
                    "trace_id": trace_id,
                    "reply": (
                        f"⚠️ **Action Requires Confirmation**:\n\n"
                        f"The **{agent.name}** is attempting to execute mutation tool: `{tool_name}`.\n\n"
                        f"- **Operation:** {tool_def.description if tool_def else tool_name}\n"
                        f"- **Parameters:** `{json.dumps(tool_args)}`\n"
                        f"- **Policy:** Human-In-The-Loop required for all Write/Mutation operations.\n\n"
                        f"Please confirm or cancel below."
                    ),
                    "routing": routing,
                    "agent_info": agent.model_dump(),
                    "action_taken": "CONFIRMATION_REQUIRED",
                    "pending_confirmation": {
                        "confirmation_id": conf_id,
                        "tool_name": tool_name,
                        "parameters": tool_args,
                        "description": tool_def.description if tool_def else tool_name,
                    },
                    "gateway_context": gateway_context,
                    "policy_decision": policy_check.model_dump(),
                    "duration_ms": round((time.time() - start_time) * 1000, 1)
                }

            # Check if tool is denied by Policy
            if not policy_check.allowed:
                return {
                    "trace_id": trace_id,
                    "reply": f"⛔ **Action Blocked by Policy Layer**: {policy_check.reason}\n\n*Rule: `{policy_check.rule_name}`*",
                    "routing": routing,
                    "agent_info": agent.model_dump(),
                    "action_taken": "POLICY_DENIED",
                    "policy_decision": policy_check.model_dump(),
                    "duration_ms": round((time.time() - start_time) * 1000, 1)
                }

            # Execute tool safely
            tool_start = time.time()
            tool_result = self._dispatch_tool_call(agent.id, tool_name, tool_args)
            tool_duration = (time.time() - tool_start) * 1000
            
            tool_def = registry.get_tool(tool_name)
            observability.log_tool_execution(
                trace_id=trace_id,
                user=user.model_dump(),
                agent_id=agent.id,
                tool_name=tool_name,
                parameters=tool_args,
                result=tool_result,
                duration_ms=tool_duration,
                is_write=tool_def.is_write if tool_def else False
            )

            reply = (
                f"**{agent.name}** successfully executed `{tool_name}`:\n\n"
                f"```json\n{json.dumps(tool_result, indent=2)}\n```\n\n"
                f"*Gateway Service Account: `{gateway_context['service_account']}`*"
            )

            return {
                "trace_id": trace_id,
                "reply": reply,
                "routing": routing,
                "agent_info": agent.model_dump(),
                "action_taken": "TOOL_EXECUTED",
                "tool_executed": {
                    "tool_name": tool_name,
                    "parameters": tool_args,
                    "result": tool_result,
                    "duration_ms": round(tool_duration, 1)
                },
                "gateway_context": gateway_context,
                "policy_decision": policy_check.model_dump(),
                "duration_ms": round((time.time() - start_time) * 1000, 1)
            }

        # 6. Fallback conversational reply
        reply = (
            f"Hello {user.name}! I am the **{agent.name}** ({agent.owner_team}).\n\n"
            f"How can I assist you today? I have access to tools such as `{', '.join(agent.allowed_tools[:3])}` "
            f"and knowledge scopes `{', '.join(agent.knowledge_scopes)}`."
        )
        return {
            "trace_id": trace_id,
            "reply": reply,
            "routing": routing,
            "agent_info": agent.model_dump(),
            "action_taken": "CONVERSATIONAL",
            "gateway_context": gateway_context,
            "policy_decision": agent_access_decision.model_dump(),
            "duration_ms": round((time.time() - start_time) * 1000, 1)
        }

    def _resume_confirmed_action(self, confirmation_id: str, user: UserContext, trace_id: str) -> Dict[str, Any]:
        """Executes a previously blocked write operation that the human approved."""
        action = PENDING_CONFIRMATIONS.pop(confirmation_id, None)
        if not action:
            return {"reply": "Confirmation expired or invalid.", "trace_id": trace_id}

        agent_id = action["agent_id"]
        tool_name = action["tool_name"]
        parameters = action["parameters"]
        agent = registry.get_agent(agent_id)

        # Log approval
        observability.log_write_confirmation(
            trace_id=trace_id,
            user=user.model_dump(),
            confirmation_id=confirmation_id,
            tool_name=tool_name,
            status="APPROVED",
            details=parameters
        )

        tool_start = time.time()
        result = self._dispatch_tool_call(agent_id, tool_name, parameters)
        duration_ms = (time.time() - tool_start) * 1000

        tool_def = registry.get_tool(tool_name)
        observability.log_tool_execution(
            trace_id=trace_id,
            user=user.model_dump(),
            agent_id=agent_id,
            tool_name=tool_name,
            parameters=parameters,
            result=result,
            duration_ms=duration_ms,
            is_write=tool_def.is_write if tool_def else True
        )

        reply = (
            f"✅ **Write Action Approved & Executed** by `{user.name}`:\n\n"
            f"**{agent.name}** ran `{tool_name}` with parameters: `{json.dumps(parameters)}`.\n\n"
            f"**Result:**\n```json\n{json.dumps(result, indent=2)}\n```"
        )

        return {
            "trace_id": trace_id,
            "reply": reply,
            "routing": {"selected_agent_id": agent_id, "confidence": 1.0, "intent": "tool_call"},
            "agent_info": agent.model_dump() if agent else None,
            "action_taken": "WRITE_APPROVED_EXECUTED",
            "tool_executed": {
                "tool_name": tool_name,
                "parameters": parameters,
                "result": result,
                "duration_ms": round(duration_ms, 1)
            },
            "duration_ms": round(duration_ms, 1)
        }

    def cancel_pending_action(self, confirmation_id: str, user: UserContext) -> Dict[str, Any]:
        action = PENDING_CONFIRMATIONS.pop(confirmation_id, None)
        trace_id = str(uuid.uuid4())
        if action:
            observability.log_write_confirmation(
                trace_id=trace_id,
                user=user.model_dump(),
                confirmation_id=confirmation_id,
                tool_name=action["tool_name"],
                status="REJECTED",
                details=action["parameters"]
            )
            return {"status": "cancelled", "message": f"Action {action['tool_name']} cancelled."}
        return {"status": "not_found", "message": "Confirmation ID not found."}

    def _handle_remote_a2a(self, prompt: str, agent: AgentManifest, user: UserContext, routing: Dict[str, Any], gateway_context: Dict[str, Any], trace_id: str, start_time: float) -> Dict[str, Any]:
        """Simulates ADK Agent-to-Agent (A2A) protocol dispatch."""
        a2a_payload = {
            "protocol": "A2A/v1.0",
            "trace_id": trace_id,
            "origin_orchestrator": "Vertex_AI_Agent_Engine_Central",
            "sender": {"sub": user.sub, "team": user.team},
            "intent": routing["intent"],
            "prompt": prompt,
            "endpoint": agent.remote_endpoint
        }
        mock_remote_response = {
            "status": "success",
            "remote_agent": agent.name,
            "a2a_handshake": "mTLS_verified_SPIFFE",
            "security_findings": [
                {"rule": "CIS-GCP-1.2", "status": "COMPLIANT", "desc": "MFA enabled on all root accounts"},
                {"rule": "CIS-GCP-3.1", "status": "WARNING", "desc": "Port 22 open on 1 staging compute instance"},
            ]
        }
        reply = (
            f"🌐 **Dispatched over A2A Protocol** to Remote Agent: `{agent.remote_endpoint}`\n\n"
            f"**Remote Agent Response:**\n```json\n{json.dumps(mock_remote_response, indent=2)}\n```\n\n"
            f"*Authenticated with dedicated SA: `{gateway_context['service_account']}`*"
        )
        return {
            "trace_id": trace_id,
            "reply": reply,
            "routing": routing,
            "agent_info": agent.model_dump(),
            "action_taken": "REMOTE_A2A_DISPATCH",
            "gateway_context": gateway_context,
            "policy_decision": {"allowed": True, "reason": "A2A mutual authentication verified"},
            "duration_ms": round((time.time() - start_time) * 1000, 1)
        }

    def _dispatch_tool_call(self, agent_id: str, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Simulates or executes the business API call behind the API Gateway."""
        if tool_name == "get_system_health":
            return {
                "cluster": args.get("cluster", "prod-us-east"),
                "status": "HEALTHY",
                "uptime": "99.98%",
                "active_pods": 48,
                "cpu_utilization": "42%",
                "memory_utilization": "58%"
            }
        elif tool_name == "lookup_jira_issue":
            issue = args.get("issue_key", "PROJ-102")
            return {
                "key": issue,
                "summary": "Fix latency spike in payment webhook processor",
                "status": "IN PROGRESS",
                "assignee": "alex.dev@company.internal",
                "priority": "High (P2)",
                "created": "2026-10-09T14:22:00Z"
            }
        elif tool_name == "restart_cloud_service":
            svc = args.get("service_name", "payments-api")
            return {
                "service": svc,
                "action": "ROLLING_RESTART",
                "status": "RESTARTED_SUCCESSFULLY",
                "new_deployment_id": f"dep-{str(uuid.uuid4())[:6]}",
                "healthy_instances": 4
            }
        elif tool_name == "check_pto_balance":
            return {
                "employee_id": args.get("employee_id", "current_user"),
                "annual_pto_days": 20,
                "used_pto_days": 6,
                "remaining_pto_days": 14,
                "sick_leave_remaining": 8,
                "rollover_limit": 5
            }
        elif tool_name == "lookup_employee":
            q = args.get("query", "")
            return {
                "match_count": 1,
                "results": [
                    {"name": "Sarah Connor", "title": "VP of Engineering", "team": "Platform", "email": "s.connor@company.internal"}
                ]
            }
        elif tool_name == "submit_timeoff_request":
            return {
                "request_id": f"REQ-{str(uuid.uuid4())[:6].upper()}",
                "start_date": args.get("start_date", "2026-11-01"),
                "end_date": args.get("end_date", "2026-11-05"),
                "status": "SUBMITTED_FOR_MANAGER_APPROVAL"
            }
        elif tool_name == "check_expense_status":
            rep = args.get("report_id", "EXP-2026-88")
            return {
                "report_id": rep,
                "amount": "$450.00",
                "status": "APPROVED",
                "estimated_payout_date": "2026-10-16"
            }
        elif tool_name == "get_budget_overview":
            dept = args.get("department", "Engineering")
            return {
                "department": dept,
                "allocated": "$1,200,000",
                "spent": "$780,450",
                "remaining": "$419,550",
                "status": "ON_TRACK"
            }
        elif tool_name == "submit_expense_claim":
            return {
                "claim_id": f"EXP-{str(uuid.uuid4())[:6].upper()}",
                "amount": args.get("amount", 100),
                "merchant": args.get("merchant", "Sample Merchant"),
                "status": "PENDING_APPROVAL"
            }
        elif tool_name == "scan_security_posture":
            return {
                "target_env": args.get("target_env", "prod"),
                "findings": 0,
                "status": "CLEAN",
                "last_scanned": "2026-10-11T20:45:00Z"
            }
        else:
            return {
                "operation": tool_name,
                "status": "EXECUTED",
                "parameters_received": args,
                "timestamp": time.time()
            }

orchestrator = Orchestrator()
