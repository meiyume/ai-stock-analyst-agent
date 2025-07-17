import streamlit as st
from na_stock import news_agent_stock

st.set_page_config(page_title="News Analyst: Stock/Sector", page_icon="📰")

st.title("📰 Stock/Sector News Analyst (AI)")
ticker = st.text_input("Enter Stock Ticker or Company Name (e.g., SIA, Wilmar):")
sector = st.text_input("Sector/Industry (optional):")
if st.button("Analyze News", type="primary"):
    with st.spinner("Fetching and analyzing news..."):
        api_key = st.secrets["NEWSAPI_KEY"]
        openai_key = st.secrets["OPENAI_API_KEY"]
        result = news_agent_stock(ticker, ticker, sector, openai_api_key=openai_key, newsapi_key=api_key)
        st.subheader("Summary")
        st.write(result["summary"])
        st.subheader("Top Headlines")
        for h in result["headlines"]:
            st.markdown(f"- [{h['title']}]({h['url']}) <small>({h['source']}, {h['publishedAt'][:10]})</small>", unsafe_allow_html=True)
