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
echo -e "\n${BLUE}⚙️  [1/5] Enabling Required Google Cloud APIs...${NC}"
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    storage.googleapis.com \
    aiplatform.googleapis.com \
    discoveryengine.googleapis.com \
    documentai.googleapis.com \
    firestore.googleapis.com \
    bigquery.googleapis.com \
    logging.googleapis.com

echo -e "${GREEN}✓ All Google Cloud APIs enabled successfully.${NC}"

# 3. Create Cloud Storage Bucket & Upload Sample Knowledge Base
echo -e "\n${BLUE}📁 [2/5] Creating Cloud Storage Bucket & Uploading Knowledge Base...${NC}"
BUCKET_NAME="cortex-docs-${PROJECT_ID}"
if ! gcloud storage buckets describe "gs://${BUCKET_NAME}" &>/dev/null; then
    echo -e "Creating GCS bucket gs://${BUCKET_NAME} in ${REGION}..."
    gcloud storage buckets create "gs://${BUCKET_NAME}" --location="${REGION}" || true
fi
if [ -d "enterprise_knowledge_base" ]; then
    echo -e "Uploading sample policies & receipts to gs://${BUCKET_NAME}/..."
    gcloud storage cp enterprise_knowledge_base/* "gs://${BUCKET_NAME}/" || true
fi
echo -e "${GREEN}✓ Cloud Storage knowledge base ready.${NC}"

# 4. Create Firestore Native Database & BigQuery Audit Dataset
echo -e "\n${BLUE}🔥 [3/5] Verifying Cloud Firestore & BigQuery...${NC}"
if ! gcloud firestore databases describe --database="(default)" &>/dev/null; then
    echo -e "Creating Firestore database in (default) native mode in ${REGION}..."
    gcloud firestore databases create --location="$REGION" --type=firestore-native || true
fi
bq mk -d --location=US "${PROJECT_ID}:cortex_audit_dataset" 2>/dev/null || true
echo -e "${GREEN}✓ Firestore and BigQuery dataset ready.${NC}"

# 5. Build Container with Cloud Build (Remote serverless build - no local Docker needed!)
echo -e "\n${BLUE}📦 [4/5] Building container image using Google Cloud Build...${NC}"
gcloud builds submit --tag "$IMAGE_TAG" .

echo -e "${GREEN}✓ Container built and pushed to Container Registry.${NC}"

# 6. Deploy to Cloud Run with Cost-Protection Guardrails (Scale-to-Zero)
echo -e "\n${BLUE}🌐 [5/5] Deploying cortex.ai to Google Cloud Run...${NC}"

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
    --set-env-vars "GCP_PROJECT_ID=${PROJECT_ID},GCP_REGION=${REGION},GEMINI_API_KEY=${GEMINI_KEY},MODEL_ARMOR_ENABLED=true,GCS_BUCKET_NAME=${BUCKET_NAME}"

# 6. Retrieve and display public service URL
PUBLIC_URL=$(gcloud run services describe "$SERVICE_NAME" --platform managed --region "$REGION" --format 'value(status.url)')

echo -e "\n${GREEN}======================================================================${NC}"
echo -e "${GREEN}🎉 DEPLOYMENT SUCCESSFUL!${NC}"
echo -e "${GREEN}======================================================================${NC}"
echo -e "Evaluator Live Web App URL: ${CYAN}${PUBLIC_URL}${NC}"
echo -e "API Swagger Documentation : ${CYAN}${PUBLIC_URL}/docs${NC}"
echo -e "Healthcheck Endpoint      : ${CYAN}${PUBLIC_URL}/health${NC}"
echo -e "${YELLOW}Share the Live Web App URL with your hackathon evaluators!${NC}"
