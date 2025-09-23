"""
Main News Orchestrator: Integrates ReportingAgent for query summarization.
"""

import os
import json
import asyncio
import traceback
from datetime import datetime, timedelta
from google.cloud import storage
import google.generativeai as genai

from agents.search_agent import SearchAgent
from agents.reporting_agent import ReportingAgent # Import the new agent

class MainNewsOrchestrator:
    """Orchestrator that now uses a ReportingAgent for query summarization."""

    def __init__(self, gemini_api_key=None):
        self.gcs_bucket = os.getenv("GCS_BUCKET", "news-hub")
        # FIX: Prioritize passed key, but fall back to environment variable.
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")

        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
        else:
            # Add a warning if no key is found at all.
            print("⚠️ WARNING: GEMINI_API_KEY not found in constructor or environment variables. LLM functionality will be disabled.")


        # Initialize all agents
        self.search_agent = SearchAgent()
        self.reporting_agent = ReportingAgent() # Initialize the new agent
        print("✅ Search and Reporting agents initialized.")

        self.llm = None
        self.trending_cache = None

        print("🎯 Main News Orchestrator Ready with Summarization!")

    def _load_llm(self):
        """Loads the Gemini model on demand."""
        if self.llm is None and self.gemini_api_key:
            try:
                print("🤖 Initializing Gemini Model for the first time...")
                self.llm = genai.GenerativeModel('gemini-1.5-pro')
                # Assign LLM to agents that need it
                self.search_agent.llm = self.llm
                self.reporting_agent.llm = self.llm
                print("✅ Gemini Model Initialized and passed to agents.")
            except Exception as e:
                print(f"❌ Failed to initialize Gemini Model: {e}")

    def get_trending_news(self, region=None, category=None):
        trending_data = self._load_trending_summary()
        if not trending_data:
            return {"success": False, "message": "No trending news available. Please run the background job.", "data": {}}
        if region and region in trending_data:
            if category and category in trending_data[region]:
                return {"success": True, "message": f"Trending {category} news in {region}", "data": {region: {category: trending_data[region][category]}}, "generation_time": trending_data.get('generation_time')}
            else:
                return {"success": True, "message": f"All trending news in {region}", "data": {region: trending_data[region]}, "generation_time": trending_data.get('generation_time')}
        return {"success": True, "message": "All trending news", "data": {"India": trending_data.get('India', {}), "Global": trending_data.get('Global', {})}, "generation_time": trending_data.get('generation_time')}

    def _load_trending_summary(self):
        if self.trending_cache:
            return self.trending_cache
        try:
            for days_back in range(3):
                date_str = (datetime.utcnow().date() - timedelta(days=days_back)).strftime("%Y-%m-%d")
                storage_client = storage.Client()
                bucket = storage_client.bucket(self.gcs_bucket)
                blob = bucket.blob(f"trending/{date_str}/summary.json")
                if blob.exists():
                    print(f"✅ Loaded trending summary from {date_str}")
                    trending_data = json.loads(blob.download_as_text())
                    self.trending_cache = trending_data
                    return trending_data
            print("⚠️ No trending summary found in the last 3 days.")
            return None
        except Exception as e:
            print(f"⚠️ Failed to load trending summary: {str(e)}")
            return None

    async def answer_query(self, query: str, max_results: int = 5):
        """
        Answers a user query by first searching for relevant articles
        and then generating a summary report.
        """
        try:
            if not self.search_agent or not self.reporting_agent:
                return {"success": False, "message": "A required agent is not available."}

            self._load_llm() # Ensure LLM is loaded

            # Step 1: Search for relevant articles
            search_task = {"query": query, "top_k": max_results}
            search_response = await self.search_agent.execute(search_task)

            if not search_response.success:
                return {"success": False, "message": f"Search failed: {search_response.message}"}

            articles = search_response.data.get('articles')
            if not articles:
                return {"success": True, "message": "I found no relevant articles for your query."}

            # Step 2: Generate a report from the found articles
            reporting_task = {"query": query, "articles": articles}
            report_response = await self.reporting_agent.execute(reporting_task)

            if not report_response.success:
                 return {"success": False, "message": f"Reporting failed: {report_response.message}"}

            # Return the successful report from the reporting agent
            return {"success": True, **report_response.data}
        except Exception as e:
            print(f"❌ Unhandled error in answer_query: {e}")
            traceback.print_exc()
            return {"success": False, "message": "An unexpected error occurred while processing your query. Please try again later."}
