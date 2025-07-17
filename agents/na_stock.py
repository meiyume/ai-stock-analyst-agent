import requests
import yfinance as yf
from datetime import datetime, timedelta

# --- 1. Get all aliases for a given ticker ---
def get_company_aliases_from_ticker(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        names = set()
        if "longName" in info:
            names.add(info["longName"])
        if "shortName" in info:
            names.add(info["shortName"])
        # Heuristic: If bank, try variations
        if "longName" in info:
            if "Bank" in info["longName"]:
                names.add(info["longName"].replace("Bank", "Bank Group"))
                names.add(info["longName"].replace("Bank", "Holdings"))
        names.add(ticker)
        return list(names)
    except Exception:
        return [ticker]

# --- 2. Fetch news for all aliases/sector ---
def fetch_stock_sector_news(query, max_articles=10, api_key=None, from_days_ago=7):
    url = (
        f"https://newsapi.org/v2/everything?q={query}"
        f"&language=en&pageSize={max_articles}"
        f"&from={ (datetime.utcnow() - timedelta(days=from_days_ago)).date() }"
        f"&sortBy=publishedAt&apiKey={api_key}"
    )
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        articles = resp.json().get("articles", [])
    except Exception:
        articles = []
    return [
        {
            "title": a.get("title", ""),
            "publishedAt": a.get("publishedAt", ""),
            "source": a.get("source", {}).get("name", ""),
            "url": a.get("url", ""),
            "description": a.get("description", ""),
        }
        for a in articles
    ]

def fetch_stock_sector_news_expanded(ticker, sector=None, max_articles=10, api_key=None, from_days_ago=7):
    queries = get_company_aliases_from_ticker(ticker)
    if sector:
        queries.append(sector)
    seen_titles = set()
    news = []
    for q in queries:
        res = fetch_stock_sector_news(q, max_articles=max_articles, api_key=api_key, from_days_ago=from_days_ago)
        for article in res:
            if article["title"] not in seen_titles:
                news.append(article)
                seen_titles.add(article["title"])
    return news

# --- 3. Summarize with OpenAI LLM (>=1.0.0 syntax) ---
def summarize_news_with_llm(headlines, company_name, sector_name=None, openai_client=None):
    if not headlines:
        return "No news found.", "N/A", []
    prompt = f"""
You are a financial news analyst AI.
Given these headlines about {company_name}{f' in the {sector_name} sector' if sector_name else ''}, provide:
- A short summary (max 2 sentences)
- Overall sentiment (Bullish, Bearish, Neutral)
- Top 2 news drivers

Headlines:
{chr(10).join(['- ' + h['title'] for h in headlines])}
Respond in JSON: {{"summary": "...", "sentiment": "...", "drivers": ["...", "..."]}}
"""
    # openai_client: an openai.OpenAI(api_key=...) client
    response = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    import json as pyjson
    content = response.choices[0].message.content
    try:
        output = pyjson.loads(content)
    except Exception:
        output = {
            "summary": content,
            "sentiment": "N/A",
            "drivers": []
        }
    return output.get("summary", ""), output.get("sentiment", ""), output.get("drivers", [])

# --- 4. Master agent function ---
def news_agent_stock(
    ticker,
    company_name=None,
    sector_name=None,
    openai_client=None,
    newsapi_key=None,
    max_articles=12,
    from_days_ago=7
):
    news = fetch_stock_sector_news_expanded(
        ticker,
        sector=sector_name,
        max_articles=max_articles,
        api_key=newsapi_key,
        from_days_ago=from_days_ago
    )
    if company_name is None:
        try:
            aliases = get_company_aliases_from_ticker(ticker)
            company_name = aliases[0] if aliases else ticker
        except Exception:
            company_name = ticker

    summary, sentiment, drivers = summarize_news_with_llm(
        news[:max_articles], company_name, sector_name, openai_client=openai_client
    )

    return {
        "company": company_name,
        "sector": sector_name,
        "summary": summary,
        "sentiment": sentiment,
        "drivers": drivers,
        "headlines": news[:max_articles],
    }
