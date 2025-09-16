#!/bin/bash

echo "🔧 Setting up environment variables"
echo "=================================="

# Replace these with your actual values
export PROJECT_ID="your-gcp-project-id"
export GCS_BUCKET="your-gcs-bucket"
export GCS_PREFIX="your-gcs-prefix"
export GEMINI_API_KEY="your-api-key"
export REGION="us-central1"

# Authenticate and set project
gcloud auth login
gcloud config set project $PROJECT_ID

# Make deployment script executable
chmod +x deploy.sh

echo "✅ Environment configured!"
echo "🚀 Run './deploy.sh' to deploy your service"
