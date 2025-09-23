#!/bin/bash

echo "🔧 Setting up environment variables"
echo "=================================="

# Replace these with your actual values
export PROJECT_ID="news-471020"
export GCS_BUCKET="news-hub"
export GCS_PREFIX="news_data"
export GEMINI_API_KEY="api-key"
export REGION="us-central1"

# Authenticate and set project
gcloud auth login
gcloud config set project $PROJECT_ID

# Make deployment script executable
chmod +x deploy.sh

echo "✅ Environment configured!"
echo "🚀 Run './deploy.sh' to deploy your service"
