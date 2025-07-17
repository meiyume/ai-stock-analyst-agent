import streamlit as st
from openai import OpenAI
from na_stock import news_agent_stock

st.title("📰 Stock/Sector News Analyst")
ticker = st.text_input("Enter Stock Ticker (e.g., U11.SI):")
sector = st.text_input("Sector (optional):")
if st.button("Analyze News", type="primary"):
    with st.spinner("Analyzing news..."):
        openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        newsapi_key = st.secrets["NEWSAPI_KEY"]
        serpapi_key = st.secrets["SERPAPI_KEY"]
        result = news_agent_stock(
            ticker,
            sector_name=sector,
            openai_client=openai_client,
            newsapi_key=newsapi_key,
            serpapi_key=serpapi_key,
        )
        st.subheader("Summary")
        st.write(result["summary"])
        st.subheader(f"Sentiment: {result['sentiment']}")
        st.subheader("Key News Drivers")
        for d in result["drivers"]:
            st.write(f"- {d}")
        st.subheader("Recent Headlines")
        for h in result["headlines"]:
            st.markdown(f"- [{h['title']}]({h['url']}) <small>({h['source']}, {h['publishedAt'][:10]})</small>", unsafe_allow_html=True)




