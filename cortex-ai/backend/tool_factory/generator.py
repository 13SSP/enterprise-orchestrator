"""
cortex.ai - ADK Tool Factory
Inspects OpenAPI 3.0 specifications from microservices and generates executable ADK tool definitions.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from tool_registry.registry import tool_registry, ToolDefinition

SERVICE_PORT_MAP = {
    "hr-api": (os.environ.get("HR_API_URL", "http://127.0.0.1:8001"), "8001"),
    "payroll-api": (os.environ.get("PAYROLL_API_URL", "http://127.0.0.1:8002"), "8002"),
    "it-support-api": (os.environ.get("IT_API_URL", "http://127.0.0.1:8003"), "8003"),
    "expense-api": (os.environ.get("EXPENSE_API_URL", "http://127.0.0.1:8004"), "8004"),
    "m365-connector": (os.environ.get("M365_API_URL", "http://127.0.0.1:8005"), "8005")
}

class ToolFactory:
    def parse_openapi_spec(self, service_name: str, base_url: str, openapi_dict: Dict[str, Any]) -> List[ToolDefinition]:
        generated_tools = []
        paths = openapi_dict.get("paths", {})
        
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.lower() not in ["get", "post", "put", "patch", "delete"]:
                    continue
                
                op_id = operation.get("operationId") or operation.get("operation_id")
                if not op_id:
                    # Synthesize operation id from method + path
                    clean_path = path.strip("/").replace("/", "_").replace("{", "").replace("}", "")
                    op_id = f"{method.lower()}_{clean_path}"

                summary = operation.get("summary") or operation.get("description") or f"Execute {method.upper()} on {path}"
                is_write = method.lower() in ["post", "put", "patch", "delete"]
                requires_human = is_write and any(k in op_id for k in ["send", "adjust", "payout", "delete", "request"])

                tool = ToolDefinition(
                    name=op_id,
                    description=summary,
                    method=method.upper(),
                    path=path,
                    service=service_name,
                    base_url=base_url,
                    parameters=operation.get("parameters", {}),
                    is_write=is_write,
                    requires_human_approval=requires_human,
                    tags=operation.get("tags", [])
                )
                tool_registry.register_tool(tool)
                generated_tools.append(tool)

        return generated_tools

    def generate_agent_and_tools(
        self,
        openapi_dict: Dict[str, Any],
        agent_name: str,
        agent_id: Optional[str] = None,
        author: str = "Enterprise Developer",
        author_id: str = "bob_ops",
        owner_team: str = "Operations",
        allowed_roles: Optional[List[str]] = None,
        base_url: str = ""
    ) -> Dict[str, Any]:
        from agent_registry.registry import agent_registry, AgentManifest

        info = openapi_dict.get("info", {})
        title = info.get("title", agent_name or "Custom OpenAPI Agent")
        desc = info.get("description", f"Specialized AI agent generated from {title} OpenAPI specification.")
        clean_id = agent_id or title.lower().replace(" ", "_").replace("-", "_")

        roles = allowed_roles if allowed_roles else ["*"]

        # Parse tools
        generated_tools = []
        paths = openapi_dict.get("paths", {})
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.lower() not in ["get", "post", "put", "patch", "delete"]:
                    continue
                op_id = operation.get("operationId") or operation.get("operation_id")
                if not op_id:
                    clean_path = path.strip("/").replace("/", "_").replace("{", "").replace("}", "")
                    op_id = f"{method.lower()}_{clean_path}"
                summary = operation.get("summary") or operation.get("description") or f"Execute {method.upper()} on {path}"
                is_write = method.lower() in ["post", "put", "patch", "delete"]
                requires_human = is_write and any(k in op_id for k in ["send", "adjust", "payout", "delete", "request"])

                tool = ToolDefinition(
                    name=op_id,
                    description=summary,
                    method=method.upper(),
                    path=path,
                    service=clean_id,
                    base_url=base_url,
                    parameters=operation.get("parameters", {}),
                    is_write=is_write,
                    requires_human_approval=requires_human,
                    tags=operation.get("tags", []),
                    allowed_roles=roles,
                    enabled=True
                )
                tool_registry.register_tool(tool)
                generated_tools.append(tool)

        tool_names = [t.name for t in generated_tools]

        manifest = AgentManifest(
            id=clean_id,
            name=agent_name or title,
            owner_team=owner_team,
            author=author,
            author_id=author_id,
            icon="hexagon",
            description=desc,
            preferred_model="google/gemini-2.5-flash",
            allowed_tools=tool_names,
            knowledge_scopes=["swagger_generated"],
            active=True,
            is_public=True,
            allowed_roles=roles,
            allowed_teams=[owner_team] if owner_team else ["*"]
        )

        agent_registry.register_agent(manifest)

        return {
            "agent": manifest.model_dump(),
            "tools": [t.model_dump() for t in generated_tools],
            "tools_count": len(generated_tools)
        }

tool_factory = ToolFactory()

