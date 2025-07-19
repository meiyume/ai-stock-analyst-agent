import streamlit as st

# --- Import your agent here ---
from agents.news_agent_micro import news_agent_micro  # Adjust if your import path differs

st.set_page_config(page_title="AI Stock News Agent", page_icon="📰", layout="wide")

st.title("📰 AI-Powered Stock News Agent")

# ---- Sidebar: Configuration ----
with st.sidebar:
    st.header("⚙️ Configuration")
    openai_key = st.text_input("OpenAI API Key", type="password", value=st.secrets.get("OPENAI_API_KEY", ""))
    newsapi_key = st.text_input("NewsAPI Key", type="password", value=st.secrets.get("NEWSAPI_KEY", ""))
    serpapi_key = st.text_input("SerpAPI Key", type="password", value=st.secrets.get("SERPAPI_KEY", ""))
    st.markdown("---")
    st.caption("Keys are stored only for this session.")
    max_articles = st.slider("Max Articles per Source", min_value=3, max_value=25, value=10, step=1)

st.markdown("Enter a **stock ticker** (e.g., `D05.SI`, `MSFT`, `TSLA`) to generate a professional, LLM-powered market sentiment summary, sector and regional outlook, and deduplicated news headlines from all major sources.")

ticker = st.text_input("Stock Ticker:", value="D05.SI", max_chars=15, help="E.g., D05.SI, MSFT, TSLA")
run_button = st.button("🔍 Run News Agent")

if run_button and ticker.strip():
    with st.spinner(f"Fetching and analyzing news for **{ticker.upper()}**..."):
        result = news_agent_micro(
            ticker=ticker,
            openai_api_key=openai_key,
            newsapi_key=newsapi_key,
            serpapi_key=serpapi_key,
            max_articles=max_articles
        )

    st.success("Analysis complete!", icon="✅")

    # --- Metadata ---
    meta = result.get("meta", {})
    st.markdown("### 🏷️ Ticker Metadata")
    cols = st.columns(4)
    cols[0].markdown(f"**Company Names:**<br>{', '.join(meta.get('company_names', []) or [])}", unsafe_allow_html=True)
    cols[1].markdown(f"**Sector:**<br>{meta.get('sector', 'N/A')}", unsafe_allow_html=True)
    cols[2].markdown(f"**Industry:**<br>{meta.get('industry', 'N/A')}", unsafe_allow_html=True)
    cols[3].markdown(f"**Region:**<br>{meta.get('region', 'N/A')}", unsafe_allow_html=True)

    st.markdown("---")

    # --- Keywords Used ---
    keywords = result.get("keywords", [])
    st.caption("**News Search Keywords:** " + (", ".join(keywords) if keywords else "N/A"))

    # --- LLM Summary and Sentiment ---
    llm = result.get("llm_output", {})
    st.markdown("### 🧠 LLM Summary & Sentiment")
    if llm and "stock_sentiment" in llm:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Stock Sentiment", llm["stock_sentiment"].get("score", "N/A"))
            st.caption(llm["stock_sentiment"].get("reason", ""))
        with c2:
            st.metric("Sector Sentiment", llm.get("sector_sentiment", {}).get("score", "N/A"))
            st.caption(llm.get("sector_sentiment", {}).get("reason", ""))
        with c3:
            region_s = llm.get("region_sentiment", {})
            st.metric("Region Sentiment", region_s.get("regional_score", "N/A"))
            st.caption(region_s.get("regional_reason", ""))
        st.markdown("#### 📄 Executive Summary")
        st.markdown(llm.get("summary", "No summary returned."))
        st.markdown("---")
        # Risks & Opportunities
        st.markdown("#### ⚡ Risks & Opportunities")
        col1, col2 = st.columns(2)
        risks = llm.get("risks", [])
        opps = llm.get("opportunities", [])
        with col1:
            st.markdown("**Risks**")
            if risks:
                for r in risks:
                    st.write(f"• **{r.get('label','')}**: {r.get('details','')}")
            else:
                st.write("None detected.")
        with col2:
            st.markdown("**Opportunities**")
            if opps:
                for o in opps:
                    st.write(f"• **{o.get('label','')}**: {o.get('details','')}")
            else:
                st.write("None detected.")

        # Major Events
        st.markdown("#### 📅 Major Events")
        events = llm.get("major_events", [])
        if events:
            for e in events:
                st.write(f"• {e.get('date','')}: {e.get('event','')}")
        else:
            st.write("No major events detected.")

    else:
        st.warning("No summary or sentiment analysis available.")

    st.markdown("---")

    # --- News Headlines by Source (Deduped) ---
    st.markdown("### 📰 Deduplicated News Headlines")
    news = result.get("deduped_news", [])
    news_by_source = {}
    for n in news:
        src = n.get("api") or n.get("source") or "Other"
        news_by_source.setdefault(src, []).append(n)

    for src, articles in news_by_source.items():
        with st.expander(f"{src} ({len(articles)})", expanded=False):
            for a in articles:
                st.markdown(f"**{a.get('title','(No Title)')}**")
                st.caption(a.get("publishedAt", ""))                
                if a.get("description"):
                    st.write(a["description"])
                if a.get("url"):
                    st.markdown(f"[Read Original]({a['url']})", unsafe_allow_html=True)
                st.markdown("---")

    # --- Macro Data Diagnostics ---
    st.markdown("### 🌏 Macro Data Used")
    macro_data = result.get("macro_data", {})
    if macro_data:
        for c, d in macro_data.items():
            st.write(f"**{c}**: {d}")
    else:
        st.write("No macro data was included in this run.")

else:
    st.info("Enter a ticker and press **Run News Agent** to start.")









