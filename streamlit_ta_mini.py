import streamlit as st
import agents.na_stock as na_stock  # Adjust path if needed

st.set_page_config(page_title="AI News Analyst Agent", page_icon="📰", layout="centered")

st.title("📰 AI News Analyst Agent")
st.markdown(
    """
    Enter a stock ticker (e.g., `AAPL`, `D05.SI`, `UOB`, `TSLA`) to see a combined AI-powered news analysis and live news headlines from Yahoo, NewsAPI, SerpAPI, Google, and Bing.
    """
)

ticker = st.text_input("Enter Ticker Symbol", value="AAPL")
max_articles = st.slider("Max news articles (after deduping)", min_value=3, max_value=25, value=12)
go = st.button("Analyze News")

if go and ticker:
    st.info(f"Running AI News Agent for **{ticker}** ...")
    # --- API keys from secrets
    newsapi_key = st.secrets.get("NEWSAPI_KEY", "")
    serpapi_key = st.secrets.get("SERPAPI_KEY", "")
    openai_key = st.secrets.get("OPENAI_API_KEY")
    if not openai_key:
        st.error("You need to provide your OpenAI API key in Streamlit secrets.")
    else:
        # --- Main Agent Call ---
        result = na_stock.news_agent_stock(
            ticker,
            openai_api_key=openai_key,
            newsapi_key=newsapi_key,
            serpapi_key=serpapi_key,
            max_articles=max_articles
        )
        
        llm_summary = result.get("llm_summary", {})
        
        # Handle possible 'text' field wrapping from OutputFixingParser
        if isinstance(llm_summary, dict) and 'text' in llm_summary and isinstance(llm_summary['text'], dict):
            llm_summary = llm_summary['text']
        
        st.markdown("---")
        st.subheader("🧠 LLM Summary & Sentiment Analysis")
        
        def get_nested(d, *keys):
            """Helper to get nested dict values without KeyError."""
            for k in keys:
                if isinstance(d, dict):
                    d = d.get(k)
                else:
                    return None
            return d
        
        if llm_summary:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("**📈 Stock Sentiment**")
                score = get_nested(llm_summary, 'stock_sentiment', 'score')
                reason = get_nested(llm_summary, 'stock_sentiment', 'reason')
                st.markdown(f"**{score or 'N/A'}**")
                st.caption(reason or "")
            with col2:
                st.markdown("**🏦 Sector Sentiment**")
                score = get_nested(llm_summary, 'sector_sentiment', 'score')
                reason = get_nested(llm_summary, 'sector_sentiment', 'reason')
                st.markdown(f"**{score or 'N/A'}**")
                st.caption(reason or "")
            with col3:
                st.markdown("**🌍 Region Sentiment**")
                score = get_nested(llm_summary, 'region_sentiment', 'score')
                reason = get_nested(llm_summary, 'region_sentiment', 'reason')
                st.markdown(f"**{score or 'N/A'}**")
                st.caption(reason or "")
            st.markdown("#### 🧾 Executive Summary")
            st.markdown(llm_summary.get("summary", ""))
        else:
            st.warning("No LLM summary returned.")
            st.write("Raw LLM summary:", llm_summary)


        # --- Company info & keywords
        st.markdown(f"""
        **Company Names / Aliases:** {', '.join(result.get('company_names', []))}
        **Sector:** {result.get('sector') or 'N/A'}
        **Industry:** {result.get('industry') or 'N/A'}
        **Region:** {result.get('region') or 'N/A'}
        **Keywords Used:** {', '.join(result.get('keywords', []))}
        """)

        # --- Source counts (now includes scrapers)
        nc = result.get("news_counts", {})
        st.markdown("**News Found:**")
        st.markdown(
            f"- Yahoo Finance: {nc.get('yfinance',0)}  \n"
            f"- NewsAPI: {nc.get('newsapi',0)}  \n"
            f"- SerpAPI: {nc.get('serpapi',0)}  \n"
            f"- Google News (Scrape): {nc.get('google_scrape',0)}  \n"
            f"- Bing News (Scrape): {nc.get('bing_scrape',0)}"
        )

        # --- News Expanders grouped by API/source
        news = result.get("news", [])
        if news:
            apis = sorted(set(n.get("api", "Other") for n in news))
            api_selected = st.selectbox("Show news from:", ["All"] + apis)
            # Group news by api
            from collections import defaultdict
            news_by_api = defaultdict(list)
            for n in news:
                news_by_api[n.get("api", "Other")].append(n)
            for api in apis:
                if api_selected != "All" and api_selected != api:
                    continue
                with st.expander(f"{api} ({len(news_by_api[api])} articles)", expanded=(len(apis) == 1)):
                    for n in news_by_api[api]:
                        st.markdown(f"**{n['title']}**")
                        st.write(f"*Source:* {n.get('source')}")
                        if n.get("publishedAt"):
                            st.write(f"*Published:* {n.get('publishedAt')}")
                        st.write(f"*Search Keyword:* {n.get('search_keyword')}")
                        if n.get('description'):
                            st.write(n['description'])
                        if n.get("url"):
                            st.markdown(f"[Read Full Article]({n['url']})")
                        st.markdown("---")
        else:
            st.warning("No live news found from any source.")

        # --- Optionally: full LLM summary (JSON) for debug/transparency
        st.markdown("---")
        st.subheader("LLM-Based News & Sentiment JSON Output")
        st.json(llm_summary)







