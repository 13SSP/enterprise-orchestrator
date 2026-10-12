import re
import json
import yaml
import requests
from typing import Dict, List, Any, Tuple, Optional
from app.core.registry import ToolDefinition, AgentManifest, registry

class OpenAPIImporter:
    """
    Parses OpenAPI 3.0.x and Swagger 2.0 specs into executable ADK Tool definitions
    and instantiates new intelligent Agents with access controls.
    - Classifies operations as READ or WRITE.
    - Enforces write confirmation policies.
    - Synthesizes Agent personas and prompts from OpenAPI metadata.
    - Limits access to agents and tools via RBAC and team scoping.
    """

    @staticmethod
    def parse_spec_content(raw_content: str) -> Dict[str, Any]:
        """Accepts either JSON or YAML string."""
        raw_content = raw_content.strip()
        if raw_content.startswith("{") or raw_content.startswith("["):
            return json.loads(raw_content)
        return yaml.safe_load(raw_content)

    @staticmethod
    def fetch_from_url(url: str, timeout: int = 10) -> Dict[str, Any]:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return OpenAPIImporter.parse_spec_content(resp.text)

    @staticmethod
    def _sanitize_tool_name(operation_id: Optional[str], method: str, path: str) -> str:
        if operation_id:
            # Clean operation_id to valid python identifier
            clean = re.sub(r"[^a-zA-Z0-9_]", "_", operation_id).lower()
            if clean and not clean[0].isdigit():
                return clean
        # Fallback: create from method and path
        path_clean = re.sub(r"[{}]", "", path)
        path_clean = re.sub(r"[^a-zA-Z0-9_]+", "_", path_clean).strip("_")
        return f"{method.lower()}_{path_clean}"

    @classmethod
    def import_spec(
        cls,
        spec_data: Dict[str, Any],
        target_agent_id: Optional[str] = None,
        default_base_url: Optional[str] = None,
        auto_register: bool = True
    ) -> Tuple[List[ToolDefinition], Dict[str, Any]]:
        """
        Parses spec, builds tools, and optionally saves them to Registry.
        """
        # Determine base URL
        base_url = default_base_url or "https://api.internal.corp"
        if "servers" in spec_data and spec_data["servers"]:
            base_url = spec_data["servers"][0].get("url", base_url)
        elif "host" in spec_data:
            scheme = spec_data.get("schemes", ["https"])[0]
            base_path = spec_data.get("basePath", "")
            base_url = f"{scheme}://{spec_data['host']}{base_path}"

        title = spec_data.get("info", {}).get("title", "Imported API")
        version = spec_data.get("info", {}).get("version", "1.0.0")

        paths = spec_data.get("paths", {})
        generated_tools: List[ToolDefinition] = []

        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue

            for method in ["get", "post", "put", "delete", "patch"]:
                if method not in path_item:
                    continue

                op = path_item[method]
                if not isinstance(op, dict):
                    continue

                operation_id = op.get("operationId")
                tool_name = cls._sanitize_tool_name(operation_id, method, path)

                # Classify read vs write
                is_write = method.upper() in ["POST", "PUT", "DELETE", "PATCH"]
                require_confirmation = is_write

                # Enhanced description for Gemini routing
                raw_summary = op.get("summary", "")
                raw_desc = op.get("description", "")
                description = raw_summary or raw_desc or f"Execute {method.upper()} on {path}"
                
                # Suffix explicit routing indicator
                op_type = "Write/Mutation operation (requires confirmation)" if is_write else "Read-only query"
                enhanced_desc = f"[{op_type}] {description}. Path: {path}"

                # Extract parameters
                properties = {}
                required = []

                # Query & Path parameters
                for param in op.get("parameters", []):
                    if isinstance(param, dict):
                        p_name = param.get("name")
                        p_desc = param.get("description", "")
                        p_schema = param.get("schema", {})
                        p_type = p_schema.get("type", param.get("type", "string"))
                        properties[p_name] = {
                            "type": p_type,
                            "description": f"{p_desc} (in {param.get('in', 'query')})"
                        }
                        if param.get("required", False):
                            required.append(p_name)

                # Request Body schema (OpenAPI 3)
                if "requestBody" in op:
                    content = op["requestBody"].get("content", {})
                    json_body = content.get("application/json", {}).get("schema", {})
                    if "properties" in json_body:
                        for b_name, b_spec in json_body["properties"].items():
                            properties[b_name] = {
                                "type": b_spec.get("type", "string"),
                                "description": b_spec.get("description", f"Body param: {b_name}")
                            }
                        if "required" in json_body and isinstance(json_body["required"], list):
                            required.extend(json_body["required"])

                param_schema = {
                    "type": "object",
                    "properties": properties,
                    "required": list(set(required))
                }

                tags = op.get("tags", [])
                tags.append("openapi_imported")
                if is_write:
                    tags.append("write")
                else:
                    tags.append("read")

                tool_def = ToolDefinition(
                    name=tool_name,
                    description=enhanced_desc,
                    method=method.upper(),
                    path=path,
                    parameters=param_schema,
                    is_write=is_write,
                    require_confirmation=require_confirmation,
                    target_url=base_url,
                    tags=tags,
                    owner_agent=target_agent_id
                )

                if auto_register:
                    registry.register_tool(tool_def)
                    # If target agent specified, add to its allowed tools
                    if target_agent_id:
                        agent = registry.get_agent(target_agent_id)
                        if agent and tool_name not in agent.allowed_tools:
                            agent.allowed_tools.append(tool_name)
                            registry.register_agent(agent)

                generated_tools.append(tool_def)

        metadata = {
            "title": title,
            "version": version,
            "base_url": base_url,
            "tools_count": len(generated_tools),
            "target_agent": target_agent_id
        }

        return generated_tools, metadata

    @classmethod
    def generate_agent_and_tools(
        cls,
        spec_data: Dict[str, Any],
        author: Optional[str] = None,
        author_id: Optional[str] = None,
        owner_team: Optional[str] = None,
        agent_id_override: Optional[str] = None,
        agent_name_override: Optional[str] = None,
        agent_description_override: Optional[str] = None,
        system_prompt_override: Optional[str] = None,
        icon: Optional[str] = "wrench",
        is_public: bool = True,
        allowed_roles: Optional[List[str]] = None,
        allowed_teams: Optional[List[str]] = None,
        tool_overrides: Optional[Dict[str, Dict[str, Any]]] = None,
        auto_register: bool = True
    ) -> Tuple[AgentManifest, List[ToolDefinition], Dict[str, Any]]:
        """
        Synthesizes both an Agent Manifest and all corresponding Tool Definitions
        directly from an OpenAPI / Swagger spec, applying fine-grained access control.
        """
        title = spec_data.get("info", {}).get("title", "Enterprise Service API")
        raw_desc = spec_data.get("info", {}).get("description", "")

        # 1. Synthesize Agent Identifier
        if agent_id_override:
            agent_id = re.sub(r"[^a-zA-Z0-9_]", "_", agent_id_override).lower().strip("_")
        else:
            slug = re.sub(r"[^a-zA-Z0-9_]+", "_", title).lower().strip("_")
            agent_id = f"{slug}_agent" if not slug.endswith("_agent") else slug

        # 2. Synthesize Display Name & Prompts
        agent_name = agent_name_override or f"{title} Agent"
        description = agent_description_override or (
            f"{raw_desc.strip()} Agent specialized in {title} capabilities. Routes and fulfills operations using registered API tools."
            if raw_desc else f"Intelligent ADK Agent for {title}. Automatically routes API queries and mutations."
        )
        system_prompt = system_prompt_override or (
            f"You are the {agent_name}. You have authorized access to tools for {title}. "
            "Assist users accurately, invoke appropriate tools, and describe side-effects for write/mutation operations."
        )

        # 3. Generate Tools from Spec
        tools, meta = cls.import_spec(
            spec_data=spec_data,
            target_agent_id=agent_id,
            auto_register=False
        )

        # 4. Apply Tool Access Overrides & Register Tools
        tool_overrides = tool_overrides or {}
        for t in tools:
            if t.name in tool_overrides:
                ov = tool_overrides[t.name]
                if "enabled" in ov:
                    t.enabled = bool(ov["enabled"])
                if "require_confirmation" in ov:
                    t.require_confirmation = bool(ov["require_confirmation"])
                if "allowed_roles" in ov:
                    t.allowed_roles = ov["allowed_roles"]
            if auto_register:
                registry.register_tool(t)

        enabled_tools = [t.name for t in tools if t.enabled]

        # 5. Build and Register Agent Manifest
        manifest = AgentManifest(
            id=agent_id,
            name=agent_name,
            description=description,
            owner_team=owner_team or "Engineering",
            author=author or "Enterprise User",
            author_id=author_id or "user",
            icon=icon or "wrench",
            system_prompt=system_prompt,
            allowed_tools=enabled_tools,
            knowledge_scopes=[],
            agent_type="local_adk",
            active=True,
            is_public=is_public,
            allowed_roles=allowed_roles if allowed_roles is not None else ["*"],
            allowed_teams=allowed_teams if allowed_teams is not None else ["*"],
        )

        if auto_register:
            registry.register_agent(manifest)

        meta["agent_id"] = agent_id
        meta["agent_name"] = agent_name
        return manifest, tools, meta


# Sample OpenAPI Spec for immediate Hackathon testing
SAMPLE_DEV_OPS_SWAGGER = """
openapi: 3.0.0
info:
  title: DevOps & Incident Management API
  version: 2.1.0
  description: Internal engineering API for managing deployments and incident hotfixes.
servers:
  - url: https://devops.internal.corp/api/v1
paths:
  /deployments/status:
    get:
      summary: Retrieve current status of microservice deployments
      description: Returns pod status, replica count, and deployment drift.
      operationId: get_deployment_status
      parameters:
        - name: service_name
          in: query
          required: true
          schema:
            type: string
          description: Microservice name e.g. auth-service, payment-api
  /deployments/rollback:
    post:
      summary: Rollback a microservice to previous stable release
      description: Performs zero-downtime rollback of active Kubernetes deployment.
      operationId: rollback_service_deployment
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - service_name
                - target_version
              properties:
                service_name:
                  type: string
                target_version:
                  type: string
                reason:
                  type: string
  /incidents/create:
    post:
      summary: Declare a P1 or P2 incident in PagerDuty & Slack
      description: Escalates critical downtime to on-call engineers.
      operationId: trigger_incident_pager
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - title
                - severity
              properties:
                title:
                  type: string
                severity:
                  type: string
                impact_summary:
                  type: string
"""
