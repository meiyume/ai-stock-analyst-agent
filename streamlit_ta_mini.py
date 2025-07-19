import streamlit as st
import agents.na_stock as na_stock  # Adjust if your import path differs

st.set_page_config(page_title="AI Stock News Agent", page_icon="📰")

st.title("📰 AI-Powered Stock News Agent")

# ---- Sidebar (API keys, etc.) ----
with st.sidebar:
    st.markdown("### Configuration")
    openai_key = st.secrets.get("OPENAI_API_KEY", "")
    newsapi_key = st.secrets.get("NEWSAPI_KEY", "")
    serpapi_key = st.secrets.get("SERPAPI_KEY", "")
    max_articles = st.number_input("Max Articles per Source", min_value=1, max_value=30, value=10)

# ---- Ticker Input ----
ticker = st.text_input("Enter Stock Ticker (e.g., D05.SI, MSFT, TSLA):", value="D05.SI")
run_button = st.button("Run News Analysis")

if run_button and ticker:
    st.info(f"Running news agent for **{ticker}**...")

    # ---- Agent Call ----
    result = na_stock.news_agent_stock(
        ticker,
        openai_api_key=openai_key,
        newsapi_key=newsapi_key,
        serpapi_key=serpapi_key,
        max_articles=max_articles
    )

    # ---- Meta Information ----
    st.markdown("---")
    st.subheader("📊 Ticker Metadata")
    st.write(f"**Company Names / Aliases:** {', '.join(result.get('company_names', []) or [])}")
    st.write(f"**Sector:** {result.get('sector', 'N/A')}")
    st.write(f"**Industry:** {result.get('industry', 'N/A')}")
    st.write(f"**Region:** {result.get('region', 'N/A')}")
    st.write(f"**Keywords Used:** {', '.join(result.get('keywords', []) or [])}")

    # ---- LLM Summary & Sentiment ----
    llm_summary = result.get("llm_summary", {})
    st.markdown("---")
    st.subheader("🧠 LLM Summary & Sentiment Analysis")
    if llm_summary and "stock_sentiment" in llm_summary:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**📈 Stock Sentiment**")
            st.markdown(f"**{llm_summary['stock_sentiment'].get('score', 'N/A')}**")
            st.caption(llm_summary['stock_sentiment'].get('reason', ''))
        with col2:
            st.markdown("**🏦 Sector Sentiment**")
            st.markdown(f"**{llm_summary.get('sector_sentiment', {}).get('score', 'N/A')}**")
            st.caption(llm_summary.get('sector_sentiment', {}).get('reason', ''))
        with col3:
            st.markdown("**🌍 Region Sentiment**")
            st.markdown(f"**{llm_summary.get('region_sentiment', {}).get('score', 'N/A')}**")
            st.caption(llm_summary.get('region_sentiment', {}).get('reason', ''))
        st.markdown("#### 🧾 Executive Summary")
        st.markdown(llm_summary.get("summary", ""))
    else:
        st.warning("No LLM summary returned or fields missing.")

    # ---- News Counts ----
    st.markdown("---")
    st.subheader("📰 News Source Counts")
    news_counts = result.get("news_counts", {})
    st.write(news_counts)

    # ---- News Results (Deduped, By Source/Expander) ----
    st.markdown("---")
    st.subheader("📰 News Headlines by Source")
    news_by_source = {}
    for n in result.get("news", []):
        src = n.get("api") or n.get("source") or "Unknown"
        news_by_source.setdefault(src, []).append(n)

    for src, articles in news_by_source.items():
        with st.expander(f"{src} ({len(articles)})", expanded=False):
            for a in articles:
                st.markdown(f"**{a.get('title','(No Title)')}**")
                st.caption(a.get("publishedAt", ""))
                if a.get("url"):
                    st.markdown(f"[Read]({a['url']})", unsafe_allow_html=True)
                if a.get("description"):
                    st.write(a["description"])
                st.markdown("---")

    # ---- Bing/Google/All News Diagnostics ----
    all_news = result.get("all_news", [])

    # Defensive: log non-dict items for diagnostics
    bad_items = []
    for i, n in enumerate(all_news):
        if not isinstance(n, dict):
            bad_items.append((i, n, type(n)))
    if bad_items:
        st.warning("Non-dict news items detected in all_news! (See below)")
        for idx, item, t in bad_items:
            st.write(f"Index {idx}: {item} (type: {t})")

    # Filter: Only keep dictionaries for processing
    all_news = [n for n in all_news if isinstance(n, dict)]

    st.markdown("---")
    st.subheader("🔎 Raw Scraper Diagnostics (Bing/Google/All News)")

    # Bing News
    bing_news = [n for n in all_news if n.get('api', '').lower().startswith('bing')]
    st.markdown("#### Bing News (Raw, Before Deduplication)")
    if bing_news:
        for n in bing_news:
            st.markdown(f"**{n.get('title', '(No Title)')}**")
            if n.get("url"):
                st.markdown(f"[Read]({n['url']})", unsafe_allow_html=True)
            st.caption(n.get("description", ""))
            st.markdown("---")
    else:
        st.write("No Bing news found.")

    # Google News
    google_news = [n for n in all_news if n.get('api', '').lower().startswith('google')]
    st.markdown("#### Google News (Raw, Before Deduplication)")
    if google_news:
        for n in google_news:
            st.markdown(f"**{n.get('title', '(No Title)')}**")
            if n.get("url"):
                st.markdown(f"[Read]({n['url']})", unsafe_allow_html=True)
            st.caption(n.get("description", ""))
            st.markdown("---")
    else:
        st.write("No Google news found.")

    # All News (optional, raw printout)
    st.markdown("#### All News (Combined Raw List, Before Deduplication)")
    st.write(all_news)

else:
    st.info("Please enter a ticker and press **Run News Analysis**.")








