#!/usr/bin/env python3
"""
Entry point for Cloud Run Job
"""
import sys
import logging
from scraper import main as scraper_main

# Configure logging for Cloud Run Jobs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

if __name__ == "__main__":
    try:
        logging.info("🚀 Starting news scraper job...")
        result = scraper_main()
        logging.info("✅ News scraper job completed successfully")
        sys.exit(0)  # Success
    except Exception as e:
        logging.error(f"❌ News scraper job failed: {str(e)}")
        sys.exit(1)  # Failure
