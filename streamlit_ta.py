import streamlit as st
import json
from datetime import datetime, timedelta
from agents.ta_global import ta_global
from llm_utils import call_llm
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

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

# --- Prepare prompt for LLM
json_summary = json.dumps(summary, indent=2)

# --- LLM Summaries FIRST ---
st.subheader("LLM-Generated Summaries")
if st.button("Generate LLM Global Summaries", type="primary"):
    with st.spinner("Querying LLM..."):
        try:
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

# --- Raw Data
st.subheader("Raw Global Technical Data")
with st.expander("Show raw summary dict", expanded=False):
    st.json(summary)

# --- Chart explanations dictionary ---
chart_explanations = {
    "S&P 500": "_The S&P 500 is a broad-based US equity index, seen as a bellwether for the US and global economy. Analysts study the S&P 500 to gauge general market direction and risk sentiment._",
    "VIX (Volatility Index)": "_The VIX measures expected volatility in the S&P 500 over the next 30 days. A high VIX indicates market fear or uncertainty; a low VIX suggests calm or complacency._",
    "Nasdaq": "_The Nasdaq Composite tracks technology and growth stocks in the US. It is a key barometer for tech sector performance and risk appetite._",
    "Eurostoxx50": "_Eurostoxx50 is a leading index of blue-chip stocks in the Eurozone. It is widely followed as a gauge of European market health._",
    "Nikkei": "_The Nikkei 225 is Japan’s primary stock market index, reflecting the performance of major companies in the Japanese economy._",
    "Hang Seng": "_The Hang Seng Index tracks the largest companies on the Hong Kong Stock Exchange, serving as a proxy for China-related equity sentiment._",
    "FTSE100": "_The FTSE 100 is the UK’s leading stock market index, representing large cap companies on the London Stock Exchange._",
    "US 10Y Yield": "_The 10-year US Treasury yield is a benchmark for global interest rates and economic expectations. Rising yields often signal inflation or rate hike expectations._",
    "US 2Y Yield": "_The 2-year US Treasury yield reflects short-term interest rate outlook and is closely watched for signals on monetary policy._",
    "DXY (US Dollar Index)": "_The US Dollar Index measures the value of the US dollar against a basket of major world currencies. Moves in DXY often signal global risk-on or risk-off._",
    "USD/SGD": "_USD/SGD is the exchange rate of the US dollar to Singapore dollar, relevant for Southeast Asia’s financial markets._",
    "USD/JPY": "_USD/JPY is a key FX pair tracking the US dollar against the Japanese yen, watched for risk sentiment and policy divergence._",
    "EUR/USD": "_EUR/USD is the most traded currency pair in the world and is a bellwether for eurozone and US economic sentiment._",
    "USD/CNH": "_USD/CNH tracks the US dollar versus the offshore Chinese yuan, providing clues to China capital flows and global FX trends._",
    "Gold": "_Gold is a safe-haven asset often bought during market uncertainty or inflation fears._",
    "Oil Brent": "_Brent crude oil prices reflect global energy supply/demand and are a major driver of inflation and economic growth expectations._",
    "Oil WTI": "_WTI crude is the US benchmark for oil prices, sensitive to US supply/demand and geopolitics._",
    "Copper": "_Copper is an industrial metal, often called Dr. Copper for its ability to predict global economic cycles._",
}

# --- Chart configs (order and labels)
chart_configs = [
    # ticker,         label,            key in summary dict if used
    ("^GSPC", "S&P 500", None),
    ("^VIX", "VIX (Volatility Index)", None),
    ("^IXIC", "Nasdaq", None),
    ("^STOXX50E", "Eurostoxx50", None),
    ("^N225", "Nikkei", None),
    ("^HSI", "Hang Seng", None),
    ("^FTSE", "FTSE100", None),
    ("^TNX", "US 10Y Yield", None),
    ("^IRX", "US 2Y Yield", None),
    ("DX-Y.NYB", "DXY (US Dollar Index)", None),
    ("USDSGD=X", "USD/SGD", None),
    ("JPY=X", "USD/JPY", None),
    ("EURUSD=X", "EUR/USD", None),
    ("USDCNH=X", "USD/CNH", None),
    ("GC=F", "Gold", None),
    ("BZ=F", "Oil Brent", None),
    ("CL=F", "Oil WTI", None),
    ("HG=F", "Copper", None),
]

# --- Chart plotting function (with robust handling) ---
def plot_chart(ticker, label, summary_key=None):
    with st.container():
        with st.spinner(f"Loading {label} historical data..."):
            try:
                end = datetime.today()
                start = end - timedelta(days=180)
                data = yf.download(ticker, start=start, end=end, interval="1d", auto_adjust=True, progress=False)

                # Flatten MultiIndex if present
                if isinstance(data.columns, pd.MultiIndex):
                    data.columns = ['_'.join([str(i) for i in col if i]) for col in data.columns.values]
                data = data.reset_index()

                # Identify date and close columns
                date_col = None
                close_col = None
                for col in data.columns:
                    if isinstance(col, str) and col.lower() in ["date", "datetime", "index"]:
                        date_col = col
                    if isinstance(col, str) and "close" in col.lower():
                        close_col = col

                # Remove NaN/blank data
                if date_col and close_col:
                    data = data.dropna(subset=[date_col, close_col])
                if not date_col or not close_col or len(data) < 5:
                    st.info(f"Not enough {label} data to plot - columns found: {list(data.columns)}")
                else:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=data[date_col],
                        y=data[close_col],
                        mode='lines',
                        name=label,
                    ))
                    fig.update_layout(
                        title=f"{label} (Last 6 Months)",
                        xaxis_title="Date",
                        yaxis_title="Price",
                        template="plotly_white",
                        height=350
                    )
                    st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.info(f"{label} chart failed to load: {e}")

# --- Show all charts, with explanations ---
for ticker, label, summary_key in chart_configs:
    st.subheader(label)
    explanation = chart_explanations.get(label)
    if explanation:
        st.markdown(explanation)
    plot_chart(ticker, label, summary_key)




