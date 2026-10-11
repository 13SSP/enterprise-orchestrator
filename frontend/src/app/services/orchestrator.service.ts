import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { ChatResponse } from '../models/chat.model';
import { AgentManifest, ToolDefinition } from '../models/agent.model';
import { AuthService } from './auth.service';

@Injectable({
  providedIn: 'root'
})
export class OrchestratorService {
  private apiUrl = '/api';

  agents = signal<AgentManifest[]>([]);
  tools = signal<ToolDefinition[]>([]);

  constructor(private http: HttpClient, private auth: AuthService) {
    this.refreshAgents();
    this.refreshTools();
  }

  // 1. Natural language Chat with Orchestrator & Gemini Router
  sendChat(prompt: string): Observable<ChatResponse> {
    const payload = {
      prompt,
      persona: this.auth.currentPersonaKey(),
      token: this.auth.getJwtToken()
    };
    return this.http.post<ChatResponse>(`${this.apiUrl}/chat`, payload);
  }

  // 2. Action Confirmation Resolution (Human-in-the-loop write operations)
  confirmAction(confirmationId: string, action: 'approve' | 'reject'): Observable<ChatResponse> {
    const payload = {
      confirmation_id: confirmationId,
      action,
      persona: this.auth.currentPersonaKey()
    };
    return this.http.post<ChatResponse>(`${this.apiUrl}/chat/confirm`, payload);
  }

  // 3. Agent Onboarding & Management
  refreshAgents(): void {
    this.http.get<{ agents: AgentManifest[] }>(`${this.apiUrl}/agents`).subscribe({
      next: (res) => this.agents.set(res.agents || []),
      error: (err) => console.error('Failed to load agents:', err)
    });
  }

  onboardAgent(manifest: AgentManifest): Observable<{ status: string; agent: AgentManifest; trace_id: string }> {
    return this.http.post<any>(`${this.apiUrl}/agents/onboard`, manifest).pipe(
      tap(() => this.refreshAgents())
    );
  }

  toggleAgent(agentId: string): Observable<{ status: string; active: boolean }> {
    return this.http.post<any>(`${this.apiUrl}/agents/${agentId}/toggle`, {}).pipe(
      tap(() => this.refreshAgents())
    );
  }

  deleteAgent(agentId: string): Observable<{ status: string }> {
    return this.http.delete<any>(`${this.apiUrl}/agents/${agentId}`).pipe(
      tap(() => this.refreshAgents())
    );
  }

  // 4. Swagger / OpenAPI Tool Builder
  refreshTools(): void {
    this.http.get<{ tools: ToolDefinition[] }>(`${this.apiUrl}/tools`).subscribe({
      next: (res) => this.tools.set(res.tools || []),
      error: (err) => console.error('Failed to load tools:', err)
    });
  }

  importSwagger(specContent: string, targetAgentId?: string | null): Observable<any> {
    const payload = {
      spec_content: specContent,
      target_agent_id: targetAgentId || null
    };
    return this.http.post<any>(`${this.apiUrl}/tools/import-swagger`, payload).pipe(
      tap(() => {
        this.refreshTools();
        this.refreshAgents();
      })
    );
  }

  getSampleSpecs(): Observable<{ devops_sample: string; finance_sample: string }> {
    return this.http.get<{ devops_sample: string; finance_sample: string }>(`${this.apiUrl}/sample-specs`);
  }
}
