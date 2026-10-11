"""
cortex.ai - Agent Registry
Auto-discovers manifests from agents/*/agent.manifest.yaml and handles runtime agent onboarding.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml
from pydantic import BaseModel, Field

class AgentManifest(BaseModel):
    id: str
    name: str
    owner_team: str
    description: str
    preferred_model: str = "google/gemini-2.5-flash"
    fallback_models: List[str] = Field(default_factory=list)
    allowed_tools: List[str] = Field(default_factory=list)
    knowledge_scopes: List[str] = Field(default_factory=list)
    active: bool = True

class AgentRegistry:
    def __init__(self):
        self._agents: Dict[str, AgentManifest] = {}
        self.discover_agents()

    def discover_agents(self):
        """Scans the agents/ root directory for agent.manifest.yaml files."""
        # Project root
        root_dir = Path(__file__).resolve().parent.parent.parent.parent
        agents_dir = root_dir / "agents"
        if not agents_dir.exists():
            return

        for manifest_file in agents_dir.glob("*/agent.manifest.yaml"):
            try:
                with open(manifest_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    manifest = AgentManifest(**data)
                    self._agents[manifest.id] = manifest
            except Exception as e:
                print(f"[AgentRegistry] Error loading manifest {manifest_file}: {e}")

    def list_agents(self, active_only: bool = True) -> List[AgentManifest]:
        if active_only:
            return [a for a in self._agents.values() if a.active]
        return list(self._agents.values())

    def get_agent(self, agent_id: str) -> Optional[AgentManifest]:
        return self._agents.get(agent_id)

    def register_agent(self, manifest: AgentManifest) -> AgentManifest:
        self._agents[manifest.id] = manifest
        return manifest

agent_registry = AgentRegistry()
