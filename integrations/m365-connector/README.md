# cortex.ai - M365 Integration Microservice
Runs on fixed port `8005`.

## Capabilities
- **Outlook Email Drafts**: `POST /api/v1/outlook/drafts` (Drafts only! Never auto-sent).
- **Human Approval Sending**: `POST /api/v1/outlook/send` (Requires user confirmation).
- **Calendar Availability**: `GET /api/v1/outlook/calendar`.
- **Word Document Generation**: `POST /api/v1/word/generate` (Creates real `.docx`).
- **PowerPoint Generation**: `POST /api/v1/powerpoint/generate` (Creates real `.pptx`).
- **File Download**: `GET /api/v1/files/download/{file_name}`.

## Execution Modes
- **MOCK** (Default): Generates real Word and PowerPoint files locally without needing an Azure tenant.
- **LIVE**: Connects to Microsoft Graph API via Entra ID App Registration.
