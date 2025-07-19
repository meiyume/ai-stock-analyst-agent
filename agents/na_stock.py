import yfinance as yf
import requests
from typing import List, Dict, Optional
import time
from bs4 import BeautifulSoup

from langchain.prompts import PromptTemplate
from langchain_community.llms import OpenAI
from langchain.chains import LLMChain
from langchain_core.output_parsers import JsonOutputParser

# ===== News Fetch Functions =====

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

def scrape_google_news(query, max_articles=10, sleep=1.5):
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; DemoBot/0.1; +https://yourdomain.com/demo)"
    }
    url = f"https://news.google.com/search?q={query.replace(' ', '%20')}&hl=en-US&gl=US&ceid=US:en"
    resp = requests.get(url, headers=headers, timeout=10)
    time.sleep(sleep)
    articles = []
    if resp.status_code == 200:
        soup = BeautifulSoup(resp.text, "html.parser")
        seen_titles = set()
        for item in soup.select("article"):
            headline_tag = item.select_one("h3, h4")
            if not headline_tag:
                continue
            title = headline_tag.text.strip()
            if title in seen_titles or not title:
                continue
            seen_titles.add(title)
            link_tag = headline_tag.find("a")
            url = "https://news.google.com" + link_tag["href"][1:] if link_tag else ""
            snippet_tag = item.find("span")
            snippet = snippet_tag.text.strip() if snippet_tag else ""
            articles.append({
                "title": title,
                "publishedAt": "",
                "source": "Google News",
                "url": url,
                "description": snippet,
                "search_keyword": query,
                "api": "GoogleNews-Scrape"
            })
            if len(articles) >= max_articles:
                break
    return articles

def scrape_bing_news(query, max_articles=10, sleep=1.5):
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; DemoBot/0.1; +https://yourdomain.com/demo)"
    }
    url = f"https://www.bing.com/news/search?q={query.replace(' ', '+')}&FORM=HDRSC6&setlang=en"
    resp = requests.get(url, headers=headers, timeout=10)
    time.sleep(sleep)
    articles = []
    if resp.status_code == 200:
        soup = BeautifulSoup(resp.text, "html.parser")
        seen_titles = set()
        for item in soup.select("div.news-card, div.t_s"):
            headline_tag = item.find("a")
            if not headline_tag or not headline_tag.text.strip():
                continue
            title = headline_tag.text.strip()
            if title in seen_titles:
                continue
            seen_titles.add(title)
            url = headline_tag["href"]
            snippet_tag = item.find("div", class_="snippet")
            snippet = snippet_tag.text.strip() if snippet_tag else ""
            source_tag = item.find("div", class_="source")
            source = source_tag.text.strip() if source_tag else "Bing News"
            articles.append({
                "title": title,
                "publishedAt": "",
                "source": source,
                "url": url,
                "description": snippet,
                "search_keyword": query,
                "api": "BingNews-Scrape"
            })
            if len(articles) >= max_articles:
                break
    return articles

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

# ===== Top-level Pipeline Function =====

def news_agent_stock(
    ticker: str,
    openai_api_key: str,
    newsapi_key: str = None,
    serpapi_key: str = None,
    max_articles: int = 12
):
    # ---- LLM Chains: Now defined inside function with API key ----
    meta_prompt = PromptTemplate.from_template(
        "Given the stock ticker {ticker}, what are the company names (list), sector, industry, and region? "
        "Respond as JSON like this: "
        '{"company_names": [...], "sector": "...", "industry": "...", "region": "..."}'
    )
    kw_prompt = PromptTemplate.from_template(
        "Generate the 6 most relevant news search keywords for {company_names}, sector: {sector}, industry: {industry}, region: {region}. "
        "Include synonyms and sector/region phrases. Respond as JSON like this: "
        '{"keywords": [...]}'
    )
    synth_prompt = PromptTemplate.from_template(
        """
You are an expert financial news analyst with deep knowledge of companies, sectors, global markets, and macro trends.

YOUR TASK:
1. Begin with your own financial intelligence, reasoning, and market context for the specified stock, sector, industry, and region. 
2. Next, review and cross-check the following recent headlines and descriptions:
{news_text}

GUIDELINES:
- Combine your internal financial expertise with the evidence from the headlines.
- If the news supports your prior reasoning, reaffirm your outlook.
- If the news contradicts or updates your prior reasoning, revise your opinion accordingly.
- If no headlines are available, provide an outlook based on your own expertise and clearly state that there is no recent news evidence.
- Avoid speculation not grounded in your knowledge or the supplied news.

OUTPUT (respond ONLY with valid JSON and no extra text):

{
  "company_names": {company_names},
  "keywords": {keywords},
  "stock_sentiment": {
    "score": "Bullish/Bearish/Neutral",
    "reason": "Explain in 1-2 sentences, mentioning if it is based on your expertise, news evidence, or both.",
    "confidence": "High/Medium/Low"
  },
  "sector_sentiment": ...,
  "region_sentiment": ...,
  "risks": [
    { "label": "...", "details": "..." }
  ],
  "opportunities": [
    { "label": "...", "details": "..." }
  ],
  "major_events": [
    { "date": "...", "event": "..." }
  ],
  "headline_sentiment": [
    { "title": "...", "sentiment": "Positive/Negative/Neutral" }
  ],
  "summary": "Provide a 4–5 sentence investor-focused executive summary, referencing your own expertise, and clearly stating if news evidence was or was not available."
}
"""
    )
    llm = OpenAI(
        model_name="gpt-3.5-turbo",
        temperature=0.2,
        openai_api_key=openai_api_key
    )
    meta_chain = LLMChain(
        llm=llm,
        prompt=meta_prompt,
        output_parser=JsonOutputParser()
    )
    kw_chain = LLMChain(
        llm=llm,
        prompt=kw_prompt,
        output_parser=JsonOutputParser()
    )
    synth_chain = LLMChain(
        llm=llm,
        prompt=synth_prompt,
        output_parser=JsonOutputParser()
    )

    # -- 1. Metadata LLM --
    meta_result = meta_chain.invoke({"ticker": ticker})
    # -- 2. Keyword Expansion LLM --
    kw_result = kw_chain.invoke({
        "company_names": meta_result.get("company_names"),
        "sector": meta_result.get("sector"),
        "industry": meta_result.get("industry"),
        "region": meta_result.get("region"),
    })
    keywords = kw_result["keywords"]
    # -- 3. News Fetch (All APIs & Scrapers) --
    yf_news = fetch_yfinance_news(ticker, max_articles)
    newsapi_news = fetch_news_newsapi(keywords, newsapi_key, max_articles)
    serpapi_news = fetch_news_serpapi(keywords, serpapi_key, max_articles)
    google_news = []
    bing_news = []
    for kw in keywords[:2]:  # Only scrape top 2 keywords for demo speed/safety
        google_news += scrape_google_news(kw, max_articles=4, sleep=1.5)
        bing_news += scrape_bing_news(kw, max_articles=4, sleep=1.5)
    all_news = yf_news + newsapi_news + serpapi_news + google_news + bing_news
    deduped_news = dedupe_news(all_news, max_articles)
    # -- 4. Synthesis LLM --
    news_text = "\n".join([
        f"- {n['title']}: {n.get('description','')}" for n in deduped_news[:12]
    ]) or "No articles available."
    synth_input = {
        "company_names": meta_result.get("company_names"),
        "sector": meta_result.get("sector"),
        "industry": meta_result.get("industry"),
        "region": meta_result.get("region"),
        "keywords": keywords,
        "news_text": news_text,
    }
    llm_summary = synth_chain.invoke(synth_input)
    # -- 5. Output --
    return {
        "ticker": ticker,
        "company_names": meta_result.get("company_names"),
        "sector": meta_result.get("sector"),
        "industry": meta_result.get("industry"),
        "region": meta_result.get("region"),
        "keywords": keywords,
        "news": deduped_news,
        "llm_summary": llm_summary,
        "news_counts": {
            "yfinance": len(yf_news),
            "newsapi": len(newsapi_news),
            "serpapi": len(serpapi_news),
            "google_scrape": len(google_news),
            "bing_scrape": len(bing_news),
        }
    }











