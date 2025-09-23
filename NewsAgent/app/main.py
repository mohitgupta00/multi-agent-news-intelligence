"""
Enhanced FastAPI Application - Same structure as original, with historical support
Keeps original trending news section with Global first, then India
Complete with proper search results display
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import sys
import logging
from datetime import datetime, timedelta
from html import escape
import re
import asyncio

# Same paths as original
sys.path.append("app")
sys.path.append("app/agents")

# Same logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Same lazy initialization pattern
orchestrator_instance = None

async def get_orchestrator():
    global orchestrator_instance
    if orchestrator_instance is None:
        try:
            from news_orchestrator import MainNewsOrchestrator
            orchestrator_instance = MainNewsOrchestrator()
            logger.info("✅ Enhanced Orchestrator initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize orchestrator: {e}")
            raise HTTPException(status_code=500, detail=f"System initialization failed: {str(e)}")
    return orchestrator_instance

# Same FastAPI setup
app = FastAPI(title="Multi-Agent News Intelligence API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Same request model
class QueryRequest(BaseModel):
    query: str
    max_results: int = 5

# Same helper functions from original
def clean_content(text):
    if not text:
        return ""
    text = str(text)
    text = re.sub(r"[^\w\s.,!?-]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def validate_content_quality(title, description):
    if not title or len(title.strip()) < 10:
        return False
    if not description or len(description.strip()) < 20:
        return False
    spam_keywords = ['click here', 'buy now', 'limited time', 'free money', 'spam']
    content_lower = (title + " " + description).lower()
    return not any(keyword in content_lower for keyword in spam_keywords)

def smart_truncate(text, max_length=100, preserve_sentences=False):
    if not text or len(text) <= max_length:
        return text

    if preserve_sentences:
        sentences = text.split('.')
        truncated_text = ""
        for sentence in sentences:
            if len(truncated_text + sentence + ".") <= max_length:
                truncated_text += sentence + "."
            else:
                break

        if truncated_text:
            return truncated_text

    end_pos = text.rfind(' ', 0, max_length)
    if end_pos > 0:
        return text[:end_pos].strip() + "..."
    else:
        return text[:max_length] + "..."

def safe_html_escape(text):
    if not text:
        return ""
    return escape(str(text))

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    try:
        orch = await get_orchestrator()
    except HTTPException as e:
        return HTMLResponse(f"""
        <html><body style="font-family: Arial; padding: 20px;">
        <h1>Multi-Agent News Intelligence</h1>
        <div style="color: red; padding: 15px; border: 1px solid red;">
        System not available. Orchestrator failed to load: {escape(e.detail)}
        </div>
        </body></html>
        """, status_code=e.status_code)

    try:
        # Same trending news logic as original
        trending = orch.get_trending_news()

        if not trending.get('success'):
            return HTMLResponse("""
            <html><body style="font-family: Arial; padding: 20px;">
            <h1>Multi-Agent News Intelligence</h1>
            <div style="color: orange; padding: 15px; border: 1px solid orange;">
            No trending news available. The background job may be running or has failed.
            </div>
            </body></html>
            """)

        data = trending.get('data')

        # Same stats calculation as original
        india_total = sum(cat.get('count', 0) for cat in data.get('India', {}).values())
        global_total = sum(cat.get('count', 0) for cat in data.get('Global', {}).values())
        version_timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')

        html_parts = []
        html_parts.append(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Multi-Agent News Intelligence</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                * {{ box-sizing: border-box; }}
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    margin: 0; padding: 20px; background: #f5f7fa; line-height: 1.6;
                }}

                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white; padding: 40px; border-radius: 12px; text-align: center;
                    margin-bottom: 30px; box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                }}
                .header h1 {{ margin: 0; font-size: 2.5em; font-weight: 700; }}
                .header p {{ margin: 10px 0 0 0; font-size: 1.2em; opacity: 0.9; }}

                .stats {{
                    display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px; margin: 30px 0;
                }}
                .stat {{
                    background: white; padding: 30px; border-radius: 12px; text-align: center;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.08); transition: transform 0.3s ease;
                }}
                .stat:hover {{ transform: translateY(-2px); }}
                .stat h2 {{ margin: 0; font-size: 3em; color: #667eea; font-weight: 700; }}
                .stat p {{ margin: 10px 0 0 0; color: #666; font-weight: 600; font-size: 1.1em; }}

                .region {{
                    background: white; padding: 35px; margin: 25px 0; border-radius: 12px;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.08);
                }}
                .region h2 {{ margin-top: 0; color: #333; font-size: 1.8em; border-bottom: 3px solid #667eea; padding-bottom: 10px; }}
                .category {{ margin: 25px 0; padding: 25px; background: #f8faff; border-left: 4px solid #4caf50; border-radius: 8px; }}
                .category h3 {{ margin-top: 0; color: #333; font-size: 1.3em; }}
                .story {{
                    padding: 20px; margin: 15px 0; background: #fff; border-radius: 10px;
                    border-left: 4px solid #ff9800; box-shadow: 0 2px 8px rgba(0,0,0,0.05);
                    transition: transform 0.2s ease, box-shadow 0.2s ease; cursor: pointer;
                }}
                .story:hover {{ transform: translateX(5px); box-shadow: 0 4px 16px rgba(0,0,0,0.1); }}
                .story h4 {{ margin: 0 0 10px 0; color: #333; font-size: 1.1em; line-height: 1.4; }}
                .story p {{ margin: 8px 0; color: #555; }}
                .story small {{ color: #888; }}
                .story a {{ color: #667eea; text-decoration: none; font-weight: 500; }}
                .story a:hover {{ text-decoration: underline; }}

                .search-section {{
                    background: white; padding: 35px; margin: 25px 0; border-radius: 12px;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.08); text-align: center;
                }}
                .search-section h2 {{ margin-top: 0; color: #333; }}
                .search-section input[type="text"] {{
                    width: 70%; padding: 15px; border: 2px solid #ddd; border-radius: 8px;
                    font-size: 1.1em; margin-right: 10px;
                }}
                .search-section button {{
                    padding: 15px 25px; border: none; background: #667eea; color: white;
                    border-radius: 8px; font-size: 1.1em; cursor: pointer;
                    transition: background 0.3s ease;
                }}
                .search-section button:hover {{ background: #5a6edc; }}

                #queryResults {{ text-align: left; margin-top: 20px; }}

                @media (max-width: 768px) {{
                    .stats {{ grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); }}
                    .search-section input[type="text"] {{ width: 100%; margin: 0 0 15px 0; }}
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🔍 Multi-Agent News Intelligence</h1>
                <p>Ask questions and see live trending topics from around the world. Enhanced with historical search. (Version: {version_timestamp})</p>
            </div>

            <div class="stats">
                <div class="stat">
                    <h2>{india_total}</h2>
                    <p>🇮🇳 India Stories</p>
                </div>
                <div class="stat">
                    <h2>{global_total}</h2>
                    <p>🌍 Global Stories</p>
                </div>
                <div class="stat">
                    <h2>{india_total + global_total}</h2>
                    <p>📊 Total Analyzed</p>
                </div>
            </div>

            <div class="search-section">
                <h2>🤖 Ask a Question</h2>
                <form id="queryForm" onsubmit="submitQuery(); return false;">
                    <input type="text" id="queryInput" placeholder="e.g., what happened in sports one week ago?">
                    <button type="submit">Search</button>
                </form>
                <div id="queryResults"></div>
            </div>
        """)

        # Modified trending section: Global first, then India
        for region in ['Global', 'India']:
            categories = data.get(region, {})
            if not categories:
                continue
            flag = "🌍" if region == "Global" else "🇮🇳"
            html_parts.append(f'<div class="region"><h2>{flag} {region} Trending News</h2>')

            for category, category_data in categories.items():
                count = category_data.get('count', 0)
                html_parts.append(f'<div class="category"><h3>{category.title()} ({count} stories)</h3>')

                if 'ai_summary' in category_data:
                    summary = safe_html_escape(category_data['ai_summary'])
                    html_parts.append(f'<p><strong>AI Summary:</strong> {summary}</p>')

                stories_added = 0
                for story in category_data.get('top_stories', []):
                    title = clean_content(story.get('title', ''))
                    description = clean_content(story.get('description', ''))

                    if not validate_content_quality(title, description):
                        continue

                    display_title = smart_truncate(title, max_length=120)
                    display_description = smart_truncate(description, max_length=280, preserve_sentences=True)
                    source = safe_html_escape(story.get('source', 'Unknown source'))
                    url = story.get('url', '')

                    stories_added += 1

                    source_html = f'<a href="{url}" target="_blank" style="color: inherit; text-decoration: none;">{source}</a>' if url else source
                    link_html = f'<p><a href="{url}" target="_blank">Read full article »</a></p>' if url else ''

                    html_parts.append(f'''
                    <div class="story">
                        <h4>{stories_added}. {display_title}</h4>
                        <p><small><strong>Source:</strong> {source_html}</small></p>
                        <p>{display_description}</p>
                        {link_html}
                    </div>
                    ''')

                    if stories_added >= 3:
                        break

                if stories_added == 0:
                    html_parts.append(f'<p><em>{count} stories are being processed for better quality display.</em></p>')

                html_parts.append('</div>')

            html_parts.append('</div>')

        # Enhanced JavaScript with historical support - COMPLETE VERSION
        html_parts.append("""
            <script>
                async function submitQuery() {
                    const query = document.getElementById('queryInput').value.trim();
                    const resultsDiv = document.getElementById('queryResults');

                    if (!query) {
                        resultsDiv.innerHTML = '<p style="color: orange;">Please enter a search query.</p>';
                        return;
                    }

                    resultsDiv.innerHTML = `
                        <div style="text-align: center; padding: 20px;">
                            <p>🔍 Searching for relevant news articles...</p>
                            <div style="margin: 10px 0;">
                                <div style="width: 100%; background: #f0f0f0; border-radius: 10px; height: 6px;">
                                    <div style="width: 0%; background: #667eea; height: 100%; border-radius: 10px; animation: loading 2s infinite;" id="progressBar"></div>
                                </div>
                            </div>
                        </div>
                        <style>
                            @keyframes loading {
                                0% { width: 0%; }
                                50% { width: 70%; }
                                100% { width: 100%; }
                            }
                        </style>
                    `;

                    try {
                        const response = await fetch('/api/query', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ query: query, max_results: 5 })
                        });

                        if (!response.ok) {
                            const errorText = await response.text();
                            throw new Error(`Server error (${response.status}): ${errorText}`);
                        }

                        const result = await response.json();
                        console.log('API Response:', result);

                        if (result.success === false) {
                            let errorHtml = '<div style="color: red; padding: 15px; border: 1px solid red; border-radius: 8px; background: #ffebee;">';
                            errorHtml += '<strong>Search Failed:</strong> ' + (result.message || 'Unknown error occurred');

                            // Show missing dates info if available
                            if (result.missing_dates && result.missing_dates.length > 0) {
                                errorHtml += '<br><small>Missing data for: ' + result.missing_dates.join(', ') + '</small>';
                            }

                            errorHtml += '</div>';
                            resultsDiv.innerHTML = errorHtml;
                            return;
                        }

                        if (result.summary) {
                            let html = '<h3 style="color: #667eea; margin-bottom: 20px;">📰 AI News Report</h3>';

                            // Add search metadata only if it contains useful info
                            if (result.search_metadata && result.search_metadata.query_type === 'historical') {
                                const metadata = result.search_metadata;
                                html += `
                                    <div style="background: #e3f2fd; padding: 15px; margin-bottom: 20px; border-radius: 8px; border-left: 4px solid #2196f3;">
                                        <strong>🔍 Historical Search:</strong> ${metadata.date_range}
                                `;

                                if (metadata.missing_dates && metadata.missing_dates.length > 0) {
                                    html += `<br><small style="color: #f57c00;">⚠️ Some data unavailable for: ${metadata.missing_dates.join(', ')}</small>`;
                                }

                                html += '</div>';
                            }

                            const formattedSummary = result.summary.replace(/\\\\n/g, '<br>');
                            html += `<div class="story" style="background: #f8faff; border-left: 4px solid #667eea; padding: 20px; margin-bottom: 20px; border-radius: 8px;"><div style="font-size: 1.1em; line-height: 1.6;">${formattedSummary}</div></div>`;

                            if (result.articles && result.articles.length > 0) {
                                html += '<h4 style="color: #333; margin: 25px 0 15px 0; border-bottom: 2px solid #667eea; padding-bottom: 8px;">📚 Referenced Sources</h4>';

                                result.articles.forEach((article, index) => {
                                    const title = article.title ? String(article.title).replace(/</g, '&lt;').replace(/>/g, '&gt;') : 'No Title';
                                    const source = article.source ? String(article.source).replace(/</g, '&lt;').replace(/>/g, '&gt;') : 'Unknown Source';
                                    const description = article.description ? String(article.description).replace(/</g, '&lt;').replace(/>/g, '&gt;') : '';
                                    const url = article.link || article.url || '';
                                    const pubDate = article.pubDate ? new Date(article.pubDate).toLocaleDateString() : '';

                                    html += `
                                        <div class="story" style="background: white; border: 1px solid #e0e0e0; border-radius: 10px; padding: 20px; margin: 15px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.1); transition: transform 0.2s ease, box-shadow 0.2s ease; cursor: pointer;"
                                             onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 16px rgba(0,0,0,0.15)';"
                                             onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 8px rgba(0,0,0,0.1)';"
                                             onclick="window.open('${url}', '_blank')">

                                            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                                                <h5 style="margin: 0; color: #333; font-size: 1.1em; line-height: 1.4; flex: 1;">
                                                    <a href="${url}" target="_blank" style="color: #667eea; text-decoration: none; font-weight: 600;" onclick="event.stopPropagation();">
                                                        ${index + 1}. ${title}
                                                    </a>
                                                </h5>
                                                <a href="${url}" target="_blank" onclick="event.stopPropagation()" style="background: #667eea; color: white; padding: 4px 8px; border-radius: 12px; font-size: 0.8em; margin-left: 10px; white-space: nowrap; text-decoration: none;">
                                                    ${source}
                                                </a>
                                            </div>

                                            ${description ? `<p style="margin: 10px 0; color: #666; line-height: 1.5; font-size: 0.95em;">${description.length > 200 ? description.substring(0, 200) + '...' : description}</p>` : ''}

                                            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 15px; padding-top: 12px; border-top: 1px solid #f0f0f0;">
                                                <div style="display: flex; align-items: center; gap: 15px;">
                                                    ${pubDate ? `<small style="color: #888; display: flex; align-items: center;"><span style="margin-right: 5px;">📅</span>${pubDate}</small>` : ''}
                                                </div>
                                                <a href="${url}" target="_blank" style="background: #4caf50; color: white; padding: 6px 12px; border-radius: 6px; text-decoration: none; font-size: 0.85em; font-weight: 500; transition: background 0.3s ease;"
                                                   onmouseover="this.style.background='#45a049'" onmouseout="this.style.background='#4caf50'" onclick="event.stopPropagation();">
                                                    Read Full Article →
                                                </a>
                                            </div>
                                        </div>
                                    `;
                                });

                                html += '<div style="margin-top: 20px; padding: 15px; background: #f5f7fa; border-radius: 8px; text-align: center; border: 1px solid #e0e6ed;"><small style="color: #666;"><strong>Tip:</strong> Click on any article card or the "Read Full Article" button to open the source in a new tab</small></div>';
                            }

                            resultsDiv.innerHTML = html;
                        } else if (result.message) {
                            resultsDiv.innerHTML = `<div style="padding: 20px; background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 8px; color: #856404;">${result.message.replace(/\\n/g, '<br>')}</div>`;
                        } else {
                            resultsDiv.innerHTML = '<div style="padding: 20px; background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; color: #6c757d; text-align: center;">No results found for your query. Try rephrasing your search or using different keywords.</div>';
                        }

                    } catch (error) {
                        console.error('Query error:', error);
                        resultsDiv.innerHTML = `<div style="color: red; padding: 20px; border: 1px solid red; border-radius: 8px; background: #ffebee;"><strong>Error:</strong> ${error.message}<br><small style="color: #666; margin-top: 10px; display: block;">If this problem persists, please check your internet connection or try again later.</small></div>`;
                    }
                }
            </script>
        </body>
        </html>
        """)

        return HTMLResponse(''.join(html_parts))

    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return HTMLResponse(f"""
        <html><body style="font-family: Arial; padding: 20px;">
        <h1>Multi-Agent News Intelligence</h1>
        <div style="color: red; padding: 15px; border: 1px solid red;">
        Error loading dashboard: {escape(str(e))}
        </div>
        </body></html>
        """, status_code=500)

@app.post("/api/query")
async def process_query(request: QueryRequest):
    """Same endpoint as original - enhanced with historical support"""
    orch = await get_orchestrator()
    result = await orch.answer_query(request.query, request.max_results)
    return result

# Keep all other endpoints same as original
@app.get("/api/trending")
async def get_trending():
    orch = await get_orchestrator()
    return orch.get_trending_news()

@app.get("/api/trending/{region}")
async def get_trending_by_region(region: str):
    orch = await get_orchestrator()
    return orch.get_trending_news(region=region)

@app.get("/api/trending/{region}/{category}")
async def get_trending_by_region_and_category(region: str, category: str):
    orch = await get_orchestrator()
    return orch.get_trending_news(region=region, category=category)
