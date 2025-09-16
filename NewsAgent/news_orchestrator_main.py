"""
Main News Orchestrator: Trending News First Approach
"""

import os
import json
import pandas as pd
import faiss
import asyncio
from datetime import datetime, timedelta
from google.cloud import storage
from sentence_transformers import SentenceTransformer
import google.generativeai as genai

class MainNewsOrchestrator:
    """Main orchestrator focusing on trending news first"""

    def __init__(self, gemini_api_key=None):
        self.gcs_bucket = os.getenv("GCS_BUCKET", "news-hub")
        self.gemini_api_key = gemini_api_key

        # Initialize Gemini for queries
        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            self.llm = genai.GenerativeModel('gemini-1.5-pro')
        else:
            self.llm = None

        # Initialize embedder for queries
        try:
            self.embedder = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        except:
            self.embedder = None

        # Cache for data
        self.trending_cache = None
        self.full_dataset_cache = None

        print("🎯 Main News Orchestrator Ready!")

    def get_trending_news(self, region=None, category=None):
        """Get trending news (primary function)"""
        print("🔥 Fetching trending news...")

        # Load trending summary from cache or GCS
        trending_data = self._load_trending_summary()

        if not trending_data:
            return {
                "success": False,
                "message": "No trending news available. Please run trending extraction.",
                "data": {}
            }

        # Filter by region/category if specified
        if region and region in trending_data:
            if category and category in trending_data[region]:
                return {
                    "success": True,
                    "message": f"Trending {category} news in {region}",
                    "data": {region: {category: trending_data[region][category]}},
                    "generation_time": trending_data.get('generation_time')
                }
            else:
                return {
                    "success": True,
                    "message": f"All trending news in {region}",
                    "data": {region: trending_data[region]},
                    "generation_time": trending_data.get('generation_time')
                }

        # Return all trending news
        return {
            "success": True,
            "message": "All trending news",
            "data": {
                "India": trending_data.get('India', {}),
                "Global": trending_data.get('Global', {})
            },
            "generation_time": trending_data.get('generation_time')
        }

    def _load_trending_summary(self):
        """Load trending summary from GCS"""

        if self.trending_cache:
            return self.trending_cache

        try:
            # Try today and yesterday
            for days_back in range(2):
                date_obj = datetime.utcnow().date() - timedelta(days=days_back)
                date_str = date_obj.strftime("%Y-%m-%d")

                storage_client = storage.Client()
                bucket = storage_client.bucket(self.gcs_bucket)
                blob = bucket.blob(f"trending/{date_str}/summary.json")

                if blob.exists():
                    content = blob.download_as_text()
                    trending_data = json.loads(content)

                    # Cache it
                    self.trending_cache = trending_data
                    print(f"✅ Loaded trending data from {date_str}")
                    return trending_data

            return None

        except Exception as e:
            print(f"⚠️ Failed to load trending summary: {str(e)}")
            return None

    async def answer_query(self, user_query, max_results=5):
        """Answer specific queries using full dataset"""
        print(f"🔍 Processing query: '{user_query}'")

        if not self.embedder:
            return {
                "success": False,
                "message": "Query system not available",
                "query": user_query
            }

        # Load full dataset index
        success = self._load_full_dataset()

        if not success:
            return {
                "success": False,
                "message": "Full dataset not available for queries",
                "query": user_query
            }

        try:
            # Create query embedding
            query_embedding = self.embedder.encode([user_query], normalize_embeddings=True)
            query_embedding = query_embedding.astype('float32')

            # Search full dataset
            distances, indices = self.full_dataset_index.search(query_embedding, max_results)

            # Get relevant articles
            relevant_articles = []
            for dist, idx in zip(distances[0], indices[0]):
                if dist > 0.3 and idx < len(self.full_dataset_meta):
                    article = self.full_dataset_meta.iloc[idx].to_dict()
                    article['relevance_score'] = float(dist)
                    relevant_articles.append(article)

            if not relevant_articles:
                return {
                    "success": True,
                    "message": f"No relevant articles found for '{user_query}'",
                    "query": user_query,
                    "articles": []
                }

            # Generate AI summary if available
            if self.llm:
                summary = await self._generate_query_summary(user_query, relevant_articles)
            else:
                summary = self._generate_basic_query_summary(user_query, relevant_articles)

            return {
                "success": True,
                "message": summary,
                "query": user_query,
                "articles": relevant_articles[:3],
                "total_found": len(relevant_articles)
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Query processing failed: {str(e)}",
                "query": user_query
            }

    def _load_full_dataset(self):
        """Load full dataset index for queries"""

        if hasattr(self, 'full_dataset_index'):
            return True

        try:
            today_str = datetime.utcnow().date().strftime("%Y-%m-%d")

            storage_client = storage.Client()
            bucket = storage_client.bucket(self.gcs_bucket)

            # Download index and metadata
            index_blob = bucket.blob(f"full_dataset/{today_str}/index.faiss")
            meta_blob = bucket.blob(f"full_dataset/{today_str}/metadata.parquet")

            if index_blob.exists() and meta_blob.exists():
                # Download files
                local_index = f"/tmp/query_index.faiss"
                local_meta = f"/tmp/query_meta.parquet"

                index_blob.download_to_filename(local_index)
                meta_blob.download_to_filename(local_meta)

                # Load into memory
                self.full_dataset_index = faiss.read_index(local_index)
                self.full_dataset_meta = pd.read_parquet(local_meta)

                print(f"✅ Loaded full dataset: {len(self.full_dataset_meta)} articles")
                return True

            return False

        except Exception as e:
            print(f"⚠️ Failed to load full dataset: {str(e)}")
            return False

    async def _generate_query_summary(self, query, articles):
        """Generate AI summary for query results"""

        # Prepare article summaries
        article_texts = []
        for article in articles[:3]:
            title = article.get('title', 'No title')
            source = article.get('source', 'Unknown')
            desc = article.get('description', '')[:100]

            article_texts.append(f"- {title} ({source}): {desc}")

        newline = '\n'
        prompt = f"""Answer this news query based on the provided articles: "{query}"

Relevant articles:
{newline.join(article_texts)}

Provide a concise, informative answer that directly addresses the user's question using information from these articles. Keep it under 150 words."""

        try:
            response = await asyncio.to_thread(self.llm.generate_content, prompt)
            return response.text.strip()
        except Exception as e:
            return self._generate_basic_query_summary(query, articles)

    def _generate_basic_query_summary(self, query, articles):
        """Generate basic summary without AI"""

        if not articles:
            return f"No relevant articles found for '{query}'"

        top_article = articles[0]
        return f"Found {len(articles)} articles related to '{query}'. Top result: '{top_article.get('title', 'No title')}' from {top_article.get('source', 'Unknown source')}."

# Initialize main orchestrator
main_orchestrator = MainNewsOrchestrator
