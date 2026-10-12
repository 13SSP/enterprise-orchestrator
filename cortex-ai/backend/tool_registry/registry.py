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
    allowed_roles: List[str] = Field(default_factory=lambda: ["*"])
    enabled: bool = True

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def register_tool(self, tool: ToolDefinition):
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def list_tools(self) -> List[ToolDefinition]:
        return list(self._tools.values())

    def update_access(self, tool_name: str, allowed_roles: Optional[List[str]] = None, enabled: Optional[bool] = None, requires_human_approval: Optional[bool] = None) -> Optional[ToolDefinition]:
        tool = self.get_tool(tool_name)
        if not tool:
            return None
        if allowed_roles is not None:
            tool.allowed_roles = allowed_roles
        if enabled is not None:
            tool.enabled = enabled
        if requires_human_approval is not None:
            tool.requires_human_approval = requires_human_approval
        return tool

tool_registry = ToolRegistry()

