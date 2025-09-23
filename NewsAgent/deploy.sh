#!/bin/bash

# Configuration
PROJECT_ID="project-id"
SERVICE_NAME="news-intelligence-api"
REGION="us-central1"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# --- Hardcoded environment variables to ensure they are passed to Cloud Run ---
# This is the most reliable way to fix the environment issue in this context.
API_KEY="api-key"
BUCKET_NAME="bucket-name"
DATA_PREFIX="data-prefix"

echo "🚀 Deploying Multi-Agent News Intelligence to Cloud Run"
echo "=================================================="

# Set active project
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "📋 Enabling required APIs..."
gcloud services enable cloudbuild.googleapis.com run.googleapis.com

# Build Docker image with an increased timeout
echo "🔨 Building Docker image with increased timeout..."
gcloud builds submit --tag $IMAGE_NAME . --timeout=3600s --machine-type=e2-highcpu-8

# Deploy to Cloud Run with hardcoded environment variables
echo "🚀 Deploying to Cloud Run with correct configuration..."
gcloud run deploy $SERVICE_NAME \
  --image $IMAGE_NAME \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --memory 4Gi \
  --cpu 2 \
  --timeout 900 \
  --set-env-vars "GEMINI_API_KEY=${API_KEY},GCS_BUCKET=${BUCKET_NAME},GCS_PREFIX=${DATA_PREFIX}"

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format='value(status.url)')

echo ""
echo "✅ Deployment Complete!"
echo "=================================================="
echo "🌐 Service URL: $SERVICE_URL"
echo "📖 API Docs: $SERVICE_URL/docs"
echo "📊 Dashboard: $SERVICE_URL"
echo "💚 Health Check: $SERVICE_URL/health"
