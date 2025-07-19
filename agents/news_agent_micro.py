import yfinance as yf
import requests
from typing import List, Dict, Optional
import time
from bs4 import BeautifulSoup
import feedparser
from urllib.parse import urlparse, parse_qs, unquote

from langchain.prompts import PromptTemplate
from langchain_community.chat_models import ChatOpenAI
from langchain.chains import LLMChain
from langchain_core.output_parsers import JsonOutputParser
from langchain.output_parsers import OutputFixingParser

def get_unwrapped(obj, *keys):
    while isinstance(obj, dict) and 'text' in obj and isinstance(obj['text'], dict):
        obj = obj['text']
    if isinstance(obj, dict) and 'result' in obj and isinstance(obj['result'], dict):
        obj = obj['result']
    for k in keys:
        if isinstance(obj, dict):
            obj = obj.get(k)
        else:
            return None
    return obj

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

GOOGLE_NAV_TITLES = {"news", "home", "for you", "following", "latest"}

def extract_original_url(google_news_url):
    parsed = urlparse(google_news_url)
    qs = parse_qs(parsed.query)
    if 'url' in qs:
        return unquote(qs['url'][0])
    return google_news_url

def parse_google_rss(query, max_articles=10):
    url = f"https://news.google.com/rss/search?q={query.replace(' ', '+')}&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(url)
    news = []
    for entry in feed.entries:
        title = entry.get("title", "").strip()
        if not title or title.lower() in GOOGLE_NAV_TITLES:
            continue
        url_ = entry.get("link", "")
        if url_.startswith("https://news.google.com") and "/articles/" not in url_:
            continue
        real_url = extract_original_url(url_)
        news.append({
            "title": title,
            "url": real_url,
            "publishedAt": entry.get("published"),
            "source": (entry.get("source", {}) or {}).get("title") or "Google News",
            "description": BeautifulSoup(entry.get("summary", ""), "html.parser").text,
            "search_keyword": query,
            "api": "GoogleNews-RSS"
        })
        if len(news) >= max_articles:
            break
    return news

def is_google_news_junk(title, url_):
    if not title or title.strip().lower() in GOOGLE_NAV_TITLES:
        return True
    if not url_:
        return True
    if url_.startswith("https://news.google.com") and "/articles/" not in url_:
        return True
    return False

def scrape_google_news_html(query, max_articles=10, sleep=1.5):
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; DemoBot/0.1; +https://yourdomain.com/demo)"
    }
    url = f"https://news.google.com/search?q={query.replace(' ', '%20')}&hl=en-US&gl=US&ceid=US:en"
    resp = requests.get(url, headers=headers, timeout=10)
    time.sleep(sleep)
    articles = []
    if resp.status_code == 200:
        soup = BeautifulSoup(resp.text, "html.parser")
        for item in soup.select("article"):
            headline_tag = item.find("h3")
            if not headline_tag or not headline_tag.text.strip():
                continue
            title = headline_tag.text.strip()
            link_tag = headline_tag.find("a")
            url_ = ("https://news.google.com" + link_tag["href"][1:]) if link_tag and link_tag.has_attr("href") and link_tag["href"].startswith(".") else ""
            if is_google_news_junk(title, url_):
                continue
            real_url = extract_original_url(url_)
            snippet = ""
            snippet_tag = item.find("span", attrs={"class": "xBbh9"})
            if snippet_tag:
                snippet = snippet_tag.text.strip()
            published = ""
            time_tag = item.find("time")
            if time_tag and time_tag.has_attr("datetime"):
                published = time_tag["datetime"]
            source = ""
            source_tag = item.find("div", class_="SVJrMe")
            if source_tag:
                source = source_tag.text.strip()
            articles.append({
                "title": title,
                "url": real_url,
                "publishedAt": published,
                "source": source or "Google News",
                "description": snippet,
                "search_keyword": query,
                "api": "GoogleNews-HTML"
            })
            if len(articles) >= max_articles:
                break
    return articles

def fetch_google_news_combined(query, max_articles=10):
    news = parse_google_rss(query, max_articles)
    if len(news) < max_articles:
        html_news = scrape_google_news_html(query, max_articles - len(news))
        news.extend(html_news)
    return news[:max_articles]

def parse_bing_rss(query, max_articles=10):
    url = f"https://www.bing.com/news/search?q={query.replace(' ', '+')}&format=rss"
    feed = feedparser.parse(url)
    news = []
    for entry in feed.entries[:max_articles]:
        news.append({
            "title": entry.get("title"),
            "url": entry.get("link"),
            "publishedAt": entry.get("published"),
            "source": (entry.get("source", {}) or {}).get("title") or "Bing News",
            "description": BeautifulSoup(entry.get("summary", ""), "html.parser").text,
            "search_keyword": query,
            "api": "BingNews-RSS"
        })
    return news

def scrape_bing_news_html(query, max_articles=10, sleep=1.5):
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; DemoBot/0.1; +https://yourdomain.com/demo)"
    }
    url = f"https://www.bing.com/news/search?q={query.replace(' ', '+')}&setlang=en"
    resp = requests.get(url, headers=headers, timeout=10)
    time.sleep(sleep)
    articles = []
    if resp.status_code == 200:
        soup = BeautifulSoup(resp.text, "html.parser")
        for item in soup.select("div.news-card, div.t_s"):
            headline_tag = item.find("a")
            if not headline_tag or not headline_tag.text.strip():
                continue
            title = headline_tag.text.strip()
            url = headline_tag["href"] if headline_tag.has_attr("href") else ""
            snippet = ""
            snippet_tag = item.find("div", class_="snippet")
            if snippet_tag:
                snippet = snippet_tag.text.strip()
            source = "Bing News"
            source_tag = item.find("div", class_="source")
            if source_tag:
                source = source_tag.text.strip()
            published = ""
            time_tag = item.find("span", class_="source")
            if time_tag:
                try:
                    parts = time_tag.text.split("·")
                    if len(parts) > 1:
                        published = parts[1].strip()
                except Exception:
                    published = ""
            articles.append({
                "title": title,
                "url": url,
                "publishedAt": published,
                "source": source,
                "description": snippet,
                "search_keyword": query,
                "api": "BingNews-HTML"
            })
            if len(articles) >= max_articles:
                break
    return articles

def fetch_bing_news_combined(query, max_articles=10):
    news = parse_bing_rss(query, max_articles)
    if len(news) < max_articles:
        html_news = scrape_bing_news_html(query, max_articles - len(news))
        news.extend(html_news)
    return news[:max_articles]

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

def enforce_json_double_quotes(text: str) -> str:
    import re
    text = re.sub(r"(?<!\\)'", '"', text)
    text = re.sub(r',(\s*[\]}])', r'\1', text)
    return text

# -- ASEAN/Asia country codes for default macro fetch --
ASEAN_CODES = ["SGP", "MYS", "IDN", "THA", "PHL", "VNM", "BRN", "KHM", "LAO", "MMR"]
ASIA_CODES = ["SGP", "MYS", "IDN", "THA", "PHL", "VNM", "CHN", "IND", "KOR", "JPN", "HKG", "TWN"]

def news_agent_micro(
    ticker: str,
    openai_api_key: str,
    newsapi_key: str = None,
    serpapi_key: str = None,
    macro_data: Optional[dict] = None,
    macro_countries: Optional[list] = None,  # NEW
    max_articles: int = 12
):
    meta_prompt = PromptTemplate.from_template(
        "Given the stock ticker {ticker}, return the corresponding company names (as a list), sector, industry, and region. "
        "If any value is not known, return an empty string or empty list. "
        "Respond ONLY with valid JSON in this format: "
        '{{"company_names": ["..."], "sector": "...", "industry": "...", "region": "..."}}'
        "\nIMPORTANT: Return double-quoted JSON only, and no extra text or explanation."
    )
    kw_prompt = PromptTemplate.from_template(
        "Generate the 6 most relevant news search keywords for {company_names}, sector: {sector}, industry: {industry}, region: {region}. "
        "Include synonyms and sector/region phrases. Respond as JSON like this: "
        '{{"keywords": ["...","...","...","...","...","..."]}}'
        "\nIMPORTANT: All JSON keys and values must use double quotes (\")."
    )
    synth_prompt = PromptTemplate.from_template(
        """
You are an expert financial news and macro analyst with deep knowledge of companies, sectors, global markets, and economic trends.

YOUR TASK:
1. Begin with your own financial and economic expertise, reasoning, and market context for the specified stock, sector, industry, and region. 
2. Consider the following RECENT MACRO DATA (if available):
{macro_data}
3. Next, review and cross-check the following recent headlines and descriptions:
{news_text}

GUIDELINES:
- Combine your internal expertise, macro data, and the evidence from news headlines.
- If macro data and news sentiment diverge, clearly explain which you weigh more and why.
- When scoring sentiment, ALWAYS use only the labels: "Bullish", "Bearish", or "Neutral".
- Unless otherwise stated, all sentiment scores and summaries refer to the expected outlook over the next 1 month (30 days).
- If no headlines are available, provide an outlook based on your own expertise and macro data, and state that there is no recent news evidence.

OUTPUT (respond ONLY with valid JSON and no extra text):

{{
  "company_names": {company_names},
  "keywords": {keywords},
  "stock_sentiment": {{
    "score": "Bullish/Bearish/Neutral",
    "reason": "Explain in 1-2 sentences, mentioning if it is based on macro data, news evidence, or both.",
    "confidence": "High/Medium/Low"
  }},
  "sector_sentiment": {{
    "score": "Bullish/Bearish/Neutral",
    "reason": "Explain briefly."
  }},
  "region_sentiment": {{
    "singapore_score": "Bullish/Bearish/Neutral",
    "singapore_reason": "Briefly explain Singapore’s market/economic sentiment, citing macro data and news.",
    "regional_score": "Bullish/Bearish/Neutral",
    "regional_reason": "Briefly explain the sentiment for Southeast Asia or Asia as a whole. Highlight if and why the regional outlook differs from Singapore, citing macro data or news. If there is divergence (e.g. Singapore positive but SE Asia negative), explain why.",
    "divergence": "Yes/No — Is there a meaningful difference in outlook between Singapore and the regional market? If yes, briefly summarize the main reason."
  }},
  "risks": [
    {{ "label": "...", "details": "..." }}
  ],
  "opportunities": [
    {{ "label": "...", "details": "..." }}
  ],
  "major_events": [
    {{ "date": "...", "event": "..." }}
  ],
  "headline_sentiment": [
    {{ "title": "...", "sentiment": "Bullish/Bearish/Neutral" }}
  ],
  "summary": "Provide a 4–5 sentence investor-focused executive summary, referencing your own expertise, macro data, and recent news evidence. Clearly state if news or macro data was not available."
}}
IMPORTANT: All JSON output **must** use double quotes (\"), not single quotes.
"""
    )

    llm = ChatOpenAI(
        model="gpt-3.5-turbo",
        temperature=0.2,
        openai_api_key=openai_api_key
    )
    json_parser = JsonOutputParser()
    fixing_parser = OutputFixingParser.from_llm(parser=json_parser, llm=llm)
    meta_chain = LLMChain(
        llm=llm,
        prompt=meta_prompt,
        output_parser=fixing_parser
    )
    kw_chain = LLMChain(
        llm=llm,
        prompt=kw_prompt,
        output_parser=fixing_parser
    )
    synth_chain = LLMChain(
        llm=llm,
        prompt=synth_prompt,
        output_parser=fixing_parser
    )

    # --- 1. Metadata LLM ---
    meta_result = meta_chain.invoke({"ticker": ticker})
    meta_text = get_unwrapped(meta_result)
    if isinstance(meta_text, str):
        meta_text = enforce_json_double_quotes(meta_text)

    # --- 2. Keyword Expansion LLM ---
    kw_result = kw_chain.invoke({
        "company_names": meta_text.get("company_names"),
        "sector": meta_text.get("sector"),
        "industry": meta_text.get("industry"),
        "region": meta_text.get("region"),
    })
    keywords = get_unwrapped(kw_result, "keywords") or []
    if not isinstance(keywords, list):
        keywords = []

    # --- 3. News Fetch (All APIs & Scrapers, improved order) ---
    yf_news = fetch_yfinance_news(ticker, max_articles)
    newsapi_news = fetch_news_newsapi(keywords, newsapi_key, max_articles)
    serpapi_news = fetch_news_serpapi(keywords, serpapi_key, max_articles)

    google_news = []
    for kw in keywords:
        google_news.extend(fetch_google_news_combined(kw, max_articles=4))
    bing_news = []
    for kw in keywords:
        bing_news.extend(fetch_bing_news_combined(kw, max_articles=4))

    # Combine & dedupe
    all_news = yf_news + newsapi_news + serpapi_news + google_news + bing_news
    deduped_news = dedupe_news(all_news, max_articles)

    # --- 4. Macro Data (auto-load if not supplied) ---
    macro_data_fmt = macro_data
    if macro_data_fmt is None:
        try:
            from macro_loader import get_macro_data
            # If macro_countries not specified, default to Singapore and ASEAN
            macro_data_fmt = get_macro_data(macro_countries or ["SGP"] + ASEAN_CODES)
        except Exception:
            macro_data_fmt = {}

    # --- 5. Synthesis LLM Call ---
    news_text = "\n".join([
        f"- {n['title']}: {n.get('description','')}" for n in deduped_news[:12]
    ]) or "No articles available."

    synth_result = synth_chain.invoke({
        "ticker": ticker,
        "company_names": meta_text.get("company_names", []),
        "sector": meta_text.get("sector", ""),
        "industry": meta_text.get("industry", ""),
        "region": meta_text.get("region", ""),
        "keywords": keywords,
        "macro_data": macro_data_fmt,
        "news_text": news_text
    })
    output = get_unwrapped(synth_result)
    if isinstance(output, str):
        output = enforce_json_double_quotes(output)

    return {
        "meta": meta_text,
        "keywords": keywords,
        "deduped_news": deduped_news,
        "llm_output": output,
        "macro_data": macro_data_fmt
    }











