# streamlit_na_stock.py

import streamlit as st
import agents.na_stock as na_stock
from openai import OpenAI

st.set_page_config(page_title="AI News Analyst Agent", page_icon="📰", layout="centered")

st.title("📰 AI News Analyst Agent")
st.markdown(
    """
    Enter a stock ticker (e.g., `AAPL`, `D05.SI`, `UOB`, `TSLA`) to see a combined AI-powered news analysis and live news headlines.
    """
)

ticker = st.text_input("Enter Ticker Symbol", value="AAPL")
max_articles = st.slider("Max news articles", min_value=3, max_value=25, value=10)
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
        client = OpenAI(api_key=openai_key)
        result = na_stock.news_agent_stock(
            ticker,
            openai_client=client,
            newsapi_key=newsapi_key,
            serpapi_key=serpapi_key,
            max_articles=max_articles,
            verbose=True
        )

        # --- Show company info and keywords
        st.markdown(f"""
        **Company Names / Aliases:** {', '.join(result.get('company_names', []))}
        **Sector:** {result.get('sector') or 'N/A'}
        **Industry:** {result.get('industry') or 'N/A'}
        **Region:** {result.get('region') or 'N/A'}
        **Keywords Used:** {', '.join(result.get('keywords', []))}
        """)

        # --- Source counts
        nc = result.get("news_counts", {})
        st.markdown(f"""
        **News Found:**  
        - Yahoo Finance: {nc.get('yfinance',0)}  
        - NewsAPI: {nc.get('newsapi',0)}  
        - SerpAPI: {nc.get('serpapi',0)}
        """)

        # --- News Expanders by API
        news = result.get("news", [])
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
                with st.expander(f"{api} ({len(news_by_api[api])} articles)", expanded=(len(apis)==1)):
                    for n in news_by_api[api]:
                        st.markdown(f"**{n['title']}**")
                        st.write(f"*Published:* {n.get('publishedAt')}  \n*Source:* {n.get('source')}  \n*Search Keyword:* {n.get('search_keyword')}")
                        if n.get('description'):
                            st.write(n['description'])
                        if n.get("url"):
                            st.markdown(f"[Read Full Article]({n['url']})")
                        st.markdown("---")
        else:
            st.warning("No live news found from Yahoo Finance or APIs.")


        # --- LLM fallback summary
        llm_summary = result.get("llm_summary")
        if llm_summary:
            st.markdown("---")
            st.subheader("LLM-Based News & Sentiment Summary")
            st.json(llm_summary)






