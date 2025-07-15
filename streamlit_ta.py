import streamlit as st
import json
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go

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

# --------- LLM SUMMARIES AT TOP ---------
st.subheader("LLM-Generated Summaries")
json_summary = json.dumps(summary, indent=2)
if st.button("Generate LLM Global Summaries", type="primary"):
    with st.spinner("Querying LLM..."):
        try:
            llm_output = call_llm("global", json_summary)
            # Expecting: "Technical Summary\n...\nPlain-English Summary\n..."
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

# ---------- RAW GLOBAL TECHNICAL DATA ----------
st.subheader("Raw Global Technical Data")
with st.expander("Show raw summary dict", expanded=False):
    st.json(summary)

# ----------- CHART PLOTTING UTILS --------------
def plot_chart_with_sma(symbol, name, sma_window=20, comment=None):
    """Plots price + SMA for a given symbol with explanation caption."""
    try:
        end = datetime.today()
        start = end - timedelta(days=180)
        df = yf.download(symbol, start=start, end=end, interval="1d", auto_adjust=True, progress=False)
        # Flatten columns and detect columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = ['_'.join([str(i) for i in col if i]) for col in df.columns.values]
        df = df.reset_index()
        date_col = next((col for col in df.columns if "date" in col.lower()), None)
        close_col = next((col for col in df.columns if "close" in col.lower()), None)
        if not date_col or not close_col or len(df) < 5:
            st.info(f"{name} chart failed to load: columns found: {list(df.columns)}")
            return
        # Drop NaN and blank values
        df = df.dropna(subset=[date_col, close_col])
        if df.empty:
            st.info(f"Not enough {name} data to plot.")
            return
        # Compute SMA
        df["SMA"] = df[close_col].rolling(sma_window).mean()
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df[date_col],
            y=df[close_col],
            mode='lines',
            name=name,
            line=dict(width=2)
        ))
        fig.add_trace(go.Scatter(
            x=df[date_col],
            y=df["SMA"],
            mode='lines',
            name=f"SMA {sma_window}",
            line=dict(dash="dash")
        ))
        fig.update_layout(
            title=f"{name} (Last 6 Months)",
            xaxis_title="Date",
            yaxis_title="Price",
            template="plotly_white",
            height=350,
            legend=dict(x=0, y=1)
        )
        st.plotly_chart(fig, use_container_width=True)
        if comment:
            st.caption(comment)
    except Exception as e:
        st.info(f"{name} chart failed to load: {e}")

# ---------- CHART EXPLANATIONS ----------
chart_info = {
    "S&P 500": "S&P 500 is a broad-based index covering all major US economic sectors. Analysts use it as the main benchmark for US equity market health and direction.",
    "VIX": "The VIX, or volatility index, reflects expected 30-day volatility for the S&P 500. High VIX often signals investor fear; a falling VIX suggests calmer markets.",
    "Nasdaq": "The Nasdaq Composite is tech-heavy and reflects performance of technology and growth companies in the US.",
    "EuroStoxx50": "EuroStoxx 50 represents blue-chip stocks from the Eurozone, serving as a bellwether for European equities.",
    "Nikkei": "Nikkei 225 tracks large-cap stocks listed on the Tokyo Stock Exchange, and is the most quoted average of Japanese equities.",
    "HangSeng": "The Hang Seng Index is the leading indicator for the Hong Kong equity market and is sensitive to China's economy.",
    "FTSE100": "The FTSE 100 covers the largest UK companies by market cap, representing the broader London market.",
    "US10Y": "The US 10-Year Treasury yield is the global reference for long-term interest rates and a key driver for risk assets.",
    "US2Y": "The US 2-Year Treasury yield reflects short-term rate expectations and monetary policy shifts.",
    "DXY": "The US Dollar Index (DXY) measures the strength of the US dollar against a basket of major currencies.",
    "USD_SGD": "USD/SGD tracks the US dollar against Singapore dollar. It reflects capital flows and relative monetary policy.",
    "USD_JPY": "USD/JPY is the world's most traded FX pair after EUR/USD, a key risk barometer for Asia-Pacific.",
    "EUR_USD": "EUR/USD is the most traded currency pair globally and a key gauge of global risk sentiment.",
    "USD_CNH": "USD/CNH tracks the US dollar against the offshore Chinese yuan. Movements can signal capital flow and China-related market risk.",
    "Gold": "Gold is the classic safe haven asset, often rising during times of economic stress or inflation.",
    "Oil_Brent": "Brent crude is the international benchmark for oil prices, sensitive to global supply-demand and geopolitics.",
    "Oil_WTI": "WTI crude is the US oil benchmark and can show trends specific to North America supply/demand.",
    "Copper": "Copper is widely used in manufacturing and construction. Prices are a leading indicator of global industrial health."
}

# ---------- ALL CHARTS ----------
st.subheader("Global Markets - Technical Charts (All with SMA)")

# Equities
plot_chart_with_sma("^GSPC", "S&P 500", comment=chart_info["S&P 500"])
plot_chart_with_sma("^VIX", "VIX", comment=chart_info["VIX"])
plot_chart_with_sma("^IXIC", "Nasdaq", comment=chart_info["Nasdaq"])
plot_chart_with_sma("^STOXX50E", "EuroStoxx50", comment=chart_info["EuroStoxx50"])
plot_chart_with_sma("^N225", "Nikkei", comment=chart_info["Nikkei"])
plot_chart_with_sma("^HSI", "HangSeng", comment=chart_info["HangSeng"])
plot_chart_with_sma("^FTSE", "FTSE100", comment=chart_info["FTSE100"])

# Rates & FX
plot_chart_with_sma("^TNX", "US10Y", comment=chart_info["US10Y"])
plot_chart_with_sma("^IRX", "US2Y", comment=chart_info["US2Y"])
plot_chart_with_sma("DX-Y.NYB", "DXY", comment=chart_info["DXY"])
plot_chart_with_sma("USDSGD=X", "USD_SGD", comment=chart_info["USD_SGD"])
plot_chart_with_sma("JPY=X", "USD_JPY", comment=chart_info["USD_JPY"])
plot_chart_with_sma("EURUSD=X", "EUR_USD", comment=chart_info["EUR_USD"])
plot_chart_with_sma("USDCNH=X", "USD_CNH", comment=chart_info["USD_CNH"])

# Commodities
plot_chart_with_sma("GC=F", "Gold", comment=chart_info["Gold"])
plot_chart_with_sma("BZ=F", "Oil_Brent", comment=chart_info["Oil_Brent"])
plot_chart_with_sma("CL=F", "Oil_WTI", comment=chart_info["Oil_WTI"])
plot_chart_with_sma("HG=F", "Copper", comment=chart_info["Copper"])

# --- END ---





