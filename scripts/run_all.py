"""
cortex.ai - Unified Platform Process Manager
Launches and orchestrates all microservices, the Cortex Orchestration Hub,
and the Angular Frontend UI. Keeps all processes running and handles clean shutdown.
"""

import os
import sys
import time
import signal
import subprocess
import urllib.request
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent

# Load .env into os.environ for all child services
env_file = ROOT_DIR / ".env"
if env_file.exists():
    try:
        with open(env_file, "r", encoding="utf-8") as f:
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

SERVICES = [
    {
        "name": "hr-api",
        "port": 8001,
        "health_url": "http://127.0.0.1:8001/docs",
        "cmd": [sys.executable, "-m", "uvicorn", "apps.hr-api.src.main:app", "--port", "8001", "--host", "127.0.0.1"]
    },
    {
        "name": "payroll-api",
        "port": 8002,
        "health_url": "http://127.0.0.1:8002/docs",
        "cmd": [sys.executable, "-m", "uvicorn", "apps.payroll-api.src.main:app", "--port", "8002", "--host", "127.0.0.1"]
    },
    {
        "name": "it-support-api",
        "port": 8003,
        "health_url": "http://127.0.0.1:8003/docs",
        "cmd": [sys.executable, "-m", "uvicorn", "apps.it-support-api.src.main:app", "--port", "8003", "--host", "127.0.0.1"]
    },
    {
        "name": "expense-api",
        "port": 8004,
        "health_url": "http://127.0.0.1:8004/docs",
        "cmd": [sys.executable, "-m", "uvicorn", "apps.expense-api.src.main:app", "--port", "8004", "--host", "127.0.0.1"]
    },
    {
        "name": "m365-connector",
        "port": 8005,
        "health_url": "http://127.0.0.1:8005/docs",
        "cmd": [sys.executable, "-m", "uvicorn", "integrations.m365-connector.src.main:app", "--port", "8005", "--host", "127.0.0.1"]
    },
    {
        "name": "cortex-backend",
        "port": 8000,
        "health_url": "http://127.0.0.1:8000/health",
        "cmd": [sys.executable, "cortex-ai/backend/main.py"]
    },
    {
        "name": "angular-frontend",
        "port": 4200,
        "health_url": "http://127.0.0.1:4200/",
        "cmd": [sys.executable, "cortex-ai/frontend/serve.py"]
    }
]

def check_health(url: str, timeout: float = 2.0) -> bool:
    try:
        req = urllib.request.urlopen(url, timeout=timeout)
        return req.status in [200, 301, 302]
    except Exception:
        return False

def main():
    print("=" * 70)
    print(" cortex.ai - Enterprise AI Orchestrator on Google Cloud & Firebase ")
    print("=" * 70)

    # 1. Seed database
    print("\n[*] Seeding database...")
    subprocess.run([sys.executable, "database/seed_db.py"], cwd=ROOT_DIR, check=True)

    # 2. Launch background processes
    log_dir = ROOT_DIR / ".logs"
    log_dir.mkdir(exist_ok=True)

    processes = {}
    print("\n[*] Starting all services...")
    for s in SERVICES:
        out_f = open(log_dir / f"{s['name']}.log", "w", encoding="utf-8")
        p = subprocess.Popen(
            s["cmd"],
            cwd=ROOT_DIR,
            stdout=out_f,
            stderr=out_f
        )
        processes[s["name"]] = (p, out_f, s)
        print(f"    [+] Started {s['name']:<20} on port {s['port']} (PID {p.pid})")

    # 3. Wait for all services to become healthy
    print("\n[*] Waiting for services to initialize...")
    max_wait = 20
    start_time = time.time()
    all_ready = False

    while time.time() - start_time < max_wait:
        ready_count = 0
        for s in SERVICES:
            if check_health(s["health_url"]):
                ready_count += 1
        if ready_count == len(SERVICES):
            all_ready = True
            break
        time.sleep(1)

    print("\n" + "=" * 70)
    if all_ready:
        print(" [+] ALL CORTEX.AI SERVICES ARE HEALTHY & LIVE!")
    else:
        print(" [!] SERVICES STARTED (Some still initializing)")
    print("=" * 70)
    print(f"{'SERVICE':<25} {'PORT':<8} {'URL':<35}")
    print("-" * 70)
    print(f"{'Angular Frontend UI':<25} {'4200':<8} {'http://127.0.0.1:4200'}")
    print(f"{'Cortex Orchestration Hub':<25} {'8000':<8} {'http://127.0.0.1:8000/docs'}")
    print(f"{'HR Domain API':<25} {'8001':<8} {'http://127.0.0.1:8001/docs'}")
    print(f"{'Payroll API (Restricted)':<25} {'8002':<8} {'http://127.0.0.1:8002/docs'}")
    print(f"{'IT Support API':<25} {'8003':<8} {'http://127.0.0.1:8003/docs'}")
    print(f"{'Expense & Receipt API':<25} {'8004':<8} {'http://127.0.0.1:8004/docs'}")
    print(f"{'M365 Integration API':<25} {'8005':<8} {'http://127.0.0.1:8005/docs'}")
    print("=" * 70)
    print("Logs: .logs/<service-name>.log")
    print("Press Ctrl+C to terminate all services gracefully.")
    print("=" * 70 + "\n")
    sys.stdout.flush()

    # 4. Monitor loop
    try:
        while True:
            for name, (proc, _, s) in list(processes.items()):
                ret = proc.poll()
                if ret is not None:
                    print(f"[!] Warning: {name} exited unexpectedly with code {ret}")
            time.sleep(2)
    except KeyboardInterrupt:
        print("\n[*] Shutting down cortex.ai services...")
    finally:
        for name, (proc, out_f, _) in processes.items():
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
            try:
                out_f.close()
            except Exception:
                pass
        print("[+] All services terminated cleanly.")

if __name__ == "__main__":
    main()
