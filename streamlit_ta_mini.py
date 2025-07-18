from agents.na_stock import (
    get_company_aliases_from_ticker,
    fetch_stock_sector_news,
    fetch_news_serpapi,
    fetch_web_search_serpapi
)
import streamlit as st

st.title("News Debugger")
ticker = st.text_input("Enter Stock Ticker (e.g., U11.SI):")
sector = st.text_input("Sector (optional):")
newsapi_key = st.secrets["NEWSAPI_KEY"]
serpapi_key = st.secrets["SERPAPI_KEY"]

if ticker:
    aliases = get_company_aliases_from_ticker(ticker)
    st.markdown("**Search queries used:**")
    st.write(", ".join(aliases + ([sector] if sector else [])))

    for q in aliases:
        st.markdown(f"### Query: `{q}`")
        # Try NewsAPI
        newsapi_results = fetch_stock_sector_news(q, api_key=newsapi_key)
        st.write(f"NewsAPI articles: {len(newsapi_results)}")
        for a in newsapi_results:
            st.write(f"- {a['title']} ({a['source']})")

        # Try SerpAPI Google News (if key provided)
        if serpapi_key:
            serpapi_news = fetch_news_serpapi(q, serpapi_key)
            st.write(f"SerpAPI Google News articles: {len(serpapi_news)}")
            for s in serpapi_news:
                st.write(f"- {s['title']} ({s['source']})")

            # Try SerpAPI Google Web
            serpapi_web = fetch_web_search_serpapi(q, serpapi_key)
            st.write(f"SerpAPI Web articles: {len(serpapi_web)}")
            for w in serpapi_web:
                st.write(f"- {w['title']} ({w['source']})")



