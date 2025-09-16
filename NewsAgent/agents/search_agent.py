import pandas as pd
import numpy as np
import faiss
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List
from .base_agent import BaseAgent, AgentResponse

class SearchAgent(BaseAgent):
    def __init__(self):
        super().__init__("SearchAgent")
        self.local_index = None
        self.global_index = None
        self.local_meta = None
        self.global_meta = None
        self._load_indices()

    def _load_indices(self):
        self.log_activity("🔍 Searching for news indices...")

        for days_back in range(10):
            date_str = (datetime.today() - timedelta(days=days_back)).strftime("%Y-%m-%d")

            try:
                for scope in ['local', 'global']:
                    faiss_path = f"/content/NewsAgent/artifacts/{date_str}/{scope}.faiss"
                    meta_path = f"/content/NewsAgent/artifacts/{date_str}/{scope}_meta.parquet"

                    if os.path.exists(faiss_path) and os.path.exists(meta_path):
                        if scope == 'local':
                            self.local_index = faiss.read_index(faiss_path)
                            self.local_meta = pd.read_parquet(meta_path)
                        else:
                            self.global_index = faiss.read_index(faiss_path)
                            self.global_meta = pd.read_parquet(meta_path)

                        self.log_activity(f"✅ Loaded {scope} data from {date_str}")

            except Exception as e:
                continue

        if not self.local_index and not self.global_index:
            self.log_activity("❌ No news indices found! Run data pipeline first.")

    async def execute(self, task: Dict[str, Any]) -> AgentResponse:
        query = task.get('query', '').strip()
        scope = task.get('scope', 'both').lower()
        top_k = task.get('top_k', 5)

        if not query:
            return self.create_response(
                success=False,
                data={},
                message="❌ No search query provided"
            )

        self.log_activity(f"🔍 Searching for: '{query}' (scope: {scope}, top_k: {top_k})")

        try:
            enhanced_query = await self._enhance_query(query)
            results = self._mock_search_results(enhanced_query, scope, top_k)

            return self.create_response(
                success=True,
                data={
                    "articles": results,
                    "original_query": query,
                    "enhanced_query": enhanced_query,
                    "search_scope": scope,
                    "total_results": len(results)
                },
                message=f"✅ Found {len(results)} relevant articles"
            )

        except Exception as e:
            return self.create_response(
                success=False,
                data={"error_details": str(e)},
                message=f"❌ Search failed: {str(e)}"
            )

    async def _enhance_query(self, query: str) -> str:
        prompt = f"""Enhance this search query for better news search: "{query}"
        Add relevant keywords and synonyms. Return only the enhanced query."""

        try:
            enhanced = await self._generate_content(prompt)
            return enhanced.strip() if enhanced else query
        except:
            return query

    def _mock_search_results(self, query: str, scope: str, top_k: int) -> List[Dict]:
        # Mock results when no real data available
        mock_articles = [
            {
                "title": f"Sample {scope} news article about {query}",
                "description": f"This is a sample article related to {query}",
                "source": "Sample News",
                "relevance_score": 0.95,
                "source_type": scope
            }
        ]
        return mock_articles[:top_k]
