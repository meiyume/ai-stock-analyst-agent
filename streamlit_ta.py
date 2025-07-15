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

# --- LLM Summaries at the top
st.subheader("LLM-Generated Summaries")
json_summary = json.dumps(summary, indent=2)

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

# --- Raw Data Section
st.subheader("Raw Global Technical Data")
with st.expander("Show raw summary dict", expanded=False):
    st.json(summary)

# --- Chart section helper ---
def find_col(possibles, columns):
    for p in possibles:
        for c in columns:
            if p in str(c).lower():
                return c
    return None

def infer_trend(row):
    # Simple logic for uptrend/downtrend/sideways using SMAs
    if pd.isna(row['SMA20']) or pd.isna(row['SMA50']) or pd.isna(row['SMA200']):
        return "No Signal"
    if row['SMA20'] > row['SMA50'] > row['SMA200']:
        return "Uptrend"
    if row['SMA20'] < row['SMA50'] < row['SMA200']:
        return "Downtrend"
    return "Sideways/Range"

def plot_chart(ticker, label, explanation):
    with st.container():
        st.markdown(f"#### {label}")
        st.caption(explanation)
        try:
            end = datetime.today()
            start = end - timedelta(days=180)
            df = yf.download(ticker, start=start, end=end, interval="1d", auto_adjust=True, progress=False)
            if df is None or len(df) < 10:
                st.info(f"Not enough {label} data to plot.")
                return

            # Flatten MultiIndex columns, if needed
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = ['_'.join([str(i) for i in col if i]) for col in df.columns.values]
            df = df.reset_index()

            date_col = find_col(['date', 'datetime', 'index'], df.columns) or df.columns[0]
            close_col = find_col(['close'], df.columns)
            volume_col = find_col(['volume'], df.columns)

            if not date_col or not close_col:
                st.info(f"{label} chart failed to load: columns found: {list(df.columns)}")
                return

            # Clean data
            df = df.dropna(subset=[date_col, close_col])
            if len(df) < 10:
                st.info(f"Not enough {label} data to plot.")
                return

            # Calculate SMA20, SMA50, SMA200
            df["SMA20"] = df[close_col].rolling(window=20).mean()
            df["SMA50"] = df[close_col].rolling(window=50).mean()
            df["SMA200"] = df[close_col].rolling(window=200).mean()

            fig = go.Figure()
            # Main price line
            fig.add_trace(go.Scatter(
                x=df[date_col], y=df[close_col],
                mode='lines', name=label
            ))
            # SMA20
            fig.add_trace(go.Scatter(
                x=df[date_col], y=df["SMA20"],
                mode='lines', name='SMA 20', line=dict(dash='dot')
            ))
            # SMA50
            fig.add_trace(go.Scatter(
                x=df[date_col], y=df["SMA50"],
                mode='lines', name='SMA 50', line=dict(dash='dash')
            ))
            # SMA200
            fig.add_trace(go.Scatter(
                x=df[date_col], y=df["SMA200"],
                mode='lines', name='SMA 200', line=dict(dash='solid', color='black')
            ))
            # Volume (secondary axis)
            if volume_col and volume_col in df.columns:
                fig.add_trace(go.Bar(
                    x=df[date_col], y=df[volume_col],
                    name="Volume", yaxis="y2",
                    marker_color="rgba(0,160,255,0.16)",
                    opacity=0.5
                ))

            # Layout for dual axis
            fig.update_layout(
                title=label,
                xaxis_title="Date",
                yaxis_title="Price",
                yaxis=dict(title="Price", showgrid=True),
                yaxis2=dict(
                    title="Volume", overlaying='y', side='right', showgrid=False, rangemode='tozero'
                ),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                template="plotly_white",
                height=350,
                bargap=0
            )

            st.plotly_chart(fig, use_container_width=True)

            # --- Trend Table (just last day) ---
            trend_row = df.iloc[-1][['SMA20', 'SMA50', 'SMA200']].to_dict()
            trend_value = infer_trend(df.iloc[-1])
            st.markdown("**Simple SMA Trend Table**")
            trend_data = {
                "SMA 20": trend_row['SMA20'],
                "SMA 50": trend_row['SMA50'],
                "SMA 200": trend_row['SMA200'],
                "Trend Signal": trend_value
            }
            st.table(pd.DataFrame([trend_data]))

        except Exception as e:
            st.info(f"{label} chart failed to load: {e}")

# --- Chart definitions and explanations ---
chart_list = [
    {
        "ticker": "^GSPC",
        "label": "S&P 500 (Last 6 Months)",
        "explanation": "The S&P 500 is a broad-based index representing large-cap US equities across economic sectors. Analysts study it to assess overall US market health and risk sentiment."
    },
    # ... (rest of your chart_list unchanged)
    {
        "ticker": "^VIX",
        "label": "VIX (Volatility Index)",
        "explanation": "The VIX reflects expected US stock market volatility (fear/greed). A rising VIX signals heightened investor anxiety."
    },
    # ... Add the rest as before ...
    {
        "ticker": "HG=F",
        "label": "Copper Futures",
        "explanation": "Copper is an industrial bellwether, used to assess the strength of global manufacturing and economic growth."
    },
]

# --- Plot all charts ---
st.subheader("Global Market Charts")
for chart in chart_list:
    plot_chart(chart["ticker"], chart["label"], chart["explanation"])








