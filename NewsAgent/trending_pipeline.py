"""
Fixed Trending Pipeline: Better region detection for Global vs India
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from google.cloud import storage
from transformers import pipeline
import json
import asyncio
import google.generativeai as genai

class TrendingNewsExtractor:
    """Extract trending news with improved region detection"""

    def __init__(self):
        self.gcs_bucket = os.getenv("GCS_BUCKET", "news-hub")
        self.gcs_prefix = os.getenv("GCS_PREFIX", "news_data")
        self.categories = ["sports", "politics", "technology", "health", "crime", "entertainment"]

        # Initialize Gemini
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            self.llm = genai.GenerativeModel('gemini-1.5-pro')
            print("🤖 Gemini enabled for trending analysis")
        else:
            self.llm = None

        # Load classifier
        try:
            self.classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli", device=-1)
            print("✅ Classification model loaded")
        except Exception as e:
            print(f"⚠️ Classifier failed: {str(e)}")
            self.classifier = None

    def get_latest_24hr_data(self):
        """Download latest 24hr news data"""
        today = datetime.utcnow().date()
        yesterday = today - timedelta(days=1)

        for date_to_try in [today, yesterday]:
            date_str = date_to_try.strftime("%Y-%m-%d")

            try:
                storage_client = storage.Client()
                bucket = storage_client.bucket(self.gcs_bucket)

                for filename in [f"news_with_content_{date_str}.csv", f"data_{date_str}.csv"]:
                    blob_name = f"{self.gcs_prefix}/{filename}"
                    blob = bucket.blob(blob_name)

                    if blob.exists():
                        local_path = f"/tmp/{filename}"
                        blob.download_to_filename(local_path)
                        print(f"✅ Downloaded 24hr data: {blob_name}")
                        return local_path, date_str
            except Exception as e:
                continue

        return None, None

    def assign_region_smart(self, df):
        """Improved region assignment logic"""
        print("🌍 Assigning regions with improved logic...")

        def detect_region(row):
            """Detect if article is India-focused or Global"""

            # Check country field first
            if 'country' in row and pd.notna(row['country']):
                country = str(row['country']).strip().upper()
                if country in ['IN', 'IND', 'INDIA']:
                    return 'India'

            # Check source field for Indian sources
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

            # Check title and description for India-related keywords
            text_fields = []
            for field in ['title', 'description', 'content']:
                if field in row and pd.notna(row[field]):
                    text_fields.append(str(row[field]).lower())

            combined_text = ' '.join(text_fields)

            # Strong India indicators
            india_keywords = [
                'india', 'indian', 'delhi', 'mumbai', 'bangalore', 'chennai',
                'kolkata', 'hyderabad', 'pune', 'modi', 'bjp', 'congress',
                'rupee', 'bollywood', 'ipl', 'bcci'
            ]

            # Count India-related mentions
            india_score = sum(1 for keyword in india_keywords if keyword in combined_text)

            # If significant India mentions, classify as India
            if india_score >= 2:
                return 'India'

            # Check for global indicators
            global_keywords = [
                'usa', 'america', 'uk', 'britain', 'china', 'europe', 'russia',
                'ukraine', 'nato', 'un ', 'world', 'international', 'global'
            ]

            global_score = sum(1 for keyword in global_keywords if keyword in combined_text)

            # Default classification logic
            if global_score > india_score:
                return 'Global'
            elif india_score > 0:
                return 'India'
            else:
                return 'Global'  # Default to Global for unclear cases

        # Apply region detection
        df['region'] = df.apply(detect_region, axis=1)

        # Show distribution
        region_counts = df['region'].value_counts()
        print(f"📊 Region distribution:")
        for region, count in region_counts.items():
            print(f"  {region}: {count} articles")

        return df

    def categorize_articles(self, df):
        """Categorize articles using local model"""
        print(f"🔄 Categorizing {len(df)} articles...")

        categories = []
        for _, row in df.iterrows():
            title = str(row.get('title', ''))
            description = str(row.get('description', ''))
            content = str(row.get('content', ''))[:200]

            category = self._categorize_single_article(title, description, content)
            categories.append(category)

        df['pred_category'] = categories

        # Filter to target categories only
        df_filtered = df[df['pred_category'].isin(self.categories)]

        print(f"✅ Filtered to {len(df_filtered)} articles in target categories")
        return df_filtered

    def _categorize_single_article(self, title, description, content):
        """Categorize single article"""
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
        """Keyword-based categorization fallback"""
        text_lower = str(text).lower()

        keywords = {
            'sports': ['sport', 'game', 'match', 'player', 'team', 'football', 'cricket', 'tennis'],
            'politics': ['politic', 'government', 'election', 'minister', 'parliament', 'vote'],
            'technology': ['tech', 'ai', 'software', 'computer', 'digital', 'app', 'startup'],
            'health': ['health', 'medical', 'doctor', 'hospital', 'covid', 'vaccine', 'medicine'],
            'crime': ['crime', 'police', 'arrest', 'court', 'murder', 'theft', 'investigation'],
            'entertainment': ['movie', 'film', 'music', 'celebrity', 'actor', 'entertainment']
        }

        scores = {}
        for category, words in keywords.items():
            scores[category] = sum(1 for word in words if word in text_lower)

        return max(scores.items(), key=lambda x: x[1])[0] if max(scores.values()) > 0 else 'general'

    def extract_trending_by_category_region(self, df):
        """Extract trending news by category and region"""
        print("📈 Extracting trending news...")

        trending_summary = {
            'India': {},
            'Global': {},
            'generation_time': datetime.utcnow().isoformat(),
            'data_date': datetime.utcnow().date().strftime("%Y-%m-%d")
        }

        # Process each region
        for region in ['India', 'Global']:
            region_df = df[df['region'] == region]

            print(f"📍 Processing {region}: {len(region_df)} articles")

            if len(region_df) == 0:
                print(f"⚠️ No articles found for {region} region")
                continue

            # Process each category
            for category in self.categories:
                category_df = region_df[region_df['pred_category'] == category]

                if len(category_df) == 0:
                    continue

                trending_stories = self._extract_category_trends(category_df, category, region)

                if trending_stories:
                    trending_summary[region][category] = trending_stories

        return trending_summary

    def _extract_category_trends(self, category_df, category, region):
        """Extract trending stories for a specific category"""

        # Sort by relevance/recency
        category_df = category_df.copy()

        # Simple trending score
        category_df['trending_score'] = (
            category_df['source'].notna().astype(int) * 0.3 +
            category_df['description'].str.len().fillna(0) / 100 * 0.4 +
            np.random.random(len(category_df)) * 0.3
        )

        # Get top 5 trending stories
        top_stories = category_df.nlargest(5, 'trending_score')

        trending_stories = {
            'count': len(category_df),
            'top_stories': [],
            'summary': f"Found {len(category_df)} {category} stories from {region}"
        }

        for _, story in top_stories.iterrows():
            story_data = {
                'title': str(story.get('title', 'No title')),
                'source': str(story.get('source', 'Unknown')),
                'description': str(story.get('description', ''))[:200] + "...",
                'trending_score': float(story.get('trending_score', 0)),
                'region': story.get('region', region)
            }
            trending_stories['top_stories'].append(story_data)

        return trending_stories

    async def generate_ai_summaries(self, trending_summary):
        """Generate AI summaries for trending topics"""
        if not self.llm:
            return trending_summary

        print("🤖 Generating AI summaries for trending topics...")

        for region in ['India', 'Global']:
            if region not in trending_summary:
                continue

            for category in trending_summary[region].keys():
                try:
                    category_data = trending_summary[region][category]

                    stories_text = []
                    for story in category_data['top_stories'][:3]:
                        stories_text.append(f"- {story['title']} ({story['source']})")

                    if stories_text:
                        newline = '\n'
                        prompt = f"""Create a brief trending news summary for {category} news in {region}.

Top stories:
{newline.join(stories_text)}

Write a 2-3 sentence summary highlighting the key trends and developments. Be concise and informative."""

                        response = await asyncio.to_thread(self.llm.generate_content, prompt)

                        if response and response.text:
                            trending_summary[region][category]['ai_summary'] = response.text.strip()

                except Exception as e:
                    print(f"⚠️ AI summary failed for {region}-{category}: {str(e)}")
                    continue

        return trending_summary

    def save_trending_summary(self, trending_summary, date_str):
        """Save trending summary to GCS"""
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

    async def run_trending_extraction(self):
        """Main trending extraction pipeline"""
        print("🔥 Starting FIXED Trending News Extraction")
        print("=" * 50)

        try:
            # Step 1: Get latest 24hr data
            data_path, date_str = self.get_latest_24hr_data()

            if not data_path:
                print("❌ No 24hr data available")
                return False

            # Step 2: Load and assign regions smartly
            df = pd.read_csv(data_path)
            print(f"✅ Loaded {len(df)} articles from last 24hrs")

            df = self.assign_region_smart(df)

            # Step 3: Categorize articles
            df_categorized = self.categorize_articles(df)

            # Step 4: Extract trending by category/region
            trending_summary = self.extract_trending_by_category_region(df_categorized)

            # Step 5: Generate AI summaries
            trending_summary = await self.generate_ai_summaries(trending_summary)

            # Step 6: Save trending summary
            success = self.save_trending_summary(trending_summary, date_str)

            if success:
                print("\n🎉 FIXED TRENDING EXTRACTION COMPLETE!")
                print("=" * 40)

                # Show detailed summary
                for region in ['India', 'Global']:
                    if region in trending_summary and trending_summary[region]:
                        print(f"\n📍 {region}:")
                        for category, data in trending_summary[region].items():
                            print(f"  ✅ {category}: {data['count']} stories")
                    else:
                        print(f"\n📍 {region}: No trending stories found")

                return trending_summary
            else:
                return False

        except Exception as e:
            print(f"❌ Trending extraction failed: {str(e)}")
            return False

# Initialize fixed trending extractor
trending_extractor_fixed = TrendingNewsExtractor()
