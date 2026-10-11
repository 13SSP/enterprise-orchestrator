# cortex.ai - Orchestration Gateway Hub
Runs on fixed port `8000`.

## Architecture
- **Router**: Gemini-powered intent classification, context recognition, and multi-agent split/merge.
- **Model Gateway**: Pluggable provider system (Gemini Vertex, Model Garden, External APIs, and Offline Stubs).
- **Access Control**: Two-layer authorization (agent manifest tool allow-list + user identity RBAC).
- **Model Armor**: Safety screening against prompt injections and PII leakage.
- **Approvals**: Human-in-the-loop pending approval workflow manager.
- **Tool Factory**: Dynamic converter from OpenAPI 3.0 / Swagger specs to ADK tools.
