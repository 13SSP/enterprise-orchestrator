export interface UserContext {
  sub: string;
  name: string;
  email: string;
  team: string;
  roles: string[];
  allowed_agent_ids: string[];
}

export interface UserPersona {
  user: UserContext;
  jwt: string;
}

export interface PolicyDecision {
  allowed: boolean;
  requires_confirmation: boolean;
  decision_code: string;
  reason: string;
  rule_name: string;
  confirmation_payload?: Record<string, any>;
}
