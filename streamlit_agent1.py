import streamlit as st
import plotly.graph_objects as go
from agents.agent1_core import run_full_technical_analysis

st.set_page_config(page_title="Technical Analyst Agent 1", layout="wide")

st.title("🧠 Agent 1: Technical Analysis")

ticker = st.text_input("Enter SGX Ticker (e.g., U11.SI for UOB):", value="U11.SI")
selected_horizon = st.selectbox("Select Analysis Horizon:", ["1 Day", "3 Days", "7 Days", "30 Days"])

if st.button("Run Technical Analysis"):
    with st.spinner("Analyzing..."):
        results, df = run_full_technical_analysis(ticker, selected_horizon)

        if df is not None and not df.empty:
            df = df.reset_index()

            if "Date" not in df.columns:
                original_columns = df.columns.tolist()
                df.columns = ["Date"] + original_columns[1:]
                st.warning(f"⚠️ Renamed columns for plotting: {original_columns} → {df.columns.tolist()}")

            if "Date" in df.columns:
                st.subheader("📈 Candlestick Chart with SMA & Bollinger Bands")
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df["Date"], y=df["Close"], mode="lines", name="Close"))
                if "SMA5" in df.columns:
                    fig.add_trace(go.Scatter(x=df["Date"], y=df["SMA5"], mode="lines", name="SMA5"))
                if "SMA10" in df.columns:
                    fig.add_trace(go.Scatter(x=df["Date"], y=df["SMA10"], mode="lines", name="SMA10"))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.error("❌ 'Date' column still missing. Columns available: " + str(df.columns.tolist()))
        else:
            st.warning("⚠️ No data returned for the selected ticker and horizon.")

        st.subheader("🧠 Technical Summary (Agent 1)")
        st.json(results)