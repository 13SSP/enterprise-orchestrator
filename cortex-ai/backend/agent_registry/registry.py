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
    author: str = "Google"
    author_id: str = "google"
    icon: str = "hexagon"
    is_public: bool = True
    allowed_roles: List[str] = Field(default_factory=lambda: ["*"])
    allowed_teams: List[str] = Field(default_factory=lambda: ["*"])

BENCHMARK_AGENTS = [
    AgentManifest(
        id="a2a_benchmark",
        name="A2A Benchmark",
        owner_team="Research & Evaluation",
        author="Google",
        author_id="google",
        icon="hexagon",
        description="Comprehensive benchmark assessing conversational accuracy and multi-agent routing performance in end-to-end applications.",
        preferred_model="google/gemini-2.5-flash",
        allowed_tools=["benchmark_evaluator", "run_synthetic_trace"],
        knowledge_scopes=["evaluation_metrics", "benchmarks"],
        active=True,
        is_public=True,
        allowed_roles=["*"],
        allowed_teams=["*"]
    ),
    AgentManifest(
        id="human_benchmark",
        name="Human Benchmark",
        owner_team="Cognitive Science",
        author="Google",
        author_id="google",
        icon="user",
        description="Simulates human baseline comparisons and reasoning benchmarks for conversational evaluation and qualitative validation.",
        preferred_model="google/gemini-2.5-flash",
        allowed_tools=["simulate_human_response", "baseline_score"],
        knowledge_scopes=["human_eval", "qualitative_rubric"],
        active=True,
        is_public=True,
        allowed_roles=["*"],
        allowed_teams=["*"]
    ),
    AgentManifest(
        id="math_agent",
        name="Math Agent",
        owner_team="Mathematical Reasoning",
        author="Google",
        author_id="google",
        icon="calculator",
        description="Autonomous agent specialized in symbolic math, calculus, linear algebra proofs, and step-by-step mathematical reasoning.",
        preferred_model="google/gemini-3.1-pro-preview",
        allowed_tools=["symbolic_math_solver", "latex_generator"],
        knowledge_scopes=["mathematics", "theorem_proving"],
        active=False,
        is_public=True,
        allowed_roles=["*"],
        allowed_teams=["*"]
    ),
    AgentManifest(
        id="swe_bench_agent",
        name="SWE-bench Agent",
        owner_team="Software Engineering Research",
        author="Google",
        author_id="google",
        icon="code",
        description="Software engineering agent specialized in resolving GitHub issues, analyzing repository codebases, and patch synthesis.",
        preferred_model="google/gemini-2.5-flash",
        allowed_tools=["code_repo_indexer", "git_patch_generator", "pytest_runner"],
        knowledge_scopes=["swe_bench", "repo_graphs"],
        active=True,
        is_public=True,
        allowed_roles=["*"],
        allowed_teams=["*"]
    ),
    AgentManifest(
        id="financial_benchmark",
        name="Financial Benchmark",
        owner_team="Corporate Finance Intelligence",
        author="Google",
        author_id="google",
        icon="trending-up",
        description="Financial reasoning and benchmark evaluation agent for market analytics, 10-K extraction, and corporate accounting workflows.",
        preferred_model="google/gemini-2.5-flash",
        allowed_tools=["get_employee_salary", "extract_sec_filings", "calculate_ebitda"],
        knowledge_scopes=["finance_statements", "tax_compliance"],
        active=True,
        is_public=True,
        allowed_roles=["Finance Officer", "DevOps Admin"],
        allowed_teams=["Finance", "Operations"]
    )
]

class AgentRegistry:
    def __init__(self):
        self._agents: Dict[str, AgentManifest] = {}
        self.discover_agents()

    def discover_agents(self):
        """Scans the agents/ root directory for agent.manifest.yaml files, then benchmark agents."""
        root_dir = Path(__file__).resolve().parent.parent.parent.parent
        agents_dir = root_dir / "agents"
        if agents_dir.exists():
            for manifest_file in agents_dir.glob("*/agent.manifest.yaml"):
                try:
                    with open(manifest_file, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                        if "author" not in data:
                            data["author"] = data.get("owner_team", "Enterprise Core")
                        if "author_id" not in data:
                            team_map = {
                                "People Operations": "alice_hr",
                                "Finance & Treasury": "charlie_fin",
                                "IT Support & Services": "bob_ops",
                                "DevOps & Cloud Infrastructure": "bob_ops",
                                "Productivity & Office 365": "bob_ops"
                            }
                            data["author_id"] = team_map.get(data.get("owner_team", ""), "bob_ops")
                        manifest = AgentManifest(**data)
                        self._agents[manifest.id] = manifest
                except Exception as e:
                    print(f"[AgentRegistry] Error loading manifest {manifest_file}: {e}")

        # Benchmark agents from reference
        for b_agent in BENCHMARK_AGENTS:
            if b_agent.id not in self._agents:
                self._agents[b_agent.id] = b_agent

    def list_agents(self, active_only: bool = False) -> List[AgentManifest]:
        if active_only:
            return [a for a in self._agents.values() if a.active]
        return list(self._agents.values())

    def search_agents(
        self,
        query: Optional[str] = None,
        scope: Optional[str] = None,
        persona_id: Optional[str] = None,
        persona_team: Optional[str] = None
    ) -> List[AgentManifest]:
        agents = list(self._agents.values())

        if scope == "mine" and persona_id:
            agents = [
                a for a in agents
                if a.author_id == persona_id or (persona_team and (persona_team.lower() in a.owner_team.lower() or a.owner_team.lower() in persona_team.lower()))
            ]

        if query:
            q = query.lower().strip()
            agents = [
                a for a in agents
                if q in a.name.lower()
                or q in a.description.lower()
                or q in a.owner_team.lower()
                or q in a.author.lower()
                or any(q in t.lower() for t in a.allowed_tools)
            ]

        return agents

    def get_agent(self, agent_id: str) -> Optional[AgentManifest]:
        return self._agents.get(agent_id)

    def register_agent(self, manifest: AgentManifest) -> AgentManifest:
        self._agents[manifest.id] = manifest
        return manifest

    def update_access(
        self,
        agent_id: str,
        allowed_roles: Optional[List[str]] = None,
        allowed_teams: Optional[List[str]] = None,
        active: Optional[bool] = None
    ) -> Optional[AgentManifest]:
        agent = self.get_agent(agent_id)
        if not agent:
            return None
        if allowed_roles is not None:
            agent.allowed_roles = allowed_roles
        if allowed_teams is not None:
            agent.allowed_teams = allowed_teams
        if active is not None:
            agent.active = active
        return agent

    def delete_agent(self, agent_id: str) -> bool:
        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False

agent_registry = AgentRegistry()
