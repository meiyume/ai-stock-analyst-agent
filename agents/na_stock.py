import yfinance as yf
from datetime import datetime
from typing import List, Dict, Optional

def get_metadata_yfinance(ticker: str):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return {
            "company_name": info.get("longName", ticker),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "region": info.get("country") or info.get("exchange") or None
        }
    except Exception:
        return {
            "company_name": ticker,
            "sector": None,
            "industry": None,
            "region": None
        }

def infer_metadata_llm(ticker: str, openai_client):
    prompt = (
        f"As a financial analyst, what are the most relevant company names (including aliases), sector, industry, "
        f"and main region for the stock ticker '{ticker}'? "
        "Respond in JSON: {\"company_names\": [...], \"sector\": \"...\", \"industry\": \"...\", \"region\": \"...\"}"
    )
    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        import json as pyjson
        content = response.choices[0].message.content
        out = pyjson.loads(content)
    except Exception:
        out = {
            "company_names": [ticker],
            "sector": "Unknown",
            "industry": "Unknown",
            "region": "Unknown"
        }
    return out

def expand_search_keywords_llm(company_names, sector, industry, region, openai_client):
    names_str = ', '.join(company_names)
    prompt = (
        f"As a financial news analyst, generate a list of the 6 most relevant search phrases/keywords to find news "
        f"related to: {names_str}, sector: {sector}, industry: {industry}, region: {region}. "
        "Include common synonyms, sector/region phrases, and stock ticker if relevant. "
        "Return as JSON: {\"keywords\": [ ... ]}"
    )
    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        import json as pyjson
        content = response.choices[0].message.content
        out = pyjson.loads(content)
        keywords = out.get("keywords", [])
    except Exception:
        keywords = [*company_names, sector, industry, region]
    return [k for k in keywords if k and k.lower() != "unknown"]

def fetch_yfinance_news(ticker: str, max_articles: int = 12) -> List[Dict]:
    stock = yf.Ticker(ticker)
    news = []
    articles = getattr(stock, "news", [])
    for n in articles[:max_articles]:
        content = n.get("content", {})
        title = content.get("title") or n.get("title", "")
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
        news.append({
            "title": title,
            "publishedAt": published,
            "source": source,
            "url": url,
            "description": summary,
            "search_keyword": ticker,
            "api": "Yahoo Finance"
        })
    return news

def fetch_news_newsapi(keywords: List[str], api_key: Optional[str], max_articles=10) -> List[Dict]:
    if not api_key:
        return []
    import requests
    url = "https://newsapi.org/v2/everything"
    news = []
    for q in keywords:
        params = {
            "q": q,
            "apiKey": api_key,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": max_articles,
        }
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            for article in data.get("articles", []):
                news.append({
                    "title": article.get("title"),
                    "publishedAt": article.get("publishedAt"),
                    "source": article.get("source", {}).get("name"),
                    "url": article.get("url"),
                    "description": article.get("description"),
                    "search_keyword": q,
                    "api": "NewsAPI"
                })
        if len(news) >= max_articles:
            break
    return news[:max_articles]

def fetch_news_serpapi(keywords: List[str], api_key: Optional[str], max_articles=10) -> List[Dict]:
    if not api_key:
        return []
    try:
        from serpapi import GoogleSearch
    except ImportError:
        return []
    news = []
    for q in keywords:
        params = {
            "q": q,
            "engine": "google_news",
            "api_key": api_key,
            "num": max_articles,
            "hl": "en"
        }
        search = GoogleSearch(params)
        results = search.get_dict()
        for article in results.get("news_results", []):
            news.append({
                "title": article.get("title"),
                "publishedAt": article.get("date"),
                "source": article.get("source"),
                "url": article.get("link"),
                "description": article.get("snippet"),
                "search_keyword": q,
                "api": "SerpAPI"
            })
        if len(news) >= max_articles:
            break
    return news[:max_articles]

def llm_news_summary(keywords, company, sector, industry, region, deduped_news, openai_client):
    import json as pyjson
    import re
    try:
        keywords = keywords[:10]
        headline_snippets = deduped_news[:15] if deduped_news else []
        news_text = "\n".join([
            f"- {n['title']}: {n.get('description', '')}" for n in headline_snippets
        ]) or "No articles available."

        prompt = f"""
You are a financial news analyst with deep domain knowledge of global markets, industries, and companies.

Your task is to:
1. Use your internal financial expertise and reasoning.
2. Cross-reference it with the following recent headlines and descriptions:
{news_text}
3. Derive sentiment and insights for:
   - The company/stock ({company})
   - The sector ({sector})
   - The region ({region})
4. Adjust or reaffirm your opinion based on the real news.
5. Provide a final 4–5 sentence executive summary.

Respond only in JSON format:
{{
  "company_keywords": {keywords},
  "stock_sentiment": {{"score": "...", "reason": "..." }},
  "sector_sentiment": {{"score": "...", "reason": "..." }},
  "region_sentiment": {{"score": "...", "reason": "..." }},
  "summary": "..."
}}
"""
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        raw = response.choices[0].message.content.strip()

        # Remove markdown code fences if present
        raw = re.sub(r"^```json\s*|```$", "", raw.strip(), flags=re.IGNORECASE)

        # Extract JSON or dict block
        json_match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if json_match:
            raw_json = json_match.group(0)
            try:
                # Try regular JSON first
                return pyjson.loads(raw_json)
            except Exception:
                # Fallback: Python dict with single quotes
                import ast
                return ast.literal_eval(raw_json)
        else:
            print("[ERROR] No JSON/dict found in LLM output! Full output was:")
            print(raw)
            return {}
    except Exception as e:
        print("[ERROR] LLM summary failed:", str(e))
        print("[ERROR] Raw LLM output was:")
        print(raw)
        return {}


def dedupe_news(news: List[Dict], max_articles=12):
    seen = set()
    deduped = []
    for n in news:
        key = (n.get("title") or "", n.get("url") or "")
        if key not in seen and n.get("title"):
            deduped.append(n)
            seen.add(key)
        if len(deduped) >= max_articles:
            break
    return deduped

def news_agent_stock(
    ticker: str,
    openai_client=None,
    newsapi_key=None,
    serpapi_key=None,
    max_articles=12,
    verbose=False
):
    if verbose:
        print(f"[DEBUG] Starting news_agent_stock for ticker: {ticker}")
    
    # Step 1: Metadata
    meta_yf = get_metadata_yfinance(ticker)
    company_names = [meta_yf.get("company_name", ticker)]
    sector = meta_yf.get("sector")
    industry = meta_yf.get("industry")
    region = meta_yf.get("region")

    # Step 2: LLM-enhanced metadata
    if openai_client:
        print("[DEBUG] Calling infer_metadata_llm ...")
        llm_meta = infer_metadata_llm(ticker, openai_client)
        print("[DEBUG] LLM meta returned:", llm_meta)
        company_names = llm_meta.get("company_names") or company_names
        sector = llm_meta.get("sector") or sector
        industry = llm_meta.get("industry") or industry
        region = llm_meta.get("region") or region
        print("[DEBUG] Calling expand_search_keywords_llm ...")
        keywords = expand_search_keywords_llm(company_names, sector, industry, region, openai_client)
        print("[DEBUG] Keywords from LLM:", keywords)
    else:
        keywords = list({ticker, *company_names, sector, industry, region})
        keywords = [k for k in keywords if k and k.lower() != "unknown"]
    if verbose:
        print(f"[DEBUG] Keywords: {keywords}")

    # Step 3: News fetching
    print("[DEBUG] Fetching yfinance news ...")
    all_news = fetch_yfinance_news(ticker, max_articles)
    print(f"[DEBUG] yfinance news: {len(all_news)} articles")
    all_news += fetch_news_newsapi(keywords, newsapi_key, max_articles)
    print(f"[DEBUG] newsapi news count: {len(all_news)}")
    all_news += fetch_news_serpapi(keywords, serpapi_key, max_articles)
    print(f"[DEBUG] serpapi news count: {len(all_news)}")

    deduped_news = dedupe_news(all_news, max_articles)
    print(f"[DEBUG] deduped_news count: {len(deduped_news)}")

    # Step 4: LLM-first synthesis
    llm_summary = None
    if openai_client:
        print("[DEBUG] Calling llm_news_summary ...")
        llm_summary = llm_news_summary(keywords, company_names, sector, industry, region, deduped_news, openai_client)
        print("[DEBUG] llm_summary returned:", llm_summary)

    return {
        "ticker": ticker,
        "company_names": company_names,
        "sector": sector,
        "industry": industry,
        "region": region,
        "keywords": keywords,
        "news": deduped_news,
        "llm_summary": llm_summary,
        "news_counts": {
            "yfinance": len(fetch_yfinance_news(ticker, max_articles)),
            "newsapi": len(fetch_news_newsapi(keywords, newsapi_key, max_articles)),
            "serpapi": len(fetch_news_serpapi(keywords, serpapi_key, max_articles)),
        }
    }

