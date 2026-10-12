import { Component, EventEmitter, Output, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { OrchestratorService } from '../../services/orchestrator.service';
import { AuthService } from '../../services/auth.service';
import { AgentManifest, ToolDefinition, GenerateAgentSwaggerRequest } from '../../models/agent.model';

@Component({
  selector: 'app-agents-list',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="max-w-7xl mx-auto w-full space-y-6">
      <!-- Top Header & Create Button -->
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-white tracking-tight">Agents</h1>
          <p class="text-xs text-slate-400 mt-0.5">
            Discover, invoke, and manage intelligent enterprise ADK sub-agents across your organization.
          </p>
        </div>

        <button 
          (click)="openCreateModal()"
          class="bg-blue-600 hover:bg-blue-500 text-white font-medium text-sm px-4 py-2 rounded-xl shadow-lg shadow-blue-600/30 flex items-center gap-2 cursor-pointer transition"
        >
          <span>➕</span>
          <span>Create an agent</span>
        </button>
      </div>

      <!-- Search and Filter Bar -->
      <div class="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <!-- Search Input -->
        <div class="relative flex-1 max-w-lg">
          <span class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400 text-sm">
            🔍
          </span>
          <input 
            type="text" 
            [(ngModel)]="searchQuery" 
            placeholder="Search agents" 
            class="w-full bg-slate-900 border border-slate-800 rounded-xl pl-10 pr-4 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition"
          />
          <button 
            *ngIf="searchQuery()" 
            (click)="searchQuery.set('')"
            class="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-500 hover:text-white text-xs cursor-pointer"
          >
            ✕
          </button>
        </div>

        <!-- Filter Scope Pills: All vs Your agents (No Starred) -->
        <div class="flex items-center bg-slate-900 border border-slate-800 p-1 rounded-xl text-xs font-medium space-x-1">
          <button 
            (click)="filterScope.set('all')"
            [class]="(filterScope() === 'all' ? 'bg-slate-800 text-white shadow-sm' : 'text-slate-400 hover:text-white') + ' px-4 py-1.5 rounded-lg transition cursor-pointer'"
          >
            All
          </button>
          <button 
            (click)="filterScope.set('mine')"
            [class]="(filterScope() === 'mine' ? 'bg-slate-800 text-white shadow-sm' : 'text-slate-400 hover:text-white') + ' px-4 py-1.5 rounded-lg transition cursor-pointer flex items-center gap-1.5'"
          >
            <span>Your agents</span>
            <span class="bg-slate-700/80 text-slate-300 text-[10px] px-1.5 py-0.2 rounded-full font-mono">
              {{ myAgentsCount() }}
            </span>
          </button>
        </div>
      </div>

      <!-- Agents Cards Grid (Matching reference screenshot) -->
      <div *ngIf="filteredAgents().length > 0; else noAgentsFound" class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div 
          *ngFor="let agent of filteredAgents()" 
          class="bg-slate-900/80 border border-slate-800 hover:border-slate-700 rounded-2xl p-5 flex flex-col justify-between transition group shadow-sm"
        >
          <div>
            <!-- Card Header: Icon Badge & Status -->
            <div class="flex items-start justify-between gap-3 mb-3">
              <!-- Icon Container -->
              <div [class]="getIconBadgeClass(agent.icon, agent.owner_team) + ' w-10 h-10 rounded-xl flex items-center justify-center text-lg flex-shrink-0 shadow-inner'">
                <span>{{ getIconSymbol(agent.icon, agent.owner_team) }}</span>
              </div>

              <!-- Top Right Status Badges -->
              <div class="flex items-center gap-1.5 flex-wrap justify-end">
                <span 
                  *ngIf="agent.is_public" 
                  class="bg-slate-800 text-slate-300 border border-slate-700/60 text-[10px] px-2 py-0.5 rounded-full"
                >
                  Public
                </span>
                <span 
                  *ngIf="!agent.is_public" 
                  class="bg-amber-950 text-amber-300 border border-amber-800/60 text-[10px] px-2 py-0.5 rounded-full"
                >
                  Restricted
                </span>
                <span 
                  class="text-[10px] px-2 py-0.5 rounded-full font-mono border"
                  [ngClass]="agent.agent_type === 'remote_a2a' ? 'bg-sky-950 text-sky-300 border-sky-800' : 'bg-indigo-950 text-indigo-300 border-indigo-800'"
                >
                  {{ agent.agent_type === 'remote_a2a' ? 'Remote A2A' : 'ADK Agent' }}
                </span>
              </div>
            </div>

            <!-- Agent Title and Author (as shown in reference image) -->
            <h2 class="text-base font-bold text-white group-hover:text-indigo-300 transition-colors">
              {{ agent.name }}
            </h2>

            <div class="text-xs text-slate-400 mt-0.5 mb-2.5 flex items-center gap-1.5 flex-wrap">
              <span>by</span>
              <a 
                href="javascript:void(0)" 
                (click)="filterByAuthor(agent.author || agent.owner_team)"
                class="text-blue-400 hover:text-blue-300 hover:underline inline-flex items-center gap-0.5"
              >
                <span>{{ agent.author || agent.owner_team }}</span>
                <span class="text-[10px]">↗</span>
              </a>
              <span *ngIf="!agent.active" class="text-slate-500 font-normal">
                (deactivated)
              </span>
            </div>

            <!-- Description -->
            <p class="text-xs text-slate-300 leading-relaxed line-clamp-3 mb-4">
              {{ agent.description }}
            </p>
          </div>

          <!-- Bottom Card Meta & Action Bar -->
          <div class="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
            <div class="flex items-center gap-2 text-[11px] font-mono">
              <span class="bg-slate-800/80 px-2 py-0.5 rounded text-slate-300">
                Team: <strong>{{ agent.owner_team }}</strong>
              </span>
              <span class="bg-slate-800/80 px-2 py-0.5 rounded text-slate-300">
                Tools: <strong>{{ agent.allowed_tools.length }}</strong>
              </span>
            </div>

            <!-- Card Actions -->
            <div class="flex items-center gap-2">
              <button 
                (click)="openAccessLimitsModal(agent)"
                class="text-[11px] text-slate-400 hover:text-white bg-slate-800 hover:bg-slate-700 px-2 py-1 rounded-lg transition cursor-pointer"
                title="Manage Access Limits and Roles"
              >
                ⚙️ Limits
              </button>
              <button 
                (click)="toggleAgentActive(agent.id)"
                class="text-[11px] text-slate-400 hover:text-white bg-slate-800 hover:bg-slate-700 px-2 py-1 rounded-lg transition cursor-pointer"
              >
                {{ agent.active ? 'Deactivate' : 'Activate' }}
              </button>
              <button 
                (click)="chatWithAgent(agent)"
                class="text-[11px] bg-indigo-600 hover:bg-indigo-500 text-white font-medium px-2.5 py-1 rounded-lg transition cursor-pointer shadow-sm"
              >
                💬 Chat
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <ng-template #noAgentsFound>
        <div class="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-12 text-center max-w-md mx-auto space-y-3">
          <span class="text-4xl block">🔍</span>
          <h3 class="text-base font-semibold text-white">No agents found</h3>
          <p class="text-xs text-slate-400">
            No agents match your current query "{{ searchQuery() }}" in {{ filterScope() === 'mine' ? 'Your agents' : 'All agents' }}.
          </p>
          <div class="pt-2 flex justify-center gap-2">
            <button 
              *ngIf="filterScope() === 'mine'" 
              (click)="filterScope.set('all')" 
              class="text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1.5 rounded-lg cursor-pointer"
            >
              Show All Agents
            </button>
            <button 
              (click)="openCreateModal()" 
              class="text-xs bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-1.5 rounded-lg cursor-pointer"
            >
              Create New Agent
            </button>
          </div>
        </div>
      </ng-template>
    </div>

    <!-- ==================================================================== -->
    <!-- CREATE AGENT MODAL (From Swagger, Custom Manifest, & Onboarding Guide) -->
    <!-- ==================================================================== -->
    <div *ngIf="showCreateModal()" class="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4 overflow-y-auto">
      <div class="bg-slate-900 border border-slate-800 rounded-2xl max-w-3xl w-full p-6 shadow-2xl space-y-5 my-8 max-h-[90vh] flex flex-col">
        <!-- Modal Header -->
        <div class="flex items-center justify-between border-b border-slate-800 pb-3 flex-shrink-0">
          <div>
            <h2 class="text-lg font-bold text-white flex items-center gap-2">
              <span class="text-indigo-400">🤖</span>
              Create an Agent
            </h2>
            <p class="text-xs text-slate-400">
              Instantly generate tools and an ADK agent from OpenAPI/Swagger or register custom manifests.
            </p>
          </div>
          <button (click)="closeCreateModal()" class="text-slate-400 hover:text-white text-xl cursor-pointer">&times;</button>
        </div>

        <!-- Modal Mode Tabs -->
        <div class="flex border-b border-slate-800 text-xs font-medium space-x-4 flex-shrink-0">
          <button 
            (click)="createTab.set('swagger')"
            [class]="(createTab() === 'swagger' ? 'text-indigo-400 border-b-2 border-indigo-500 font-bold' : 'text-slate-400 hover:text-white') + ' pb-2.5 transition cursor-pointer flex items-center gap-1.5'"
          >
            <span>⚡</span>
            <span>From Swagger / OpenAPI (Automated)</span>
          </button>
          <button 
            (click)="createTab.set('manifest')"
            [class]="(createTab() === 'manifest' ? 'text-indigo-400 border-b-2 border-indigo-500 font-bold' : 'text-slate-400 hover:text-white') + ' pb-2.5 transition cursor-pointer flex items-center gap-1.5'"
          >
            <span>📝</span>
            <span>Custom Manifest Form</span>
          </button>
          <button 
            (click)="createTab.set('guide')"
            [class]="(createTab() === 'guide' ? 'text-indigo-400 border-b-2 border-indigo-500 font-bold' : 'text-slate-400 hover:text-white') + ' pb-2.5 transition cursor-pointer flex items-center gap-1.5'"
          >
            <span>📖</span>
            <span>Onboarding Instructions & Steps</span>
          </button>
        </div>

        <!-- Modal Body (Scrollable) -->
        <div class="overflow-y-auto flex-1 pr-1 space-y-4 text-xs">
          
          <!-- TAB 1: SWAGGER AUTO-GENERATION -->
          <div *ngIf="createTab() === 'swagger'" class="space-y-4">
            <!-- Spec Pre-Fill Buttons -->
            <div class="flex items-center justify-between bg-slate-950/60 p-3 rounded-xl border border-slate-800/80">
              <span class="text-slate-400">Quick-load sample Swagger spec:</span>
              <div class="flex gap-2">
                <button 
                  type="button" 
                  (click)="loadDevOpsSwaggerSample()" 
                  class="bg-slate-800 hover:bg-slate-700 text-indigo-300 border border-slate-700 px-2.5 py-1 rounded-lg cursor-pointer"
                >
                  DevOps API Spec
                </button>
                <button 
                  type="button" 
                  (click)="loadFinanceSwaggerSample()" 
                  class="bg-slate-800 hover:bg-slate-700 text-emerald-300 border border-slate-700 px-2.5 py-1 rounded-lg cursor-pointer"
                >
                  ERP Payments Spec
                </button>
              </div>
            </div>

            <!-- Swagger Spec Input -->
            <div>
              <label class="block font-semibold text-slate-300 mb-1">
                OpenAPI 3.0 / Swagger 2.0 Spec (YAML or JSON)
              </label>
              <textarea 
                [(ngModel)]="swaggerForm.spec_content" 
                rows="7" 
                class="w-full font-mono text-[11px] bg-slate-950 border border-slate-700 rounded-xl p-3 text-slate-200 focus:outline-none focus:border-indigo-500" 
                placeholder="Paste OpenAPI YAML or JSON here..."
              ></textarea>
            </div>

            <!-- Agent Identity Overrides -->
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label class="block font-semibold text-slate-300 mb-1">Agent Name (Optional override)</label>
                <input 
                  [(ngModel)]="swaggerForm.agent_name" 
                  type="text" 
                  placeholder="Auto-derived from spec title" 
                  class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none"
                />
              </div>
              <div>
                <label class="block font-semibold text-slate-300 mb-1">Owner Team</label>
                <input 
                  [(ngModel)]="swaggerForm.owner_team" 
                  type="text" 
                  placeholder="e.g. Engineering" 
                  class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none"
                />
              </div>
              <div>
                <label class="block font-semibold text-slate-300 mb-1">Icon Category</label>
                <select 
                  [(ngModel)]="swaggerForm.icon" 
                  class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none cursor-pointer"
                >
                  <option value="wrench">🔧 Wrench / Ops</option>
                  <option value="chart">📊 Chart / Analytics</option>
                  <option value="shield">🛡️ Shield / Security</option>
                  <option value="docs">📄 Docs / Content</option>
                  <option value="cart">🛒 Cart / Commerce</option>
                  <option value="user">👤 User / HR</option>
                  <option value="bot">🤖 Bot / AI</option>
                </select>
              </div>
            </div>

            <!-- ACCESS LIMITATION SECTION (Requirement 2) -->
            <div class="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3">
              <div class="flex items-center justify-between">
                <div>
                  <h3 class="font-bold text-white flex items-center gap-1.5">
                    <span class="text-amber-400">🔒</span>
                    Limit Access to Agent & Tools
                  </h3>
                  <p class="text-[11px] text-slate-400">
                    Define enterprise RBAC roles, team boundaries, and Human-in-the-Loop write confirmations.
                  </p>
                </div>
                <!-- Public Toggle -->
                <label class="flex items-center gap-2 cursor-pointer">
                  <input 
                    type="checkbox" 
                    [(ngModel)]="swaggerForm.is_public" 
                    class="rounded bg-slate-800 border-slate-700 text-indigo-600 focus:ring-indigo-500"
                  />
                  <span class="text-xs font-semibold text-slate-300">Public (All Employees)</span>
                </label>
              </div>

              <!-- Role & Team Limits if not public -->
              <div *ngIf="!swaggerForm.is_public" class="space-y-2 pt-2 border-t border-slate-800">
                <label class="block font-semibold text-slate-300">Allowed Enterprise Roles:</label>
                <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px]">
                  <label *ngFor="let role of availableRoles" class="flex items-center gap-1.5 bg-slate-900 px-2 py-1.5 rounded-lg border border-slate-800 cursor-pointer">
                    <input 
                      type="checkbox" 
                      [checked]="isRoleSelected(role.key)" 
                      (change)="toggleRole(role.key)"
                      class="rounded bg-slate-800 border-slate-700 text-indigo-600"
                    />
                    <span class="text-slate-200">{{ role.label }}</span>
                  </label>
                </div>

                <div class="pt-1">
                  <label class="block font-semibold text-slate-300 mb-1">Allowed Teams (comma-separated):</label>
                  <input 
                    [(ngModel)]="swaggerFormAllowedTeamsInput" 
                    type="text" 
                    placeholder="e.g. Engineering, IT & Operations" 
                    class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-white focus:outline-none"
                  />
                </div>
              </div>

              <div class="text-[11px] text-slate-400 bg-slate-900/60 p-2.5 rounded-lg flex items-center gap-2">
                <span>🛡️</span>
                <span>All write operations (`POST`, `PUT`, `DELETE`) will automatically require Human-in-the-Loop confirmation by default.</span>
              </div>
            </div>

            <!-- Submit Button -->
            <button 
              type="button" 
              (click)="submitGenerateFromSwagger()" 
              [disabled]="generating() || !swaggerForm.spec_content.trim()"
              class="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-3 rounded-xl shadow-lg transition flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
            >
              <span>⚡</span>
              <span>{{ generating() ? 'Generating Agent & Tools...' : 'Generate Agent & Register Tools' }}</span>
            </button>
          </div>

          <!-- TAB 2: MANUAL MANIFEST ONBOARDING -->
          <div *ngIf="createTab() === 'manifest'" class="space-y-4">
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block font-semibold text-slate-300 mb-1">Agent ID</label>
                <input 
                  [(ngModel)]="manifestForm.id" 
                  type="text" 
                  placeholder="e.g. customer_feedback_agent" 
                  class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none"
                />
              </div>
              <div>
                <label class="block font-semibold text-slate-300 mb-1">Display Name</label>
                <input 
                  [(ngModel)]="manifestForm.name" 
                  type="text" 
                  placeholder="e.g. Customer Feedback Analyst" 
                  class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none"
                />
              </div>
            </div>

            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block font-semibold text-slate-300 mb-1">Owner Team</label>
                <input 
                  [(ngModel)]="manifestForm.owner_team" 
                  type="text" 
                  placeholder="e.g. Customer Success" 
                  class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none"
                />
              </div>
              <div>
                <label class="block font-semibold text-slate-300 mb-1">Agent Type</label>
                <select 
                  [(ngModel)]="manifestForm.agent_type" 
                  class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none cursor-pointer"
                >
                  <option value="local_adk">Local ADK Sub-Agent</option>
                  <option value="remote_a2a">Remote Agent (A2A Protocol)</option>
                </select>
              </div>
            </div>

            <div *ngIf="manifestForm.agent_type === 'remote_a2a'">
              <label class="block font-semibold text-slate-300 mb-1">Remote A2A Protocol Endpoint</label>
              <input 
                [(ngModel)]="manifestForm.remote_endpoint" 
                type="url" 
                placeholder="https://agent.service.corp/a2a/v1/agent" 
                class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none"
              />
            </div>

            <div>
              <label class="block font-semibold text-slate-300 mb-1">Semantic Description (Used for Gemini Router Selection)</label>
              <textarea 
                [(ngModel)]="manifestForm.description" 
                rows="2" 
                placeholder="Describe what prompts this agent handles..." 
                class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none"
              ></textarea>
            </div>

            <div>
              <label class="block font-semibold text-slate-300 mb-1">System Prompt / Agent Instructions</label>
              <textarea 
                [(ngModel)]="manifestForm.system_prompt" 
                rows="2" 
                placeholder="Instructions and persona for this sub-agent..." 
                class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none"
              ></textarea>
            </div>

            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block font-semibold text-slate-300 mb-1">Allowed Tools (comma-separated)</label>
                <input 
                  [(ngModel)]="manifestToolsInput" 
                  type="text" 
                  placeholder="e.g. get_system_health, lookup_employee" 
                  class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none"
                />
              </div>
              <div>
                <label class="block font-semibold text-slate-300 mb-1">Knowledge Scopes (comma-separated)</label>
                <input 
                  [(ngModel)]="manifestScopesInput" 
                  type="text" 
                  placeholder="e.g. hr_policies, finance_guidelines" 
                  class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none"
                />
              </div>
            </div>

            <button 
              type="button" 
              (click)="submitManifest()" 
              [disabled]="generating() || !manifestForm.id || !manifestForm.name"
              class="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-3 rounded-xl shadow-lg transition cursor-pointer disabled:opacity-50"
            >
              {{ generating() ? 'Registering Agent...' : 'Onboard & Register Agent' }}
            </button>
          </div>

          <!-- TAB 3: ONBOARDING INSTRUCTIONS & STEPS (Requirement 3) -->
          <div *ngIf="createTab() === 'guide'" class="space-y-4 text-slate-300 leading-relaxed">
            <div class="bg-indigo-950/40 border border-indigo-900/60 p-4 rounded-xl space-y-2">
              <h3 class="font-bold text-indigo-200 text-sm flex items-center gap-2">
                <span>📘</span>
                How to Onboard a New Agent to Enterprise Orchestrator
              </h3>
              <p class="text-xs text-indigo-300/90">
                The platform supports four standardized pathways for teams to deploy and register agents into the Gemini Orchestrator Router.
              </p>
            </div>

            <!-- Pathway 1 -->
            <div class="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-2">
              <h4 class="font-bold text-white text-xs flex items-center gap-2">
                <span class="bg-indigo-600 text-white w-5 h-5 rounded-full inline-flex items-center justify-center text-[10px]">1</span>
                Low-Code Swagger / OpenAPI Auto-Generation (Fastest)
              </h4>
              <p class="text-slate-400 text-xs">
                Provide any OpenAPI 3.0 or Swagger 2.0 YAML or JSON specification. The engine automatically parses endpoints into ADK tools, synthesizes a semantic description and system prompt, and binds them to the new agent.
              </p>
              <ul class="list-disc list-inside text-[11px] text-slate-400 space-y-1">
                <li>Paste the spec in the <strong>"From Swagger / OpenAPI"</strong> tab.</li>
                <li>Configure Role Limits (`allowed_roles`) and Team Limits.</li>
                <li>Click <strong>Generate Agent & Register Tools</strong>. The agent is immediately active in the router!</li>
              </ul>
            </div>

            <!-- Pathway 2 -->
            <div class="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-2">
              <h4 class="font-bold text-white text-xs flex items-center gap-2">
                <span class="bg-indigo-600 text-white w-5 h-5 rounded-full inline-flex items-center justify-center text-[10px]">2</span>
                Manifest-Driven Registration
              </h4>
              <p class="text-slate-400 text-xs">
                For existing sub-agents or custom agents without OpenAPI definitions, register an <code>AgentManifest</code> via the UI form or <code>POST /api/agents/onboard</code>.
              </p>
            </div>

            <!-- Pathway 3 -->
            <div class="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-2">
              <h4 class="font-bold text-white text-xs flex items-center gap-2">
                <span class="bg-indigo-600 text-white w-5 h-5 rounded-full inline-flex items-center justify-center text-[10px]">3</span>
                Native ADK Code Sub-Agent (Python Package)
              </h4>
              <p class="text-slate-400 text-xs">
                For deep reasoning agents with custom Python workflows:
              </p>
              <pre class="bg-slate-900 p-2.5 rounded text-[10px] text-emerald-400 font-mono overflow-x-auto">
agents/
  ├── my-agent/
  │   ├── agent.manifest.yaml   # ID, name, routing description, tools
  │   ├── requirements.txt      # Dependencies
  │   └── src/
  │       └── agent.py          # Python Agent class and create_agent()</pre>
            </div>

            <!-- Pathway 4 -->
            <div class="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-2">
              <h4 class="font-bold text-white text-xs flex items-center gap-2">
                <span class="bg-indigo-600 text-white w-5 h-5 rounded-full inline-flex items-center justify-center text-[10px]">4</span>
                Remote Microservice via Agent-to-Agent (A2A) Protocol
              </h4>
              <p class="text-slate-400 text-xs">
                Deploy an external microservice on Cloud Run or Kubernetes implementing the A2A spec, then register its URL as <code>agent_type: "remote_a2a"</code>.
              </p>
            </div>

            <!-- Verification Checklist -->
            <div class="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-1.5">
              <h4 class="font-bold text-emerald-400 text-xs">✓ Post-Onboarding Verification Checklist</h4>
              <p class="text-[11px] text-slate-400">1. Verify your agent card appears under "All" and "Your agents".</p>
              <p class="text-[11px] text-slate-400">2. Prompt the AI Chat to verify semantic routing directs queries to the new agent.</p>
              <p class="text-[11px] text-slate-400">3. Switch identity to test role access enforcement and human write confirmation.</p>
            </div>
          </div>

        </div>
      </div>
    </div>

    <!-- ==================================================================== -->
    <!-- ACCESS LIMITS MODAL (For editing existing agent permissions)         -->
    <!-- ==================================================================== -->
    <div *ngIf="showAccessModal()" class="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div class="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
        <div class="flex items-center justify-between border-b border-slate-800 pb-3">
          <h3 class="font-bold text-white flex items-center gap-2 text-base">
            <span class="text-amber-400">🔒</span>
            Access Limits: {{ editingAgent()?.name }}
          </h3>
          <button (click)="closeAccessModal()" class="text-slate-400 hover:text-white text-lg cursor-pointer">&times;</button>
        </div>

        <p class="text-xs text-slate-400">
          Configure which enterprise personas, roles, and departments have permission to invoke this agent.
        </p>

        <div class="space-y-3 text-xs">
          <label class="flex items-center gap-2 cursor-pointer bg-slate-950 p-3 rounded-xl border border-slate-800">
            <input 
              type="checkbox" 
              [(ngModel)]="editAccessForm.is_public" 
              class="rounded bg-slate-800 border-slate-700 text-indigo-600"
            />
            <div>
              <span class="font-bold text-white block">Public Agent (All Employees)</span>
              <span class="text-[10px] text-slate-400">When checked, any employee persona can invoke this agent.</span>
            </div>
          </label>

          <div *ngIf="!editAccessForm.is_public" class="space-y-3 pt-2">
            <div>
              <label class="block font-semibold text-slate-300 mb-1.5">Authorized Roles:</label>
              <div class="grid grid-cols-2 gap-2 text-[11px]">
                <label *ngFor="let role of availableRoles" class="flex items-center gap-1.5 bg-slate-950 px-2.5 py-2 rounded-lg border border-slate-800 cursor-pointer">
                  <input 
                    type="checkbox" 
                    [checked]="isEditRoleSelected(role.key)" 
                    (change)="toggleEditRole(role.key)"
                    class="rounded bg-slate-800 border-slate-700 text-indigo-600"
                  />
                  <span class="text-slate-300">{{ role.label }}</span>
                </label>
              </div>
            </div>

            <div>
              <label class="block font-semibold text-slate-300 mb-1">Authorized Teams (comma-separated):</label>
              <input 
                [(ngModel)]="editTeamsInput" 
                type="text" 
                placeholder="e.g. Engineering, Finance" 
                class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none"
              />
            </div>
          </div>

          <div class="flex gap-2 pt-2">
            <button 
              (click)="closeAccessModal()" 
              class="flex-1 bg-slate-800 hover:bg-slate-700 text-slate-300 py-2.5 rounded-xl cursor-pointer"
            >
              Cancel
            </button>
            <button 
              (click)="saveAgentAccess()" 
              [disabled]="savingAccess()"
              class="flex-1 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-2.5 rounded-xl cursor-pointer disabled:opacity-50"
            >
              {{ savingAccess() ? 'Saving...' : 'Save Access Limits' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  `
})
export class AgentsListComponent {
  @Output() selectAgentForChat = new EventEmitter<AgentManifest>();

  searchQuery = signal<string>('');
  filterScope = signal<'all' | 'mine'>('all'); // 'all' | 'mine' (no starred)

  showCreateModal = signal<boolean>(false);
  createTab = signal<'swagger' | 'manifest' | 'guide'>('swagger');
  generating = signal<boolean>(false);

  showAccessModal = signal<boolean>(false);
  editingAgent = signal<AgentManifest | null>(null);
  savingAccess = signal<boolean>(false);

  availableRoles = [
    { key: 'devops_admin', label: 'DevOps Admin' },
    { key: 'it_engineer', label: 'IT Engineer' },
    { key: 'hr_manager', label: 'HR Manager' },
    { key: 'finance_officer', label: 'Finance Officer' },
    { key: 'employee', label: 'General Employee' },
    { key: 'contractor', label: 'External Contractor' }
  ];

  // Swagger creation form
  swaggerForm: GenerateAgentSwaggerRequest = {
    spec_content: '',
    agent_name: '',
    owner_team: 'Engineering',
    icon: 'wrench',
    is_public: true,
    allowed_roles: ['*'],
    allowed_teams: ['*']
  };
  swaggerFormAllowedTeamsInput = '';

  // Manifest form
  manifestForm: Partial<AgentManifest> = {
    id: '',
    name: '',
    owner_team: '',
    agent_type: 'local_adk',
    remote_endpoint: null,
    description: '',
    system_prompt: '',
    active: true,
    is_public: true
  };
  manifestToolsInput = '';
  manifestScopesInput = '';

  // Access limits editing form
  editAccessForm = {
    is_public: true,
    allowed_roles: ['*'],
    allowed_teams: ['*']
  };
  editTeamsInput = '';

  constructor(
    public orchestrator: OrchestratorService,
    public auth: AuthService
  ) {}

  // Filtered agents signal computation
  filteredAgents = computed(() => {
    const q = this.searchQuery().toLowerCase().trim();
    const scope = this.filterScope();
    const currentPersona = this.auth.currentPersona();
    const userSub = currentPersona?.user.sub;
    const userTeam = currentPersona?.user.team;
    const userRoles = currentPersona?.user.roles || [];
    const allowedAgentIds = currentPersona?.user.allowed_agent_ids || ['*'];

    return this.orchestrator.agents().filter(agent => {
      // 1. Filter by Scope ('mine')
      if (scope === 'mine') {
        const isAuthor = agent.author_id === userSub || (agent.author && agent.author.toLowerCase().includes(currentPersona?.user.name.toLowerCase() || ''));
        const isMyTeam = userTeam && agent.owner_team.toLowerCase() === userTeam.toLowerCase();
        const isAssigned = allowedAgentIds.includes('*') || allowedAgentIds.includes(agent.id);
        if (!isAuthor && !isMyTeam && !isAssigned) return false;
      }

      // 2. Search query filter across name, description, author, team, and allowed tools
      if (!q) return true;
      return agent.name.toLowerCase().includes(q) ||
             agent.description.toLowerCase().includes(q) ||
             agent.owner_team.toLowerCase().includes(q) ||
             (agent.author && agent.author.toLowerCase().includes(q)) ||
             agent.allowed_tools.some(t => t.toLowerCase().includes(q));
    });
  });

  myAgentsCount = computed(() => {
    const currentPersona = this.auth.currentPersona();
    const userSub = currentPersona?.user.sub;
    const userTeam = currentPersona?.user.team;
    const allowedAgentIds = currentPersona?.user.allowed_agent_ids || ['*'];

    return this.orchestrator.agents().filter(agent => {
      const isAuthor = agent.author_id === userSub || (agent.author && agent.author.toLowerCase().includes(currentPersona?.user.name.toLowerCase() || ''));
      const isMyTeam = userTeam && agent.owner_team.toLowerCase() === userTeam.toLowerCase();
      const isAssigned = allowedAgentIds.includes('*') || allowedAgentIds.includes(agent.id);
      return isAuthor || isMyTeam || isAssigned;
    }).length;
  });

  filterByAuthor(authorName: string): void {
    this.searchQuery.set(authorName);
  }

  toggleAgentActive(agentId: string): void {
    this.orchestrator.toggleAgent(agentId).subscribe();
  }

  chatWithAgent(agent: AgentManifest): void {
    this.selectAgentForChat.emit(agent);
  }

  // Modals management
  openCreateModal(): void {
    this.swaggerForm = {
      spec_content: '',
      agent_name: '',
      owner_team: this.auth.currentPersona()?.user.team || 'Engineering',
      author: this.auth.getUserName(),
      author_id: this.auth.currentPersona()?.user.sub || 'user',
      icon: 'wrench',
      is_public: true,
      allowed_roles: ['*'],
      allowed_teams: ['*']
    };
    this.swaggerFormAllowedTeamsInput = '';
    this.createTab.set('swagger');
    this.showCreateModal.set(true);
  }

  closeCreateModal(): void {
    this.showCreateModal.set(false);
  }

  openAccessLimitsModal(agent: AgentManifest): void {
    this.editingAgent.set(agent);
    this.editAccessForm = {
      is_public: agent.is_public !== false,
      allowed_roles: agent.allowed_roles ? [...agent.allowed_roles] : ['*'],
      allowed_teams: agent.allowed_teams ? [...agent.allowed_teams] : ['*']
    };
    this.editTeamsInput = (agent.allowed_teams || []).filter(t => t !== '*').join(', ');
    this.showAccessModal.set(true);
  }

  closeAccessModal(): void {
    this.showAccessModal.set(false);
    this.editingAgent.set(null);
  }

  // Swagger quick samples
  loadDevOpsSwaggerSample(): void {
    this.orchestrator.getSampleSpecs().subscribe({
      next: (res) => {
        this.swaggerForm.spec_content = res.devops_sample;
        this.swaggerForm.agent_name = 'DevOps & Incident Manager';
        this.swaggerForm.owner_team = 'Engineering';
        this.swaggerForm.icon = 'wrench';
      }
    });
  }

  loadFinanceSwaggerSample(): void {
    this.orchestrator.getSampleSpecs().subscribe({
      next: (res) => {
        this.swaggerForm.spec_content = res.finance_sample;
        this.swaggerForm.agent_name = 'ERP & Vendor Payment Agent';
        this.swaggerForm.owner_team = 'Finance';
        this.swaggerForm.icon = 'cart';
      }
    });
  }

  // Role checkbox management for Swagger creation
  isRoleSelected(roleKey: string): boolean {
    return (this.swaggerForm.allowed_roles || []).includes(roleKey);
  }

  toggleRole(roleKey: string): void {
    let roles = (this.swaggerForm.allowed_roles || []).filter(r => r !== '*');
    if (roles.includes(roleKey)) {
      roles = roles.filter(r => r !== roleKey);
    } else {
      roles.push(roleKey);
    }
    this.swaggerForm.allowed_roles = roles.length > 0 ? roles : ['*'];
  }

  // Role checkbox management for Access Limits edit
  isEditRoleSelected(roleKey: string): boolean {
    return (this.editAccessForm.allowed_roles || []).includes(roleKey);
  }

  toggleEditRole(roleKey: string): void {
    let roles = (this.editAccessForm.allowed_roles || []).filter(r => r !== '*');
    if (roles.includes(roleKey)) {
      roles = roles.filter(r => r !== roleKey);
    } else {
      roles.push(roleKey);
    }
    this.editAccessForm.allowed_roles = roles.length > 0 ? roles : ['*'];
  }

  submitGenerateFromSwagger(): void {
    if (!this.swaggerForm.spec_content?.trim()) return;

    this.generating.set(true);

    const teams = this.swaggerFormAllowedTeamsInput
      ? this.swaggerFormAllowedTeamsInput.split(',').map(s => s.trim()).filter(Boolean)
      : ['*'];

    const payload = {
      spec_content: this.swaggerForm.spec_content,
      agent_name: this.swaggerForm.agent_name || undefined,
      owner_team: this.swaggerForm.owner_team || 'Engineering',
      author: this.auth.getUserName(),
      author_id: this.auth.currentPersona()?.user.sub || 'user',
      icon: this.swaggerForm.icon || 'wrench',
      is_public: this.swaggerForm.is_public,
      allowed_roles: this.swaggerForm.is_public ? ['*'] : this.swaggerForm.allowed_roles,
      allowed_teams: this.swaggerForm.is_public ? ['*'] : teams,
      auto_register: true
    };

    this.orchestrator.generateAgentFromSwagger(payload).subscribe({
      next: (res) => {
        alert(`Success! Generated agent '${res.agent.name}' with ${res.tools.length} ADK tools.`);
        this.generating.set(false);
        this.closeCreateModal();
      },
      error: (err) => {
        alert(`Generation failed: ${err.message || 'Invalid OpenAPI specification'}`);
        this.generating.set(false);
      }
    });
  }

  submitManifest(): void {
    if (!this.manifestForm.id || !this.manifestForm.name) return;

    this.generating.set(true);
    const manifest: AgentManifest = {
      id: this.manifestForm.id,
      name: this.manifestForm.name,
      owner_team: this.manifestForm.owner_team || 'General',
      author: this.auth.getUserName(),
      author_id: this.auth.currentPersona()?.user.sub || 'user',
      icon: 'bot',
      agent_type: (this.manifestForm.agent_type as any) || 'local_adk',
      remote_endpoint: this.manifestForm.remote_endpoint || null,
      description: this.manifestForm.description || '',
      system_prompt: this.manifestForm.system_prompt || '',
      allowed_tools: this.manifestToolsInput.split(',').map(s => s.trim()).filter(Boolean),
      knowledge_scopes: this.manifestScopesInput.split(',').map(s => s.trim()).filter(Boolean),
      active: true,
      is_public: true,
      allowed_roles: ['*'],
      allowed_teams: ['*']
    };

    this.orchestrator.onboardAgent(manifest).subscribe({
      next: () => {
        alert(`Agent '${manifest.name}' registered successfully!`);
        this.generating.set(false);
        this.closeCreateModal();
      },
      error: (err) => {
        alert(`Failed to onboard agent: ${err.message}`);
        this.generating.set(false);
      }
    });
  }

  saveAgentAccess(): void {
    const agent = this.editingAgent();
    if (!agent) return;

    this.savingAccess.set(true);
    const teams = this.editTeamsInput
      ? this.editTeamsInput.split(',').map(s => s.trim()).filter(Boolean)
      : ['*'];

    const accessPayload = {
      is_public: this.editAccessForm.is_public,
      allowed_roles: this.editAccessForm.is_public ? ['*'] : this.editAccessForm.allowed_roles,
      allowed_teams: this.editAccessForm.is_public ? ['*'] : teams
    };

    this.orchestrator.updateAgentAccess(agent.id, accessPayload).subscribe({
      next: () => {
        alert(`Access limits updated for '${agent.name}'.`);
        this.savingAccess.set(false);
        this.closeAccessModal();
      },
      error: (err) => {
        alert(`Failed to update access: ${err.message}`);
        this.savingAccess.set(false);
      }
    });
  }

  getIconSymbol(icon?: string, team?: string): string {
    switch (icon) {
      case 'wrench': return '🔧';
      case 'chart': return '📊';
      case 'shield': return '🛡️';
      case 'docs': return '📄';
      case 'cart': return '🛒';
      case 'user': return '👤';
      case 'bot': return '🤖';
      case 'code': return '💻';
      default:
        if (team?.toLowerCase().includes('it') || team?.toLowerCase().includes('engineer')) return '🔧';
        if (team?.toLowerCase().includes('hr') || team?.toLowerCase().includes('people')) return '👤';
        if (team?.toLowerCase().includes('finance')) return '🛒';
        return '🤖';
    }
  }

  getIconBadgeClass(icon?: string, team?: string): string {
    switch (icon) {
      case 'chart': return 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/60';
      case 'docs': return 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/60';
      case 'shield': return 'bg-sky-950/80 text-sky-400 border border-sky-800/60';
      case 'cart': return 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/60';
      case 'user': return 'bg-blue-950/80 text-blue-400 border border-blue-800/60';
      case 'wrench': return 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/60';
      default: return 'bg-indigo-950/80 text-indigo-400 border border-indigo-800/60';
    }
  }
}
