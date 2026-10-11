"""
cortex.ai - Finance Agent
Handles corporate expenses, receipts, and authorized salary records.
"""

from typing import Dict, Any, List

class FinanceAgent:
    def __init__(self, manifest: Dict[str, Any]):
        self.manifest = manifest
        self.id = manifest["id"]
        self.name = manifest["name"]

    def process_query(self, query: str, context: Dict[str, Any], tools_available: List[str]) -> Dict[str, Any]:
        q_lower = query.lower()
        if "salary" in q_lower or "compensation" in q_lower or "pay" in q_lower:
            target_emp = context.get("user", {}).get("sub", "bob_ops")
            return {
                "agent_id": self.id,
                "action": "INVOKE_TOOL",
                "suggested_tool": "get_employee_salary",
                "args": {"employee_id": target_emp},
                "response_text": f"Retrieving confidential salary tier for employee {target_emp}."
            }
        elif "expense" in q_lower or "claim" in q_lower:
            return {
                "agent_id": self.id,
                "action": "INVOKE_TOOL",
                "suggested_tool": "list_claims",
                "args": {},
                "response_text": "Retrieving corporate expense claim history."
            }
        return {
            "agent_id": self.id,
            "action": "CONVERSATIONAL",
            "response_text": f"Hello! I am the {self.name}. How can I assist you with corporate claims or finances?"
        }

def create_agent(manifest: Dict[str, Any]) -> FinanceAgent:
    return FinanceAgent(manifest)
