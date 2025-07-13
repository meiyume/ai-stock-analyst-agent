# agents/agent1_stock.py

import yfinance as yf
import pandas as pd
import numpy as np
import re
from openai import OpenAI  # Modern SDK v1 import

def enforce_date_column(df):
    """
    Ensures DataFrame has a 'Date' column of dtype datetime64[ns], sorted, and unique.
    """
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

def decide_history_period(horizon: str, ticker: str, use_llm: bool = False) -> str:
    if use_llm:
        return "60d"
    else:
        map_lookup = {
            "1 Day": "30d",
            "3 Days": "45d",
            "7 Days": "90d",
            "30 Days": "180d"
        }
        return map_lookup.get(horizon, "90d")

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    rsi = 100 - (100 / (1 + rs))
    return rsi

def compute_stochastic(df, k_period=14, d_period=3):
    low_min = df['Low'].rolling(window=k_period).min()
    high_max = df['High'].rolling(window=k_period).max()
    df['Stochastic_%K'] = 100 * ((df['Close'] - low_min) / (high_max - low_min + 1e-10))
    df['Stochastic_%D'] = df['Stochastic_%K'].rolling(window=d_period).mean()
    return df

def compute_cmf(df, period=20):
    mfv = ((df['Close'] - df['Low']) - (df['High'] - df['Close'])) / \
          (df['High'] - df['Low'] + 1e-10) * df['Volume']
    df['CMF'] = mfv.rolling(window=period).sum() / df['Volume'].rolling(window=period).sum()
    return df

def compute_obv(df):
    obv = [0]
    for i in range(1, len(df)):
        if df['Close'].iloc[i] > df['Close'].iloc[i - 1]:
            obv.append(obv[-1] + df['Volume'].iloc[i])
        elif df['Close'].iloc[i] < df['Close'].iloc[i - 1]:
            obv.append(obv[-1] - df['Volume'].iloc[i])
        else:
            obv.append(obv[-1])
    df['OBV'] = obv
    return df

def compute_adx(df, period=14):
    df['H-L'] = df['High'] - df['Low']
    df['H-PC'] = np.abs(df['High'] - df['Close'].shift(1))
    df['L-PC'] = np.abs(df['Low'] - df['Close'].shift(1))
    df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
    df['+DM'] = np.where((df['High'] - df['High'].shift(1)) > (df['Low'].shift(1) - df['Low']),
                         np.maximum(df['High'] - df['High'].shift(1), 0), 0)
    df['-DM'] = np.where((df['Low'].shift(1) - df['Low']) > (df['High'] - df['High'].shift(1)),
                         np.maximum(df['Low'].shift(1) - df['Low'], 0), 0)
    tr_smooth = df['TR'].rolling(window=period).sum()
    plus_dm_smooth = df['+DM'].rolling(window=period).sum()
    minus_dm_smooth = df['-DM'].rolling(window=period).sum()
    df['+DI'] = 100 * (plus_dm_smooth / (tr_smooth + 1e-10))
    df['-DI'] = 100 * (minus_dm_smooth / (tr_smooth + 1e-10))
    df['DX'] = 100 * (np.abs(df['+DI'] - df['-DI']) / (df['+DI'] + df['-DI'] + 1e-10))
    df['ADX'] = df['DX'].rolling(window=period).mean()
    return df

def compute_atr(df, period=14):
    df['H-L'] = df['High'] - df['Low']
    df['H-PC'] = np.abs(df['High'] - df['Close'].shift(1))
    df['L-PC'] = np.abs(df['Low'] - df['Close'].shift(1))
    df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
    df['ATR'] = df['TR'].rolling(window=period).mean()
    return df

def detect_patterns(df):
    patterns = []
    if len(df) < 3:
        return patterns
    # Simple Hammer pattern example for last candle
    last = df.iloc[-1]
    body = abs(last['Close'] - last['Open'])
    range_ = last['High'] - last['Low']
    lower_shadow = min(last['Close'], last['Open']) - last['Low']
    upper_shadow = last['High'] - max(last['Close'], last['Open'])
    if body < range_ * 0.3 and lower_shadow > body * 2 and upper_shadow < body:
        patterns.append("Hammer")
    return patterns

def scan_all_anomalies(df):
    events = []
    df = enforce_date_column(df)
    for i in range(1, len(df)):
        date = df["Date"].iloc[i]

        # RSI spike
        if abs(df["RSI"].iloc[i] - df["RSI"].iloc[i - 1]) > 15:
            events.append({"date": date, "indicator": "RSI", "event": "Spike"})
        # RSI Overbought/Oversold cross
        if df["RSI"].iloc[i] > 70 and df["RSI"].iloc[i - 1] <= 70:
            events.append({"date": date, "indicator": "RSI", "event": "Overbought Cross"})
        if df["RSI"].iloc[i] < 30 and df["RSI"].iloc[i - 1] >= 30:
            events.append({"date": date, "indicator": "RSI", "event": "Oversold Cross"})
        # MACD spike
        if abs(df["MACD"].iloc[i] - df["MACD"].iloc[i - 1]) > 0.5:
            events.append({"date": date, "indicator": "MACD", "event": "Spike"})
        # MACD Crossover
        if (df["MACD"].iloc[i] > df["Signal"].iloc[i] and df["MACD"].iloc[i - 1] <= df["Signal"].iloc[i - 1]):
            events.append({"date": date, "indicator": "MACD", "event": "Bullish Crossover"})
        if (df["MACD"].iloc[i] < df["Signal"].iloc[i] and df["MACD"].iloc[i - 1] >= df["Signal"].iloc[i - 1]):
            events.append({"date": date, "indicator": "MACD", "event": "Bearish Crossover"})
        # Price Gap
        if abs(df["Open"].iloc[i] - df["Close"].iloc[i - 1]) > 0.02 * df["Close"].iloc[i - 1]:
            events.append({"date": date, "indicator": "Price", "event": "Gap"})
        # Volume Spike
        avg_vol = df["Volume"].rolling(window=5).mean().iloc[i - 1]
        if avg_vol > 0 and df["Volume"].iloc[i] > 1.5 * avg_vol:
            events.append({"date": date, "indicator": "Volume", "event": "Spike"})
        # ATR Spike
        avg_atr = df["ATR"].rolling(window=20).mean().iloc[i - 1]
        if avg_atr > 0 and df["ATR"].iloc[i] > 1.5 * avg_atr:
            events.append({"date": date, "indicator": "ATR", "event": "Spike"})
        # Stochastic Overbought/Oversold
        if "Stochastic_%K" in df.columns:
            if df["Stochastic_%K"].iloc[i] > 80 and df["Stochastic_%K"].iloc[i - 1] <= 80:
                events.append({"date": date, "indicator": "Stochastic", "event": "Overbought Cross"})
            if df["Stochastic_%K"].iloc[i] < 20 and df["Stochastic_%K"].iloc[i - 1] >= 20:
                events.append({"date": date, "indicator": "Stochastic", "event": "Oversold Cross"})
    return events

def analyze(ticker: str, horizon: str = "7 Days"):
    history_period = decide_history_period(horizon, ticker, use_llm=False)
    stock = yf.Ticker(ticker)
    df = stock.history(period=history_period, interval="1d")
    df = enforce_date_column(df)
    if df.empty:
        return {
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
            "heatmap_signals": {}
        }, df

    df["SMA5"] = df["Close"].rolling(window=5).mean()
    df["SMA10"] = df["Close"].rolling(window=10).mean()
    df["EMA12"] = df["Close"].ewm(span=12, adjust=False).mean()
    df["EMA26"] = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = df["EMA12"] - df["EMA26"]
    df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["20dSTD"] = df["Close"].rolling(window=20).std()
    df["Upper"] = df["SMA10"] + (df["20dSTD"] * 2)
    df["Lower"] = df["SMA10"] - (df["20dSTD"] * 2)
    df["RSI"] = compute_rsi(df["Close"], 14)

    df = compute_stochastic(df)
    df = compute_cmf(df)
    df = compute_obv(df)
    df = compute_adx(df)
    df = compute_atr(df)

    df_for_plotting = df.copy()

    df_signals = df.dropna(subset=[
        "SMA5", "SMA10", "MACD", "Signal", "Upper", "Lower",
        "RSI", "Stochastic_%K", "Stochastic_%D",
        "CMF", "OBV", "ADX", "ATR"
    ])
    if df_signals.empty:
        return {"summary": "⚠️ Not enough data to generate signals."}, df_for_plotting

    latest = df_signals.iloc[-1]

    sma_trend = (
        "Bullish" if latest["SMA5"] > latest["SMA10"] else
        "Bearish" if latest["SMA5"] < latest["SMA10"] else
        "Neutral"
    )
    macd_signal = "Bullish" if latest["MACD"] > latest["Signal"] else "Bearish"
    bollinger_signal = (
        "Above upper band" if latest["Close"] > latest["Upper"]
        else "Below lower band" if latest["Close"] < latest["Lower"]
        else "Within band"
    )
    rsi_signal = (
        "Overbought" if latest["RSI"] > 70
        else "Oversold" if latest["RSI"] < 30
        else "Neutral"
    )
    stochastic_signal = (
        "Bullish crossover" if latest["Stochastic_%K"] > latest["Stochastic_%D"] and latest["Stochastic_%K"] < 20
        else "Bearish crossover" if latest["Stochastic_%K"] < latest["Stochastic_%D"] and latest["Stochastic_%K"] > 80
        else "Neutral"
    )
    cmf_signal = (
        "Buying" if latest["CMF"] > 0
        else "Selling" if latest["CMF"] < 0
        else "Neutral"
    )
    obv_signal = (
        "Rising" if latest["OBV"] > df["OBV"].iloc[-2]
        else "Falling" if latest["OBV"] < df["OBV"].iloc[-2]
        else "Flat"
    )
    adx_signal = "Strong trend" if latest["ADX"] > 25 else "Weak trend"
    atr_mean = df["ATR"].mean()
    atr_signal = "High volatility" if latest["ATR"] > atr_mean else "Low volatility"

    avg_vol = df["Volume"].rolling(window=5).mean().iloc[-1]
    vol_spike = latest["Volume"] > 1.5 * avg_vol if avg_vol > 0 else False

    patterns = detect_patterns(df_signals)
    anomaly_events = scan_all_anomalies(df_signals)

    # === Comprehensive Heatmap Signal Status ===
    heatmap_signals = {}

    # SMA Trend
    heatmap_signals["SMA Trend"] = sma_trend

    # MACD
    heatmap_signals["MACD"] = "Bullish Crossover" if macd_signal == "Bullish" else "Bearish Crossover"

    # RSI
    if latest["RSI"] > 70:
        heatmap_signals["RSI"] = "Overbought"
    elif latest["RSI"] < 30:
        heatmap_signals["RSI"] = "Oversold"
    else:
        heatmap_signals["RSI"] = "Neutral"

    # Bollinger
    heatmap_signals["Bollinger"] = (
        "Above Upper Band" if latest["Close"] > latest["Upper"]
        else "Below Lower Band" if latest["Close"] < latest["Lower"]
        else "Within Band"
    )

    # Stochastic
    stoch = latest["Stochastic_%K"]
    if stoch > 80:
        heatmap_signals["Stochastic"] = "Overbought"
    elif stoch < 20:
        heatmap_signals["Stochastic"] = "Oversold"
    else:
        heatmap_signals["Stochastic"] = "Neutral"

    # CMF
    if latest["CMF"] > 0:
        heatmap_signals["CMF"] = "Buying"
    elif latest["CMF"] < 0:
        heatmap_signals["CMF"] = "Selling"
    else:
        heatmap_signals["CMF"] = "Neutral"

    # OBV
    if latest["OBV"] > df["OBV"].iloc[-2]:
        heatmap_signals["OBV"] = "Rising"
    elif latest["OBV"] < df["OBV"].iloc[-2]:
        heatmap_signals["OBV"] = "Falling"
    else:
        heatmap_signals["OBV"] = "Flat"

    # ADX
    heatmap_signals["ADX"] = "Strong Trend" if latest["ADX"] > 25 else "Weak Trend"

    # ATR
    heatmap_signals["ATR"] = "High Volatility" if latest["ATR"] > atr_mean else "Stable"

    # Volume
    heatmap_signals["Volume"] = "Spike" if vol_spike else "Normal"

    # Pattern
    heatmap_signals["Pattern"] = patterns[0] if patterns else "None"

    # === Composite Risk Score (Weights can be tuned as needed) ===
    weights = {
        "SMA Trend": 0.08,
        "MACD": 0.15,
        "RSI": 0.10,
        "Bollinger": 0.07,
        "Stochastic": 0.10,
        "CMF": 0.08,
        "OBV": 0.07,
        "ADX": 0.10,
        "ATR": 0.10,
        "Volume": 0.08,
        "Pattern": 0.07,
    }

    risk_score = 0

    score_map = {
        "Bearish": 1, "Bearish Crossover": 1, "Overbought": 1, "Selling": 1,
        "Falling": 1, "Weak Trend": 1, "High Volatility": 1, "Spike": 1,
        "Below Lower Band": 1, "Oversold": 0, "Bullish": 0, "Bullish Crossover": 0,
        "Buying": 0, "Rising": 0, "Strong Trend": 0, "Stable": 0, "Above Upper Band": 1,
        "Neutral": 0.5, "Normal": 0.5, "Within Band": 0.5, "Flat": 0.5, "None": 0.5,
    }

    for k, v in heatmap_signals.items():
        risk_score += weights.get(k, 0) * score_map.get(v, 0.5)

    if risk_score >= 0.61:
        risk_level = "High Risk"
    elif risk_score >= 0.34:
        risk_level = "Caution"
    else:
        risk_level = "Low Risk"

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
        "composite_risk_score": round(risk_score, 2),
        "risk_level": risk_level
    }

    return summary, df_for_plotting

def run_full_technical_analysis(ticker, horizon):
    return analyze(ticker, horizon)

# === LLM Summary using OpenAI GPT-3.5-turbo ===

def get_llm_summary(signals, api_key):
    client = OpenAI(api_key=api_key)
    prompt = f"""
You are an expert technical analyst for a leading financial institution.

Based on the following technical signals and anomalies, do the following:
- First, write a detailed summary for technical readers (using precise, professional terminology and concise reasoning). For each indicator, explain not just the signal, but also why it matters right now. Connect supporting indicators together (e.g., “Rising OBV + bullish MACD reinforces uptrend…”). Summarize the overall risk or opportunity, and recommend what a technical analyst should watch for in the next few sessions. Include actionable insight or a forward-looking caution. Use a confident, objective tone.
- Then, write a second summary for non-technical readers. Imagine you are explaining it to a grandparent with no finance background:
    - Avoid technical terms and acronyms unless you give a short, simple explanation.
    - Use analogies and plain language.
    - Give gentle, practical advice for someone considering buying or selling for the chosen outlook horizon ({signals.get('horizon', 'the next few days')}). 
    - Clearly mention if things look good for buying, if caution is advised, or if it might be wise to hold off, and explain why in simple terms.
    - Focus on helping the reader make a simple decision for the chosen time frame, and always explain the risk in plain language.
    - Make it warm, clear, and friendly.
    - Absolutely no jargon!

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

Write two clearly separated sections, each starting with a clear title:
- For Technical Readers
- For Grandmas and Grandpas

Do not number or prefix the titles with any numbers or colons.
Just start each section with the title on its own line.
"""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=700,
        temperature=0.6,
    )
    return response.choices[0].message.content.strip()





