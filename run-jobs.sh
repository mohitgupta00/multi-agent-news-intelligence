#!/usr/bin/env bash
set -e

# run-jobs.sh – Build & run scraper and processor

# Ensure required environment variables are set
: "${NEWSDATA_API_KEY:?Need to set NEWSDATA_API_KEY}"
: "${GEMINI_API_KEY:?Need to set GEMINI_API_KEY}"
: "${GCS_BUCKET:?Need to set GCS_BUCKET}"
: "${GCS_PREFIX:=news_data}"

# Build and run the scraper
echo "📥 Building NewsScraper image..."
docker build \
  --file NewsAgentData/NewsScraper/Dockerfile \
  --tag news-scraper:latest \
  NewsAgentData/NewsScraper

echo "📥 Running NewsScraper container..."
docker run --rm \
  --name news-scraper \
  --env NEWSDATA_API_KEY="${NEWSDATA_API_KEY}" \
  --env GCS_BUCKET="${GCS_BUCKET}" \
  --env GCS_PREFIX="${GCS_PREFIX}" \
  news-scraper:latest

# Build and run the data processor
echo "⚙️ Building DataProcessor image..."
docker build \
  --file NewsAgentData/NewsDataProcessor/Dockerfile \
  --tag data-processor:latest \
  NewsAgentData/NewsDataProcessor

echo "⚙️ Running DataProcessor container..."
docker run --rm \
  --name data-processor \
  --env GEMINI_API_KEY="${GEMINI_API_KEY}" \
  --env GCS_BUCKET="${GCS_BUCKET}" \
  --env GCS_PREFIX="${GCS_PREFIX}" \
  data-processor:latest

echo "✅ Data pipeline jobs completed"
