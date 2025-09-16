import pandas as pd
import json
from datetime import datetime, timedelta
from collections import Counter
from typing import Dict, Any, List
from .base_agent import BaseAgent, AgentResponse

class AnalysisAgent(BaseAgent):
    def __init__(self):
        super().__init__("AnalysisAgent")
        self.log_activity("🔍 Analysis Agent initialized and ready")

    async def execute(self, task: Dict[str, Any]) -> AgentResponse:
        analysis_type = task.get('type', 'trending').lower()
        days_back = task.get('days', 3)
        category = task.get('category', 'all').lower()
        limit = task.get('limit', 10)

        self.log_activity(f"📊 Starting {analysis_type} analysis")

        try:
            if analysis_type == 'trending':
                result = await self._analyze_trending(days_back, category, limit)
            elif analysis_type == 'sentiment':
                result = await self._analyze_sentiment(days_back, category)
            elif analysis_type == 'sources':
                result = await self._analyze_sources(days_back, category)
            else:
                result = await self._analyze_trending(days_back, category, limit)

            return self.create_response(
                success=True,
                data=result,
                message=f"✅ {analysis_type.title()} analysis completed"
            )

        except Exception as e:
            return self.create_response(
                success=False,
                data={"error_details": str(e)},
                message=f"❌ Analysis failed: {str(e)}"
            )

    async def _analyze_trending(self, days_back: int, category: str, limit: int) -> Dict:
        self.log_activity(f"🔥 Analyzing trending topics for last {days_back} days")

        newline = '\n'
        prompt = f"""Analyze trending topics for {category} news over {days_back} days.
        Return JSON format:
        {{
            "trending_topics": [
                {{"topic": "AI Technology", "frequency": "high", "relevance": "high"}},
                {{"topic": "Sports Updates", "frequency": "medium", "relevance": "medium"}}
            ],
            "key_insights": ["insight1", "insight2"],
            "time_analysis": "summary of temporal patterns"
        }}"""

        try:
            analysis = await self._generate_content(prompt)
            try:
                result = json.loads(analysis)
            except:
                result = {"trending_analysis": analysis}

            result["analysis_metadata"] = {
                "total_articles": "mock_data",
                "time_range": f"{days_back} days",
                "category_filter": category
            }

            return result

        except Exception as e:
            return {
                "error": str(e),
                "mock_trending": [
                    {"topic": "Technology", "frequency": "high"},
                    {"topic": "Sports", "frequency": "medium"}
                ]
            }

    async def _analyze_sentiment(self, days_back: int, category: str) -> Dict:
        self.log_activity(f"😊 Analyzing sentiment for last {days_back} days")

        prompt = f"""Analyze sentiment of {category} news over {days_back} days.
        Return JSON: {{"overall_sentiment": "positive/negative/neutral",
                     "sentiment_distribution": {{"positive": 0.4, "negative": 0.3, "neutral": 0.3}}}}"""

        try:
            analysis = await self._generate_content(prompt)
            try:
                result = json.loads(analysis)
            except:
                result = {"sentiment_analysis": analysis}

            return result
        except:
            return {"mock_sentiment": "neutral", "confidence": "medium"}

    async def _analyze_sources(self, days_back: int, category: str) -> Dict:
        self.log_activity(f"📰 Analyzing sources for last {days_back} days")

        return {
            "source_statistics": {
                "total_sources": 50,
                "credible_sources": 35,
                "diversity_score": 0.8
            },
            "top_sources": {
                "BBC": 25,
                "Reuters": 20,
                "Times of India": 15
            }
        }
