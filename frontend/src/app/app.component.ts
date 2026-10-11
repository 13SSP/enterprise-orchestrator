import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NavbarComponent } from './components/navbar/navbar.component';
import { ChatComponent } from './components/chat/chat.component';
import { OnboardingComponent } from './components/onboarding/onboarding.component';
import { ToolBuilderComponent } from './components/tool-builder/tool-builder.component';
import { RagStoresComponent } from './components/rag-stores/rag-stores.component';
import { AuditTrailComponent } from './components/audit-trail/audit-trail.component';
import { OrchestratorService } from './services/orchestrator.service';

type TabType = 'chat' | 'onboard' | 'swagger' | 'rag' | 'audit';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule,
    NavbarComponent,
    ChatComponent,
    OnboardingComponent,
    ToolBuilderComponent,
    RagStoresComponent,
    AuditTrailComponent
  ],
  templateUrl: './app.component.html'
})
export class AppComponent {
  activeTab = signal<TabType>('chat');

  constructor(public orchestrator: OrchestratorService) {}

  setTab(tab: TabType): void {
    this.activeTab.set(tab);
  }
}
