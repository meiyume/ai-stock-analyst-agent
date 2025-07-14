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

    # --- Flatten MultiIndex columns ---
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = [
            '_'.join(filter(None, map(str, col))).replace(f"_{ticker}", "") 
            for col in data.columns.values
        ]

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

def calculate_indicators(df):
    # SMA
    df['SMA5'] = df['Close'].rolling(window=5).mean()
    df['SMA10'] = df['Close'].rolling(window=10).mean()

    # Bollinger Bands
    df['Upper'] = df['SMA10'] + 2 * df['Close'].rolling(window=10).std()
    df['Lower'] = df['SMA10'] - 2 * df['Close'].rolling(window=10).std()

    # RSI
    delta = df['Close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # MACD
    exp12 = df['Close'].ewm(span=12, adjust=False).mean()
    exp26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp12 - exp26
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()

    # Volume
    df['Volume'] = df['Volume']

    # ATR
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    df['ATR'] = ranges.max(axis=1).rolling(window=14).mean()

    # Stochastic
    low_min = df['Low'].rolling(window=14).min()
    high_max = df['High'].rolling(window=14).max()
    df['Stochastic_%K'] = 100 * (df['Close'] - low_min) / (high_max - low_min)
    df['Stochastic_%D'] = df['Stochastic_%K'].rolling(window=3).mean()

    # CMF
    mfv = ((df['Close'] - df['Low']) - (df['High'] - df['Close'])) / (df['High'] - df['Low'] + 1e-9) * df['Volume']
    df['CMF'] = mfv.rolling(window=20).sum() / df['Volume'].rolling(window=20).sum()

    # OBV
    obv = [0]
    for i in range(1, len(df)):
        if df.loc[i, 'Close'] > df.loc[i-1, 'Close']:
            obv.append(obv[-1] + df.loc[i, 'Volume'])
        elif df.loc[i, 'Close'] < df.loc[i-1, 'Close']:
            obv.append(obv[-1] - df.loc[i, 'Volume'])
        else:
            obv.append(obv[-1])
    df['OBV'] = obv

    # ADX (stub)
    df['ADX'] = np.nan

    return df

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
    ticker,
    company_name=None,
    horizon="7 Days",
    lookback_days=None,
    api_key=None
):
    # --- Dynamic lookback ---
    if lookback_days is None:
        lookback_days = decide_lookback_days(horizon)

    df = fetch_data(ticker, lookback_days=lookback_days)
    df = enforce_date_column(df)

    # Calculate technicals
    df = calculate_indicators(df)

    # --- Ensure all indicator columns exist ---
    indicator_cols = [
        "Open", "High", "Low", "Close", "SMA5", "SMA10", "Upper", "Lower",
        "RSI", "MACD", "Signal", "Volume", "ATR", "Stochastic_%K",
        "Stochastic_%D", "CMF", "OBV", "ADX"
    ]
    for col in indicator_cols:
        if col not in df.columns:
            df[col] = np.nan

    # Only use columns that actually exist (no KeyError even with missing columns)
    existing_cols = [col for col in indicator_cols if col in df.columns]
    remaining_cols = [c for c in df.columns if c not in existing_cols]
    cols_to_use = [col for col in existing_cols + remaining_cols if col in df.columns]
    df = df[cols_to_use]

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
            "llm_plain_summary": "No LLM report (no data available).",
            "df": df
        }
        # Ensure chart and LLM summary keys always exist
        summary["llm_summary"] = summary["llm_technical_summary"]
        summary["chart"] = None
        return summary

    # --- Real technical signal summaries (stub logic here, can expand) ---
    sma_trend = "Bullish" if df['SMA5'].iloc[-1] > df['SMA10'].iloc[-1] else "Bearish"
    macd_signal = "Bullish" if df['MACD'].iloc[-1] > df['Signal'].iloc[-1] else "Bearish"
    rsi_signal = (
        "Overbought" if df['RSI'].iloc[-1] > 70 else
        "Oversold" if df['RSI'].iloc[-1] < 30 else
        "Neutral"
    )
    bollinger_signal = (
        "Breakout" if df['Close'].iloc[-1] > df['Upper'].iloc[-1]
        else "Breakdown" if df['Close'].iloc[-1] < df['Lower'].iloc[-1]
        else "Neutral"
    )
    stochastic_signal = (
        "Overbought" if df['Stochastic_%K'].iloc[-1] > 80 else
        "Oversold" if df['Stochastic_%K'].iloc[-1] < 20 else
        "Neutral"
    )
    cmf_signal = "Bullish" if df['CMF'].iloc[-1] > 0 else "Bearish"
    obv_signal = "Up" if df['OBV'].iloc[-1] > df['OBV'].iloc[-10] else "Down"
    adx_signal = "Strong Trend" if df['ADX'].iloc[-1] > 25 else "Weak/No Trend"
    atr_signal = "High Volatility" if df['ATR'].iloc[-1] > df['ATR'].rolling(window=30).mean().iloc[-1] else "Normal"

    # Example volume spike/anomaly (stub)
    vol_spike = bool(df['Volume'].iloc[-1] > df['Volume'].rolling(window=30).mean().iloc[-1] * 1.5)
    patterns = []
    anomaly_events = []

    # Compose signals for LLM
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
        "heatmap_signals": {},  # Add if you compute
        "composite_risk_score": 0.5,  # Placeholder, update with logic
        "risk_level": "Caution",      # Placeholder, update with logic
        "lookback_days": lookback_days,
        "horizon": horizon,
        "df": df  # Always include DataFrame in dict
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

    # Make sure summary always has 'llm_summary' (for orchestrator and Streamlit)
    summary["llm_summary"] = summary.get("llm_technical_summary", summary["summary"])

    # --- Example chart: candlestick with overlays ---
    try:
        import plotly.graph_objects as go
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df['Date'],
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name='Candlestick'
        ))
        fig.add_trace(go.Scatter(
            x=df['Date'],
            y=df['SMA5'],
            mode='lines',
            name='SMA5'
        ))
        fig.add_trace(go.Scatter(
            x=df['Date'],
            y=df['SMA10'],
            mode='lines',
            name='SMA10'
        ))
        summary["chart"] = fig
    except Exception as e:
        summary["chart"] = None

    return summary
