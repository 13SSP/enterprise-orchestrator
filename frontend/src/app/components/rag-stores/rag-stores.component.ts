import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RagService } from '../../services/rag.service';

@Component({
  selector: 'app-rag-stores',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 max-w-7xl mx-auto w-full">
      <!-- Ingestion Form -->
      <div class="lg:col-span-4 bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-4">
        <h2 class="text-lg font-bold text-white flex items-center gap-2">
          <span class="text-indigo-400">📄</span>
          Ingest Document (RAG)
        </h2>
        <p class="text-xs text-slate-400">
          Simulates Document AI PDF ingestion into isolated Vertex AI Search team datastores.
        </p>

        <form (submit)="uploadDoc()" class="space-y-3 text-xs">
          <div>
            <label class="block font-semibold text-slate-300 mb-1">Document Title</label>
            <input 
              [(ngModel)]="title" 
              name="title" 
              type="text" 
              required 
              placeholder="e.g. Remote Work Security Guidelines" 
              class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none"
            />
          </div>

          <div>
            <label class="block font-semibold text-slate-300 mb-1">Datastore Scope</label>
            <input 
              [(ngModel)]="scope" 
              name="scope" 
              type="text" 
              required 
              placeholder="e.g. hr_policies, it_runbooks" 
              class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none"
            />
          </div>

          <div>
            <label class="block font-semibold text-slate-300 mb-1">Document Content</label>
            <textarea 
              [(ngModel)]="content" 
              name="content" 
              rows="6" 
              required 
              placeholder="Text or policy guidelines..." 
              class="w-full bg-slate-800 border border-slate-700 rounded-lg p-3 text-white focus:outline-none"
            ></textarea>
          </div>

          <button 
            type="submit" 
            [disabled]="uploading() || !title.trim() || !content.trim()"
            class="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-2.5 rounded-xl shadow-lg transition cursor-pointer disabled:opacity-50"
          >
            {{ uploading() ? 'Ingesting...' : 'Ingest Document' }}
          </button>
        </form>
      </div>

      <!-- Datastore Explorer -->
      <div class="lg:col-span-8 bg-slate-900/80 border border-slate-800 rounded-2xl p-6 flex flex-col">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-lg font-bold text-white flex items-center gap-2">
            <span class="text-sky-400">🗄️</span>
            Team-Isolated Knowledge Stores
          </h2>
          <div class="flex gap-1.5 flex-wrap">
            <button 
              (click)="filterScope(null)" 
              [class]="(selectedScope() === null ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-400') + ' text-xs px-2.5 py-1 rounded-full cursor-pointer'"
            >
              All Scopes
            </button>
            <button 
              *ngFor="let s of rag.scopes()" 
              (click)="filterScope(s)" 
              [class]="(selectedScope() === s ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-400') + ' text-xs px-2.5 py-1 rounded-full cursor-pointer'"
            >
              {{ s }}
            </button>
          </div>
        </div>

        <div class="space-y-3 overflow-y-auto max-h-[500px] flex-1 pr-1">
          <div 
            *ngFor="let doc of filteredDocs()" 
            class="p-4 rounded-xl bg-slate-800/70 border border-slate-700/80 text-xs space-y-2 hover:border-slate-600 transition"
          >
            <div class="flex items-center justify-between">
              <span class="font-bold text-white text-sm flex items-center gap-2">
                <span>📄</span>
                {{ doc.title }}
              </span>
              <span class="bg-indigo-950 text-indigo-300 border border-indigo-800 px-2.5 py-0.5 rounded-full text-[10px] font-mono">
                Scope: {{ doc.scope }}
              </span>
            </div>

            <p class="text-slate-300 leading-relaxed font-sans text-xs bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/80 whitespace-pre-line">
              {{ doc.content }}
            </p>

            <div class="flex items-center justify-between text-[10px] text-slate-400">
              <span>Ingest Method: <strong class="text-slate-300">{{ doc.source_type }}</strong></span>
              <span>Team: <strong class="text-slate-300">{{ doc.author_team }}</strong></span>
            </div>
          </div>
        </div>
      </div>
    </div>
  `
})
export class RagStoresComponent {
  title = '';
  scope = '';
  content = '';
  uploading = signal(false);
  selectedScope = signal<string | null>(null);

  constructor(public rag: RagService) {}

  filterScope(s: string | null): void {
    this.selectedScope.set(s);
  }

  filteredDocs() {
    const s = this.selectedScope();
    if (!s) return this.rag.documents();
    return this.rag.documents().filter(d => d.scope === s);
  }

  uploadDoc(): void {
    if (!this.title.trim() || !this.content.trim()) return;

    this.uploading.set(true);
    this.rag.uploadDocument({
      title: this.title,
      scope: this.scope || 'general',
      content: this.content,
      source_type: 'document_ai_pdf'
    }).subscribe({
      next: () => {
        alert(`Document '${this.title}' ingested into scope '${this.scope}'!`);
        this.title = '';
        this.scope = '';
        this.content = '';
        this.uploading.set(false);
      },
      error: (err) => {
        alert(`Ingest error: ${err.message}`);
        this.uploading.set(false);
      }
    });
  }
}
