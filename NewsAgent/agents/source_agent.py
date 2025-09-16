import json
from urllib.parse import urlparse
from typing import Dict, Any, List
from .base_agent import BaseAgent, AgentResponse

class SourceAgent(BaseAgent):
    def __init__(self):
        super().__init__("SourceAgent")
        self.credible_sources = {
            'high_credibility': ['reuters', 'bbc', 'associated press', 'bloomberg'],
            'medium_credibility': ['cnn', 'times of india', 'hindustan times'],
            'questionable': ['unknown', 'blog', 'unverified']
        }
        self.log_activity("📰 Source credibility database loaded")

    async def execute(self, task: Dict[str, Any]) -> AgentResponse:
        source_url = task.get('url', '').strip()
        source_name = task.get('source', '').strip()
        analysis_type = task.get('analysis_type', 'comprehensive').lower()

        if not source_url and not source_name:
            return self.create_response(
                success=False,
                data={},
                message="❌ Either source URL or name required"
            )

        self.log_activity(f"🔍 Analyzing source: {source_name or source_url}")

        try:
            if analysis_type == 'credibility':
                result = await self._analyze_credibility(source_url, source_name)
            else:
                result = await self._comprehensive_analysis(source_url, source_name)

            return self.create_response(
                success=True,
                data=result,
                message=f"✅ Source analysis completed"
            )

        except Exception as e:
            return self.create_response(
                success=False,
                data={"error_details": str(e)},
                message=f"❌ Analysis failed: {str(e)}"
            )

    async def _analyze_credibility(self, url: str, source: str) -> Dict:
        database_score, level = self._check_source_database(source)

        prompt = f"""Analyze credibility of news source: {source} (URL: {url})
        Return JSON: {{"credibility_score": 0.0-1.0, "credibility_level": "high/medium/low",
                     "trust_indicators": ["indicator1"], "red_flags": ["flag1"]}}"""

        try:
            analysis = await self._generate_content(prompt)
            try:
                ai_result = json.loads(analysis)
            except:
                ai_result = {"credibility_analysis": analysis}
        except:
            ai_result = {}

        return {
            "credibility_assessment": {
                "database_score": database_score,
                "database_level": level,
                **ai_result
            },
            "source_metadata": {"source_name": source, "source_url": url}
        }

    async def _comprehensive_analysis(self, url: str, source: str) -> Dict:
        credibility = await self._analyze_credibility(url, source)

        return {
            "comprehensive_analysis": {
                "credibility": credibility,
                "overall_rating": "good" if credibility["credibility_assessment"]["database_score"] > 0.7 else "fair"
            }
        }

    def _check_source_database(self, source: str) -> tuple:
        if not source:
            return 0.5, "unknown"

        source_lower = source.lower()

        for level, sources in self.credible_sources.items():
            for known_source in sources:
                if known_source in source_lower:
                    if level == 'high_credibility':
                        return 0.9, 'high'
                    elif level == 'medium_credibility':
                        return 0.7, 'medium'
                    else:
                        return 0.3, 'questionable'

        return 0.5, "unknown"
