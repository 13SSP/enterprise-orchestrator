import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

interface ChatMessage {
  sender: 'user' | 'cortex';
  text: string;
  timestamp: string;
  handledBy?: {
    agent: string;
    tool?: string;
    reasoning?: string;
    model?: string;
  };
  status?: string;
  downloadCard?: {
    fileName: string;
    fileType: string;
    downloadUrl: string;
    slideCount?: number;
    title: string;
  };
  emailDraft?: {
    draftId: string;
    recipientEmail: string;
    subject: string;
    body: string;
  };
  pendingApproval?: {
    confirmationId: string;
    actionType: string;
    summary: string;
    toolName: string;
  };
}

interface PromptItem {
  id: string;
  category: string;
  title: string;
  description: string;
  prompt: string;
  recommended_persona: string;
  persona_name: string;
  target_agent: string;
  tags: string[];
  hackathon_highlight: string;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="flex h-screen bg-slate-950 text-slate-100 overflow-hidden font-sans">
      <!-- Sidebar Navigation -->
      <aside class="w-64 bg-slate-900 border-r border-slate-800 flex flex-col justify-between p-4">
        <div>
          <!-- Logo & Brand -->
          <div class="flex items-center gap-3 px-2 py-3 mb-6">
            <div class="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-cyan-400 flex items-center justify-center font-bold text-lg shadow-lg shadow-blue-500/20">
              ⚡
            </div>
            <div>
              <h1 class="font-bold text-lg tracking-tight bg-gradient-to-r from-blue-400 to-indigo-200 bg-clip-text text-transparent">cortex.ai</h1>
              <p class="text-[10px] text-slate-400 font-mono">Google Cloud & Firebase</p>
            </div>
          </div>

          <!-- Persona / Identity Switcher -->
          <div class="mb-6 p-3 rounded-xl bg-slate-800/60 border border-slate-700/60">
            <label class="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block mb-2">Firebase User Identity</label>
            <select [(ngModel)]="currentPersona" class="w-full bg-slate-900 border border-slate-700 rounded-lg text-xs p-2 text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option value="bob_ops">Bob Martinez (DevOps Admin)</option>
              <option value="alice_hr">Alice Henderson (HR Manager)</option>
              <option value="charlie_fin">Charlie Zhao (Finance Officer)</option>
              <option value="dave_contractor">Dave Miller (Restricted Contractor)</option>
            </select>
          </div>

          <!-- Navigation Links -->
          <nav class="space-y-1">
            <button (click)="activeTab = 'chat'" [class.bg-blue-600]="activeTab === 'chat'" [class.text-white]="activeTab === 'chat'" [class.text-slate-400]="activeTab !== 'chat'" class="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition hover:bg-slate-800">
              💬 <span>Chat Assistant</span>
            </button>
            <button (click)="activeTab = 'prompts'; loadPrompts()" [class.bg-blue-600]="activeTab === 'prompts'" [class.text-white]="activeTab === 'prompts'" [class.text-slate-400]="activeTab !== 'prompts'" class="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition hover:bg-slate-800">
              📚 <span>Prompt Library ({{ promptsList.length || 18 }})</span>
            </button>
            <button (click)="activeTab = 'agents'; loadAgents()" [class.bg-blue-600]="activeTab === 'agents'" [class.text-white]="activeTab === 'agents'" [class.text-slate-400]="activeTab !== 'agents'" class="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition hover:bg-slate-800">
              🤖 <span>Team Agents (5)</span>
            </button>
            <button (click)="activeTab = 'tools'; loadTools()" [class.bg-blue-600]="activeTab === 'tools'" [class.text-white]="activeTab === 'tools'" [class.text-slate-400]="activeTab !== 'tools'" class="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition hover:bg-slate-800">
              🛠️ <span>Tool Catalog (25)</span>
            </button>
            <button (click)="activeTab = 'models'; loadModels()" [class.bg-blue-600]="activeTab === 'models'" [class.text-white]="activeTab === 'models'" [class.text-slate-400]="activeTab !== 'models'" class="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition hover:bg-slate-800">
              🧠 <span>Model Gateway</span>
            </button>
            <button (click)="activeTab = 'audit'; loadAudit()" [class.bg-blue-600]="activeTab === 'audit'" [class.text-white]="activeTab === 'audit'" [class.text-slate-400]="activeTab !== 'audit'" class="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition hover:bg-slate-800">
              📜 <span>Cloud Audit Trail</span>
            </button>
          </nav>
        </div>

        <!-- System Footer -->
        <div class="pt-4 border-t border-slate-800 text-[11px] text-slate-500 font-mono space-y-1">
          <div class="flex items-center gap-2">
            <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span>Firestore: Native (:8080)</span>
          </div>
          <div>Cortex Gateway: :8000</div>
        </div>
      </aside>

      <!-- Main Workspace -->
      <main class="flex-1 flex flex-col h-full bg-slate-950 overflow-hidden">
        <!-- Top Status Bar -->
        <header class="h-14 border-b border-slate-800 px-6 flex items-center justify-between bg-slate-900/40">
          <div class="flex items-center gap-3">
            <h2 class="text-sm font-semibold capitalize text-slate-200">{{ activeTab === 'prompts' ? 'Prompt Library' : activeTab }} Workspace</h2>
            <span class="px-2 py-0.5 text-[10px] rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20 font-mono">
              Role: {{ getPersonaRole() }}
            </span>
          </div>
          <div class="flex items-center gap-4 text-xs text-slate-400">
            <span>Model Armor: <strong class="text-emerald-400">Active</strong></span>
            <span>Zero-Trust RBAC: <strong class="text-emerald-400">Enforced</strong></span>
          </div>
        </header>

        <!-- Dynamic Content Tabs -->
        <div class="flex-1 overflow-y-auto p-6">
          <!-- 1. CHAT WORKSPACE -->
          <div *ngIf="activeTab === 'chat'" class="h-full flex flex-col justify-between max-w-4xl mx-auto">
            <!-- Messages Container -->
            <div class="flex-1 overflow-y-auto space-y-4 mb-4 pr-2">
              <div *ngFor="let msg of messages" [class.justify-end]="msg.sender === 'user'" class="flex gap-3">
                <div *ngIf="msg.sender === 'cortex'" class="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center font-bold text-sm shrink-0">
                  ⚡
                </div>
                <div [class.bg-blue-600]="msg.sender === 'user'" [class.bg-slate-900]="msg.sender === 'cortex'" [class.border-slate-800]="msg.sender === 'cortex'" class="border p-4 rounded-2xl max-w-2xl text-sm shadow-sm space-y-3">
                  <div class="whitespace-pre-wrap leading-relaxed">{{ msg.text }}</div>

                  <!-- Handled-by Badge -->
                  <div *ngIf="msg.handledBy" class="pt-2 border-t border-slate-800 flex flex-wrap items-center gap-2 text-[11px] font-mono text-slate-400">
                    <span class="px-2 py-0.5 rounded bg-slate-800 text-blue-400 border border-slate-700">Handled by: {{ msg.handledBy.agent }}</span>
                    <span *ngIf="msg.handledBy.tool" class="px-2 py-0.5 rounded bg-slate-800 text-cyan-400 border border-slate-700">Tool: {{ msg.handledBy.tool }}</span>
                    <span class="px-2 py-0.5 rounded bg-slate-800 text-amber-400 border border-slate-700">Model: {{ msg.handledBy.model || 'Gemini' }}</span>
                  </div>

                  <!-- PowerPoint / Word Download Card -->
                  <div *ngIf="msg.downloadCard" class="p-3 rounded-xl bg-slate-800/80 border border-slate-700 flex items-center justify-between">
                    <div class="flex items-center gap-3">
                      <span class="text-2xl">{{ msg.downloadCard.fileType === 'pptx' ? '📊' : '📝' }}</span>
                      <div>
                        <div class="font-semibold text-xs text-slate-200">{{ msg.downloadCard.title }}</div>
                        <div class="text-[11px] text-slate-400 font-mono">{{ msg.downloadCard.fileName }} ({{ msg.downloadCard.slideCount || 1 }} slides/sections)</div>
                      </div>
                    </div>
                    <a [href]="'http://127.0.0.1:8005' + msg.downloadCard.downloadUrl" target="_blank" class="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-xs font-semibold text-white transition flex items-center gap-1.5">
                      ⬇️ Download
                    </a>
                  </div>

                  <!-- Email Draft Card -->
                  <div *ngIf="msg.emailDraft" class="p-3 rounded-xl bg-indigo-950/40 border border-indigo-800/60 text-xs space-y-1">
                    <div class="text-indigo-400 font-semibold flex items-center gap-1.5">✉️ Outlook Draft Ready:</div>
                    <div class="text-slate-300"><strong>To:</strong> {{ msg.emailDraft.recipientEmail }}</div>
                    <div class="text-slate-300"><strong>Subject:</strong> {{ msg.emailDraft.subject }}</div>
                  </div>

                  <!-- Human-in-the-Loop Approval Action Card -->
                  <div *ngIf="msg.pendingApproval" class="p-4 rounded-xl bg-amber-950/30 border border-amber-600/40 space-y-3">
                    <div class="flex items-center gap-2 text-amber-400 text-xs font-semibold">
                      <span>⚠️ Sensitive Action Pending User Confirmation</span>
                    </div>
                    <div class="text-xs text-slate-300">{{ msg.pendingApproval.summary }}</div>
                    <div class="flex items-center gap-2 pt-1">
                      <button (click)="confirmAction(msg.pendingApproval.confirmationId, 'approve')" class="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs transition">
                        ✓ Approve & Execute
                      </button>
                      <button (click)="confirmAction(msg.pendingApproval.confirmationId, 'reject')" class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs border border-slate-700 transition">
                        ✕ Reject
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <!-- Prompt Input -->
            <form (submit)="submitPrompt($event)" class="relative mt-2 flex items-center">
              <input type="text" [(ngModel)]="currentInput" name="prompt" placeholder="Ask cortex.ai anything across HR, IT, Finance, Operations, or Office documents..." class="w-full bg-slate-900 border border-slate-800 rounded-2xl py-3.5 pl-4 pr-64 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-inner" />
              <div class="absolute right-2 top-2 bottom-2 flex items-center gap-2">
                <select [(ngModel)]="selectedModel" name="selectedModel" class="bg-slate-800/90 hover:bg-slate-800 border border-slate-700/80 text-xs font-medium text-slate-200 rounded-xl px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500 shadow-sm cursor-pointer transition">
                  <option *ngFor="let m of modelsList" [value]="m.id" [disabled]="!m.available">
                    {{ m.name }}{{ m.available ? '' : ' (No API Key)' }}
                  </option>
                </select>
                <button type="submit" [disabled]="loading" class="w-9 h-9 rounded-xl bg-blue-600 hover:bg-blue-500 flex items-center justify-center text-white disabled:opacity-50 shadow-md shadow-blue-600/30 transition">
                  ➤
                </button>
              </div>
            </form>
          </div>

          <!-- 2. AGENTS REGISTRY VIEW -->
          <div *ngIf="activeTab === 'agents'" class="max-w-4xl mx-auto space-y-4">
            <h3 class="text-base font-bold text-slate-200">Onboarded Team Agents</h3>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div *ngFor="let a of agentsList" class="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                <div class="flex items-center justify-between">
                  <div class="font-bold text-sm text-blue-400">{{ a.name }}</div>
                  <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Active</span>
                </div>
                <div class="text-xs text-slate-400">{{ a.description }}</div>
                <div class="text-[11px] font-mono text-slate-500 pt-2 border-t border-slate-800/80">
                  <div>Team: <span class="text-slate-300">{{ a.owner_team }}</span></div>
                  <div>Model: <span class="text-indigo-400">{{ a.preferred_model }}</span></div>
                  <div>Tools: <span class="text-cyan-400">{{ a.allowed_tools.length }} permitted</span></div>
                </div>
              </div>
            </div>
          </div>

          <!-- 3. TOOLS CATALOG VIEW -->
          <div *ngIf="activeTab === 'tools'" class="max-w-5xl mx-auto space-y-4">
            <h3 class="text-base font-bold text-slate-200">Dynamically Generated ADK Tools</h3>
            <div class="overflow-x-auto rounded-xl border border-slate-800">
              <table class="w-full text-left text-xs font-mono">
                <thead class="bg-slate-900 text-slate-400 border-b border-slate-800">
                  <tr>
                    <th class="p-3">Tool Name</th>
                    <th class="p-3">Method</th>
                    <th class="p-3">Service</th>
                    <th class="p-3">Path</th>
                    <th class="p-3">Approval Gate</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-800/60 bg-slate-950">
                  <tr *ngFor="let t of toolsList" class="hover:bg-slate-900/40">
                    <td class="p-3 text-cyan-400 font-semibold">{{ t.name }}</td>
                    <td class="p-3"><span [class.text-emerald-400]="t.method === 'GET'" [class.text-amber-400]="t.method === 'POST'" [class.text-blue-400]="t.method === 'PATCH'">{{ t.method }}</span></td>
                    <td class="p-3 text-slate-300">{{ t.service }}</td>
                    <td class="p-3 text-slate-400">{{ t.path }}</td>
                    <td class="p-3">{{ t.requires_human_approval ? '⚠️ Required' : '✓ Direct' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- 4. MODEL GATEWAY VIEW -->
          <div *ngIf="activeTab === 'models'" class="max-w-4xl mx-auto space-y-4">
            <h3 class="text-base font-bold text-slate-200">Active Multi-Model Providers</h3>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div *ngFor="let m of modelsList" class="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                <div class="flex items-center justify-between">
                  <div class="text-sm font-bold text-slate-200">{{ m.name }}</div>
                  <span *ngIf="m.available" class="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Active / Live</span>
                  <span *ngIf="!m.available" class="text-[10px] font-mono px-2 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20">{{ m.disabled_reason || 'No API Key' }}</span>
                </div>
                <div class="text-xs text-slate-400">Provider: {{ m.provider }} | Family: {{ m.family }}</div>
                <div class="text-[11px] font-mono text-slate-500">Model ID: <code class="text-indigo-400">{{ m.id }}</code></div>
              </div>
            </div>
          </div>

          <!-- 5. AUDIT TRAIL VIEW -->
          <div *ngIf="activeTab === 'audit'" class="max-w-5xl mx-auto space-y-4">
            <h3 class="text-base font-bold text-slate-200">Google Cloud Logging & Trace Audit Log</h3>
            <div class="space-y-2">
              <div *ngFor="let ev of auditList" class="p-3 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono space-y-1">
                <div class="flex items-center justify-between text-slate-400">
                  <span class="text-blue-400 font-bold">[{{ ev.event_type }}]</span>
                  <span>{{ ev.timestamp }}</span>
                </div>
                <div class="text-slate-300">User: {{ ev.user }} | Severity: {{ ev.severity }}</div>
                <div class="text-slate-500 text-[11px]">{{ ev.details | json }}</div>
              </div>
            </div>
          </div>

          <!-- 6. PROMPT LIBRARY VIEW -->
          <div *ngIf="activeTab === 'prompts'" class="max-w-6xl mx-auto space-y-5">
            <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <h3 class="text-lg font-bold text-slate-100">Enterprise Prompt Library</h3>
                <p class="text-xs text-slate-400">Curated, domain-specific templates designed for zero-prompt-engineering workflows across IT, HR, Finance, Operations, M365, and Security.</p>
              </div>
              <div class="w-full md:w-72">
                <input type="text" [(ngModel)]="promptSearchQuery" placeholder="🔍 Search prompts, tags, agents..." class="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
            </div>

            <!-- Category Filter Pills -->
            <div class="flex flex-wrap gap-2 pt-1 border-b border-slate-800/80 pb-3">
              <button *ngFor="let cat of promptCategories" (click)="selectedPromptCategory = cat" [class.bg-blue-600]="selectedPromptCategory === cat" [class.text-white]="selectedPromptCategory === cat" [class.bg-slate-900]="selectedPromptCategory !== cat" [class.text-slate-400]="selectedPromptCategory !== cat" class="px-3 py-1.5 rounded-lg text-xs font-medium transition border border-slate-800 hover:text-slate-200">
                {{ cat }}
              </button>
            </div>

            <!-- Prompts Grid -->
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-4">
              <div *ngFor="let p of filteredPrompts" class="p-5 rounded-2xl bg-slate-900 border border-slate-800 hover:border-slate-700/80 transition flex flex-col justify-between space-y-4 shadow-sm">
                <div class="space-y-3">
                  <div class="flex items-center justify-between gap-2">
                    <span class="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">{{ p.category }}</span>
                    <span class="text-[11px] font-mono text-cyan-400">🤖 {{ p.target_agent }}</span>
                  </div>
                  <div>
                    <h4 class="font-bold text-sm text-slate-100">{{ p.title }}</h4>
                    <p class="text-xs text-slate-400 mt-1 leading-relaxed">{{ p.description }}</p>
                  </div>
                  <div class="bg-slate-950 p-3 rounded-xl border border-slate-800/90 text-xs font-mono text-slate-200 select-all leading-relaxed">
                    "{{ p.prompt }}"
                  </div>
                  <div class="p-2.5 rounded-lg bg-amber-950/20 border border-amber-900/30 text-[11px] text-amber-300/90 space-y-1">
                    <div class="font-semibold flex items-center gap-1.5">💡 Hackathon Demo Note:</div>
                    <div class="text-amber-400/80 leading-normal">{{ p.hackathon_highlight }}</div>
                  </div>
                  <div class="flex items-center justify-between text-[11px] text-slate-500 font-mono pt-1">
                    <span>👤 Recommended: <strong class="text-slate-300">{{ p.persona_name }}</strong></span>
                  </div>
                  <div class="flex flex-wrap gap-1.5 pt-1">
                    <span *ngFor="let tag of p.tags" class="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-400 border border-slate-700/60">{{ tag }}</span>
                  </div>
                </div>
                <div class="pt-3 border-t border-slate-800/80 flex items-center justify-between gap-2">
                  <button (click)="copyPrompt(p.prompt, $event)" class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700 transition flex items-center gap-1.5">
                    📋 Copy Prompt
                  </button>
                  <button (click)="tryPromptInChat(p)" class="px-3.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-sm transition flex items-center gap-1.5">
                    🚀 Try in Chat
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  `
})
export class AppComponent implements OnInit {
  activeTab: 'chat' | 'prompts' | 'agents' | 'tools' | 'models' | 'audit' = 'chat';
  currentPersona: string = 'bob_ops';
  currentInput: string = '';
  loading: boolean = false;

  promptsList: PromptItem[] = [];
  promptCategories: string[] = ['All'];
  selectedPromptCategory: string = 'All';
  promptSearchQuery: string = '';

  get filteredPrompts(): PromptItem[] {
    const cat = this.selectedPromptCategory;
    const q = this.promptSearchQuery.toLowerCase().trim();
    return this.promptsList.filter(p => {
      const matchesCat = (cat === 'All' || p.category === cat);
      const matchesQuery = !q ||
        p.title.toLowerCase().includes(q) ||
        p.description.toLowerCase().includes(q) ||
        p.prompt.toLowerCase().includes(q) ||
        p.target_agent.toLowerCase().includes(q) ||
        (p.tags && p.tags.some(t => t.toLowerCase().includes(q)));
      return matchesCat && matchesQuery;
    });
  }

  messages: ChatMessage[] = [
    {
      sender: 'cortex',
      text: "👋 Welcome to **cortex.ai**! I am your enterprise orchestration hub. I connect you to HR, IT Support, Finance, Cloud Ops, and Microsoft 365 document creation.",
      timestamp: new Date().toLocaleTimeString()
    }
  ];

  agentsList: any[] = [];
  toolsList: any[] = [];
  auditList: any[] = [];
  selectedModel: string = 'google/gemini-3.8-flash';
  modelsList: any[] = [
    { id: 'google/gemini-3.8-flash', name: 'Gemini 3.8 Flash', provider: 'Google', family: 'gemini', available: true },
    { id: 'google/gemini-1.5-pro', name: 'Gemini 1.5 Pro', provider: 'Google', family: 'gemini', available: true },
    { id: 'anthropic/claude-3-5-sonnet', name: 'Claude 3.5 Sonnet', provider: 'Anthropic', family: 'claude', available: false, disabled_reason: 'Missing ANTHROPIC_API_KEY in .env' },
    { id: 'anthropic/claude-3-opus', name: 'Claude 3 Opus', provider: 'Anthropic', family: 'claude', available: false, disabled_reason: 'Missing ANTHROPIC_API_KEY in .env' }
  ];

  ngOnInit() {
    this.loadPrompts();
    this.loadAgents();
    this.loadModels();
  }

  getPersonaRole(): string {
    const map: Record<string, string> = {
      bob_ops: 'DevOps Admin',
      alice_hr: 'HR Manager',
      charlie_fin: 'Finance Officer',
      dave_contractor: 'Contractor'
    };
    return map[this.currentPersona] || 'Employee';
  }

  async submitPrompt(event?: Event) {
    if (event) event.preventDefault();
    if (!this.currentInput.trim() || this.loading) return;

    const userText = this.currentInput;
    this.currentInput = '';
    this.messages.push({
      sender: 'user',
      text: userText,
      timestamp: new Date().toLocaleTimeString()
    });

    this.loading = true;
    try {
      const res = await fetch('http://127.0.0.1:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: userText,
          persona: this.currentPersona,
          model: this.selectedModel
        })
      });
      const data = await res.json();
      this.messages.push({
        sender: 'cortex',
        text: data.reply,
        timestamp: new Date().toLocaleTimeString(),
        handledBy: data.handled_by,
        downloadCard: data.download_card,
        emailDraft: data.email_draft,
        pendingApproval: data.pending_approval
      });
    } catch (err) {
      this.messages.push({
        sender: 'cortex',
        text: '⚠️ Network or server error connecting to cortex.ai backend hub (:8000).',
        timestamp: new Date().toLocaleTimeString()
      });
    } finally {
      this.loading = false;
    }
  }

  async confirmAction(confirmationId: string, action: 'approve' | 'reject') {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/chat/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          confirmation_id: confirmationId,
          action: action,
          persona: this.currentPersona
        })
      });
      const data = await res.json();
      this.messages.push({
        sender: 'cortex',
        text: `✅ **Action ${action === 'approve' ? 'Approved & Executed' : 'Rejected'}**:\n\n${data.message}`,
        timestamp: new Date().toLocaleTimeString()
      });
    } catch (err) {
      alert('Error resolving confirmation.');
    }
  }

  async loadAgents() {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/agents');
      const data = await res.json();
      this.agentsList = data.agents || [];
    } catch (e) {}
  }

  async loadTools() {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/tools');
      const data = await res.json();
      this.toolsList = data.tools || [];
    } catch (e) {}
  }

  async loadModels() {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/models');
      const data = await res.json();
      if (data.models && data.models.length > 0) {
        this.modelsList = data.models;
        if (data.default_model) {
          this.selectedModel = data.default_model;
        }
      }
    } catch (e) {}
  }

  async loadAudit() {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/audit');
      const data = await res.json();
      this.auditList = data.events || [];
    } catch (e) {}
  }

  async loadPrompts() {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/prompts');
      const data = await res.json();
      this.promptsList = data.prompts || [];
      this.promptCategories = data.categories || ['All'];
    } catch (e) {}
  }

  copyPrompt(text: string, event: Event) {
    const btn = event.currentTarget as HTMLElement;
    navigator.clipboard.writeText(text).then(() => {
      const orig = btn.innerText;
      btn.innerText = '✓ Copied!';
      btn.classList.add('bg-emerald-600', 'text-white');
      setTimeout(() => {
        btn.innerText = orig;
        btn.classList.remove('bg-emerald-600', 'text-white');
      }, 2000);
    });
  }

  tryPromptInChat(p: PromptItem) {
    if (p.recommended_persona) {
      this.currentPersona = p.recommended_persona;
    }
    this.activeTab = 'chat';
    this.currentInput = p.prompt;
    this.submitPrompt();
  }
}
