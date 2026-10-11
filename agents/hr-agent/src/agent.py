"""
cortex.ai - HR Agent
Google ADK Agent implementation for People Operations and Leave Management.
"""

from typing import Dict, Any, List

class HRAgent:
    def __init__(self, manifest: Dict[str, Any]):
        self.manifest = manifest
        self.id = manifest["id"]
        self.name = manifest["name"]

    def process_query(self, query: str, context: Dict[str, Any], tools_available: List[str]) -> Dict[str, Any]:
        q_lower = query.lower()
        if "leave" in q_lower or "pto" in q_lower or "balance" in q_lower:
            return {
                "agent_id": self.id,
                "action": "INVOKE_TOOL",
                "suggested_tool": "get_leave_balance",
                "args": {"employee_id": context.get("user", {}).get("sub", "bob_ops")},
                "response_text": "I am checking your remaining PTO and leave balance."
            }
        elif "employee" in q_lower or "team" in q_lower or "directory" in q_lower:
            return {
                "agent_id": self.id,
                "action": "INVOKE_TOOL",
                "suggested_tool": "list_employees",
                "args": {},
                "response_text": "Retrieving employee directory details."
            }
        return {
            "agent_id": self.id,
            "action": "CONVERSATIONAL",
            "response_text": f"Hello! I am the {self.name}. How can I assist you with HR policies, leave balances, or personnel records?"
        }

def create_agent(manifest: Dict[str, Any]) -> HRAgent:
    return HRAgent(manifest)
