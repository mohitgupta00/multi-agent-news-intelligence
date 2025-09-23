from .base_agent import BaseAgent, AgentResponse
from typing import Dict, Any, List

class ReportingAgent(BaseAgent):
    """
    An agent that synthesizes information from multiple sources
    into a coherent news report.
    """

    def __init__(self):
        super().__init__("ReportingAgent")

    async def execute(self, task: Dict[str, Any]) -> AgentResponse:
        query = task.get('query')
        articles = task.get('articles', [])

        if not query or not articles:
            return self.create_response(
                success=False,
                data={},
                message="Missing query or articles for reporting."
            )

        self.log_activity(f"Generating a report for the query: '{query}'")

        prompt = self._create_prompt(query, articles)

        try:
            # *** FIX: The method is called `_generate_content` in the base class ***
            report_text = await self._generate_content(prompt)

            summary = report_text.strip()

            # Map article fields for JavaScript compatibility
            mapped_articles = []
            for article in articles:
                mapped_article = article.copy()
                if 'url' in mapped_article and 'link' not in mapped_article:
                    mapped_article['link'] = mapped_article['url']
                mapped_articles.append(mapped_article)


            return self.create_response(
                success=True,
                data={"summary": summary, "articles": mapped_articles},
                message="Report generated successfully."
            )
        except Exception as e:
            self.log_activity(f"Report generation failed: {str(e)}")
            return self.create_response(
                success=False,
                data={"error": str(e)},
                message="Failed to generate report."
            )

    def _create_prompt(self, query: str, articles: List[Dict[str, Any]]) -> str:
        """Creates a detailed prompt for the LLM to generate a news report."""

        article_summaries = []
        for i, article in enumerate(articles):
            title = article.get('title', 'No Title')
            source = article.get('source', 'Unknown')
            description = article.get('description', 'No description available.')
            article_summaries.append(f"Source {i+1} ({source}): {title}\n{description}")

        articles_text = "\n\n".join(article_summaries)

        prompt = f"""You are a senior news reporter. Your task is to answer the user's query based on a provided list of news articles.

User Query: {query}

Synthesize the information from the following articles to generate a concise, well-written summary that directly answers the user's question.
- Start with a headline-style summary.
- Then, provide a 2-4 paragraph summary of the key events, trends, or findings.
- Do not make up information. Base your report only on the content of the articles provided below.
- At the end of your report, list the articles you used as sources, for example: "Sources: 1, 2."

Here are the articles:
---
{articles_text}
---

Your Final Report:
"""

        return prompt
