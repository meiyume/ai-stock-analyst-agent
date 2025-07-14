import yfinance as yf
import pandas as pd
import numpy as np
from openai import OpenAI

def fetch_data(ticker, lookback_days=30, interval="1d"):
    end_date = pd.Timestamp.today()
    start_date = end_date - pd.Timedelta(days=lookback_days * 2)
    data = yf.download(
        tickers=ticker,
        start=start_date.strftime("%Y-%m-%d"),
        end=end_date.strftime("%Y-%m-%d"),
        interval=interval,
        progress=False
    )
    data = data.reset_index()
    return data

def enforce_date_column(df):
    if 'Date' not in df.columns:
        df = df.reset_index()
        possible = [col for col in df.columns if 'date' in col.lower() or 'time' in col.lower()]
        if possible and possible[0] != 'Date':
            df.rename(columns={possible[0]: 'Date'}, inplace=True)
        elif 'Date' not in df.columns:
            df['Date'] = pd.to_datetime(df.index)
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date').drop_duplicates('Date').reset_index(drop=True)
    return df

def decide_lookback_days(horizon: str):
    try:
        num = int(''.join(filter(str.isdigit, horizon)))
    except:
        num = 7
    lookback_days = max(30, num * 3)
    lookback_days = min(lookback_days, 360)
    return lookback_days

def get_llm_dual_summary(signals, api_key):
    client = OpenAI(api_key=api_key)
    prompt = f"""
You are an expert technical analyst and educator for a leading financial institution.

Based on the following technical signals and anomalies, produce two summaries:
1. Technical Summary (for professional or advanced readers): Write a detailed, precise analysis using standard technical terms and concise logic. Explain not just the signal, but why it matters *now*. Synthesize supporting or conflicting indicators. Highlight risk/opportunity, and explicitly reference the outlook horizon ({signals.get('horizon', 'the next few days')}). Make actionable suggestions.

2. Plain-English Summary (for non-technical users, e.g., grandma/grandpa): Start with "If you're looking at this stock outlook over {signals.get('horizon', 'the next few days')}, here’s what you should know:". Avoid jargon; use analogies and simple language. Give practical advice, mention risk, and be warm, clear, and friendly.

Here are the signals:
SMA Trend: {signals.get('sma_trend')}
MACD: {signals.get('macd_signal')}
RSI: {signals.get('rsi_signal')}
Bollinger Bands: {signals.get('bollinger_signal')}
Stochastic: {signals.get('stochastic_signal')}
CMF: {signals.get('cmf_signal')}
OBV: {signals.get('obv_signal')}
ADX: {signals.get('adx_signal')}
ATR: {signals.get('atr_signal')}
Volume Spike: {signals.get('vol_spike')}
Candlestick Patterns: {signals.get('patterns')}
Key Anomalies: {signals.get('anomaly_events')}
Outlook Horizon: {signals.get('horizon', 'the next few days')}
Risk Level: {signals.get('risk_level')}

Write two sections, each starting with a title: "Technical Summary" and "Plain-English Summary".
Do not number or prefix the titles with any numbers or colons.
"""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=800,
        temperature=0.6,
    )
    # Split response by titles
    output = response.choices[0].message.content.strip()
    tech, plain = "", ""
    if "Technical Summary" in output and "Plain-English Summary" in output:
        parts = output.split("Plain-English Summary")
        tech = parts[0].replace("Technical Summary", "").strip()
        plain = parts[1].strip()
    else:
        tech = output
        plain = output
    return tech, plain

def analyze(
    ticker: str,
    horizon: str = "7 Days",
    lookback_days: int = None,
    api_key: str = None
):
    # --- Dynamic lookback ---
    if lookback_days is None:
        lookback_days = decide_lookback_days(horizon)

    df = fetch_data(ticker, lookback_days=lookback_days)
    df = enforce_date_column(df)

    # --- Ensure all indicator columns exist ---
    indicator_cols = [
    "Open", "High", "Low", "Close", "SMA5", "SMA10", "Upper", "Lower",
    "RSI", "MACD", "Signal", "Volume", "ATR", "Stochastic_%K",
    "Stochastic_%D", "CMF", "OBV", "ADX"
    ]
    for col in indicator_cols:
        if col not in df.columns:
            df[col] = np.nan

# Only use columns that actually exist to avoid KeyError
existing_cols = [col for col in indicator_cols if col in df.columns]
remaining_cols = [c for c in df.columns if c not in existing_cols]
df = df[existing_cols + remaining_cols]


    # --- Handle empty data case ---
    if df.empty or df["Close"].isna().all():
        summary = {
            "summary": f"⚠️ No data available for {ticker}.",
            "sma_trend": "N/A",
            "macd_signal": "N/A",
            "bollinger_signal": "N/A",
            "rsi_signal": "N/A",
            "stochastic_signal": "N/A",
            "cmf_signal": "N/A",
            "obv_signal": "N/A",
            "adx_signal": "N/A",
            "atr_signal": "N/A",
            "vol_spike": False,
            "patterns": [],
            "anomaly_events": [],
            "heatmap_signals": {},
            "composite_risk_score": np.nan,
            "risk_level": "N/A",
            "lookback_days": lookback_days,
            "horizon": horizon,
            "llm_technical_summary": "No LLM report (no data available).",
            "llm_plain_summary": "No LLM report (no data available)."
        }
        return summary, df

    # --- [Insert your technical calculations here] ---
    # Example stub logic (replace with your real code)
    sma_trend = "Neutral"
    macd_signal = "Neutral"
    bollinger_signal = "Neutral"
    rsi_signal = "Neutral"
    stochastic_signal = "Neutral"
    cmf_signal = "Neutral"
    obv_signal = "Neutral"
    adx_signal = "Neutral"
    atr_signal = "Neutral"
    vol_spike = False
    patterns = []
    anomaly_events = []
    heatmap_signals = {}
    risk_score = 0.5
    risk_level = "Caution"

    # TODO: Use real indicator calculations!

    summary = {
        "summary": f"{sma_trend} SMA, {macd_signal} MACD, {rsi_signal} RSI, {bollinger_signal} Bollinger, "
                   f"{stochastic_signal} Stochastic, {cmf_signal} CMF, {obv_signal} OBV, "
                   f"{adx_signal} ADX, {atr_signal} ATR",
        "sma_trend": sma_trend,
        "macd_signal": macd_signal,
        "bollinger_signal": bollinger_signal,
        "rsi_signal": rsi_signal,
        "stochastic_signal": stochastic_signal,
        "cmf_signal": cmf_signal,
        "obv_signal": obv_signal,
        "adx_signal": adx_signal,
        "atr_signal": atr_signal,
        "vol_spike": vol_spike,
        "patterns": patterns,
        "anomaly_events": anomaly_events,
        "heatmap_signals": heatmap_signals,
        "composite_risk_score": risk_score,
        "risk_level": risk_level,
        "lookback_days": lookback_days,
        "horizon": horizon
    }

    # --- LLM Dual Summary (for both technical & non-technical) ---
    if api_key:
        try:
            tech, plain = get_llm_dual_summary(summary, api_key)
            summary["llm_technical_summary"] = tech
            summary["llm_plain_summary"] = plain
        except Exception as e:
            summary["llm_technical_summary"] = f"LLM error: {e}"
            summary["llm_plain_summary"] = f"LLM error: {e}"
    else:
        summary["llm_technical_summary"] = "No API key provided for LLM summary."
        summary["llm_plain_summary"] = "No API key provided for LLM summary."

    return summary, df

def run_full_technical_analysis(ticker, horizon, lookback_days=None, api_key=None):
    return analyze(ticker, horizon, lookback_days=lookback_days, api_key=api_key)






