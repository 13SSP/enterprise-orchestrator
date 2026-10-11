"""
cortex.ai - IT Support Agent
Assists with Jira tickets and system incident triage.
"""

from typing import Dict, Any, List
import re

class ITSupportAgent:
    def __init__(self, manifest: Dict[str, Any]):
        self.manifest = manifest
        self.id = manifest["id"]
        self.name = manifest["name"]

    def process_query(self, query: str, context: Dict[str, Any], tools_available: List[str]) -> Dict[str, Any]:
        q_lower = query.lower()
        match = re.search(r"([A-Z]+-\d+)", query, re.IGNORECASE)
        if match:
            ticket_key = match.group(1).upper()
            return {
                "agent_id": self.id,
                "action": "INVOKE_TOOL",
                "suggested_tool": "get_ticket",
                "args": {"ticket_key": ticket_key},
                "response_text": f"Looking up Jira ticket {ticket_key}."
            }
        elif "ticket" in q_lower or "jira" in q_lower or "bug" in q_lower:
            return {
                "agent_id": self.id,
                "action": "INVOKE_TOOL",
                "suggested_tool": "list_tickets",
                "args": {},
                "response_text": "Listing current Jira tickets and engineering incidents."
            }
        return {
            "agent_id": self.id,
            "action": "CONVERSATIONAL",
            "response_text": f"Hello! I am the {self.name}. How can I help you with IT incidents or Jira tickets?"
        }

def create_agent(manifest: Dict[str, Any]) -> ITSupportAgent:
    return ITSupportAgent(manifest)
