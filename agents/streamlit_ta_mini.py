import requests
from datetime import datetime, timedelta
import openai  # or your preferred LLM client

# Example using NewsAPI (replace with your provider/keys)
NEWSAPI_KEY = "your_newsapi_key"

def fetch_stock_sector_news(query, max_articles=10, api_key=NEWSAPI_KEY, from_days_ago=7):
    """Fetch latest news headlines for a stock or sector (by keyword)"""
    url = f"https://newsapi.org/v2/everything?q={query}&language=en&pageSize={max_articles}&from={ (datetime.utcnow() - timedelta(days=from_days_ago)).date() }&sortBy=publishedAt&apiKey={api_key}"
    resp = requests.get(url)
    articles = resp.json().get("articles", [])
    return [
        {
            "title": a["title"],
            "publishedAt": a.get("publishedAt", ""),
            "source": a.get("source", {}).get("name", ""),
            "url": a.get("url", ""),
            "description": a.get("description", "")
        }
        for a in articles
    ]

def summarize_news_with_llm(headlines, company_name, sector_name=None, openai_api_key=None):
    """Send headlines to LLM, get back sentiment and summary."""
    prompt = f"""
You are a financial news analyst AI.
Given these headlines about {company_name}{f' in the {sector_name} sector' if sector_name else ''}, provide:
- A short summary (max 2 sentences)
- Overall sentiment (Bullish, Bearish, Neutral)
- Top 2 news drivers

Headlines:
{chr(10).join(['- ' + h['title'] for h in headlines])}
"""
    openai.api_key = openai_api_key
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  # or "gpt-4" if you want
        messages=[{"role": "user", "content": prompt}]
    )
    return response["choices"][0]["message"]["content"]

def news_agent_stock(ticker, company_name, sector_name=None, openai_api_key=None, newsapi_key=None):
    # Fetch news for ticker and (optionally) sector
    news = fetch_stock_sector_news(company_name, api_key=newsapi_key)
    if sector_name:
        news += fetch_stock_sector_news(sector_name, api_key=newsapi_key)
    if not news:
        return {"summary": "No news found.", "sentiment": "N/A", "drivers": [], "headlines": []}

    # Summarize and score
    summary = summarize_news_with_llm(news, company_name, sector_name, openai_api_key=openai_api_key)

    return {
        "company": company_name,
        "sector": sector_name,
        "summary": summary,
        "headlines": news[:10],  # For display in UI
    }

# Usage:
# result = news_agent_stock("C6L.SI", "Singapore Airlines", "Airlines", openai_api_key="...", newsapi_key="...")
