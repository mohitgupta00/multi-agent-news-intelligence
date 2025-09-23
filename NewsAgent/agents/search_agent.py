import pandas as pd
import numpy as np
import faiss
import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
from .base_agent import BaseAgent, AgentResponse
from google.cloud import storage
from sentence_transformers import SentenceTransformer

class SearchAgent(BaseAgent):
    """
    An agent that performs semantic search over the indexed news articles
    stored in Google Cloud Storage.
    """
    def __init__(self):
        super().__init__("SearchAgent")
        self.gcs_bucket = os.getenv("GCS_BUCKET", "news-hub")
        self.index = None
        self.meta = None

        # Use the public HuggingFace path for local testing and the local path for Docker.
        model_path = 'sentence-transformers/all-MiniLM-L6-v2'
        local_model_dir = 'all-MiniLM-L6-v2-local'
        if os.path.exists(local_model_dir):
            model_path = local_model_dir

        try:
            self.log_activity(f"📥 Loading sentence transformer model: {model_path}...")
            self.embedder = SentenceTransformer(model_path)
            self.log_activity("✅ Sentence transformer loaded.")
        except Exception as e:
            self.log_activity(f"❌ CRITICAL: Failed to load sentence transformer model: {e}")
            self.embedder = None # Ensure embedder is None on failure

        self._load_indices()

    def _load_indices(self):
        if self.index is not None and self.meta is not None:
            self.log_activity("✅ Index and metadata already loaded.")
            return

        if not self.embedder:
            self.log_activity("⚠️ Cannot load indices because embedder is not available.")
            return

        self.log_activity("🔍 Searching for latest news index in GCS...")
        try:
            storage_client = storage.Client()
            bucket = storage_client.bucket(self.gcs_bucket)

            for days_back in range(3):
                date_str = (datetime.utcnow().date() - timedelta(days=days_back)).strftime("%Y-%m-%d")
                index_path = f"full_dataset/{date_str}/faiss_index.index"
                meta_path = f"full_dataset/{date_str}/metadata.json"

                index_blob = bucket.blob(index_path)
                meta_blob = bucket.blob(meta_path)

                if index_blob.exists() and meta_blob.exists():
                    self.log_activity(f"✅ Found dataset for {date_str}. Downloading...")

                    local_index_path = "/tmp/agent_faiss_index.index"
                    index_blob.download_to_filename(local_index_path)
                    self.index = faiss.read_index(local_index_path)

                    meta_content = meta_blob.download_as_string()
                    self.meta = pd.DataFrame(json.loads(meta_content).get('articles', []))

                    self.log_activity(f"✅ Index loaded with {self.index.ntotal} vectors and {len(self.meta)} articles.")
                    if 'url' not in self.meta.columns:
                        self.log_activity("⚠️ 'url' column is missing from the metadata. Links in search results will not work.")
                    return

            self.log_activity("⚠️ No recent news index found in GCS. Search will be unavailable until the job runs.")
        except Exception as e:
            self.log_activity(f"❌ Failed during index loading: {e}. Search will be unavailable.")
            self.index = None
            self.meta = None

    async def execute(self, task: Dict[str, Any]) -> AgentResponse:
        query = task.get('query', '').strip()
        top_k = task.get('top_k', 5)

        if not query:
            return self.create_response(success=False, data={}, message="❌ No search query provided")

        if self.index is None or self.meta is None:
            self._load_indices()

        if not self.index or self.meta is None or self.embedder is None:
            return self.create_response(success=False, data={}, message="Search is temporarily unavailable. The data may still be processing.")

        self.log_activity(f"🧠 Performing semantic search for: '{query}' (top_k: {top_k})")
        try:
            enhanced_query = await self._enhance_query(query)
            self.log_activity(f"✨ Enhanced query: '{enhanced_query}'")
            query_embedding = self.embedder.encode([enhanced_query], normalize_embeddings=True).astype('float32')
            distances, indices = self.index.search(query_embedding, top_k)

            raw_results = [self.meta.iloc[idx].to_dict() | {'relevance_score': float(distances[0][i])} for i, idx in enumerate(indices[0]) if idx < len(self.meta)]

            results = []
            for r in raw_results:
                cleaned_article = {}
                for key, value in r.items():
                    if pd.isna(value):
                        cleaned_article[key] = None
                    elif isinstance(value, np.generic):
                        cleaned_article[key] = value.item()
                    else:
                        cleaned_article[key] = value
                results.append(cleaned_article)

            return self.create_response(
                success=True,
                data={"articles": results, "original_query": query, "enhanced_query": enhanced_query},
                message=f"✅ Found {len(results)} relevant articles."
            )
        except Exception as e:
            self.log_activity(f"❌ Search execution failed: {str(e)}")
            return self.create_response(success=False, data={"error_details": str(e)}, message=f"❌ Search failed: {str(e)}")

    async def _enhance_query(self, query: str) -> str:
        prompt = f'Rewrite the user\'s news query for a semantic search engine. Focus on keywords and concepts. Query: "{query}"'
        if not self.llm: return query
        try:
            enhanced = await self._generate_content(prompt)
            return enhanced.strip().replace('"', '') if enhanced else query
        except Exception as e:
            self.log_activity(f"⚠️ Could not enhance query. Error: {e}")
            return query
