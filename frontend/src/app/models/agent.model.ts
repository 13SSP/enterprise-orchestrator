export interface AgentManifest {
  id: string;
  name: string;
  description: string;
  owner_team: string;
  author?: string;
  author_id?: string;
  icon?: string;
  system_prompt: string;
  allowed_tools: string[];
  knowledge_scopes: string[];
  agent_type: 'local_adk' | 'remote_a2a';
  remote_endpoint?: string | null;
  active: boolean;
  is_public?: boolean;
  allowed_roles?: string[];
  allowed_teams?: string[];
  created_at?: string;
}

export interface ToolDefinition {
  name: string;
  description: string;
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  path: string;
  parameters: Record<string, any>;
  is_write: boolean;
  require_confirmation: boolean;
  target_url?: string;
  tags: string[];
  owner_agent?: string;
  enabled?: boolean;
  allowed_roles?: string[];
}

export interface GenerateAgentSwaggerRequest {
  spec_content?: string;
  spec_url?: string;
  agent_id?: string;
  agent_name?: string;
  agent_description?: string;
  system_prompt?: string;
  owner_team?: string;
  author?: string;
  author_id?: string;
  icon?: string;
  is_public?: boolean;
  allowed_roles?: string[];
  allowed_teams?: string[];
  tool_overrides?: Record<string, { enabled?: boolean; require_confirmation?: boolean; allowed_roles?: string[] }>;
  auto_register?: boolean;
}
