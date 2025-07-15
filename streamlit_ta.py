import streamlit as st
import json
from datetime import datetime, timedelta
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from agents.ta_global import ta_global
from llm_utils import call_llm

st.set_page_config(page_title="AI Global Technical Macro Analyst", page_icon="🌍")
st.title("🌍 AI Global Macro Technical Analyst Demo")
st.markdown(
    """
    This demo fetches global market data, computes technical metrics, and asks the LLM to summarize the global technical outlook
    in both a professional (analyst) and plain-English (executive) format.
    """
)

# --- Get latest global technical summary
with st.spinner("Loading global technical summary..."):
    try:
        summary = ta_global()
        st.success("Fetched and computed global technical metrics.")
    except Exception as e:
        st.error(f"Error in ta_global(): {e}")
        st.stop()

st.subheader("Raw Global Technical Data")
with st.expander("Show raw summary dict", expanded=False):
    st.json(summary)

# ========== EQUITIES ==========
with st.header("Equities"):
    for label, ticker in [
        ("S&P 500", "^GSPC"),
        ("Nasdaq", "^IXIC"),
        ("EuroStoxx50", "^STOXX50E"),
        ("Nikkei", "^N225"),
        ("Hang Seng", "^HSI"),
        ("FTSE100", "^FTSE"),
        ("VIX", "^VIX"),
    ]:
        with st.expander(f"{label} ({ticker})", expanded=False):
            try:
                end = datetime.today()
                start = end - timedelta(days=180)
                df = yf.download(ticker, start=start, end=end, interval="1d", auto_adjust=True, progress=False)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = ['_'.join([str(i) for i in col if i]) for col in df.columns.values]
                df = df.reset_index()
                date_col, close_col = None, None
                for col in df.columns:
                    if isinstance(col, str) and col.lower() in ["date", "datetime", "index"]:
                        date_col = col
                    if isinstance(col, str) and "close" in col.lower():
                        close_col = col
                if not date_col or not close_col or len(df.dropna(subset=[date_col, close_col])) < 5:
                    st.info(f"Not enough {label} data to plot.")
                else:
                    df = df.dropna(subset=[date_col, close_col])
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=df[date_col], y=df[close_col], mode='lines', name=label
                    ))
                    fig.update_layout(
                        title=f"{label} (Last 6 Months)",
                        xaxis_title="Date", yaxis_title="Price",
                        template="plotly_white", height=320
                    )
                    st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.info(f"{label} chart failed to load: {e}")

# ========== FIXED INCOME / RATES ==========
with st.header("Fixed Income / Rates"):
    for label, ticker in [
        ("US 10Y Yield", "^TNX"),
        ("US 2Y Yield", "^IRX"),
    ]:
        with st.expander(f"{label} ({ticker})", expanded=False):
            try:
                end = datetime.today()
                start = end - timedelta(days=180)
                df = yf.download(ticker, start=start, end=end, interval="1d", auto_adjust=True, progress=False)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = ['_'.join([str(i) for i in col if i]) for col in df.columns.values]
                df = df.reset_index()
                date_col, close_col = None, None
                for col in df.columns:
                    if isinstance(col, str) and col.lower() in ["date", "datetime", "index"]:
                        date_col = col
                    if isinstance(col, str) and "close" in col.lower():
                        close_col = col
                if not date_col or not close_col or len(df.dropna(subset=[date_col, close_col])) < 5:
                    st.info(f"Not enough {label} data to plot.")
                else:
                    df = df.dropna(subset=[date_col, close_col])
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=df[date_col], y=df[close_col], mode='lines', name=label
                    ))
                    fig.update_layout(
                        title=f"{label} (Last 6 Months)",
                        xaxis_title="Date", yaxis_title="Yield (%)",
                        template="plotly_white", height=320
                    )
                    st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.info(f"{label} chart failed to load: {e}")

# ========== FX ==========
with st.header("FX"):
    for label, ticker in [
        ("DXY Dollar Index", "DX-Y.NYB"),
        ("USD/SGD", "USDSGD=X"),
        ("USD/JPY", "JPY=X"),
        ("EUR/USD", "EURUSD=X"),
        ("USD/CNH", "USDCNH=X"),
    ]:
        with st.expander(f"{label} ({ticker})", expanded=False):
            try:
                end = datetime.today()
                start = end - timedelta(days=180)
                df = yf.download(ticker, start=start, end=end, interval="1d", auto_adjust=True, progress=False)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = ['_'.join([str(i) for i in col if i]) for col in df.columns.values]
                df = df.reset_index()
                date_col, close_col = None, None
                for col in df.columns:
                    if isinstance(col, str) and col.lower() in ["date", "datetime", "index"]:
                        date_col = col
                    if isinstance(col, str) and "close" in col.lower():
                        close_col = col
                if not date_col or not close_col or len(df.dropna(subset=[date_col, close_col])) < 5:
                    st.info(f"Not enough {label} data to plot.")
                else:
                    df = df.dropna(subset=[date_col, close_col])
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=df[date_col], y=df[close_col], mode='lines', name=label
                    ))
                    fig.update_layout(
                        title=f"{label} (Last 6 Months)",
                        xaxis_title="Date", yaxis_title="FX Rate",
                        template="plotly_white", height=320
                    )
                    st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.info(f"{label} chart failed to load: {e}")

# ========== COMMODITIES ==========
with st.header("Commodities"):
    for label, ticker in [
        ("Gold", "GC=F"),
        ("Brent Oil", "BZ=F"),
        ("WTI Oil", "CL=F"),
        ("Copper", "HG=F"),
    ]:
        with st.expander(f"{label} ({ticker})", expanded=False):
            try:
                end = datetime.today()
                start = end - timedelta(days=180)
                df = yf.download(ticker, start=start, end=end, interval="1d", auto_adjust=True, progress=False)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = ['_'.join([str(i) for i in col if i]) for col in df.columns.values]
                df = df.reset_index()
                date_col, close_col = None, None
                for col in df.columns:
                    if isinstance(col, str) and col.lower() in ["date", "datetime", "index"]:
                        date_col = col
                    if isinstance(col, str) and "close" in col.lower():
                        close_col = col
                if not date_col or not close_col or len(df.dropna(subset=[date_col, close_col])) < 5:
                    st.info(f"Not enough {label} data to plot.")
                else:
                    df = df.dropna(subset=[date_col, close_col])
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=df[date_col], y=df[close_col], mode='lines', name=label
                    ))
                    fig.update_layout(
                        title=f"{label} (Last 6 Months)",
                        xaxis_title="Date", yaxis_title="Price",
                        template="plotly_white", height=320
                    )
                    st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.info(f"{label} chart failed to load: {e}")

# --- LLM Summaries Section
st.subheader("LLM-Generated Summaries")
if st.button("Generate LLM Global Summaries", type="primary"):
    with st.spinner("Querying LLM..."):
        try:
            json_summary = json.dumps(summary, indent=2)
            llm_output = call_llm("global", json_summary)
            if "Technical Summary" in llm_output and "Plain-English Summary" in llm_output:
                tech = llm_output.split("Plain-English Summary")[0].replace("Technical Summary", "").strip()
                plain = llm_output.split("Plain-English Summary")[1].strip()
                st.markdown("**Technical Summary**")
                st.info(tech)
                st.markdown("**Plain-English Summary**")
                st.success(plain)
            else:
                st.warning("LLM output did not match expected template. Full output below:")
                st.code(llm_output)
        except Exception as e:
            st.error(f"LLM error: {e}")

st.caption("If you do not see the summaries, check the console logs for LLM errors or ensure your OpenAI API key is correctly set.")



