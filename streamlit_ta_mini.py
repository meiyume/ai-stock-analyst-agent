import streamlit as st
from openai import OpenAI
import yfinance as yf

# ======= News Source Functions ========

# --- 1. Yahoo Finance ---
def fetch_yfinance_news(ticker, max_articles=12):
    try:
        stock = yf.Ticker(ticker)
        news = getattr(stock, "news", [])
        articles = []
        for n in news:
            # New Yahoo format: everything under 'content'
            content = n.get("content", {})
            title = content.get("title") or n.get("title", "")
            # URL may be under clickThroughUrl or canonicalUrl
            url = None
            for k in ["clickThroughUrl", "canonicalUrl"]:
                if content.get(k) and isinstance(content.get(k), dict):
                    url = content[k].get("url")
                    if url:
                        break
            url = url or n.get("link", "")
            summary = content.get("summary") or n.get("summary", "")
            published = content.get("pubDate") or n.get("providerPublishTime", "")
            source = (content.get("provider", {}) or {}).get("displayName", n.get("publisher", "Yahoo Finance"))
            articles.append({
                "title": title,
                "publishedAt": published,
                "source": source,
                "url": url,
                "description": summary,
                "api": "Yahoo Finance",
                "search_keyword": ticker
            })
            if len(articles) >= max_articles:
                break
        return articles
    except Exception as e:
        print("Error fetching yfinance news:", e)
        return []


# --- 2. NewsAPI ---
def fetch_news_newsapi(query, max_articles=12, api_key=None, from_days_ago=14):
    if not api_key:
        return []
    import requests
    from datetime import datetime, timedelta
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
            "api": "NewsAPI",
            "search_keyword": query
        }
        for a in articles
    ]

# --- 3. SerpAPI Google News ---
def fetch_news_serpapi(query, serpapi_key, max_articles=12):
    if not serpapi_key:
        return []
    try:
        from serpapi import GoogleSearch
    except ImportError:
        return []
    params = {
        "engine": "google_news",
        "q": query,
        "api_key": serpapi_key,
        "num": max_articles,
        "hl": "en",
    }
    try:
        results = GoogleSearch(params).get_dict()
        news = results.get("news_results", [])
    except Exception:
        news = []
    return [
        {
            "title": n.get("title", ""),
            "publishedAt": n.get("date", ""),
            "source": n.get("source", ""),
            "url": n.get("link", ""),
            "description": n.get("snippet", ""),
            "api": "SerpAPI News",
            "search_keyword": query
        }
        for n in news
    ]

# --- 4. SerpAPI Web ---
def fetch_web_search_serpapi(query, serpapi_key, max_articles=12):
    if not serpapi_key:
        return []
    try:
        from serpapi import GoogleSearch
    except ImportError:
        return []
    params = {
        "engine": "google",
        "q": query,
        "api_key": serpapi_key,
        "num": max_articles,
        "hl": "en",
    }
    try:
        results = GoogleSearch(params).get_dict()
        organic_results = results.get("organic_results", [])
    except Exception:
        organic_results = []
    return [
        {
            "title": r.get("title", ""),
            "publishedAt": "",  # No publish date from web
            "source": r.get("displayed_link", ""),
            "url": r.get("link", ""),
            "description": r.get("snippet", ""),
            "api": "SerpAPI Web",
            "search_keyword": query
        }
        for r in organic_results
    ]

# ======= Metadata & Keyword Expansion ========

def get_metadata_yfinance(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        sector = info.get("sector", None)
        industry = info.get("industry", None)
        region = info.get("country", None) or info.get("exchange", None)
        return {
            "company_name": info.get("longName", ticker),
            "sector": sector,
            "industry": industry,
            "region": region
        }
    except Exception:
        return {
            "company_name": ticker,
            "sector": None,
            "industry": None,
            "region": None
        }

def infer_metadata_llm(ticker, openai_client):
    prompt = (
        f"As a financial analyst, what are the most relevant sector, industry, and country/region for the stock ticker '{ticker}'? "
        "Respond in JSON: {\"company_name\": \"...\", \"sector\": \"...\", \"industry\": \"...\", \"region\": \"...\"}"
    )
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
            "company_name": ticker,
            "sector": "Unknown",
            "industry": "Unknown",
            "region": "Unknown"
        }
    return output

def expand_search_keywords_llm(company_name, sector, industry, region, openai_client):
    prompt = (
        f"As a financial news analyst, generate a list of the 6 most relevant search phrases or keywords to find news related to the company '{company_name}', its sector '{sector}', industry '{industry}', and region '{region}'. "
        "Include the stock ticker and all related synonyms or common sector/region keywords. "
        "Return the list in JSON: {\"keywords\": [ ... ]}"
    )
    response = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    import json as pyjson
    content = response.choices[0].message.content
    try:
        output = pyjson.loads(content)
        keywords = output.get("keywords", [])
    except Exception:
        keywords = [company_name, sector, industry, region]
    keywords = [k for k in keywords if k and k.lower() != "unknown"]
    return keywords

# ======= Main App ========

st.set_page_config(page_title="LLM-powered News Analyst", page_icon="📰")
st.title("📰 LLM-powered Stock/Sector News Analyst")

ticker = st.text_input("Enter Stock Ticker (e.g., U11.SI):")
max_articles = st.slider("Max Articles", 5, 20, 10)
from_days_ago = st.slider("Lookback days (for NewsAPI)", 3, 30, 14)

# Optionally use OpenAI for LLM-powered expansion
use_llm = st.toggle("Expand queries with LLM (OpenAI)", value=True)
openai_key = st.secrets.get("OPENAI_API_KEY")
newsapi_key = st.secrets.get("NEWSAPI_KEY")
serpapi_key = st.secrets.get("SERPAPI_KEY")
openai_client = OpenAI(api_key=openai_key) if (openai_key and use_llm) else None

if st.button("Analyze News") and ticker:
    # --- Metadata ---
    metadata = get_metadata_yfinance(ticker)
    st.markdown(f"**Company Name:** {metadata['company_name']}")
    st.markdown(f"**Sector:** {metadata['sector']}")
    st.markdown(f"**Industry:** {metadata['industry']}")
    st.markdown(f"**Region:** {metadata['region']}")

    # --- LLM Fallback if enabled and info missing ---
    if openai_client and (not metadata["sector"] or not metadata["industry"] or not metadata["region"]):
        st.info("LLM used to infer missing sector/region/industry info.")
        metadata = infer_metadata_llm(ticker, openai_client)
        st.markdown(f"**(LLM) Company Name:** {metadata['company_name']}")
        st.markdown(f"**(LLM) Sector:** {metadata['sector']}")
        st.markdown(f"**(LLM) Industry:** {metadata['industry']}")
        st.markdown(f"**(LLM) Region:** {metadata['region']}")

    # --- Generate keywords/aliases ---
    if openai_client:
        keywords = expand_search_keywords_llm(
            metadata["company_name"], metadata["sector"], metadata["industry"], metadata["region"], openai_client
        )
        st.markdown(f"**Keywords used for news search:** {', '.join(keywords)}")
    else:
        keywords = [ticker]
        st.markdown(f"**Keywords used for news search:** {', '.join(keywords)}")

    # --- Gather news from all sources ---
    all_articles = []
    for kw in keywords:
        # Yahoo Finance
        ynews = fetch_yfinance_news(kw, max_articles=max_articles)
        all_articles.extend(ynews)
        # NewsAPI (optional)
        if newsapi_key:
            na = fetch_news_newsapi(kw, max_articles=max_articles, api_key=newsapi_key, from_days_ago=from_days_ago)
            all_articles.extend(na)
        # SerpAPI (optional)
        if serpapi_key:
            sa_news = fetch_news_serpapi(kw, serpapi_key, max_articles=max_articles)
            all_articles.extend(sa_news)
            sa_web = fetch_web_search_serpapi(kw, serpapi_key, max_articles=max_articles)
            all_articles.extend(sa_web)

    # --- Deduplicate by title ---
    seen_titles = set()
    deduped_articles = []
    for a in all_articles:
        if a["title"] and a["title"] not in seen_titles:
            deduped_articles.append(a)
            seen_titles.add(a["title"])
        if len(deduped_articles) >= max_articles:
            break

    # --- Show Results by Source ---
    sources = {}
    for a in deduped_articles:
        api = a.get("api", "Unknown")
        sources.setdefault(api, []).append(a)
    st.markdown(f"**Articles by Source:**")
    for api, arts in sources.items():
        with st.expander(f"{api} ({len(arts)})", expanded=(api == "Yahoo Finance")):
            for a in arts:
                st.markdown(
                    f"- [{a['title']}]({a['url']}) <small>({a.get('source','')}, {str(a.get('publishedAt',''))[:10]})</small> [Searched: {a['search_keyword']}]",
                    unsafe_allow_html=True
                )
                if a.get("description"):
                    st.caption(a["description"])
    if not deduped_articles:
        st.warning("No news found from any enabled source.")

else:
    st.info("Enter a ticker, select options, then click **Analyze News** to begin.")





