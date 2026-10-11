# Enterprise AI Orchestrator - Angular Frontend 🅰️

Standalone Angular 18+ frontend designed for the Enterprise AI Orchestrator with Google Cloud ADK & Vertex AI Agent Engine.

---

## 🏗️ Structure Overview

```
frontend/
├── angular.json               # Angular CLI configuration
├── package.json               # Dependencies and scripts
├── tsconfig.json              # TypeScript configuration
└── src/
    ├── proxy.conf.json        # Forward /api requests to http://127.0.0.1:8000
    ├── index.html             # Tailwind CSS & Typography fonts
    ├── main.ts                # Standalone Angular bootstrap
    └── app/
        ├── app.config.ts      # HttpClient & Router providers
        ├── app.component.ts   # Main Layout with tab switcher
        ├── app.component.html # Layout template
        ├── models/            # ChatResponse, AgentManifest, ToolDefinition, etc.
        ├── services/          # AuthService, OrchestratorService, RagService, AuditService
        └── components/
            ├── navbar/        # Persona switcher & JWT Claims modal
            ├── chat/          # Real-time chat, telemetry badges, write confirmation cards
            ├── onboarding/    # Team agent manifest form & registry cards
            ├── tool-builder/  # Swagger/OpenAPI parser with Read vs Write tagger
            ├── rag-stores/    # Isolated team datastores & Document AI ingestion
            └── audit-trail/   # Real-time Cloud Logging & Trace stream
```

---

## 🚀 How to Run the Frontend

### 1. Install Dependencies
```bash
cd frontend
npm install
```

### 2. Start the Development Server
```bash
npm start
```
*(This executes `ng serve --proxy-config src/proxy.conf.json`).*

Open **http://localhost:4200** in your browser. All API calls to `/api/...` will automatically be proxied to your FastAPI backend at `http://127.0.0.1:8000`.

---

## 🔗 Integrated Backend Endpoints

| Backend Route | Angular Service Method | Description |
| :--- | :--- | :--- |
| `POST /api/chat` | `OrchestratorService.sendChat()` | Sends prompt, persona, and JWT token to the Gemini router |
| `POST /api/chat/confirm` | `OrchestratorService.confirmAction()` | Resolves write/mutation human authorization (`approve` / `reject`) |
| `GET /api/agents` | `OrchestratorService.refreshAgents()` | Fetches active team agents from the registry |
| `POST /api/agents/onboard` | `OrchestratorService.onboardAgent()` | Onboards a new team agent manifest into Firestore storage |
| `GET /api/tools` | `OrchestratorService.refreshTools()` | Retrieves all registered tools and their read/write classification |
| `POST /api/tools/import-swagger` | `OrchestratorService.importSwagger()` | Parses OpenAPI JSON/YAML and binds tools to target agents |
| `GET /api/knowledge/documents` | `RagService.getDocuments()` | Retrieves team documents from Vertex AI Search datastores |
| `POST /api/knowledge/upload` | `RagService.uploadDocument()` | Ingests new documents into a datastore scope |
| `GET /api/audit/logs` | `AuditService.refreshLogs()` | Streams live Google Cloud Logging entries with Trace IDs |
| `GET /api/personas` | `AuthService.loadPersonas()` | Fetches personas and signed Identity Platform JWT tokens |
