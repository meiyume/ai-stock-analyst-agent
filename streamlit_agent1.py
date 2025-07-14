st.markdown(f"## 🏆 Chief Analyst Grand Outlook — {results['company_name']} ({results['ticker']}) — {results['horizon']}")

# Show only stock chart once at the top:
stock_chart = results['stock'].get("chart")
if stock_chart:
    st.plotly_chart(stock_chart, use_container_width=True, key="stock_chart")

st.divider()

tab_labels = ["Stock", "Sector", "Market", "Commodities", "Globals"]
tabs = st.tabs(tab_labels)
for i, label in enumerate(tab_labels):
    agent = label.lower()
    agent_data = results.get(agent, {})
    with tabs[i]:
        st.markdown(f"### {label} Agent AI Summary")
        st.markdown(f"**AI Summary:** {agent_data.get('llm_summary', 'No summary.')}")
        st.markdown(f"**Risk Level:** {agent_data.get('risk_level', 'N/A')}")
        with st.expander("Show technical details / raw data"):
            st.write(agent_data)
            df = agent_data.get("df")
            if isinstance(df, pd.DataFrame):
                st.dataframe(df)
        st.download_button(
            label="Download Agent Report",
            data=agent_data.get("llm_summary", ""),
            file_name=f"{ticker}_{label}_report.md"
        )






