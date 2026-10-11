"""
cortex.ai - ADK Tool Factory
Inspects OpenAPI 3.0 specifications from microservices and generates executable ADK tool definitions.
"""

import sys
from pathlib import Path
from typing import Dict, Any, List

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from tool_registry.registry import tool_registry, ToolDefinition

SERVICE_PORT_MAP = {
    "hr-api": ("http://127.0.0.1:8001", "8001"),
    "payroll-api": ("http://127.0.0.1:8002", "8002"),
    "it-support-api": ("http://127.0.0.1:8003", "8003"),
    "expense-api": ("http://127.0.0.1:8004", "8004"),
    "m365-connector": ("http://127.0.0.1:8005", "8005")
}

class ToolFactory:
    def parse_openapi_spec(self, service_name: str, base_url: str, openapi_dict: Dict[str, Any]) -> List[ToolDefinition]:
        generated_tools = []
        paths = openapi_dict.get("paths", {})
        
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.lower() not in ["get", "post", "put", "patch", "delete"]:
                    continue
                
                op_id = operation.get("operation_id")
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

tool_factory = ToolFactory()
