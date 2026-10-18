<#
.SYNOPSIS
    cortex.ai - One-Click Google Cloud Deployment Script (Windows PowerShell)
.DESCRIPTION
    Builds and deploys cortex.ai to Google Cloud Run with $300 GCP credit optimization.
#>

param(
    [string]$ProjectId = "",
    [string]$Region = "us-central1"
)

$ErrorActionPreference = "Stop"

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "⚡ cortex.ai - Google Cloud Production Deployment (Cloud Run)" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

# Check gcloud CLI
if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
    Write-Host "❌ 'gcloud' CLI is not found in PATH on your Windows machine." -ForegroundColor Red
    Write-Host "👉 RECOMMENDED FAST PATH: Use Google Cloud Shell (in your browser at https://shell.cloud.google.com)." -ForegroundColor Yellow
    Write-Host "   Cloud Shell comes with gcloud, git, and Docker pre-installed with zero setup!" -ForegroundColor Yellow
    Write-Host "   Simply run: git clone <your-repo> && cd enterprise-orchestrator && chmod +x deploy_gcp.sh && ./deploy_gcp.sh" -ForegroundColor Yellow
    Exit 1
}

if (-not $ProjectId) {
    $ProjectId = gcloud config get-value project 2>$null
    if (-not $ProjectId -or $ProjectId -eq "(unset)") {
        $ProjectId = Read-Host "Please enter your Google Cloud Project ID"
        gcloud config set project $ProjectId
    }
}

$ServiceName = "cortex-hub"
$RepoName = "cortex-repo"
$ImageTag = "${Region}-docker.pkg.dev/${ProjectId}/${RepoName}/${ServiceName}:latest"

Write-Host "🚀 Deploying to Project: $ProjectId in Region: $Region" -ForegroundColor Green

# 1. Enable Required Google Cloud Services
Write-Host "`n⚙️  [1/4] Enabling Required Google Cloud APIs..." -ForegroundColor Blue
gcloud services enable `
    run.googleapis.com `
    cloudbuild.googleapis.com `
    artifactregistry.googleapis.com `
    storage.googleapis.com `
    aiplatform.googleapis.com `
    discoveryengine.googleapis.com `
    documentai.googleapis.com `
    firestore.googleapis.com `
    bigquery.googleapis.com `
    logging.googleapis.com

Write-Host "✓ All Google Cloud APIs enabled successfully." -ForegroundColor Green

# 2. Verify Firestore
Write-Host "`n🔥 [2/4] Verifying Cloud Firestore Database..." -ForegroundColor Blue
try {
    gcloud firestore databases describe --database="(default)" 2>$null
} catch {
    Write-Host "Creating Firestore database in native mode in $Region..." -ForegroundColor Yellow
    gcloud firestore databases create --location=$Region --type=firestore-native
}
Write-Host "✓ Firestore database ready." -ForegroundColor Green

# 3. Build Container via Cloud Build (Serverless remote build - no local Docker needed!)
Write-Host "`n📦 [3/4] Building container image using Google Cloud Build & Artifact Registry..." -ForegroundColor Blue
gcloud artifacts repositories create $RepoName `
    --repository-format=docker `
    --location=$Region `
    --description="Docker repository for cortex.ai" `
    --quiet 2>$null

gcloud builds submit --tag $ImageTag .
Write-Host "✓ Container image built and pushed." -ForegroundColor Green

# 4. Deploy to Cloud Run
Write-Host "`n🌐 [4/4] Deploying to Google Cloud Run..." -ForegroundColor Blue

$GeminiKey = $env:GEMINI_API_KEY
if (-not $GeminiKey -and (Test-Path ".env")) {
    $envContent = Get-Content ".env" | Where-Object { $_ -match "^GEMINI_API_KEY=" }
    if ($envContent) {
        $GeminiKey = ($envContent -split "=", 2)[1].Trim('"', "'")
    }
}

gcloud run deploy $ServiceName `
    --image $ImageTag `
    --platform managed `
    --region $Region `
    --port 8080 `
    --allow-unauthenticated `
    --min-instances 0 `
    --max-instances 2 `
    --memory 1Gi `
    --cpu 1 `
    --timeout 300 `
    --set-env-vars "GCP_PROJECT_ID=$ProjectId,GCP_REGION=$Region,GEMINI_API_KEY=$GeminiKey,MODEL_ARMOR_ENABLED=true"

$PublicUrl = gcloud run services describe $ServiceName --platform managed --region $Region --format 'value(status.url)'

Write-Host "`n======================================================================" -ForegroundColor Green
Write-Host "🎉 DEPLOYMENT SUCCESSFUL!" -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Green
Write-Host "Evaluator Live Web App URL: $PublicUrl" -ForegroundColor Cyan
Write-Host "API Swagger Documentation : $PublicUrl/docs" -ForegroundColor Cyan
Write-Host "Healthcheck Endpoint      : $PublicUrl/health" -ForegroundColor Cyan
Write-Host "Share the Live Web App URL with your hackathon evaluators!" -ForegroundColor Yellow
