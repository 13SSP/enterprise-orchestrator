import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { KnowledgeDocument } from '../models/rag.model';

@Injectable({
  providedIn: 'root'
})
export class RagService {
  private apiUrl = '/api/knowledge';

  documents = signal<KnowledgeDocument[]>([]);
  scopes = signal<string[]>([]);

  constructor(private http: HttpClient) {
    this.refreshAll();
  }

  refreshAll(): void {
    this.getDocuments().subscribe(res => this.documents.set(res.documents || []));
    this.getScopes().subscribe(res => this.scopes.set(res.scopes || []));
  }

  getDocuments(scope?: string): Observable<{ documents: KnowledgeDocument[] }> {
    const url = scope ? `${this.apiUrl}/documents?scope=${scope}` : `${this.apiUrl}/documents`;
    return this.http.get<{ documents: KnowledgeDocument[] }>(url);
  }

  getScopes(): Observable<{ scopes: string[] }> {
    return this.http.get<{ scopes: string[] }>(`${this.apiUrl}/scopes`);
  }

  uploadDocument(doc: Partial<KnowledgeDocument>): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/upload`, doc).pipe(
      tap(() => this.refreshAll())
    );
  }
}
