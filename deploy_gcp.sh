#!/usr/bin/env bash
# ==============================================================================
# cortex.ai - One-Click Google Cloud Deployment Script
# Built for Hackathon Deployment with $300 GCP Credits Optimization
# ==============================================================================

set -e

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}======================================================================${NC}"
echo -e "${CYAN}⚡ cortex.ai - Google Cloud Production Deployment (Cloud Run)${NC}"
echo -e "${CYAN}======================================================================${NC}"

# 1. Detect or prompt for Google Cloud Project ID
PROJECT_ID=$(gcloud config get-value project 2>/dev/null || true)
if [ -z "$PROJECT_ID" ] || [ "$PROJECT_ID" = "(unset)" ]; then
    echo -e "${YELLOW}Please enter your Google Cloud Project ID:${NC}"
    read -r PROJECT_ID
    gcloud config set project "$PROJECT_ID"
fi

REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="cortex-hub"
IMAGE_TAG="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest"

echo -e "🚀 Deploying to Project: ${GREEN}${PROJECT_ID}${NC} in Region: ${GREEN}${REGION}${NC}"

# 2. Enable Required Google Cloud Services (Zero-Cost until invoked)
echo -e "\n${BLUE}⚙️  [1/4] Enabling Required Google Cloud APIs...${NC}"
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    aiplatform.googleapis.com \
    discoveryengine.googleapis.com \
    documentai.googleapis.com \
    firestore.googleapis.com \
    bigquery.googleapis.com \
    logging.googleapis.com

echo -e "${GREEN}✓ All Google Cloud APIs enabled successfully.${NC}"

# 3. Create Firestore Native Database if not already created
echo -e "\n${BLUE}🔥 [2/4] Verifying Cloud Firestore Database...${NC}"
if ! gcloud firestore databases describe --database="(default)" &>/dev/null; then
    echo -e "Creating Firestore database in (default) native mode in ${REGION}..."
    gcloud firestore databases create --location="$REGION" --type=firestore-native || true
fi
echo -e "${GREEN}✓ Firestore database ready.${NC}"

# 4. Build Container with Cloud Build (Remote serverless build - no local Docker needed!)
echo -e "\n${BLUE}📦 [3/4] Building container image using Google Cloud Build...${NC}"
gcloud builds submit --tag "$IMAGE_TAG" .

echo -e "${GREEN}✓ Container built and pushed to Container Registry.${NC}"

# 5. Deploy to Cloud Run with Cost-Protection Guardrails (Scale-to-Zero)
echo -e "\n${BLUE}🌐 [4/4] Deploying cortex.ai to Google Cloud Run...${NC}"

# Retrieve Gemini API key if set in environment or prompt
GEMINI_KEY="${GEMINI_API_KEY:-}"
if [ -z "$GEMINI_KEY" ] && [ -f ".env" ]; then
    GEMINI_KEY=$(grep '^GEMINI_API_KEY=' .env | cut -d '=' -f2- | tr -d '"' | tr -d "'" || true)
fi

gcloud run deploy "$SERVICE_NAME" \
    --image "$IMAGE_TAG" \
    --platform managed \
    --region "$REGION" \
    --allow-unauthenticated \
    --min-instances 0 \
    --max-instances 2 \
    --memory 1Gi \
    --cpu 1 \
    --timeout 300 \
    --set-env-vars "GCP_PROJECT_ID=${PROJECT_ID},GCP_REGION=${REGION},GEMINI_API_KEY=${GEMINI_KEY},MODEL_ARMOR_ENABLED=true"

# 6. Retrieve and display public service URL
PUBLIC_URL=$(gcloud run services describe "$SERVICE_NAME" --platform managed --region "$REGION" --format 'value(status.url)')

echo -e "\n${GREEN}======================================================================${NC}"
echo -e "${GREEN}🎉 DEPLOYMENT SUCCESSFUL!${NC}"
echo -e "${GREEN}======================================================================${NC}"
echo -e "Evaluator Live Web App URL: ${CYAN}${PUBLIC_URL}${NC}"
echo -e "API Swagger Documentation : ${CYAN}${PUBLIC_URL}/docs${NC}"
echo -e "Healthcheck Endpoint      : ${CYAN}${PUBLIC_URL}/health${NC}"
echo -e "${YELLOW}Share the Live Web App URL with your hackathon evaluators!${NC}"
