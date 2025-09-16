"""
FastAPI Application for Multi-Agent News Intelligence
Production-ready version
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import sys
import logging
from datetime import datetime

# Add paths
sys.path.append('/app')
sys.path.append('/app/agents')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Multi-Agent News Intelligence API",
    description="AI-powered trending news analysis across India and Global markets",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
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

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Professional trending news dashboard"""

    if not orchestrator:
        return """
        <html><body style="font-family: Arial, sans-serif; padding: 20px;">
        <h1>📰 Multi-Agent News Intelligence</h1>
        <div style="color: red; padding: 15px; border: 1px solid red; background: #ffe6e6;">
            ❌ System not available. Please check configuration.
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
                ⚠️ No trending news available. Please run the batch pipeline first.
            </div>
            </body></html>
            """

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
                    margin: 0; padding: 20px; background: #f5f7fa;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px;
                }}
                .stats {{
                    display: flex; gap: 20px; margin-bottom: 30px; flex-wrap: wrap;
                }}
                .stat-card {{
                    background: white; padding: 20px; border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1); flex: 1; min-width: 200px;
                }}
                .region {{
                    background: white; border-radius: 10px; padding: 25px;
                    margin: 20px 0; box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                }}
                .category {{
                    margin: 20px 0; padding: 20px; background: #f8f9ff;
                    border-radius: 8px; border-left: 4px solid #667eea;
                }}
                .story {{
                    background: white; margin: 10px 0; padding: 15px;
                    border-radius: 6px; border-left: 3px solid #28a745;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.05);
                }}
                .api-docs {{
                    background: #e3f2fd; border: 1px solid #2196f3;
                    padding: 20px; border-radius: 8px; margin: 30px 0;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🔥 Multi-Agent News Intelligence Dashboard</h1>
                <p>AI-powered trending news analysis across India and Global markets</p>
                <small>Last updated: {trending.get('generation_time', 'Unknown')}</small>
            </div>
        """

        # Add statistics
        total_india = sum(data['count'] for data in trending['data'].get('India', {}).values())
        total_global = sum(data['count'] for data in trending['data'].get('Global', {}).values())

        html += f"""
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
                    <h2>{total_india + total_global}</h2>
                    <p>Articles analyzed</p>
                </div>
            </div>
        """

        # Add trending news by region
        for region_name, region_data in trending['data'].items():
            if not region_data:
                continue

            region_icon = "🇮🇳" if region_name == "India" else "🌍"
            html += f"""
            <div class="region">
                <h2>{region_icon} {region_name} Trending News</h2>
            """

            for category, category_data in region_data.items():
                category_icons = {
                    'sports': '⚽', 'politics': '🏛️', 'technology': '💻',
                    'health': '🏥', 'crime': '🚨', 'entertainment': '🎬'
                }
                icon = category_icons.get(category, '📰')

                html += f"""
                <div class="category">
                    <h3>{icon} {category.title()}</h3>
                    <p><strong>{category_data['count']} stories</strong></p>
                """

                if 'ai_summary' in category_data:
                    html += f"<p><strong>AI Summary:</strong> {category_data['ai_summary']}</p>"

                # Add top stories
                for i, story in enumerate(category_data.get('top_stories', [])[:3], 1):
                    html += f"""
                    <div class="story">
                        <h4>{i}. {story['title']}</h4>
                        <p><strong>Source:</strong> {story['source']}</p>
                        <p>{story['description']}</p>
                    </div>
                    """

                html += "</div>"

            html += "</div>"

        # Add API documentation
        html += """
            <div class="api-docs">
                <h2>🔗 API Endpoints</h2>
                <p><strong>Access programmatically:</strong></p>
                <ul>
                    <li><code>GET /api/trending</code> - All trending news</li>
                    <li><code>GET /api/trending/India</code> - India trending news</li>
                    <li><code>GET /api/trending/Global</code> - Global trending news</li>
                    <li><code>GET /api/trending/{region}/{category}</code> - Specific category</li>
                    <li><code>POST /api/query</code> - Ask questions about news</li>
                    <li><code>GET /docs</code> - Interactive API documentation</li>
                </ul>
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
            ❌ Error loading dashboard: {str(e)}
        </div>
        </body></html>
        """

@app.get("/api/trending")
async def get_all_trending():
    """Get all trending news - API endpoint"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not available")

    try:
        result = orchestrator.get_trending_news()
        return result
    except Exception as e:
        logger.error(f"Trending API error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/trending/{region}")
async def get_region_trending(region: str):
    """Get trending news for specific region"""
    if region not in ['India', 'Global']:
        raise HTTPException(status_code=400, detail="Region must be 'India' or 'Global'")

    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not available")

    try:
        result = orchestrator.get_trending_news(region=region)
        return result
    except Exception as e:
        logger.error(f"Region trending error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/trending/{region}/{category}")
async def get_category_trending(region: str, category: str):
    """Get trending news for specific region and category"""
    valid_categories = ["sports", "politics", "technology", "health", "crime", "entertainment"]

    if region not in ['India', 'Global']:
        raise HTTPException(status_code=400, detail="Region must be 'India' or 'Global'")

    if category not in valid_categories:
        raise HTTPException(status_code=400, detail=f"Category must be one of: {valid_categories}")

    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not available")

    try:
        result = orchestrator.get_trending_news(region=region, category=category)
        return result
    except Exception as e:
        logger.error(f"Category trending error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/query")
async def process_query(request: QueryRequest):
    """Process specific news queries"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not available")

    try:
        result = await orchestrator.answer_query(request.query, request.max_results)
        return result
    except Exception as e:
        logger.error(f"Query processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check for Cloud Run"""
    return {
        "status": "healthy",
        "service": "Multi-Agent News Intelligence",
        "timestamp": datetime.utcnow().isoformat(),
        "orchestrator_status": "available" if orchestrator else "unavailable"
    }

@app.get("/api/status")
async def system_status():
    """Detailed system status"""
    if not orchestrator:
        return {"status": "error", "message": "Orchestrator not initialized"}

    try:
        trending = orchestrator.get_trending_news()

        return {
            "status": "operational",
            "trending_available": trending['success'],
            "regions": list(trending.get('data', {}).keys()),
            "last_update": trending.get('generation_time'),
            "total_categories": sum(len(region_data) for region_data in trending.get('data', {}).values())
        }
    except Exception as e:
        return {"status": "degraded", "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
