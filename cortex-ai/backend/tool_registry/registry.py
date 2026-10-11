"""
cortex.ai - Tool Registry
Maintains catalog of all tools generated from OpenAPI specifications across domain apps.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

class ToolDefinition(BaseModel):
    name: str
    description: str
    method: str
    path: str
    service: str
    base_url: str
    parameters: Any = Field(default_factory=list)
    is_write: bool = False
    requires_human_approval: bool = False
    tags: List[str] = Field(default_factory=list)

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def register_tool(self, tool: ToolDefinition):
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def list_tools(self) -> List[ToolDefinition]:
        return list(self._tools.values())

tool_registry = ToolRegistry()
