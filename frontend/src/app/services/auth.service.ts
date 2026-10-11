import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { UserPersona } from '../models/policy.model';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private apiUrl = '/api';

  // Signals for reactive identity state
  currentPersonaKey = signal<string>('devops_admin');
  currentPersona = signal<UserPersona | null>(null);
  allPersonas = signal<Record<string, UserPersona>>({});

  constructor(private http: HttpClient) {
    this.loadPersonas();
  }

  loadPersonas(): void {
    this.http.get<{ personas: Record<string, UserPersona> }>(`${this.apiUrl}/personas`)
      .subscribe({
        next: (res) => {
          this.allPersonas.set(res.personas);
          this.setPersona(this.currentPersonaKey());
        },
        error: (err) => console.error('Failed to load personas:', err)
      });
  }

  setPersona(key: string): void {
    this.currentPersonaKey.set(key);
    const p = this.allPersonas()[key];
    if (p) {
      this.currentPersona.set(p);
    }
  }

  getJwtToken(): string {
    return this.currentPersona()?.jwt || '';
  }

  getUserName(): string {
    return this.currentPersona()?.user.name || 'Anonymous';
  }

  getUserRoleLabel(): string {
    const roles = this.currentPersona()?.user.roles || [];
    return roles.join(', ');
  }
}
