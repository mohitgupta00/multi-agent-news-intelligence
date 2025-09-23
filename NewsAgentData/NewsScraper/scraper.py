#!/usr/bin/env python3

import os
import time
import requests
import pandas as pd
from datetime import datetime
from google.cloud import storage
from newspaper import Article
import logging
import sys
import nltk
import threading

# -----------------------
# CONFIG - UNCHANGED  
# -----------------------

NEWSDATA_API_KEY = os.getenv("NEWSDATA_API_KEY")
GCS_BUCKET = os.getenv("GCS_BUCKET", "news-hub")
GCS_PREFIX = os.getenv("GCS_PREFIX", "news_data")
BASE_URL = "https://newsdata.io/api/1/latest"
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT_S", 15))
PER_REQUEST_SLEEP = float(os.getenv("PER_REQUEST_SLEEP_S", 1.0))
USER_AGENT = os.getenv("HTTP_USER_AGENT", "news-hub-bot/1.0 (+https://example.com)")

if not NEWSDATA_API_KEY:
    print("ERROR: set NEWSDATA_API_KEY environment variable.")
    sys.exit(1)

CATEGORIES = ["sports", "politics", "technology", "health", "crime", "entertainment"]
REGIONS = {
    "Global": {"country": None, "limit": 80},  # Using your logs config
    "India": {"country": "in", "limit": 50}
}

# Global storage
all_articles = []
articles_lock = threading.Lock()
rate_limit_start_time = None

storage_client = storage.Client()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# -----------------------
# GCS helpers - UNCHANGED
# -----------------------

def gcs_blob_exists(bucket_name, blob_name):
    bucket = storage_client.bucket(bucket_name)
    return bucket.blob(blob_name).exists()

def upload_file_to_gcs(local_path, bucket_name, blob_name):
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(local_path)
    logging.info(f"Uploaded local '{local_path}' -> gs://{bucket_name}/{blob_name}")

# -----------------------
# FIXED rate limit handling
# -----------------------

def scrape_article_text(url, timeout=20):
    """Scrape article text with fallback"""
    try:
        article = Article(url)
        article.download()
        article.parse()
        text = article.text.strip()
        if text:
            return text
    except Exception as e:
        logging.debug(f"newspaper failed for {url}: {e}")

    try:
        headers = {"User-Agent": USER_AGENT}
        r = requests.get(url, headers=headers, timeout=timeout)
        if r.status_code == 200 and r.text:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(r.text, "html.parser")
            paragraphs = soup.find_all("p")
            text = "\n\n".join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
            return text if text else None
    except Exception as e:
        logging.debug(f"fallback failed for {url}: {e}")

    return None

def scrape_content_efficiently():
    """Scrape content and return time taken"""
    global all_articles, rate_limit_start_time
    
    scrape_start = time.time()
    
    with articles_lock:
        unscrapped = [art for art in all_articles if not art.get('content')]
    
    if not unscrapped:
        return 0
    
    logging.info(f"🔍 Scraping content for {len(unscrapped)} articles during rate limit wait...")
    
    for i, article in enumerate(unscrapped):
        try:
            content = scrape_article_text(article.get('link'))
            
            with articles_lock:
                for j, art in enumerate(all_articles):
                    if art.get('link') == article.get('link'):
                        all_articles[j]['content'] = content
                        break
            
            if (i + 1) % 50 == 0:
                elapsed = time.time() - scrape_start
                logging.info(f"🔍 Scraped {i+1}/{len(unscrapped)} articles in {elapsed:.1f}s")
            
            time.sleep(0.8)
            
        except Exception as e:
            logging.warning(f"Failed scraping {article.get('link')}: {e}")
            with articles_lock:
                for j, art in enumerate(all_articles):
                    if art.get('link') == article.get('link'):
                        all_articles[j]['content'] = None
                        break
    
    scraping_duration = time.time() - scrape_start
    logging.info(f"✅ Content scraping completed in {scraping_duration:.1f}s")
    return scraping_duration

def fetch_page_with_smart_wait(category, country=None, next_page_token=None):
    """FIXED rate limit detection and smart waiting"""
    global rate_limit_start_time
    
    params = {
        "apikey": NEWSDATA_API_KEY,
        "category": category,
        "language": "en",
    }
    if country:
        params["country"] = country
    if next_page_token:
        params["page"] = next_page_token

    headers = {"User-Agent": USER_AGENT}
    
    try:
        resp = requests.get(BASE_URL, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
        data = resp.json()
        
        # FIXED: Correct rate limit detection
        if data.get("status") == "error":
            results = data.get("results", {})
            error_msg = results.get("message", "")
            error_code = results.get("code", "")
            
            # Check for rate limit
            if "rate limit" in error_msg.lower() or error_code == "RateLimitExceeded":
                logging.warning(f"⚠️ Rate limit detected for {category} {country}")
                
                # Record when rate limit started (for calculating total window time)
                if rate_limit_start_time is None:
                    rate_limit_start_time = time.time()
                
                # Start scraping immediately
                scraping_duration = scrape_content_efficiently()
                
                # Calculate elapsed time since rate limit started
                elapsed_since_rate_limit = time.time() - rate_limit_start_time
                
                # Wait for remaining time in 15-minute window
                rate_limit_window = 15 * 60  # 900 seconds
                remaining_wait = rate_limit_window - elapsed_since_rate_limit
                remaining_wait = max(10, remaining_wait)  # Minimum 10 seconds
                
                logging.info(f"⏳ Scraping took {scraping_duration/60:.1f} mins. Waiting {remaining_wait/60:.1f} more mins...")
                time.sleep(remaining_wait)
                
                # Reset rate limit timer
                rate_limit_start_time = None
                
                # Retry the same request
                logging.info(f"🔄 Retrying {category} {country}...")
                return fetch_page_with_smart_wait(category, country, next_page_token)
            else:
                logging.warning(f"API error for {category} {country}: {data}")
                return [], None
        
        elif data.get("status") == "success":
            return data.get("results", []), data.get("nextPage")
        else:
            logging.warning(f"Unexpected API response for {category} {country}: {data}")
            return [], None
            
    except Exception as e:
        logging.error(f"Request failed for {category} {country}: {e}")
        return [], None

def fetch_limited_articles():
    """Fetch articles with FIXED retry logic"""
    global all_articles
    all_articles = []
    seen_ids = set()

    for cat in CATEGORIES:
        for region_label, region_info in REGIONS.items():
            country = region_info["country"]
            limit = region_info["limit"]
            
            logging.info(f"📰 Fetching {cat} | {region_label} up to {limit}")
            
            next_page = None
            fetched = 0
            loop_guard = 0

            while fetched < limit and loop_guard < 100:
                loop_guard += 1
                
                # Use FIXED fetch function
                results, next_page = fetch_page_with_smart_wait(cat, country, next_page)
                
                if not results:
                    break

                for art in results:
                    aid = art.get("article_id") or art.get("link") or art.get("title")
                    if aid in seen_ids:
                        continue
                    
                    seen_ids.add(aid)
                    article_data = {
                        "article_id": art.get("article_id"),
                        "title": art.get("title"),
                        "link": art.get("link"),
                        "description": art.get("description"),
                        "pubDate": art.get("pubDate"),
                        "source": art.get("source_name"),
                        "country": art.get("country"),
                        "category": art.get("category"),
                        "image": art.get("image_url"),
                        "region": region_label,
                        "content": None
                    }
                    
                    with articles_lock:
                        all_articles.append(article_data)
                    
                    fetched += 1
                    if fetched >= limit:
                        break

                logging.info(f"✅ {cat} | {region_label}: {fetched}/{limit} articles")
                
                if fetched >= limit or not next_page:
                    break
                
                time.sleep(PER_REQUEST_SLEEP)

            logging.info(f"✅ Completed {cat} | {region_label}: {fetched} articles")

    return all_articles

def scrape_final_remaining(articles):
    """Final scrape for any remaining articles"""
    unscrapped = [art for art in articles if not art.get('content')]
    
    if not unscrapped:
        logging.info("✅ All articles already have content")
        return
    
    logging.info(f"🔍 Final scraping for remaining {len(unscrapped)} articles...")
    
    for i, article in enumerate(unscrapped):
        try:
            content = scrape_article_text(article.get('link'))
            article['content'] = content
            if (i + 1) % 20 == 0:
                logging.info(f"🔍 Final progress: {i+1}/{len(unscrapped)}")
            time.sleep(0.8)
        except Exception as e:
            article['content'] = None

def main():
    logging.info("🚀 Starting FIXED Rate-Limited Scraper...")
    
    try:
        nltk.data.find("tokenizers/punkt")
    except LookupError:
        nltk.download("punkt")

    today = datetime.utcnow().date()
    today_str = today.strftime("%Y-%m-%d")
    content_blob = f"{GCS_PREFIX}/news_with_content_{today_str}.csv"

    if gcs_blob_exists(GCS_BUCKET, content_blob):
        logging.info("✅ Already completed today")
        return

    start_time = datetime.now()
    articles = fetch_limited_articles()
    
    if not articles:
        logging.error("❌ No articles fetched")
        return

    # Final scraping for any remaining
    scrape_final_remaining(articles)
    
    # Save result
    df = pd.DataFrame(articles)
    local_file = f"news_with_content_{today_str}.csv"
    df.to_csv(local_file, index=False)
    upload_file_to_gcs(local_file, GCS_BUCKET, content_blob)
    
    duration = (datetime.now() - start_time).total_seconds() / 60
    with_content = len([art for art in articles if art.get('content')])
    
    logging.info(f"🎉 DONE! {len(df)} articles ({with_content} with content) in {duration:.1f} minutes")

if __name__ == "__main__":
    main()
