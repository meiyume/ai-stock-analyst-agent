import streamlit as st
import json
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go

from agents.ta_global import ta_global  # Update this if your path differs
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

# --- Prepare prompt for LLM
json_summary = json.dumps(summary, indent=2)

# --- Run LLM agent for summary (global)
st.subheader("LLM-Generated Summaries")
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

st.markdown("---")
st.subheader("Global Macro Charts")

# --- Define chart settings and explanations
chart_configs = [
    {
        "label": "S&P 500 (Last 6 Months)",
        "ticker": "^GSPC",
        "explanation": "S&P 500 is a broad-based US equity index representing major economic sectors. Analysts watch its trends for signals on US and global risk appetite."
    },
    {
        "label": "VIX - Volatility Index",
        "ticker": "^VIX",
        "explanation": "The VIX reflects expected S&P 500 volatility. Higher VIX indicates fear or uncertainty in markets."
    },
    {
        "label": "Nasdaq (Last 6 Months)",
        "ticker": "^IXIC",
        "explanation": "The Nasdaq index tracks tech-heavy US stocks, often leading bull/bear market turns and reflecting risk-on/off sentiment."
    },
    {
        "label": "EuroStoxx 50 (Last 6 Months)",
        "ticker": "^STOXX50E",
        "explanation": "EuroStoxx 50 is the bellwether for blue-chip European equities. Useful for assessing continental European sentiment."
    },
    {
        "label": "Nikkei 225 (Last 6 Months)",
        "ticker": "^N225",
        "explanation": "Nikkei 225 tracks Japan's largest companies and is a proxy for Asia-Pacific investor confidence."
    },
    {
        "label": "Hang Seng Index (Last 6 Months)",
        "ticker": "^HSI",
        "explanation": "Hang Seng reflects the health of Hong Kong’s stock market and, by extension, China-facing financial flows."
    },
    {
        "label": "FTSE 100 (Last 6 Months)",
        "ticker": "^FTSE",
        "explanation": "FTSE 100 is the UK's flagship equity index, with a strong weighting to global exporters and commodity firms."
    },
    {
        "label": "Gold Price (Last 6 Months)",
        "ticker": "GC=F",
        "explanation": "Gold is a traditional safe-haven asset. Its trend often reflects investor caution or inflation concerns."
    },
    {
        "label": "Brent Crude Oil (Last 6 Months)",
        "ticker": "BZ=F",
        "explanation": "Brent is the main global oil benchmark. Oil prices influence inflation, sector rotation, and geopolitics."
    },
    {
        "label": "USD/JPY Exchange Rate (Last 6 Months)",
        "ticker": "JPY=X",
        "explanation": "USD/JPY tracks the US dollar versus Japanese yen, reflecting carry trade flows and global risk mood."
    },
    {
        "label": "USD/SGD Exchange Rate (Last 6 Months)",
        "ticker": "USDSGD=X",
        "explanation": "USD/SGD measures the US dollar against Singapore dollar, often watched for emerging Asia FX trends."
    },
    {
        "label": "USD/CNH Exchange Rate (Last 6 Months)",
        "ticker": "USDCNH=X",
        "explanation": "USD/CNH is the offshore Chinese yuan rate, key for tracking China-related capital flows and policy signals."
    }
]

# --- Plot function for all charts
def plot_chart(ticker, title, explanation):
    with st.container():
        with st.spinner(f"Loading {title}..."):
            end = datetime.today()
            start = end - timedelta(days=180)
            df = yf.download(ticker, start=start, end=end, interval="1d", auto_adjust=True, progress=False)
            df = df.reset_index()

            # Column identification (robust to MultiIndex)
            date_col = None
            close_col = None
            volume_col = None
            for col in df.columns:
                if isinstance(col, str) and col.lower() in ["date", "datetime", "index"]:
                    date_col = col
                if isinstance(col, str) and "close" in col.lower():
                    close_col = col
                if isinstance(col, str) and "volume" in col.lower():
                    volume_col = col
            # Handle fallback for Yahoo-style
            if not date_col:
                date_col = df.columns[0]
            if not close_col:
                # Try to use the second column
                close_col = df.columns[1] if len(df.columns) > 1 else None
            # NaN/tuple data check
            if not date_col or not close_col or df.empty or df[close_col].isnull().all():
                st.info(f"Not enough {title} data to plot.")
                return

            # Calculate SMAs only if enough data
            df['SMA_20'] = df[close_col].rolling(window=20).mean() if close_col in df else None
            df['SMA_50'] = df[close_col].rolling(window=50).mean() if close_col in df else None
            df['SMA_200'] = df[close_col].rolling(window=200).mean() if close_col in df else None

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df[date_col], y=df[close_col],
                mode='lines', name=title, line=dict(width=2)
            ))
            # Add SMAs if data is valid
            if 'SMA_20' in df and not df['SMA_20'].isnull().all():
                fig.add_trace(go.Scatter(x=df[date_col], y=df['SMA_20'], mode='lines', name="SMA 20", line=dict(dash='dot')))
            if 'SMA_50' in df and not df['SMA_50'].isnull().all():
                fig.add_trace(go.Scatter(x=df[date_col], y=df['SMA_50'], mode='lines', name="SMA 50", line=dict(dash='dash')))
            if 'SMA_200' in df and not df['SMA_200'].isnull().all():
                fig.add_trace(go.Scatter(x=df[date_col], y=df['SMA_200'], mode='lines', name="SMA 200", line=dict(dash='dashdot')))
            # Add Volume (if available)
            if volume_col and not df[volume_col].isnull().all():
                fig.add_trace(go.Bar(
                    x=df[date_col], y=df[volume_col],
                    name="Volume", yaxis='y2',
                    marker=dict(color='rgba(0,180,255,0.15)'),
                    opacity=0.7
                ))
            # Axes config
            fig.update_layout(
                title=title,
                xaxis_title="Date",
                yaxis=dict(title="Price"),
                yaxis2=dict(
                    title="Volume",
                    overlaying='y',
                    side='right',
                    showgrid=False
                ),
                bargap=0,
                template="plotly_white",
                height=400,
                legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption(explanation)

# --- Plot all charts (can limit to first few for speed)
for chart in chart_configs:
    plot_chart(chart["ticker"], chart["label"], chart["explanation"])

st.markdown("---")
st.subheader("Raw Global Technical Data")
with st.expander("Show raw summary dict", expanded=False):
    st.json(summary)




