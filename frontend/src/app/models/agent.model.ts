export interface AgentManifest {
  id: string;
  name: string;
  description: string;
  owner_team: string;
  system_prompt: string;
  allowed_tools: string[];
  knowledge_scopes: string[];
  agent_type: 'local_adk' | 'remote_a2a';
  remote_endpoint?: string | null;
  active: boolean;
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
}
