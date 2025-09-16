#!/bin/bash

# Configuration
PROJECT_ID="news-471020"  # Replace with your project ID
SERVICE_NAME="news-intelligence-api"
REGION="us-central1"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "🚀 Deploying Multi-Agent News Intelligence to Cloud Run"
echo "=================================================="

# Set active project
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "📋 Enabling required APIs..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com

# Build Docker image
echo "🔨 Building Docker image..."
gcloud builds submit --tag $IMAGE_NAME .

# Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image $IMAGE_NAME \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --memory 4Gi \
  --cpu 2 \
  --timeout 900 \
  --concurrency 100 \
  --min-instances 1 \
  --max-instances 10 \
  --set-env-vars GEMINI_API_KEY=$GEMINI_API_KEY,GCS_BUCKET=$GCS_BUCKET,GCS_PREFIX=$GCS_PREFIX

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format='value(status.url)')

echo ""
echo "✅ Deployment Complete!"
echo "=================================================="
echo "🌐 Service URL: $SERVICE_URL"
echo "📖 API Docs: $SERVICE_URL/docs"
echo "📊 Dashboard: $SERVICE_URL"
echo "💚 Health Check: $SERVICE_URL/health"
