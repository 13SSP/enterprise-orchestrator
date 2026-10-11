export interface RoutingResult {
  selected_agent_id: string | null;
  confidence: number;
  intent: 'tool_call' | 'knowledge_retrieval' | 'conversational' | 'out_of_scope';
  reasoning: string;
  candidate_agents: string[];
  suggested_tool?: string | null;
  suggested_args?: Record<string, any>;
}

export interface PendingConfirmation {
  confirmation_id: string;
  tool_name: string;
  parameters: Record<string, any>;
  description: string;
}

export interface ChatResponse {
  trace_id: string;
  reply: string;
  routing: RoutingResult;
  agent_info?: any;
  action_taken: 'TOOL_EXECUTED' | 'CONFIRMATION_REQUIRED' | 'RAG_RETRIEVAL' | 'CONVERSATIONAL' | 'POLICY_DENIED' | 'POLICY_BLOCKED' | 'REMOTE_A2A_DISPATCH' | 'WRITE_APPROVED_EXECUTED' | 'NONE';
  tool_executed?: {
    tool_name: string;
    parameters: any;
    result: any;
    duration_ms: number;
  };
  pending_confirmation?: PendingConfirmation;
  rag_sources?: Array<{
    doc_id?: string;
    title: string;
    scope: string;
    content: string;
    score: number;
  }>;
  gateway_context?: {
    service_account: string;
    iam_roles: string[];
    secret_ref?: string;
  };
  policy_decision?: {
    allowed: boolean;
    decision_code: string;
    reason: string;
    rule_name: string;
  };
  duration_ms: number;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'orchestrator';
  text: string;
  timestamp: Date;
  response?: ChatResponse;
}
