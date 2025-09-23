import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from google.cloud import storage
from transformers import pipeline
import json
import asyncio
import google.generativeai as genai
from sentence_transformers import SentenceTransformer
import faiss

class DataProcessingJob:
    def __init__(self):
        self.gcs_bucket = os.getenv("GCS_BUCKET", "news-hub")
        self.gcs_prefix = os.getenv("GCS_PREFIX", "news_data")
        self.categories = ["sports", "politics", "technology", "health", "crime", "entertainment"]
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.llm = None
        self.classifier = None
        self.embedder = None

    def setup_models(self):
        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            self.llm = genai.GenerativeModel('gemini-1.5-pro')
            print("🤖 Gemini enabled for trending analysis")

        try:
            self.classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli", device=-1)
            print("✅ Classification model loaded")
        except Exception as e:
            print(f"⚠️ Classifier failed: {str(e)}")

        try:
            self.embedder = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
            print("✅ SentenceTransformer model loaded")
        except Exception as e:
            print(f"⚠️ Embedder failed: {str(e)}")


    def get_latest_news_data(self):
        today = datetime.utcnow().date()
        for days_back in range(3): # Try today and last two days
            date_to_try = today - timedelta(days=days_back)
            date_str = date_to_try.strftime("%Y-%m-%d")
            try:
                storage_client = storage.Client()
                bucket = storage_client.bucket(self.gcs_bucket)
                blob_name = f"{self.gcs_prefix}/news_with_content_{date_str}.csv"
                blob = bucket.blob(blob_name)
                if blob.exists():
                    local_path = f"/tmp/news_data_{date_str}.csv"
                    blob.download_to_filename(local_path)
                    print(f"✅ Downloaded data for {date_str}: {blob_name}")
                    return pd.read_csv(local_path), date_str
            except Exception as e:
                print(f"Could not download data for {date_str}. Error: {e}")
                continue
        return None, None

    def run_trending_extraction(self, df, date_str):
        print("--- Starting Trending Topic Processing ---")
        df_regional = self.assign_region_smart(df)
        df_categorized = self.categorize_articles(df_regional)
        trending_summary = self.extract_trending_by_category_region(df_categorized)
        trending_summary = asyncio.run(self.generate_ai_summaries(trending_summary))
        self.save_trending_summary(trending_summary, date_str)
        print("--- Finished Trending Topic Processing ---")

    def build_faiss_index(self, df, date_str):
        print("--- Starting Faiss Index Processing ---")
        if not self.embedder:
            print("❌ Cannot process Faiss index, embedder not loaded.")
            return

        # Ensure the 'link' column exists, if not, create it as empty
        if 'link' not in df.columns:
            df['link'] = ''

        # Fill NaN values in critical columns to prevent errors
        df['title'] = df['title'].fillna('No Title')
        df['description'] = df['description'].fillna('')
        df['link'] = df['link'].fillna('')

        texts = []
        valid_rows = []
        for _, row in df.iterrows():
            text = f"{row['title']} {row['description']}".strip()
            if len(text) > 20:
                texts.append(text[:1000])
                valid_rows.append(row.to_dict())

        if not texts:
            print("❌ No valid texts found for indexing.")
            return

        print(f"🧠 Creating embeddings for {len(texts)} articles...")
        embeddings = self.embedder.encode(texts, normalize_embeddings=True, show_progress_bar=True)

        dimension = embeddings.shape[1]
        index = faiss.IndexFlatIP(dimension)
        index.add(embeddings.astype('float32'))
        print(f"✅ FAISS index built with {index.ntotal} vectors")

        storage_client = storage.Client()
        bucket = storage_client.bucket(self.gcs_bucket)

        temp_index_path = "/tmp/faiss_index.index"
        faiss.write_index(index, temp_index_path)
        index_blob = bucket.blob(f"full_dataset/{date_str}/faiss_index.index")
        index_blob.upload_from_filename(temp_index_path)
        print(f"✅ Saved Faiss index to GCS: {index_blob.name}")

        metadata = {'articles': valid_rows}
        temp_meta_path = "/tmp/metadata.json"
        with open(temp_meta_path, 'w') as f:
            json.dump(metadata, f)
        meta_blob = bucket.blob(f"full_dataset/{date_str}/metadata.json")
        meta_blob.upload_from_filename(temp_meta_path)
        print(f"✅ Saved metadata to GCS: {meta_blob.name}")
        print("--- Finished Faiss Index Processing ---")

    def assign_region_smart(self, df):
        print("🌍 Assigning regions with improved logic...")
        def detect_region(row):
            if 'country' in row and pd.notna(row['country']):
                country = str(row['country']).strip().upper()
                if country in ['IN', 'IND', 'INDIA']:
                    return 'India'
            if 'source' in row and pd.notna(row['source']):
                source = str(row['source']).lower()
                indian_sources = [
                    'times of india', 'toi', 'hindustan times', 'indian express',
                    'ndtv', 'zee news', 'aaj tak', 'india today', 'news18',
                    'firstpost', 'livemint', 'economic times', 'dna india',
                    'deccan herald', 'the hindu', 'outlook india'
                ]
                if any(indian_source in source for indian_source in indian_sources):
                    return 'India'
            text_fields = []
            for field in ['title', 'description', 'content']:
                if field in row and pd.notna(row[field]):
                    text_fields.append(str(row[field]).lower())
            combined_text = ' '.join(text_fields)
            india_keywords = [
                'india', 'indian', 'delhi', 'mumbai', 'bangalore', 'chennai',
                'kolkata', 'hyderabad', 'pune', 'modi', 'bjp', 'congress',
                'rupee', 'bollywood', 'ipl', 'bcci'
            ]
            india_score = sum(1 for keyword in india_keywords if keyword in combined_text)
            if india_score >= 2:
                return 'India'
            global_keywords = [
                'usa', 'america', 'uk', 'britain', 'china', 'europe', 'russia',
                'ukraine', 'nato', 'un ', 'world', 'international', 'global'
            ]
            global_score = sum(1 for keyword in global_keywords if keyword in combined_text)
            if global_score > india_score:
                return 'Global'
            elif india_score > 0:
                return 'India'
            else:
                return 'Global'
        df['region'] = df.apply(detect_region, axis=1)
        region_counts = df['region'].value_counts()
        print(f"📊 Region distribution:")
        for region, count in region_counts.items():
            print(f"  {region}: {count} articles")
        return df

    def categorize_articles(self, df):
        print(f"🔄 Categorizing {len(df)} articles...")
        categories = []
        for _, row in df.iterrows():
            title = str(row.get('title', ''))
            description = str(row.get('description', ''))
            content = str(row.get('content', ''))[:200]
            category = self._categorize_single_article(title, description, content)
            categories.append(category)
        df['pred_category'] = categories
        df_filtered = df[df['pred_category'].isin(self.categories)]
        print(f"✅ Filtered to {len(df_filtered)} articles in target categories")
        return df_filtered

    def _categorize_single_article(self, title, description, content):
        if not self.classifier:
            return self._keyword_categorize(f"{title} {description} {content}")
        try:
            text = f"{title}. {description}. {content}".strip()
            if len(text) < 10:
                return 'general'
            result = self.classifier(text, self.categories)
            if result and 'labels' in result and 'scores' in result:
                best_category = result['labels'][0].lower()
                confidence = result['scores'][0]
                if confidence > 0.4 and best_category in self.categories:
                    return best_category
            return self._keyword_categorize(text)
        except Exception:
            return self._keyword_categorize(f"{title} {description}")

    def _keyword_categorize(self, text):
        text_lower = str(text).lower()
        keywords = {
            'sports': ['sport', 'game', 'match', 'player', 'team', 'football', 'cricket', 'tennis'],
            'politics': ['politic', 'government', 'election', 'minister', 'parliament', 'vote'],
            'technology': ['tech', 'ai', 'software', 'computer', 'digital', 'app', 'startup'],
            'health': ['health', 'medical', 'doctor', 'hospital', 'covid', 'vaccine', 'medicine'],
            'crime': ['crime', 'police', 'arrest', 'court', 'murder', 'theft', 'investigation'],
            'entertainment': ['movie', 'film', 'music', 'celebrity', 'actor', 'entertainment']
        }
        scores = {cat: sum(1 for word in words if word in text_lower) for cat, words in keywords.items()}
        return max(scores.items(), key=lambda x: x[1])[0] if max(scores.values()) > 0 else 'general'

    def extract_trending_by_category_region(self, df):
        print("📈 Extracting trending news...")
        trending_summary = {
            'India': {},
            'Global': {},
            'generation_time': datetime.utcnow().isoformat(),
            'data_date': datetime.utcnow().date().strftime("%Y-%m-%d")
        }
        for region in ['India', 'Global']:
            region_df = df[df['region'] == region]
            print(f"📍 Processing {region}: {len(region_df)} articles")
            if len(region_df) == 0:
                continue
            for category in self.categories:
                category_df = region_df[region_df['pred_category'] == category]
                if len(category_df) > 0:
                    trending_stories = self._extract_category_trends(category_df, category, region)
                    if trending_stories:
                        trending_summary[region][category] = trending_stories
        return trending_summary

    def _extract_category_trends(self, category_df, category, region):
        category_df = category_df.copy()
        category_df['trending_score'] = (category_df['source'].notna().astype(int) * 0.3 + category_df['description'].str.len().fillna(0) / 100 * 0.4 + np.random.random(len(category_df)) * 0.3)
        top_stories = category_df.nlargest(5, 'trending_score')
        trending_stories = {'count': len(category_df), 'top_stories': [], 'summary': f"Found {len(category_df)} {category} stories from {region}"}
        for _, story in top_stories.iterrows():
            story_data = {
                'title': str(story.get('title', 'No title')),
                'source': str(story.get('source', 'Unknown')),
                'description': str(story.get('description', ''))[:200] + "...",
                'url': str(story.get('link', '')),  # FIX: Add the 'link' as 'url'
                'trending_score': float(story.get('trending_score', 0)),
                'region': story.get('region', region)
            }
            trending_stories['top_stories'].append(story_data)
        return trending_stories

    async def generate_ai_summaries(self, trending_summary):
        if not self.llm:
            return trending_summary
        print("🤖 Generating AI summaries for trending topics...")
        for region in ['India', 'Global']:
            if region not in trending_summary: continue
            for category in trending_summary[region].keys():
                try:
                    category_data = trending_summary[region][category]
                    stories_text = [f"- {story['title']} ({story['source']})" for story in category_data['top_stories'][:3]]
                    if stories_text:
                        newline = '\n'
                        prompt = f"""Create a brief trending news summary for {category} news in {region}.\n\nTop stories:\n{newline.join(stories_text)}\n\nWrite a 2-3 sentence summary highlighting the key trends and developments. Be concise and informative."""
                        response = await asyncio.to_thread(self.llm.generate_content, prompt)
                        if response and response.text:
                            trending_summary[region][category]['ai_summary'] = response.text.strip()
                except Exception as e:
                    print(f"⚠️ AI summary failed for {region}-{category}: {str(e)}")
        return trending_summary

    def save_trending_summary(self, trending_summary, date_str):
        print("💾 Saving trending summary...")
        try:
            local_path = f"/tmp/trending_summary_{date_str}.json"
            with open(local_path, 'w') as f:
                json.dump(trending_summary, f, indent=2, ensure_ascii=False)
            storage_client = storage.Client()
            bucket = storage_client.bucket(self.gcs_bucket)
            blob_name = f"trending/{date_str}/summary.json"
            blob = bucket.blob(blob_name)
            blob.upload_from_filename(local_path)
            print(f"✅ Trending summary saved: gs://{self.gcs_bucket}/{blob_name}")
            return True
        except Exception as e:
            print(f"❌ Failed to save trending summary: {str(e)}")
            return False

    def run(self):
        print("🚀 Starting daily data processing job...")
        self.setup_models()
        df, date_str = self.get_latest_news_data()
        if df is not None:
            self.run_trending_extraction(df.copy(), date_str)
            self.build_faiss_index(df.copy(), date_str)
            print("🎉 Job finished successfully!")
        else:
            print("❌ No data found to process. Exiting job.")

if __name__ == "__main__":
    job = DataProcessingJob()
    job.run()
