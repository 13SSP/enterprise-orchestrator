"""
cortex.ai - Central Orchestration Hub Service (Port 8000)
Initializes Agent Registry, Tool Factory, Model Gateway, Zero-Trust Access Control, and REST API.
"""

import sys
import os
import importlib.util
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Automatically load environment variables from root .env if not already set
env_path = root_dir / ".env"
if env_path.exists():
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("'\"")
                    if k and k not in os.environ:
                        os.environ[k] = v
    except Exception:
        pass

from api.routes import router_api
from agent_registry.registry import agent_registry
from tool_factory.generator import tool_factory
from tool_registry.registry import tool_registry

app = FastAPI(
    title="cortex.ai Enterprise Orchestrator Hub",
    description="Multi-agent routing, tool factory, zero-trust access control, and model gateway on Google Cloud & Firebase.",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json"
)

# Enable CORS for Angular frontend (allow localhost, 127.0.0.1, and Google Cloud Run domains)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|.*\.run\.app|.*\.googleusercontent\.com|.*)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include API routes
app.include_router(router_api)

# Mount generated files download directory
generated_dir = root_dir / "integrations" / "m365-connector" / "generated_files"
generated_dir.mkdir(parents=True, exist_ok=True)
app.mount("/downloads", StaticFiles(directory=str(generated_dir)), name="downloads")

# Serve Frontend Web Shell for Cloud Run evaluators
from fastapi.responses import FileResponse
frontend_file = root_dir / "cortex-ai" / "frontend" / "index.html"
if frontend_file.exists():
    @app.get("/", tags=["Frontend"], response_class=FileResponse)
    def serve_frontend_ui():
        return FileResponse(frontend_file)

def load_app_spec(app_path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, app_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.app.openapi()

@app.on_event("startup")
def startup_event():
    print("[cortex.ai Hub] Auto-discovering team agents from manifests...")
    agent_registry.discover_agents()
    print(f"[cortex.ai Hub] Successfully onboarded {len(agent_registry.list_agents())} team agents.")

    print("[cortex.ai Hub] Ingesting OpenAPI tool catalogs from domain microservices...")
    try:
        hr_spec = load_app_spec(root_dir / "apps" / "hr-api" / "src" / "main.py", "hr_mod")
        payroll_spec = load_app_spec(root_dir / "apps" / "payroll-api" / "src" / "main.py", "payroll_mod")
        it_spec = load_app_spec(root_dir / "apps" / "it-support-api" / "src" / "main.py", "it_mod")
        expense_spec = load_app_spec(root_dir / "apps" / "expense-api" / "src" / "main.py", "expense_mod")
        m365_spec = load_app_spec(root_dir / "integrations" / "m365-connector" / "src" / "main.py", "m365_mod")

        tool_factory.parse_openapi_spec("hr-api", "http://127.0.0.1:8001", hr_spec)
        tool_factory.parse_openapi_spec("payroll-api", "http://127.0.0.1:8002", payroll_spec)
        tool_factory.parse_openapi_spec("it-support-api", "http://127.0.0.1:8003", it_spec)
        tool_factory.parse_openapi_spec("expense-api", "http://127.0.0.1:8004", expense_spec)
        tool_factory.parse_openapi_spec("m365-connector", "http://127.0.0.1:8005", m365_spec)
        print(f"[cortex.ai Hub] Successfully generated {len(tool_registry.list_tools())} ADK tools into tool registry.")
    except Exception as e:
        print(f"[cortex.ai Hub] Notice while loading tool specs: {e}")

@app.get("/health", tags=["System"])
def health():
    return {
        "status": "healthy",
        "service": "cortex-backend",
        "port": 8000,
        "agents_count": len(agent_registry.list_agents()),
        "tools_count": len(tool_registry.list_tools())
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

