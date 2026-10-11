import { Component, signal, ViewChild, ElementRef, AfterViewChecked } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { OrchestratorService } from '../../services/orchestrator.service';
import { AuthService } from '../../services/auth.service';
import { ChatMessage, ChatResponse } from '../../models/chat.model';

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="flex-1 flex flex-col gap-4 max-w-7xl mx-auto w-full">
      <!-- Demo Prompt Chips -->
      <div class="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
        <span class="text-slate-400 whitespace-nowrap font-medium flex items-center gap-1">
          <span class="text-amber-400">✨</span> Try Demo Prompts:
        </span>
        <button 
          *ngFor="let prompt of samplePrompts" 
          (click)="fillPrompt(prompt.text)"
          [class]="prompt.cssClass + ' bg-slate-800 hover:bg-slate-700 border px-3 py-1 rounded-full whitespace-nowrap transition cursor-pointer'"
        >
          {{ prompt.label }}
        </button>
      </div>

      <!-- Chat History Box -->
      <div #scrollBox class="flex-1 bg-slate-900/60 border border-slate-800/90 rounded-2xl p-4 sm:p-6 overflow-y-auto space-y-4 max-h-[58vh] min-h-[420px]">
        <!-- Welcome Message -->
        <div class="flex items-start gap-3.5">
          <div class="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center flex-shrink-0 text-white shadow font-bold text-xs">
            AI
          </div>
          <div class="flex-1 max-w-3xl bg-slate-800/80 border border-slate-700/70 rounded-2xl p-4 text-sm text-slate-200">
            <p class="font-semibold text-white mb-1">Enterprise Router Agent Initialized</p>
            <p class="text-slate-300 leading-relaxed text-xs">
              Welcome to the Multi-Agent Orchestrator. When you submit a request, I will:
            </p>
            <ul class="list-disc list-inside mt-2 space-y-1 text-xs text-slate-400">
              <li><strong class="text-slate-200">Route Intent:</strong> Determine whether you need HR, IT Ops, Finance, or SecOps.</li>
              <li><strong class="text-slate-200">Enforce Policy (ADK Callback):</strong> Verify your JWT role claims and filter unauthorized tools.</li>
              <li><strong class="text-slate-200">Safeguard Mutations:</strong> Halt write/destructive tools until you provide explicit confirmation.</li>
              <li><strong class="text-slate-200">Datastore RAG:</strong> Retrieve documents with strict team-boundary isolation.</li>
            </ul>
          </div>
        </div>

        <!-- Rendered Chat Messages -->
        <div *ngFor="let msg of messages()" class="animate-fade-in">
          <!-- User Bubble -->
          <div *ngIf="msg.sender === 'user'" class="flex items-start justify-end gap-3">
            <div class="max-w-2xl bg-indigo-600/90 text-white rounded-2xl rounded-tr-sm px-4 py-3 text-sm shadow-md">
              <div class="flex items-center gap-1.5 mb-1 text-[11px] text-indigo-200">
                <span>👤</span>
                <span>{{ auth.getUserName() }}</span>
              </div>
              <p class="leading-relaxed">{{ msg.text }}</p>
            </div>
            <div class="w-8 h-8 rounded-lg bg-indigo-500 flex items-center justify-center flex-shrink-0 text-white text-xs font-bold">
              {{ auth.getUserName()[0] }}
            </div>
          </div>

          <!-- Orchestrator Bot Response Card -->
          <div *ngIf="msg.sender === 'orchestrator'" class="flex items-start gap-3.5 mt-2">
            <div 
              class="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 text-white text-xs font-bold shadow"
              [ngClass]="msg.response?.action_taken === 'POLICY_DENIED' || msg.response?.action_taken === 'POLICY_BLOCKED' ? 'bg-rose-600' : 'bg-indigo-600'"
            >
              {{ msg.response?.action_taken === 'POLICY_DENIED' ? '⛔' : 'AI' }}
            </div>

            <div 
              class="flex-1 max-w-3xl border rounded-2xl rounded-tl-sm p-4 text-sm text-slate-200"
              [ngClass]="msg.response?.action_taken === 'POLICY_DENIED' || msg.response?.action_taken === 'POLICY_BLOCKED' ? 'border-rose-700/80 bg-rose-950/20' : 'border-slate-700/70 bg-slate-800/80'"
            >
              <!-- Telemetry Badges -->
              <div class="flex flex-wrap items-center gap-1.5 mb-2.5" *ngIf="msg.response as res">
                <!-- Selected Agent -->
                <span *ngIf="res.routing?.selected_agent_id" class="inline-flex items-center gap-1 bg-indigo-950/80 text-indigo-300 border border-indigo-800/60 px-2 py-0.5 rounded-full text-[10px]">
                  <span>🤖</span>
                  {{ res.agent_info?.name || res.routing.selected_agent_id }} ({{ (res.routing.confidence * 100).toFixed(0) }}%)
                </span>

                <!-- Intent -->
                <span *ngIf="res.routing?.intent" [class]="getIntentBadgeClass(res.routing.intent) + ' border px-2 py-0.5 rounded-full text-[10px]'">
                  <span>⚡</span>
                  Intent: {{ res.routing.intent }}
                </span>

                <!-- Trace ID -->
                <span *ngIf="res.trace_id" class="inline-flex items-center gap-1 bg-slate-900 text-slate-400 border border-slate-800 px-2 py-0.5 rounded-full text-[10px] font-mono">
                  Trace: {{ res.trace_id.slice(0, 8) }}
                </span>
              </div>

              <!-- Message Text / Formatted Markdown -->
              <div class="leading-relaxed text-slate-200 text-xs sm:text-sm whitespace-pre-line">
                {{ msg.text }}
              </div>

              <!-- Write Confirmation Card -->
              <div *ngIf="msg.response?.pending_confirmation as conf" class="mt-3 p-3.5 rounded-xl bg-amber-950/40 border border-amber-600/50 text-amber-200">
                <div class="flex items-center gap-2 font-semibold text-xs mb-1">
                  <span>⚠️</span>
                  Human Write Confirmation Required
                </div>
                <p class="text-xs text-amber-300/90 mb-2">
                  Executing this tool mutates production state. Under the ADK security policy, human authorization is required.
                </p>
                <div class="bg-slate-950/70 p-2.5 rounded-lg border border-slate-800 font-mono text-[11px] mb-3 text-slate-300">
                  <strong>Tool:</strong> {{ conf.tool_name }}<br>
                  <strong>Parameters:</strong> {{ conf.parameters | json }}
                </div>
                <div class="flex gap-2">
                  <button 
                    (click)="confirmWriteAction(conf.confirmation_id, 'approve')" 
                    class="bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs px-3.5 py-1.5 rounded-lg flex items-center gap-1.5 transition cursor-pointer"
                  >
                    <span>✓</span> Approve & Execute
                  </button>
                  <button 
                    (click)="confirmWriteAction(conf.confirmation_id, 'reject')" 
                    class="bg-rose-900/60 hover:bg-rose-900 text-rose-300 text-xs px-3 py-1.5 rounded-lg border border-rose-800 flex items-center gap-1.5 transition cursor-pointer"
                  >
                    <span>✕</span> Reject
                  </button>
                </div>
              </div>

              <!-- Gateway Context Footer -->
              <div *ngIf="msg.response?.gateway_context as gw" class="mt-2 pt-2 border-t border-slate-700/60 flex items-center justify-between text-[11px] text-slate-400">
                <span class="flex items-center gap-1">
                  <span class="text-emerald-400">🔒</span>
                  Gateway SA: <code class="text-slate-300 font-mono text-[10px]">{{ gw.service_account }}</code>
                </span>
                <span>{{ msg.response?.duration_ms || 0 }}ms</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Typing Indicator -->
        <div *ngIf="loading()" class="flex items-start gap-3.5 animate-fade-in">
          <div class="w-8 h-8 rounded-lg bg-indigo-600/80 flex items-center justify-center flex-shrink-0 text-white animate-pulse text-xs font-bold">
            ...
          </div>
          <div class="bg-slate-800/80 border border-slate-700/60 rounded-2xl px-4 py-3 text-xs text-slate-400 flex items-center gap-2">
            <span class="inline-block w-2 h-2 rounded-full bg-indigo-400 animate-ping"></span>
            <span>Gemini Router analyzing prompt & checking ADK policies...</span>
          </div>
        </div>
      </div>

      <!-- Chat Input Form -->
      <form (submit)="sendMessage()" class="flex items-center gap-2 bg-slate-900 border border-slate-800 p-2 rounded-2xl shadow-xl focus-within:border-indigo-500 transition">
        <input 
          [(ngModel)]="currentPrompt"
          name="prompt"
          type="text" 
          placeholder="Ask a question, query Jira, request PTO, restart a service, or audit security..." 
          class="flex-1 bg-transparent px-4 py-2 text-sm text-white placeholder-slate-500 focus:outline-none"
          autocomplete="off"
        />
        <button 
          type="submit" 
          [disabled]="loading() || !currentPrompt.trim()"
          class="bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-xl font-medium text-sm flex items-center gap-2 shadow-lg shadow-indigo-600/20 transition disabled:opacity-50 cursor-pointer"
        >
          <span>Send</span>
          <span>&rarr;</span>
        </button>
      </form>
    </div>
  `
})
export class ChatComponent implements AfterViewChecked {
  @ViewChild('scrollBox') private scrollBox!: ElementRef;

  currentPrompt = '';
  loading = signal(false);
  messages = signal<ChatMessage[]>([]);

  samplePrompts = [
    { label: 'PTO & Leave Policy (HR RAG)', text: 'What is our 2026 PTO and leave policy?', cssClass: 'text-slate-300 border-slate-700/60' },
    { label: 'Jira PROJ-102 (IT Read)', text: 'Check status of Jira ticket PROJ-102', cssClass: 'text-slate-300 border-slate-700/60' },
    { label: 'Restart Service (IT Write)', text: 'Restart payments-api in cloud cluster', cssClass: 'text-amber-300 border-amber-800/60' },
    { label: 'Expense EXP-2026-88 (Finance)', text: 'Check status of expense report EXP-2026-88', cssClass: 'text-slate-300 border-slate-700/60' },
    { label: 'Security VPC Audit (A2A Remote)', text: 'Audit VPC security posture (Remote A2A)', cssClass: 'text-sky-300 border-sky-800/60' }
  ];

  constructor(
    public orchestrator: OrchestratorService,
    public auth: AuthService
  ) {}

  ngAfterViewChecked(): void {
    this.scrollToBottom();
  }

  scrollToBottom(): void {
    if (this.scrollBox) {
      this.scrollBox.nativeElement.scrollTop = this.scrollBox.nativeElement.scrollHeight;
    }
  }

  fillPrompt(text: string): void {
    this.currentPrompt = text;
  }

  sendMessage(): void {
    const text = this.currentPrompt.trim();
    if (!text) return;

    this.currentPrompt = '';
    const userMsg: ChatMessage = {
      id: Math.random().toString(),
      sender: 'user',
      text,
      timestamp: new Date()
    };
    this.messages.update(m => [...m, userMsg]);
    this.loading.set(true);

    this.orchestrator.sendChat(text).subscribe({
      next: (res) => {
        const botMsg: ChatMessage = {
          id: Math.random().toString(),
          sender: 'orchestrator',
          text: res.reply,
          timestamp: new Date(),
          response: res
        };
        this.messages.update(m => [...m, botMsg]);
        this.loading.set(false);
      },
      error: (err) => {
        const botMsg: ChatMessage = {
          id: Math.random().toString(),
          sender: 'orchestrator',
          text: `Error connecting to backend: ${err.message || err.statusText}`,
          timestamp: new Date()
        };
        this.messages.update(m => [...m, botMsg]);
        this.loading.set(false);
      }
    });
  }

  confirmWriteAction(confirmationId: string, action: 'approve' | 'reject'): void {
    this.orchestrator.confirmAction(confirmationId, action).subscribe({
      next: (res) => {
        const botMsg: ChatMessage = {
          id: Math.random().toString(),
          sender: 'orchestrator',
          text: res.reply,
          timestamp: new Date(),
          response: res
        };
        this.messages.update(m => [...m, botMsg]);
      },
      error: (err) => console.error(err)
    });
  }

  getIntentBadgeClass(intent: string): string {
    return intent === 'tool_call' 
      ? 'bg-amber-950/80 text-amber-300 border-amber-800/60'
      : 'bg-sky-950/80 text-sky-300 border-sky-800/60';
  }
}
