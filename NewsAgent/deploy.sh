#!/usr/bin/env bash
set -e

# deploy.sh – Deploy the NewsAgent dashboard

# Ensure required environment variables are set
: "${GEMINI_API_KEY:?Need to set GEMINI_API_KEY}"
: "${GCS_BUCKET:?Need to set GCS_BUCKET}"

echo "🔧 Building and tagging dashboard image..."
docker build \
  --file Dockerfile \
  --tag news-intelligence-dashboard:latest \
  .

echo "🚀 Starting dashboard container..."
docker run -d \
  --name news-dashboard \
  --env GEMINI_API_KEY="${GEMINI_API_KEY}" \
  --env GCS_BUCKET="${GCS_BUCKET}" \
  -p 8080:8080 \
  news-intelligence-dashboard:latest

echo "✅ Dashboard is running on port 8080"
