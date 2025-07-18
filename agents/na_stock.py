import yfinance as yf

# 1. Try to get sector/industry/region from yfinance
def get_metadata_yfinance(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        sector = info.get("sector", None)
        industry = info.get("industry", None)
        # Try to guess region from country or exchange
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

# 2. If yfinance metadata is missing, use LLM to infer sector/region
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

# 3. Use LLM to expand keywords/phrases for news search
def expand_search_keywords_llm(company_name, sector, industry, region, openai_client):
    prompt = (
        f"As a financial news analyst, generate a list of the 6 most relevant search phrases or keywords to find news related to the company '{company_name}', its sector '{sector}', industry '{industry}', and region '{region}'. "
        "Include stock ticker and all related synonyms or common sector/region keywords. "
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
    # Remove any duplicates, None, or "Unknown"
    keywords = [k for k in keywords if k and k.lower() != "unknown"]
    return keywords

# 4. Search Yahoo Finance news for all generated keywords
def fetch_yfinance_news_for_keywords(keywords, max_articles=12):
    import yfinance as yf
    news = []
    for kw in keywords:
        try:
            stock = yf.Ticker(kw)
            articles = getattr(stock, "news", [])
            for n in articles:
                # New Yahoo format: info is nested under 'content'
                content = n.get("content", {})
                title = content.get("title") or n.get("title", "")
                # Try to find url in either clickThroughUrl or canonicalUrl
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
                article = {
                    "title": title,
                    "publishedAt": published,
                    "source": source,
                    "url": url,
                    "description": summary,
                    "search_keyword": kw
                }
                news.append(article)
        except Exception:
            continue
    # Deduplicate by title
    seen_titles = set()
    deduped_news = []
    for a in news:
        if a["title"] and a["title"] not in seen_titles:
            deduped_news.append(a)
            seen_titles.add(a["title"])
        if len(deduped_news) >= max_articles:
            break
    return deduped_news

# 5. Master function: run all steps
def news_agent_stock(
    ticker,
    openai_client=None,
    max_articles=12,
    verbose=False
):
    # Step 1: Try yfinance metadata
    metadata = get_metadata_yfinance(ticker)
    # Step 2: Use LLM if any key info missing
    if openai_client and (not metadata["sector"] or not metadata["region"] or not metadata["industry"]):
        if verbose:
            print("Falling back to LLM for metadata...")
        metadata = infer_metadata_llm(ticker, openai_client)
    if verbose:
        print(f"Metadata for {ticker}:", metadata)

    # Step 3: Generate search keywords
    keywords = [ticker]
    if openai_client:
        keywords = expand_search_keywords_llm(
            metadata["company_name"], metadata["sector"], metadata["industry"], metadata["region"], openai_client
        )
    if verbose:
        print("Keywords:", keywords)

    # Step 4: Fetch news
    news = fetch_yfinance_news_for_keywords(keywords, max_articles=max_articles)
    summary = f"{len(news)} news articles found for keywords: {', '.join(keywords)}."
    sentiment = "N/A"
    drivers = []

    return {
        "ticker": ticker,
        "company_name": metadata.get("company_name"),
        "sector": metadata.get("sector"),
        "industry": metadata.get("industry"),
        "region": metadata.get("region"),
        "keywords": keywords,
        "summary": summary,
        "sentiment": sentiment,
        "drivers": drivers,
        "headlines": news,
    }




