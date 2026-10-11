"""
cortex.ai - Ops Agent
Cloud infrastructure operations, cluster health, and service deployments.
"""

from typing import Dict, Any, List

class OpsAgent:
    def __init__(self, manifest: Dict[str, Any]):
        self.manifest = manifest
        self.id = manifest["id"]
        self.name = manifest["name"]

    def process_query(self, query: str, context: Dict[str, Any], tools_available: List[str]) -> Dict[str, Any]:
        q_lower = query.lower()
        if "restart" in q_lower or "deploy" in q_lower:
            return {
                "agent_id": self.id,
                "action": "INVOKE_TOOL",
                "suggested_tool": "restart_cloud_service",
                "args": {"service_name": "payments-api"},
                "response_text": "Initiating graceful restart procedure for cloud service."
            }
        elif "health" in q_lower or "cluster" in q_lower or "status" in q_lower or "uptime" in q_lower:
            return {
                "agent_id": self.id,
                "action": "INVOKE_TOOL",
                "suggested_tool": "get_system_health",
                "args": {"cluster": "prod-us-east"},
                "response_text": "Checking real-time cluster health and infrastructure metrics."
            }
        return {
            "agent_id": self.id,
            "action": "CONVERSATIONAL",
            "response_text": f"Hello! I am the {self.name}. How can I assist you with cloud reliability and infrastructure?"
        }

def create_agent(manifest: Dict[str, Any]) -> OpsAgent:
    return OpsAgent(manifest)
