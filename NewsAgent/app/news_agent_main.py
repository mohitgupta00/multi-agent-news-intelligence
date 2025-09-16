"""
Fixed FastAPI Application with improved dashboard rendering
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import sys
import logging
from datetime import datetime
from html import escape

# Add paths
sys.path.append('/app')
sys.path.append('/app/agents')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Multi-Agent News Intelligence API",
    description="AI-powered trending news analysis",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize orchestrator
try:
    from news_orchestrator_main import MainNewsOrchestrator
    orchestrator = MainNewsOrchestrator(os.getenv("GEMINI_API_KEY"))
    logger.info("✅ Orchestrator initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize orchestrator: {str(e)}")
    orchestrator = None

class QueryRequest(BaseModel):
    query: str
    max_results: int = 5

def safe_truncate(text, max_length=250):
    """Safely truncate text and add ellipsis"""
    if not text:
        return ""
    text = str(text).strip()
    if len(text) <= max_length:
        return text
    return text[:max_length].rsplit(' ', 1)[0] + "..."

def safe_html_escape(text):
    """Safely escape HTML characters"""
    if not text:
        return ""
    return escape(str(text))

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Improved trending news dashboard with fixed rendering"""

    if not orchestrator:
        return """
        <html><body style="font-family: Arial, sans-serif; padding: 20px;">
        <h1>📰 Multi-Agent News Intelligence</h1>
        <div style="color: red; padding: 15px; border: 1px solid red; background: #ffe6e6;">
            ❌ System not available. Check configuration.
        </div>
        </body></html>
        """

    try:
        trending = orchestrator.get_trending_news()

        if not trending['success']:
            return """
            <html><body style="font-family: Arial, sans-serif; padding: 20px;">
            <h1>📰 Multi-Agent News Intelligence</h1>
            <div style="color: orange; padding: 15px; border: 1px solid orange; background: #fff3cd;">
                ⚠️ No trending news available. Run batch pipeline first.
            </div>
            </body></html>
            """

        # Calculate statistics
        total_india = sum(data.get('count', 0) for data in trending['data'].get('India', {}).values())
        total_global = sum(data.get('count', 0) for data in trending['data'].get('Global', {}).values())
        total_articles = total_india + total_global

        # Generate professional HTML dashboard
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Multi-Agent News Intelligence</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 0; padding: 20px; background: #f5f7fa; line-height: 1.6;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white; padding: 30px; border-radius: 12px; margin-bottom: 30px;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                }}
                .header h1 {{ margin: 0 0 10px 0; font-size: 2.5em; }}
                .header p {{ margin: 5px 0; opacity: 0.9; }}
                .header small {{ opacity: 0.8; }}
                .stats {{
                    display: flex; gap: 20px; margin-bottom: 30px; flex-wrap: wrap;
                }}
                .stat-card {{
                    background: white; padding: 25px; border-radius: 10px;
                    box-shadow: 0 3px 15px rgba(0,0,0,0.08); flex: 1; min-width: 200px;
                    text-align: center; transition: transform 0.2s ease;
                }}
                .stat-card:hover {{ transform: translateY(-2px); }}
                .stat-card h3 {{ margin: 0 0 10px 0; color: #666; font-size: 1.1em; }}
                .stat-card h2 {{ margin: 0 0 5px 0; font-size: 2.5em; color: #333; }}
                .stat-card p {{ margin: 0; color: #888; }}
                .region {{
                    background: white; border-radius: 12px; padding: 30px;
                    margin: 25px 0; box-shadow: 0 4px 20px rgba(0,0,0,0.08);
                }}
                .region h2 {{
                    margin: 0 0 25px 0; color: #333; border-bottom: 3px solid #667eea;
                    padding-bottom: 10px; font-size: 1.8em;
                }}
                .category {{
                    margin: 25px 0; padding: 20px; background: #f8faff;
                    border-radius: 10px; border-left: 5px solid #667eea;
                }}
                .category h3 {{
                    margin: 0 0 15px 0; color: #333; font-size: 1.4em;
                    display: flex; align-items: center; gap: 10px;
                }}
                .category-count {{
                    background: #667eea; color: white; padding: 4px 12px;
                    border-radius: 20px; font-size: 0.9em; font-weight: normal;
                }}
                .ai-summary {{
                    background: #e8f4fd; border-left: 4px solid #2196f3;
                    padding: 15px; margin: 15px 0; border-radius: 5px; font-style: italic;
                }}
                .story {{
                    background: white; margin: 15px 0; padding: 20px;
                    border-radius: 8px; border-left: 4px solid #4caf50;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
                }}
                .story h4 {{
                    margin: 0 0 8px 0; color: #333; font-size: 1.1em; line-height: 1.4;
                }}
                .story-meta {{
                    color: #666; font-size: 0.9em; margin-bottom: 10px;
                    display: flex; align-items: center; gap: 15px;
                }}
                .story p {{
                    margin: 0; color: #555; line-height: 1.5;
                }}
                .api-section {{
                    background: linear-gradient(135deg, #e3f2fd 0%, #f3e5f5 100%);
                    border: 1px solid #2196f3; padding: 25px; border-radius: 10px;
                    margin: 40px 0 20px 0;
                }}
                .api-section h2 {{ margin: 0 0 15px 0; color: #1976d2; }}
                .api-section ul {{ margin: 10px 0; padding-left: 20px; }}
                .api-section li {{ margin: 8px 0; }}
                .api-section code {{
                    background: #f5f5f5; padding: 2px 6px; border-radius: 3px;
                    font-family: 'Courier New', monospace; color: #d32f2f;
                }}
                .footer {{
                    text-align: center; margin-top: 40px; padding: 20px;
                    color: #666; border-top: 1px solid #eee;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🔥 Multi-Agent News Intelligence Dashboard</h1>
                <p>AI-powered trending news analysis across India and Global markets</p>
                <small>Last updated: {safe_html_escape(trending.get('generation_time', 'Unknown'))}</small>
            </div>

            <div class="stats">
                <div class="stat-card">
                    <h3>🇮🇳 India News</h3>
                    <h2>{total_india}</h2>
                    <p>Trending articles</p>
                </div>
                <div class="stat-card">
                    <h3>🌍 Global News</h3>
                    <h2>{total_global}</h2>
                    <p>International stories</p>
                </div>
                <div class="stat-card">
                    <h3>📊 Total Coverage</h3>
                    <h2>{total_articles}</h2>
                    <p>Articles analyzed</p>
                </div>
            </div>
        """

        # Add trending news by region
        category_icons = {
            'sports': '⚽', 'politics': '🏛️', 'technology': '💻',
            'health': '🏥', 'crime': '🚨', 'entertainment': '🎬'
        }

        for region_name, region_data in trending['data'].items():
            if not region_data:
                continue

            region_icon = "🇮🇳" if region_name == "India" else "🌍"
            html += f"""
            <div class="region">
                <h2>{region_icon} {safe_html_escape(region_name)} Trending News</h2>
            """

            # Limit categories to prevent page being too long
            for category, category_data in list(region_data.items())[:6]:  # Max 6 categories
                icon = category_icons.get(category, '📰')

                html += f"""
                <div class="category">
                    <h3>
                        {icon} {safe_html_escape(category.title())}
                        <span class="category-count">{category_data.get('count', 0)} stories</span>
                    </h3>
                """

                # Add AI summary if available
                if 'ai_summary' in category_data:
                    html += f"""
                    <div class="ai-summary">
                        <strong>AI Summary:</strong> {safe_html_escape(safe_truncate(category_data['ai_summary'], 200))}
                    </div>
                    """

                # Add top stories (limit to 3)
                for i, story in enumerate(category_data.get('top_stories', [])[:3], 1):
                    title = safe_html_escape(safe_truncate(story.get('title', 'No title'), 120))
                    source = safe_html_escape(story.get('source', 'Unknown source'))
                    description = safe_html_escape(safe_truncate(story.get('description', 'No description'), 200))

                    html += f"""
                    <div class="story">
                        <h4>{i}. {title}</h4>
                        <div class="story-meta">
                            <span><strong>Source:</strong> {source}</span>
                        </div>
                        <p>{description}</p>
                    </div>
                    """

                html += "</div>"

            html += "</div>"

        # Add API documentation
        html += """
            <div class="api-section">
                <h2>🔗 API Endpoints</h2>
                <p><strong>Access your data programmatically:</strong></p>
                <ul>
                    <li><code>GET /api/trending</code> - Get all trending news</li>
                    <li><code>GET /api/trending/India</code> - Get India trending news</li>
                    <li><code>GET /api/trending/Global</code> - Get Global trending news</li>
                    <li><code>GET /api/trending/{region}/{category}</code> - Get specific category</li>
                    <li><code>POST /api/query</code> - Ask questions about news</li>
                    <li><code>GET /docs</code> - Interactive API documentation</li>
                </ul>
            </div>

            <div class="footer">
                <p>Powered by Multi-Agent AI • Deployed on Google Cloud Run</p>
            </div>
        </body>
        </html>
        """

        return html

    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")
        return f"""
        <html><body style="font-family: Arial, sans-serif; padding: 20px;">
        <h1>📰 Multi-Agent News Intelligence</h1>
        <div style="color: red; padding: 15px; border: 1px solid red; background: #ffe6e6;">
            ❌ Error loading dashboard: {safe_html_escape(str(e))}
        </div>
        </body></html>
        """

# Keep all other endpoints the same
@app.get("/api/trending")
async def get_all_trending():
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not available")
    return orchestrator.get_trending_news()

@app.get("/api/trending/{region}")
async def get_region_trending(region: str):
    if region not in ['India', 'Global']:
        raise HTTPException(status_code=400, detail="Region must be 'India' or 'Global'")
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not available")
    return orchestrator.get_trending_news(region=region)

@app.get("/api/trending/{region}/{category}")
async def get_category_trending(region: str, category: str):
    valid_categories = ["sports", "politics", "technology", "health", "crime", "entertainment"]
    if region not in ['India', 'Global']:
        raise HTTPException(status_code=400, detail="Region must be 'India' or 'Global'")
    if category not in valid_categories:
        raise HTTPException(status_code=400, detail=f"Category must be one of: {valid_categories}")
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not available")
    return orchestrator.get_trending_news(region=region, category=category)

# Keep your existing POST endpoint
@app.post("/admin/run-trending-extraction")
async def run_trending_extraction_post():
    """Admin endpoint to trigger trending extraction via POST"""

    logger.info("🔥 Triggered trending extraction via POST")

    try:
        from trending_pipeline_fixed import trending_extractor_fixed

        # Run the extraction
        result = await trending_extractor_fixed.run_trending_extraction()

        if result:
            # Clear API cache to load new data
            if orchestrator:
                orchestrator.trending_cache = None

            return {
                "success": True,
                "message": "Trending extraction completed successfully",
                "timestamp": datetime.utcnow().isoformat(),
                "regions_processed": list(result.keys()) if isinstance(result, dict) else [],
                "triggered_by": "POST"
            }
        else:
            return {
                "success": False,
                "message": "Trending extraction failed - check logs",
                "timestamp": datetime.utcnow().isoformat()
            }

    except Exception as e:
        logger.error(f"❌ Trending extraction error: {str(e)}")
        return {
            "success": False,
            "message": f"Exception during extraction: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }

# ADD THIS NEW GET ENDPOINT
@app.get("/admin/run-trending-extraction")
async def run_trending_extraction_get():
    """Admin endpoint to trigger trending extraction via GET (for scheduler compatibility)"""

    logger.info("🔥 Triggered trending extraction via GET")

    try:
        from trending_pipeline_fixed import trending_extractor_fixed

        # Run the extraction
        result = await trending_extractor_fixed.run_trending_extraction()

        if result:
            # Clear API cache to load new data
            if orchestrator:
                orchestrator.trending_cache = None

            return {
                "success": True,
                "message": "Trending extraction completed successfully (via GET)",
                "timestamp": datetime.utcnow().isoformat(),
                "regions_processed": list(result.keys()) if isinstance(result, dict) else [],
                "triggered_by": "GET"
            }
        else:
            return {
                "success": False,
                "message": "Trending extraction failed - check logs",
                "timestamp": datetime.utcnow().isoformat()
            }

    except Exception as e:
        logger.error(f"❌ Trending extraction error: {str(e)}")
        return {
            "success": False,
            "message": f"Exception during extraction: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }

@app.post("/api/query")
async def process_query(request: QueryRequest):
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not available")
    result = await orchestrator.answer_query(request.query, request.max_results)
    return result

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Multi-Agent News Intelligence",
        "timestamp": datetime.utcnow().isoformat(),
        "orchestrator_status": "available" if orchestrator else "unavailable"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
