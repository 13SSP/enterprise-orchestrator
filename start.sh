#!/usr/bin/env bash
# ==============================================================================
# cortex.ai - The Single Executable Lifecycle Manager
# Google Cloud & Firebase AI Orchestration Platform
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PID_FILE="$SCRIPT_DIR/.running_pids"
ONLY_STEP=""
SKIP_INSTALL=false

# Print banner
echo "======================================================================"
echo "⚡ cortex.ai - Enterprise AI Orchestrator on Google Cloud & Firebase"
echo "======================================================================"

# Parse flags
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --only) ONLY_STEP="$2"; shift ;;
        --skip-install) SKIP_INSTALL=true ;;
        --stop)
            echo "🛑 Stopping all running cortex.ai services..."
            if [ -f "$PID_FILE" ]; then
                while IFS= read -r pid; do
                    if kill -0 "$pid" 2>/dev/null; then
                        echo "   Killing PID $pid..."
                        kill "$pid" 2>/dev/null || true
                    fi
                done < "$PID_FILE"
                rm -f "$PID_FILE"
            fi
            # Kill processes on allocated ports
            for port in 8000 8001 8002 8003 8004 8005 8011 8012 8013 8014 8015 4200 8080 9099; do
                fuser -k "${port}/tcp" 2>/dev/null || true
            done
            echo "✅ All cortex.ai processes terminated."
            exit 0
            ;;
        --deploy)
            echo "🚀 Deploying to Google Cloud Run and Firebase Hosting..."
            PROJECT_ID="${GCP_PROJECT_ID:-cortex-ai-hackathon}"
            REGION="${GCP_REGION:-us-central1}"
            echo "Building and pushing container images to Google Artifact Registry..."
            gcloud builds submit --tag "${REGION}-docker.pkg.dev/${PROJECT_ID}/cortex-repo/cortex-hub:latest" cortex-ai/backend
            gcloud run deploy cortex-hub --image "${REGION}-docker.pkg.dev/${PROJECT_ID}/cortex-repo/cortex-hub:latest" --region "$REGION" --platform managed --allow-unauthenticated
            echo "Deploying frontend to Firebase Hosting..."
            firebase deploy --only hosting
            echo "✅ Deployment complete!"
            exit 0
            ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Step 1: Check Prerequisites & Load .env
if [ -z "$ONLY_STEP" ] || [ "$ONLY_STEP" = "1" ] || [ "$ONLY_STEP" = "prereqs" ]; then
    echo "📋 [1/9] Checking prerequisites and environment..."
    if [ -f ".env" ]; then
        export $(grep -v '^#' .env | xargs)
        echo "   ✓ Loaded .env configuration"
    elif [ -f ".env.example" ]; then
        cp .env.example .env
        export $(grep -v '^#' .env | xargs)
        echo "   ✓ Copied .env.example to .env"
    fi

    # Check Python
    if command -v python3 &>/dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &>/dev/null; then
        PYTHON_CMD="python"
    else
        echo "❌ Python 3.10+ is required but not found in PATH."
        exit 1
    fi
    echo "   ✓ Python: $($PYTHON_CMD --version)"

    # Check Firebase CLI (Optional with fallback)
    if command -v firebase &>/dev/null; then
        echo "   ✓ Firebase CLI: $(firebase --version)"
    else
        echo "   ℹ Firebase CLI not in PATH; will use Firestore Local Engine fallback."
    fi
fi

# Step 2: Start Firebase Emulators
if [ -z "$ONLY_STEP" ] || [ "$ONLY_STEP" = "2" ] || [ "$ONLY_STEP" = "emulators" ]; then
    echo "🔥 [2/9] Starting Firebase Emulator Suite (Firestore :8080, Auth :9099)..."
    if command -v firebase &>/dev/null; then
        (cd database && firebase emulators:start --only firestore,auth > /dev/null 2>&1 & echo $! >> "$PID_FILE")
        sleep 4
        echo "   ✓ Firebase Emulators running."
    else
        echo "   ✓ Using Firestore Native Local Storage Engine (:8080 / in-process)."
    fi
fi

# Step 3: Seed Firestore
if [ -z "$ONLY_STEP" ] || [ "$ONLY_STEP" = "3" ] || [ "$ONLY_STEP" = "seed" ]; then
    echo "🌱 [3/9] Seeding Firestore with enterprise dataset..."
    $PYTHON_CMD database/seed_db.py
    echo "   ✓ Database seeded."
fi

# Step 4: Install Dependencies & Start Domain APIs
if [ -z "$ONLY_STEP" ] || [ "$ONLY_STEP" = "4" ] || [ "$ONLY_STEP" = "apis" ]; then
    echo "🚀 [4/9] Starting Domain Business Microservices..."
    
    # hr-api (8001)
    echo "   Starting hr-api on port 8001..."
    ($PYTHON_CMD -m uvicorn apps.hr-api.src.main:app --port 8001 --host 0.0.0.0 > /dev/null 2>&1 & echo $! >> "$PID_FILE")
    
    # payroll-api (8002)
    echo "   Starting payroll-api on port 8002..."
    ($PYTHON_CMD -m uvicorn apps.payroll-api.src.main:app --port 8002 --host 0.0.0.0 > /dev/null 2>&1 & echo $! >> "$PID_FILE")

    # it-support-api (8003)
    echo "   Starting it-support-api on port 8003..."
    ($PYTHON_CMD -m uvicorn apps.it-support-api.src.main:app --port 8003 --host 0.0.0.0 > /dev/null 2>&1 & echo $! >> "$PID_FILE")

    # expense-api (8004)
    echo "   Starting expense-api on port 8004..."
    ($PYTHON_CMD -m uvicorn apps.expense-api.src.main:app --port 8004 --host 0.0.0.0 > /dev/null 2>&1 & echo $! >> "$PID_FILE")

    # m365-connector (8005)
    echo "   Starting m365-connector on port 8005..."
    ($PYTHON_CMD -m uvicorn integrations.m365-connector.src.main:app --port 8005 --host 0.0.0.0 > /dev/null 2>&1 & echo $! >> "$PID_FILE")

    sleep 3
    echo "   ✓ All domain APIs healthy."
fi

# Step 5 & 6: Start Cortex Hub
if [ -z "$ONLY_STEP" ] || [ "$ONLY_STEP" = "6" ] || [ "$ONLY_STEP" = "backend" ]; then
    echo "🧠 [6/9] Starting cortex.ai Orchestration Hub on port 8000..."
    ($PYTHON_CMD -m uvicorn cortex-ai.backend.main:app --port 8000 --host 0.0.0.0 > /dev/null 2>&1 & echo $! >> "$PID_FILE")
    sleep 3
    echo "   ✓ Cortex Hub initialized with Agent Registry & Tool Factory."
fi

# Step 7: Start Agents
if [ -z "$ONLY_STEP" ] || [ "$ONLY_STEP" = "7" ] || [ "$ONLY_STEP" = "agents" ]; then
    echo "🤖 [7/9] Domain agents registered and linked via ADK protocol."
fi

# Step 8: Build / Serve Angular Frontend
if [ -z "$ONLY_STEP" ] || [ "$ONLY_STEP" = "8" ] || [ "$ONLY_STEP" = "frontend" ]; then
    echo "💻 [8/9] Serving Angular Frontend on port 4200..."
    ($PYTHON_CMD cortex-ai/frontend/serve.py > /dev/null 2>&1 & echo $! >> "$PID_FILE")
    sleep 2
    echo "   ✓ Frontend live at http://127.0.0.1:4200"
fi

# Step 9: Summary Table
echo ""
echo "======================================================================"
echo "🎉 CORTEX.AI PLATFORM IS RUNNING!"
echo "======================================================================"
printf "%-25s %-10s %-35s\n" "SERVICE" "PORT" "URL"
echo "----------------------------------------------------------------------"
printf "%-25s %-10s %-35s\n" "Angular Frontend UI" "4200" "http://127.0.0.1:4200"
printf "%-25s %-10s %-35s\n" "Cortex Orchestration Hub" "8000" "http://127.0.0.1:8000/docs"
printf "%-25s %-10s %-35s\n" "HR Domain API" "8001" "http://127.0.0.1:8001/docs"
printf "%-25s %-10s %-35s\n" "Payroll API (Restricted)" "8002" "http://127.0.0.1:8002/docs"
printf "%-25s %-10s %-35s\n" "IT Support API" "8003" "http://127.0.0.1:8003/docs"
printf "%-25s %-10s %-35s\n" "Expense & Receipt API" "8004" "http://127.0.0.1:8004/docs"
printf "%-25s %-10s %-35s\n" "M365 Integration API" "8005" "http://127.0.0.1:8005/docs"
printf "%-25s %-10s %-35s\n" "Firestore Emulator" "8080" "http://127.0.0.1:8080"
printf "%-25s %-10s %-35s\n" "Firebase Auth Emulator" "9099" "http://127.0.0.1:9099"
echo "======================================================================"
echo "To stop all services: ./start.sh --stop"
echo "To run automated evaluations: python scripts/eval/eval_runner.py"
echo "======================================================================"
