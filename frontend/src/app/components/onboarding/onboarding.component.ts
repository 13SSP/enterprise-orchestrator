import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { OrchestratorService } from '../../services/orchestrator.service';
import { AgentManifest } from '../../models/agent.model';

@Component({
  selector: 'app-onboarding',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 max-w-7xl mx-auto w-full">
      <!-- Manifest Submission Form -->
      <div class="lg:col-span-7 bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-4">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-lg font-bold text-white flex items-center gap-2">
              <span class="text-indigo-400">➕</span>
              Onboard Team Agent
            </h2>
            <p class="text-xs text-slate-400">
              Registers manifest in Firestore. Dynamically loaded by Orchestrator as ADK sub-agents.
            </p>
          </div>
          <button 
            type="button"
            (click)="autoFillMarketingAgent()"
            class="text-xs bg-slate-800 hover:bg-slate-700 text-indigo-300 border border-indigo-900/60 px-3 py-1.5 rounded-lg cursor-pointer transition"
          >
            Auto-fill Marketing Agent
          </button>
        </div>

        <form (submit)="submitManifest()" class="space-y-4 text-xs">
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block font-semibold text-slate-300 mb-1">Agent ID</label>
              <input 
                [(ngModel)]="form.id" 
                name="id" 
                type="text" 
                required 
                placeholder="e.g. marketing_agent" 
                class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label class="block font-semibold text-slate-300 mb-1">Display Name</label>
              <input 
                [(ngModel)]="form.name" 
                name="name" 
                type="text" 
                required 
                placeholder="e.g. Growth & Marketing Agent" 
                class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block font-semibold text-slate-300 mb-1">Owner Team</label>
              <input 
                [(ngModel)]="form.owner_team" 
                name="owner_team" 
                type="text" 
                required 
                placeholder="e.g. Marketing" 
                class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label class="block font-semibold text-slate-300 mb-1">Agent Type</label>
              <select 
                [(ngModel)]="form.agent_type" 
                name="agent_type" 
                class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
              >
                <option value="local_adk">Local ADK Sub-Agent</option>
                <option value="remote_a2a">Remote Agent (A2A Protocol)</option>
              </select>
            </div>
          </div>

          <!-- Remote Endpoint Row (if remote_a2a) -->
          <div *ngIf="form.agent_type === 'remote_a2a'">
            <label class="block font-semibold text-slate-300 mb-1">Remote A2A Protocol Endpoint</label>
            <input 
              [(ngModel)]="form.remote_endpoint" 
              name="remote_endpoint" 
              type="url" 
              placeholder="https://secops.partner.corp/a2a/v1/agent" 
              class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div>
            <label class="block font-semibold text-slate-300 mb-1">Semantic Description (Used for Gemini Router Selection)</label>
            <textarea 
              [(ngModel)]="form.description" 
              name="description" 
              rows="2" 
              required 
              placeholder="Describe tasks this agent handles so the Router can match prompts..." 
              class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
            ></textarea>
          </div>

          <div>
            <label class="block font-semibold text-slate-300 mb-1">System Prompt / Agent Instructions</label>
            <textarea 
              [(ngModel)]="form.system_prompt" 
              name="system_prompt" 
              rows="2" 
              required 
              placeholder="Instructions and persona for this sub-agent..." 
              class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
            ></textarea>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block font-semibold text-slate-300 mb-1">Allowed Tools (comma-separated)</label>
              <input 
                [(ngModel)]="toolsInput" 
                name="tools" 
                type="text" 
                placeholder="e.g. get_system_health, lookup_employee" 
                class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label class="block font-semibold text-slate-300 mb-1">Knowledge Scopes (comma-separated)</label>
              <input 
                [(ngModel)]="scopesInput" 
                name="scopes" 
                type="text" 
                placeholder="e.g. marketing_guidelines, brand_book" 
                class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          <button 
            type="submit" 
            [disabled]="submitting()"
            class="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-2.5 rounded-xl shadow-lg transition cursor-pointer disabled:opacity-50"
          >
            {{ submitting() ? 'Registering Agent...' : 'Onboard & Register Agent' }}
          </button>
        </form>
      </div>

      <!-- Active Agent Registry Cards -->
      <div class="lg:col-span-5 bg-slate-900/80 border border-slate-800 rounded-2xl p-6 flex flex-col">
        <h2 class="text-lg font-bold text-white flex items-center justify-between mb-4">
          <span class="flex items-center gap-2">
            <span class="text-sky-400">📚</span>
            Active Agent Registry
          </span>
          <span class="text-xs font-normal text-slate-400">{{ orchestrator.agents().length }} agents loaded</span>
        </h2>

        <div class="space-y-3 overflow-y-auto max-h-[500px] flex-1 pr-1">
          <div 
            *ngFor="let agent of orchestrator.agents()" 
            class="p-3.5 rounded-xl bg-slate-800/70 border border-slate-700/80 text-xs space-y-2 hover:border-slate-600 transition"
          >
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="w-2.5 h-2.5 rounded-full" [ngClass]="agent.active ? 'bg-emerald-400' : 'bg-slate-500'"></span>
                <span class="font-bold text-white text-sm">{{ agent.name }}</span>
              </div>
              <span 
                class="px-2 py-0.5 rounded-full text-[10px] font-semibold border"
                [ngClass]="agent.agent_type === 'remote_a2a' ? 'bg-sky-950 text-sky-300 border-sky-800' : 'bg-indigo-950 text-indigo-300 border-indigo-800'"
              >
                {{ agent.agent_type === 'remote_a2a' ? 'Remote A2A' : 'ADK Sub-Agent' }}
              </span>
            </div>

            <p class="text-slate-300 leading-snug">{{ agent.description }}</p>

            <div class="flex flex-wrap gap-1 text-[10px] text-slate-400">
              <span class="bg-slate-900 px-2 py-0.5 rounded">Team: <strong class="text-slate-300">{{ agent.owner_team }}</strong></span>
              <span class="bg-slate-900 px-2 py-0.5 rounded">Tools: <strong class="text-slate-300">{{ agent.allowed_tools.length }}</strong></span>
              <span class="bg-slate-900 px-2 py-0.5 rounded">Scopes: <strong class="text-slate-300">{{ agent.knowledge_scopes.join(', ') || 'None' }}</strong></span>
            </div>

            <div class="flex items-center justify-between pt-1 border-t border-slate-700/50">
              <span class="text-[10px] text-slate-500 font-mono">ID: {{ agent.id }}</span>
              <div class="flex gap-2">
                <button 
                  (click)="toggleActive(agent.id)" 
                  class="text-[11px] text-slate-300 hover:text-white underline cursor-pointer"
                >
                  {{ agent.active ? 'Deactivate' : 'Activate' }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `
})
export class OnboardingComponent {
  submitting = signal(false);

  form: Partial<AgentManifest> = {
    id: '',
    name: '',
    owner_team: '',
    agent_type: 'local_adk',
    remote_endpoint: null,
    description: '',
    system_prompt: '',
    active: true
  };

  toolsInput = '';
  scopesInput = '';

  constructor(public orchestrator: OrchestratorService) {}

  autoFillMarketingAgent(): void {
    this.form = {
      id: 'marketing_growth_agent',
      name: 'Marketing & Brand Growth Agent',
      owner_team: 'Marketing',
      agent_type: 'local_adk',
      remote_endpoint: null,
      description: 'Handles marketing campaigns, brand identity standards, social media copy reviews, and growth analytics.',
      system_prompt: 'You are the Marketing Growth Agent. Advise team members on branding, messaging, and campaign metrics.',
      active: true
    };
    this.toolsInput = 'get_system_health';
    this.scopesInput = 'marketing_guidelines';
  }

  submitManifest(): void {
    if (!this.form.id || !this.form.name) return;

    this.submitting.set(true);
    const manifest: AgentManifest = {
      id: this.form.id,
      name: this.form.name,
      owner_team: this.form.owner_team || 'General',
      agent_type: this.form.agent_type as any || 'local_adk',
      remote_endpoint: this.form.remote_endpoint || null,
      description: this.form.description || '',
      system_prompt: this.form.system_prompt || '',
      allowed_tools: this.toolsInput.split(',').map(s => s.trim()).filter(Boolean),
      knowledge_scopes: this.scopesInput.split(',').map(s => s.trim()).filter(Boolean),
      active: true
    };

    this.orchestrator.onboardAgent(manifest).subscribe({
      next: () => {
        alert(`Agent '${manifest.name}' onboarded successfully! It is now active in the Orchestrator router.`);
        this.resetForm();
        this.submitting.set(false);
      },
      error: (err) => {
        alert(`Failed to onboard agent: ${err.message}`);
        this.submitting.set(false);
      }
    });
  }

  toggleActive(agentId: string): void {
    this.orchestrator.toggleAgent(agentId).subscribe();
  }

  private resetForm(): void {
    this.form = {
      id: '',
      name: '',
      owner_team: '',
      agent_type: 'local_adk',
      remote_endpoint: null,
      description: '',
      system_prompt: '',
      active: true
    };
    this.toolsInput = '';
    this.scopesInput = '';
  }
}
