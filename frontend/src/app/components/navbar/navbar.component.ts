import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
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
            ⚡
          </div>
          <div>
            <h1 class="text-base font-bold bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
              cortex.ai
            </h1>
            <p class="text-xs text-slate-400 flex items-center gap-1.5">
              <span class="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              Vertex AI Agent Engine &bull; Angular Standalone
            </p>
          </div>
        </div>

        <!-- Top Right Actions & Profile -->
        <div class="flex items-center space-x-4">
          <div class="hidden md:flex items-center gap-2 text-xs text-slate-400">
            <span class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-blue-400"></span>ShieldGemma: <strong class="text-blue-400">Active</strong></span>
          </div>

          <!-- Top Right User Profile Button Trigger -->
          <div class="relative">
            <button 
              (click)="showProfileMenu.set(!showProfileMenu())" 
              class="flex items-center gap-2 p-1 rounded-full hover:ring-2 hover:ring-blue-500/50 transition focus:outline-none cursor-pointer"
            >
              <div class="relative">
                <div class="w-9 h-9 rounded-full bg-slate-700/80 border border-slate-600 flex items-center justify-center font-bold text-xs text-slate-100 shadow-sm">
                  {{ getUserInitials() }}
                </div>
                <span class="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-blue-500 border-2 border-slate-900"></span>
              </div>
            </button>

            <!-- Profile Popover Menu -->
            <div 
              *ngIf="showProfileMenu()" 
              class="absolute right-0 mt-2 w-80 rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl z-50 overflow-hidden"
            >
              <!-- User Profile Header Card -->
              <div class="p-5 border-b border-slate-800 bg-slate-800/40 text-center relative">
                <div class="inline-flex relative mb-2.5">
                  <div class="w-14 h-14 rounded-full bg-gradient-to-tr from-blue-600 via-indigo-600 to-cyan-500 text-white font-bold text-lg flex items-center justify-center shadow-md border-2 border-slate-700">
                    {{ getUserInitials() }}
                  </div>
                </div>
                <h3 class="font-bold text-sm text-slate-100">{{ getUserDisplayName() }}</h3>
                <p class="text-xs text-slate-400 font-mono mt-0.5">{{ getUserEmail() }}</p>
                <div class="mt-2.5 inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-medium bg-blue-500/15 text-blue-300 border border-blue-500/25">
                  <span class="w-1.5 h-1.5 rounded-full bg-blue-400"></span>
                  <span>{{ getUserRoleLabel() }}</span>
                </div>
              </div>

              <div class="p-2.5 space-y-2">
                <!-- Shifted User Identity Switcher -->
                <div>
                  <div class="px-2 py-1 text-[10px] font-semibold tracking-wider uppercase text-slate-400 flex items-center justify-between">
                    <span>Firebase Identity</span>
                    <span class="text-[9px] text-blue-400">Active</span>
                  </div>
                  <div class="space-y-1 mt-1 max-h-40 overflow-y-auto pr-1">
                    <div 
                      (click)="onPersonaSelect('devops_admin')" 
                      class="flex items-center justify-between p-2 rounded-xl cursor-pointer hover:bg-slate-800/80 transition"
                      [class.bg-slate-800]="auth.currentPersonaKey() === 'devops_admin'"
                    >
                      <div class="flex items-center gap-2.5">
                        <div class="w-7 h-7 rounded-full bg-indigo-600/30 text-indigo-300 font-bold text-xs flex items-center justify-center border border-indigo-500/30">BM</div>
                        <div>
                          <div class="text-xs font-semibold text-slate-200">Bob Martinez</div>
                          <div class="text-[10px] text-slate-400">DevOps Admin</div>
                        </div>
                      </div>
                      <span *ngIf="auth.currentPersonaKey() === 'devops_admin'" class="text-blue-400 text-xs font-bold">✓</span>
                    </div>

                    <div 
                      (click)="onPersonaSelect('hr_manager')" 
                      class="flex items-center justify-between p-2 rounded-xl cursor-pointer hover:bg-slate-800/80 transition"
                      [class.bg-slate-800]="auth.currentPersonaKey() === 'hr_manager'"
                    >
                      <div class="flex items-center gap-2.5">
                        <div class="w-7 h-7 rounded-full bg-pink-600/30 text-pink-300 font-bold text-xs flex items-center justify-center border border-pink-500/30">AH</div>
                        <div>
                          <div class="text-xs font-semibold text-slate-200">Alice Henderson</div>
                          <div class="text-[10px] text-slate-400">HR Manager</div>
                        </div>
                      </div>
                      <span *ngIf="auth.currentPersonaKey() === 'hr_manager'" class="text-blue-400 text-xs font-bold">✓</span>
                    </div>

                    <div 
                      (click)="onPersonaSelect('finance_officer')" 
                      class="flex items-center justify-between p-2 rounded-xl cursor-pointer hover:bg-slate-800/80 transition"
                      [class.bg-slate-800]="auth.currentPersonaKey() === 'finance_officer'"
                    >
                      <div class="flex items-center gap-2.5">
                        <div class="w-7 h-7 rounded-full bg-emerald-600/30 text-emerald-300 font-bold text-xs flex items-center justify-center border border-emerald-500/30">CZ</div>
                        <div>
                          <div class="text-xs font-semibold text-slate-200">Charlie Zhao</div>
                          <div class="text-[10px] text-slate-400">Finance Officer</div>
                        </div>
                      </div>
                      <span *ngIf="auth.currentPersonaKey() === 'finance_officer'" class="text-blue-400 text-xs font-bold">✓</span>
                    </div>

                    <div 
                      (click)="onPersonaSelect('contractor_guest')" 
                      class="flex items-center justify-between p-2 rounded-xl cursor-pointer hover:bg-slate-800/80 transition"
                      [class.bg-slate-800]="auth.currentPersonaKey() === 'contractor_guest'"
                    >
                      <div class="flex items-center gap-2.5">
                        <div class="w-7 h-7 rounded-full bg-amber-600/30 text-amber-300 font-bold text-xs flex items-center justify-center border border-amber-500/30">DM</div>
                        <div>
                          <div class="text-xs font-semibold text-slate-200">Dave Miller</div>
                          <div class="text-[10px] text-slate-400">Restricted Contractor</div>
                        </div>
                      </div>
                      <span *ngIf="auth.currentPersonaKey() === 'contractor_guest'" class="text-blue-400 text-xs font-bold">✓</span>
                    </div>
                  </div>
                </div>

                <div class="border-t border-slate-800"></div>

                <!-- Appearance: Light & Dark Mode 2-toggle pill -->
                <div class="flex items-center justify-between p-2 rounded-xl hover:bg-slate-800/50 transition">
                  <div class="flex items-center gap-2.5 text-xs text-slate-200 font-medium">
                    <span class="text-sm">🌗</span>
                    <span>Appearance</span>
                  </div>
                  <div class="flex items-center p-0.5 rounded-full bg-slate-800 border border-slate-700/80">
                    <button 
                      (click)="toggleTheme('light')" 
                      title="Light Mode" 
                      class="flex items-center justify-center w-7 h-7 rounded-full transition cursor-pointer"
                      [class.bg-white]="isLightMode()" 
                      [class.text-blue-600]="isLightMode()" 
                      [class.text-slate-400]="!isLightMode()"
                    >
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"></path></svg>
                    </button>
                    <button 
                      (click)="toggleTheme('dark')" 
                      title="Dark Mode" 
                      class="flex items-center justify-center w-7 h-7 rounded-full transition cursor-pointer"
                      [class.bg-slate-700]="!isLightMode()" 
                      [class.text-blue-400]="!isLightMode()" 
                      [class.text-slate-400]="isLightMode()"
                    >
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"></path></svg>
                    </button>
                  </div>
                </div>

                <div class="border-t border-slate-800"></div>

                <!-- Navigation: Tool Catalog, Model Details, Cloud Audit Logs -->
                <div>
                  <div class="px-2 py-1 text-[10px] font-semibold tracking-wider uppercase text-slate-400">Navigation & Tools</div>
                  <div class="space-y-0.5 mt-0.5">
                    <button 
                      (click)="navigateTo('/tools')" 
                      class="w-full flex items-center justify-between p-2 rounded-xl hover:bg-slate-800/80 text-left transition group cursor-pointer"
                    >
                      <div class="flex items-center gap-2.5">
                        <span class="text-sm">🛠️</span>
                        <div>
                          <div class="text-xs font-semibold text-slate-200 group-hover:text-blue-400 transition">Tool Catalog</div>
                          <div class="text-[10px] text-slate-400">25 Registered API Tools</div>
                        </div>
                      </div>
                      <span class="text-[10px] bg-slate-800 text-blue-400 font-mono px-2 py-0.5 rounded-full border border-slate-700">25</span>
                    </button>

                    <button 
                      (click)="navigateTo('/models')" 
                      class="w-full flex items-center justify-between p-2 rounded-xl hover:bg-slate-800/80 text-left transition group cursor-pointer"
                    >
                      <div class="flex items-center gap-2.5">
                        <span class="text-sm">🧠</span>
                        <div>
                          <div class="text-xs font-semibold text-slate-200 group-hover:text-purple-400 transition">Model Details</div>
                          <div class="text-[10px] text-slate-400">Gemini 2.5/3, ShieldGemma</div>
                        </div>
                      </div>
                      <span class="text-[10px] bg-slate-800 text-purple-400 font-mono px-2 py-0.5 rounded-full border border-slate-700">Active</span>
                    </button>

                    <button 
                      (click)="navigateTo('/audit')" 
                      class="w-full flex items-center justify-between p-2 rounded-xl hover:bg-slate-800/80 text-left transition group cursor-pointer"
                    >
                      <div class="flex items-center gap-2.5">
                        <span class="text-sm">📜</span>
                        <div>
                          <div class="text-xs font-semibold text-slate-200 group-hover:text-amber-400 transition">Logs & Audit Trail</div>
                          <div class="text-[10px] text-slate-400">SOC2 Audit & Security Blocks</div>
                        </div>
                      </div>
                      <span class="text-[10px] bg-slate-800 text-amber-400 font-mono px-2 py-0.5 rounded-full border border-slate-700">SOC2</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </header>
  `
})
export class NavbarComponent {
  showProfileMenu = signal(false);
  isLightMode = signal(false);

  constructor(public auth: AuthService, private router: Router) {
    const saved = localStorage.getItem('cortex_theme');
    if (saved !== 'dark') {
      this.isLightMode.set(true);
      document.body.classList.add('theme-light');
    }
  }

  getUserInitials(): string {
    const key = this.auth.currentPersonaKey();
    if (key === 'hr_manager') return 'AH';
    if (key === 'finance_officer') return 'CZ';
    if (key === 'contractor_guest') return 'DM';
    return 'BM';
  }

  getUserDisplayName(): string {
    return this.auth.currentPersona()?.user?.name || 'Bob Martinez';
  }

  getUserEmail(): string {
    return this.auth.currentPersona()?.user?.email || 'bob.ops@company.internal';
  }

  getUserRoleLabel(): string {
    const key = this.auth.currentPersonaKey();
    if (key === 'hr_manager') return 'HR Manager • People Ops';
    if (key === 'finance_officer') return 'Finance Officer • Compensation';
    if (key === 'contractor_guest') return 'Restricted Contractor • External';
    return 'DevOps Admin • Platform Lead';
  }

  onPersonaSelect(key: string): void {
    this.auth.setPersona(key);
    this.showProfileMenu.set(false);
  }

  toggleTheme(mode: 'light' | 'dark'): void {
    if (mode === 'light') {
      this.isLightMode.set(true);
      localStorage.setItem('cortex_theme', 'light');
      document.body.classList.add('theme-light');
      document.documentElement.classList.add('theme-light');
    } else {
      this.isLightMode.set(false);
      localStorage.setItem('cortex_theme', 'dark');
      document.body.classList.remove('theme-light');
      document.documentElement.classList.remove('theme-light');
    }
  }

  navigateTo(path: string): void {
    this.showProfileMenu.set(false);
    this.router.navigate([path]).catch(() => {});
  }
}
