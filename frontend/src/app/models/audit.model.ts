export interface AuditLogEntry {
  log_id: string;
  trace_id: string;
  span_id: string;
  timestamp: string;
  severity: 'INFO' | 'NOTICE' | 'WARNING' | 'ERROR';
  event_type: 'ROUTING_DECISION' | 'POLICY_EVALUATION' | 'POLICY_DENIAL' | 'TOOL_EXECUTION' | 'WRITE_CONFIRMATION' | 'RAG_RETRIEVAL' | 'AGENT_ONBOARDED' | 'TOOL_REGISTERED';
  message: string;
  details: Record<string, any>;
  user: Record<string, any>;
  'logging.googleapis.com/trace'?: string;
  'logging.googleapis.com/spanId'?: string;
}
