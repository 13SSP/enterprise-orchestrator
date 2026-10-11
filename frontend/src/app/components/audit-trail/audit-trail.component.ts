import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuditService } from '../../services/audit.service';

@Component({
  selector: 'app-audit-trail',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="flex-1 flex flex-col gap-4 max-w-7xl mx-auto w-full">
      <!-- Controls Topbar -->
      <div class="flex items-center justify-between bg-slate-900/80 border border-slate-800 p-4 rounded-2xl">
        <div class="flex items-center gap-3">
          <div class="w-3 h-3 rounded-full bg-emerald-500 animate-pulse"></div>
          <div>
            <h2 class="text-sm font-bold text-white">Google Cloud Logging & Trace Audit Stream</h2>
            <p class="text-xs text-slate-400">
              Captures routing decisions, ADK policy evaluations, tool executions, and security denials in real-time.
            </p>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <select 
            [ngModel]="audit.activeFilter()" 
            (ngModelChange)="onFilterChange($event)"
            class="bg-slate-800 border border-slate-700 text-xs rounded-lg px-3 py-1.5 text-white focus:outline-none cursor-pointer"
          >
            <option value="">All Events</option>
            <option value="ROUTING_DECISION">Routing Decisions</option>
            <option value="POLICY_DENIAL">Policy Denials ⛔</option>
            <option value="TOOL_EXECUTION">Tool Executions</option>
            <option value="WRITE_CONFIRMATION">Write Confirmations ⚠️</option>
            <option value="RAG_RETRIEVAL">RAG Queries</option>
          </select>

          <button 
            (click)="audit.refreshLogs()" 
            class="bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs px-3 py-1.5 rounded-lg flex items-center gap-1 text-slate-300 cursor-pointer"
          >
            <span>🔄</span> Refresh
          </button>

          <button 
            (click)="audit.clearLogs()" 
            class="bg-rose-950/40 hover:bg-rose-900/60 border border-rose-800 text-rose-300 text-xs px-3 py-1.5 rounded-lg cursor-pointer"
          >
            Clear
          </button>
        </div>
      </div>

      <!-- Logs Stream Feed -->
      <div class="bg-slate-900/60 border border-slate-800 rounded-2xl p-4 overflow-y-auto flex-1 max-h-[58vh] min-h-[420px] space-y-2.5 font-mono text-xs">
        <div *ngIf="audit.logs().length === 0" class="text-slate-500 text-center py-8">
          No audit logs recorded yet.
        </div>

        <div 
          *ngFor="let log of audit.logs()" 
          class="p-2.5 rounded-xl bg-slate-950/70 border border-slate-800 text-[11px] font-mono space-y-1 hover:border-slate-700 transition"
        >
          <div class="flex items-center justify-between text-[10px]">
            <div class="flex items-center gap-2">
              <span class="text-slate-500">{{ formatTime(log.timestamp) }}</span>
              <span [class]="getSeverityBadgeClass(log.severity) + ' px-1.5 py-0.2 rounded border font-semibold'">
                {{ log.severity }}
              </span>
              <span class="text-indigo-400 font-bold">{{ log.event_type }}</span>
            </div>
            <span class="text-slate-500">Trace: {{ log.trace_id.slice(0, 8) }}</span>
          </div>

          <p class="text-slate-200">{{ log.message }}</p>

          <details class="text-slate-400 text-[10px] cursor-pointer">
            <summary class="text-slate-500 hover:text-slate-300">View Cloud Logging JSON Payload</summary>
            <pre class="bg-slate-900 p-2 mt-1 rounded border border-slate-800 text-emerald-400 overflow-x-auto">{{ log | json }}</pre>
          </details>
        </div>
      </div>
    </div>
  `
})
export class AuditTrailComponent {
  constructor(public audit: AuditService) {}

  onFilterChange(f: string): void {
    this.audit.setFilter(f);
  }

  formatTime(iso: string): string {
    return new Date(iso).toLocaleTimeString();
  }

  getSeverityBadgeClass(sev: string): string {
    switch (sev) {
      case 'WARNING':
      case 'ERROR': return 'text-rose-400 bg-rose-950/60 border-rose-800';
      case 'NOTICE': return 'text-amber-400 bg-amber-950/60 border-amber-800';
      default: return 'text-sky-400 bg-sky-950/60 border-sky-800';
    }
  }
}
