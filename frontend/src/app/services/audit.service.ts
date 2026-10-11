import { Injectable, signal, OnDestroy } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { AuditLogEntry } from '../models/audit.model';

@Injectable({
  providedIn: 'root'
})
export class AuditService implements OnDestroy {
  private apiUrl = '/api/audit';
  private timer: any = null;

  logs = signal<AuditLogEntry[]>([]);
  activeFilter = signal<string>('');

  constructor(private http: HttpClient) {
    this.refreshLogs();
    this.startPolling();
  }

  startPolling(intervalMs: number = 3500): void {
    if (this.timer) clearInterval(this.timer);
    this.timer = setInterval(() => this.refreshLogs(), intervalMs);
  }

  stopPolling(): void {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
  }

  refreshLogs(): void {
    const filter = this.activeFilter();
    const url = filter 
      ? `${this.apiUrl}/logs?event_type=${filter}&limit=60` 
      : `${this.apiUrl}/logs?limit=60`;

    this.http.get<{ logs: AuditLogEntry[] }>(url).subscribe({
      next: (res) => this.logs.set(res.logs || []),
      error: (err) => console.error('Error fetching audit logs:', err)
    });
  }

  setFilter(eventType: string): void {
    this.activeFilter.set(eventType);
    this.refreshLogs();
  }

  clearLogs(): void {
    this.http.post(`${this.apiUrl}/clear`, {}).subscribe(() => {
      this.logs.set([]);
    });
  }

  ngOnDestroy(): void {
    this.stopPolling();
  }
}
