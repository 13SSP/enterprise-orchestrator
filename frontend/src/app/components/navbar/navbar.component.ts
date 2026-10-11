import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <header class="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-50">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <!-- Logo and Engine Status -->
        <div class="flex items-center space-x-3">
          <div class="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-sky-400 flex items-center justify-center shadow-lg shadow-indigo-500/20 text-white font-black text-sm">
            AI
          </div>
          <div>
            <h1 class="text-base font-bold bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
              Enterprise AI Orchestrator
            </h1>
            <p class="text-xs text-slate-400 flex items-center gap-1.5">
              <span class="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              Vertex AI Agent Engine &bull; Angular Standalone
            </p>
          </div>
        </div>

        <!-- Tier 1 Auth: Persona Switcher and JWT Inspector -->
        <div class="flex items-center space-x-4">
          <div class="flex items-center bg-slate-800/90 border border-slate-700/80 rounded-xl px-3 py-1.5">
            <span class="text-indigo-400 text-xs mr-2 font-mono">🔒 Identity:</span>
            <select 
              [ngModel]="auth.currentPersonaKey()" 
              (ngModelChange)="onPersonaChange($event)"
              class="bg-transparent text-xs font-semibold text-white focus:outline-none cursor-pointer"
            >
              <option value="devops_admin" class="bg-slate-900 text-white">Bob Martinez (DevOps Admin)</option>
              <option value="hr_manager" class="bg-slate-900 text-white">Alice Henderson (HR Manager)</option>
              <option value="finance_officer" class="bg-slate-900 text-white">Charlie Zhao (Finance Lead)</option>
              <option value="contractor_guest" class="bg-slate-900 text-amber-300">Dave Miller (Restricted Contractor)</option>
            </select>
          </div>

          <button 
            (click)="showJwtModal.set(true)"
            class="text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition"
          >
            <span class="text-amber-400">🔑</span>
            <span>JWT Claims</span>
          </button>
        </div>
      </div>
    </header>

    <!-- JWT Claims Modal -->
    <div *ngIf="showJwtModal()" class="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div class="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
        <div class="flex items-center justify-between border-b border-slate-800 pb-3">
          <h3 class="font-bold text-white flex items-center gap-2 text-base">
            <span class="text-amber-400">🔑</span>
            Identity Platform JWT Claims
          </h3>
          <button (click)="showJwtModal.set(false)" class="text-slate-400 hover:text-white text-lg">&times;</button>
        </div>
        <p class="text-xs text-slate-400">
          Simulated Identity Platform token passed to Orchestrator to enforce RBAC and ADK tool filtering.
        </p>

        <div>
          <span class="text-xs font-semibold text-slate-400">Decoded Token Payload:</span>
          <pre class="bg-slate-950 p-3 rounded-lg border border-slate-800 text-emerald-400 text-xs overflow-x-auto max-h-48 font-mono mt-1">{{ auth.currentPersona()?.user | json }}</pre>
        </div>

        <div>
          <span class="text-xs font-semibold text-slate-400">Raw Signed JWT:</span>
          <p class="bg-slate-950 p-2.5 rounded-lg border border-slate-800 text-slate-400 text-[10px] break-all select-all font-mono mt-1">{{ auth.getJwtToken() }}</p>
        </div>

        <button (click)="showJwtModal.set(false)" class="w-full bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold py-2 rounded-lg">
          Close Inspector
        </button>
      </div>
    </div>
  `
})
export class NavbarComponent {
  showJwtModal = signal(false);

  constructor(public auth: AuthService) {}

  onPersonaChange(key: string): void {
    this.auth.setPersona(key);
  }
}
