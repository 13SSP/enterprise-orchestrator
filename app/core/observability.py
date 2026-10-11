import time
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from collections import deque

class AuditLogEntry:
    def __init__(
        self,
        event_type: str,
        severity: str,
        message: str,
        details: Dict[str, Any],
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
        user: Optional[Dict[str, Any]] = None,
    ):
        self.log_id = str(uuid.uuid4())
        self.trace_id = trace_id or str(uuid.uuid4())
        self.span_id = span_id or uuid.uuid4().hex[:16]
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.event_type = event_type
        self.severity = severity
        self.message = message
        self.details = details or {}
        self.user = user or {"sub": "system", "roles": ["anonymous"]}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "log_id": self.log_id,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "timestamp": self.timestamp,
            "severity": self.severity,
            "event_type": self.event_type,
            "message": self.message,
            "details": self.details,
            "user": self.user,
            # Cloud Logging compatible format
            "logging.googleapis.com/trace": f"projects/hackathon-orchestrator/traces/{self.trace_id}",
            "logging.googleapis.com/spanId": self.span_id,
        }

class ObservabilityManager:
    """
    Central audit & telemetry logger.
    Captures routing decisions, policy evaluations, tool executions, and security denials
    in Google Cloud Logging & Trace compatible format.
    """
    def __init__(self, max_buffer_size: int = 500):
        self._buffer: deque = deque(maxlen=max_buffer_size)

    def log_event(
        self,
        event_type: str,
        severity: str,
        message: str,
        details: Dict[str, Any],
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
        user: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        entry = AuditLogEntry(
            event_type=event_type,
            severity=severity,
            message=message,
            details=details,
            trace_id=trace_id,
            span_id=span_id,
            user=user,
        )
        data = entry.to_dict()
        self._buffer.appendleft(data)
        return data

    def log_routing(
        self,
        trace_id: str,
        user: Dict[str, Any],
        prompt: str,
        selected_agent: Optional[str],
        confidence: float,
        reasoning: str,
        intent: str,
        candidate_agents: List[str]
    ) -> Dict[str, Any]:
        return self.log_event(
            event_type="ROUTING_DECISION",
            severity="INFO",
            message=f"Router selected agent '{selected_agent}' (confidence: {confidence * 100:.1f}%)",
            details={
                "prompt": prompt,
                "selected_agent": selected_agent,
                "confidence": confidence,
                "intent": intent,
                "reasoning": reasoning,
                "candidate_agents": candidate_agents,
            },
            trace_id=trace_id,
            user=user,
        )

    def log_policy_evaluation(
        self,
        trace_id: str,
        user: Dict[str, Any],
        agent_id: str,
        tool_name: Optional[str],
        decision: str,  # "ALLOWED", "DENIED", "REQUIRES_CONFIRMATION"
        reason: str,
        rule_name: str,
    ) -> Dict[str, Any]:
        severity = "WARNING" if decision == "DENIED" else "INFO"
        return self.log_event(
            event_type="POLICY_DENIAL" if decision == "DENIED" else "POLICY_EVALUATION",
            severity=severity,
            message=f"Policy {decision} for user '{user.get('sub')}' on {agent_id}:{tool_name or '*'}",
            details={
                "agent_id": agent_id,
                "tool_name": tool_name,
                "decision": decision,
                "reason": reason,
                "rule_name": rule_name,
                "user_roles": user.get("roles", []),
                "user_team": user.get("team", ""),
            },
            trace_id=trace_id,
            user=user,
        )

    def log_tool_execution(
        self,
        trace_id: str,
        user: Dict[str, Any],
        agent_id: str,
        tool_name: str,
        parameters: Dict[str, Any],
        result: Any,
        duration_ms: float,
        is_write: bool,
    ) -> Dict[str, Any]:
        return self.log_event(
            event_type="TOOL_EXECUTION",
            severity="INFO",
            message=f"Executed tool '{tool_name}' ({'WRITE' if is_write else 'READ'}) in {duration_ms:.1f}ms",
            details={
                "agent_id": agent_id,
                "tool_name": tool_name,
                "parameters": parameters,
                "result": result,
                "duration_ms": duration_ms,
                "is_write": is_write,
            },
            trace_id=trace_id,
            user=user,
        )

    def log_write_confirmation(
        self,
        trace_id: str,
        user: Dict[str, Any],
        confirmation_id: str,
        tool_name: str,
        status: str,  # "PENDING", "APPROVED", "REJECTED"
        details: Dict[str, Any],
    ) -> Dict[str, Any]:
        return self.log_event(
            event_type="WRITE_CONFIRMATION",
            severity="NOTICE",
            message=f"Write confirmation {status} for tool '{tool_name}'",
            details={
                "confirmation_id": confirmation_id,
                "tool_name": tool_name,
                "status": status,
                "action_details": details,
            },
            trace_id=trace_id,
            user=user,
        )

    def log_rag_retrieval(
        self,
        trace_id: str,
        user: Dict[str, Any],
        query: str,
        scopes: List[str],
        matches_found: int,
        sources: List[str],
    ) -> Dict[str, Any]:
        return self.log_event(
            event_type="RAG_RETRIEVAL",
            severity="INFO",
            message=f"RAG retrieval found {matches_found} docs across scopes: {', '.join(scopes)}",
            details={
                "query": query,
                "scopes": scopes,
                "matches_found": matches_found,
                "sources": sources,
            },
            trace_id=trace_id,
            user=user,
        )

    def get_logs(self, limit: int = 50, event_type: Optional[str] = None, trace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        results = list(self._buffer)
        if event_type:
            results = [r for r in results if r["event_type"] == event_type]
        if trace_id:
            results = [r for r in results if r["trace_id"] == trace_id]
        return results[:limit]

    def clear(self):
        self._buffer.clear()

observability = ObservabilityManager()
