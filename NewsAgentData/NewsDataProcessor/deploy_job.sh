#!/bin/bash

PROJECT_ID="news-471020" # Replace with your project ID
JOB_NAME="news-data-processor"
REGION="us-central1"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${JOB_NAME}"


echo "🚀 Deploying Data Processing Job to Cloud Run"

# Set active project
gcloud config set project $PROJECT_ID

# Build Docker image for the job from within the 'job' directory
# The 'cd' command ensures the build context is correct
cd /content/NewsAgent/job
echo "🔨 Building job Docker image from $(pwd)..."
gcloud builds submit --tag $IMAGE_NAME .

# Deploy to Cloud Run Jobs
echo "🚀 Deploying to Cloud Run Jobs..."
gcloud run jobs deploy $JOB_NAME \
  --image $IMAGE_NAME \
  --region $REGION \
  --memory 8Gi \
  --cpu 4 \
  --tasks 1 \
  --set-env-vars "GEMINI_API_KEY=$GEMINI_API_KEY,GCS_BUCKET=$GCS_BUCKET,GCS_PREFIX=$GCS_PREFIX" \
  --task-timeout 3600 # 1 hour timeout

# Example of how to run the job manually
echo "
✅ Job Deployed. To run it manually, use:
  gcloud run jobs execute $JOB_NAME --region $REGION
"
