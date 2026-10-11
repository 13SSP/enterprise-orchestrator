import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { OrchestratorService } from '../../services/orchestrator.service';
import { ToolDefinition } from '../../models/agent.model';

@Component({
  selector: 'app-tool-builder',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 max-w-7xl mx-auto w-full">
      <!-- Importer Column -->
      <div class="lg:col-span-6 bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-4">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-lg font-bold text-white flex items-center gap-2">
              <span class="text-indigo-400">⚡</span>
              Swagger / OpenAPI Tool Builder
            </h2>
            <p class="text-xs text-slate-400">
              Parses OpenAPI specs into ADK tools, tags Read/Write, and requires write confirmation.
            </p>
          </div>
          <div class="flex gap-2">
            <button 
              type="button" 
              (click)="loadDevOpsSpec()" 
              class="text-xs bg-slate-800 hover:bg-slate-700 text-indigo-300 border border-slate-700 px-2.5 py-1 rounded-lg cursor-pointer"
            >
              DevOps Spec
            </button>
            <button 
              type="button" 
              (click)="loadFinanceSpec()" 
              class="text-xs bg-slate-800 hover:bg-slate-700 text-emerald-300 border border-slate-700 px-2.5 py-1 rounded-lg cursor-pointer"
            >
              ERP Spec
            </button>
          </div>
        </div>

        <div class="space-y-3 text-xs">
          <div>
            <label class="block font-semibold text-slate-300 mb-1">Target Agent to Bind Tools (Optional)</label>
            <select 
              [(ngModel)]="selectedAgentId" 
              class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none"
            >
              <option [ngValue]="null">-- Global Tool Registry (No binding) --</option>
              <option *ngFor="let agent of orchestrator.agents()" [value]="agent.id">
                {{ agent.name }} ({{ agent.owner_team }})
              </option>
            </select>
          </div>

          <div>
            <label class="block font-semibold text-slate-300 mb-1">OpenAPI 3.0 / Swagger 2.0 Spec (YAML or JSON)</label>
            <textarea 
              [(ngModel)]="specContent" 
              rows="14" 
              class="w-full font-mono text-xs bg-slate-800 border border-slate-700 rounded-lg p-3 text-slate-200 focus:outline-none focus:border-indigo-500" 
              placeholder="Paste OpenAPI YAML or JSON here..."
            ></textarea>
          </div>

          <button 
            (click)="importSpec()" 
            [disabled]="importing() || !specContent.trim()"
            class="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-semibold py-2.5 rounded-xl shadow-lg transition flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
          >
            <span>⚙️</span>
            <span>{{ importing() ? 'Parsing & Generating Tools...' : 'Parse & Generate ADK Tools' }}</span>
          </button>
        </div>
      </div>

      <!-- Generated Tools Preview Table -->
      <div class="lg:col-span-6 bg-slate-900/80 border border-slate-800 rounded-2xl p-6 flex flex-col">
        <h2 class="text-lg font-bold text-white flex items-center justify-between mb-4">
          <span class="flex items-center gap-2">
            <span class="text-amber-400">🔧</span>
            Active Tool Registry
          </span>
          <span class="text-xs font-normal text-slate-400">{{ orchestrator.tools().length }} tools registered</span>
        </h2>

        <div class="space-y-2.5 overflow-y-auto max-h-[500px] flex-1 pr-1">
          <div 
            *ngFor="let tool of orchestrator.tools()" 
            class="p-3 rounded-xl bg-slate-800/70 border border-slate-700/80 text-xs space-y-1.5 hover:border-slate-600 transition"
          >
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span [class]="getMethodBadgeClass(tool.method) + ' px-2 py-0.5 rounded font-mono font-bold text-[10px] border'">
                  {{ tool.method }}
                </span>
                <span class="font-mono font-semibold text-white text-xs">{{ tool.name }}</span>
              </div>
              <div>
                <span 
                  *ngIf="tool.is_write" 
                  class="bg-amber-950/80 text-amber-300 border border-amber-800/60 px-1.5 py-0.5 rounded text-[10px]"
                >
                  Write (Confirmation)
                </span>
                <span 
                  *ngIf="!tool.is_write" 
                  class="bg-emerald-950/80 text-emerald-300 border border-emerald-800/60 px-1.5 py-0.5 rounded text-[10px]"
                >
                  Read-Only
                </span>
              </div>
            </div>

            <p class="text-slate-300 text-[11px] leading-tight">{{ tool.description }}</p>

            <div class="flex items-center justify-between text-[10px] text-slate-400 font-mono pt-1 border-t border-slate-700/50">
              <span>Path: {{ tool.path }}</span>
              <span>Agent: {{ tool.owner_agent || 'Global' }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  `
})
export class ToolBuilderComponent {
  specContent = '';
  selectedAgentId: string | null = null;
  importing = signal(false);

  constructor(public orchestrator: OrchestratorService) {}

  loadDevOpsSpec(): void {
    this.orchestrator.getSampleSpecs().subscribe({
      next: (res) => {
        this.specContent = res.devops_sample;
        this.selectedAgentId = 'it_agent';
      }
    });
  }

  loadFinanceSpec(): void {
    this.orchestrator.getSampleSpecs().subscribe({
      next: (res) => {
        this.specContent = res.finance_sample;
        this.selectedAgentId = 'finance_agent';
      }
    });
  }

  importSpec(): void {
    if (!this.specContent.trim()) return;

    this.importing.set(true);
    this.orchestrator.importSwagger(this.specContent, this.selectedAgentId).subscribe({
      next: (res) => {
        alert(`Success! Generated ${res.imported_tools.length} ADK tools.`);
        this.importing.set(false);
      },
      error: (err) => {
        alert(`Import error: ${err.message || 'Invalid OpenAPI format'}`);
        this.importing.set(false);
      }
    });
  }

  getMethodBadgeClass(method: string): string {
    switch (method) {
      case 'GET': return 'bg-emerald-950 text-emerald-300 border-emerald-800';
      case 'POST': return 'bg-amber-950 text-amber-300 border-amber-800';
      case 'DELETE': return 'bg-rose-950 text-rose-300 border-rose-800';
      default: return 'bg-sky-950 text-sky-300 border-sky-800';
    }
  }
}
