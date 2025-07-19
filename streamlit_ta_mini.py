import streamlit as st

# ---- Sidebar/User Input Example ----
st.set_page_config(page_title="AI News Agent", page_icon="📰")
st.title("📰 AI-Powered Stock News & Sentiment Agent")

ticker = st.text_input("Enter SGX Stock Ticker", value="D05.SI")
max_articles = st.number_input("Max Articles per Source", min_value=3, max_value=20, value=12)
openai_key = st.secrets.get("OPENAI_API_KEY", "")
newsapi_key = st.secrets.get("NEWSAPI_KEY", "")
serpapi_key = st.secrets.get("SERPAPI_KEY", "")

run_button = st.button("Run News Agent")

if run_button and ticker:
    import agents.na_stock as na_stock

    # ---- Run News Agent ----
    result = na_stock.news_agent_stock(
        ticker,
        openai_api_key=openai_key,
        newsapi_key=newsapi_key,
        serpapi_key=serpapi_key,
        max_articles=max_articles
    )

    st.markdown("---")
    st.subheader("🗂️ Ticker Meta Information")
    company_names = result.get('company_names')
    if not company_names or not isinstance(company_names, list):
        company_names = []
    st.markdown(f"**Company Names / Aliases:** {', '.join(company_names) if company_names else 'N/A'}")
    st.markdown(f"**Sector:** {result.get('sector') or 'N/A'}")
    st.markdown(f"**Industry:** {result.get('industry') or 'N/A'}")
    st.markdown(f"**Region:** {result.get('region') or 'N/A'}")
    st.markdown(f"**News Search Keywords:** {', '.join(result.get('keywords', []) or []) or 'N/A'}")

    # ---- LLM Summary & Sentiment ----
    st.markdown("---")
    st.subheader("🧠 LLM Summary & Sentiment Analysis")

    llm_summary = result.get("llm_summary", {})
    # Defensive: handle OutputFixingParser 'text' wrapping
    if isinstance(llm_summary, dict) and 'text' in llm_summary and isinstance(llm_summary['text'], dict):
        llm_summary = llm_summary['text']

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

    # ---- News Results (by Source/Expander) ----
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

    # ---- News Source Counts (Optional) ----
    st.markdown("---")
    st.markdown("##### News Source Counts")
    for src, count in result.get("news_counts", {}).items():
        st.write(f"{src}: {count}")

else:
    st.info("Enter a ticker and press 'Run News Agent' to start.")

st.markdown("### Bing News (raw, before deduplication)")
bing_news = [n for n in all_news if n.get('api', '').lower().startswith('bing')]
st.write(bing_news)

st.markdown("### Google News (raw, before deduplication)")
google_news = [n for n in all_news if n.get('api', '').lower().startswith('google')]
st.write(google_news)



all_news = result.get('all_news', [])

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




