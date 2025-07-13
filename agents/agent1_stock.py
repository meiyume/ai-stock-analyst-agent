# agent1_stock.py

import yfinance as yf
import pandas as pd
import numpy as np
import re

# === Optional OpenAI LLM import (scaffolded) ===
# from openai import OpenAI  # Uncomment if integrating
# client = OpenAI(api_key="your-key-here")

# === Intelligent History Selector ===
def decide_history_period(horizon: str, ticker: str, use_llm: bool = False) -> str:
    if use_llm:
        # Simulated LLM response logic
        prompt = f"""
        You are Agent 1, a technical analysis expert. Agent 2 has requested a stock forecast for the next {horizon}.
        How many days of historical data would you like to compute relevant indicators (e.g. MACD, RSI, ADX)?
        Reply only with a single number like: 60
        """
        # Placeholder: Replace with actual LLM call
        print("🔮 Using LLM to decide historical lookback...")
        simulated_response = "60"
        try:
            days = int(re.findall(r"\d+", simulated_response)[0])
            return f"{days}d"
        except:
            return "90d"
    else:
        # Fallback rule-based map
        map_lookup = {
            "1 Day": "30d",
            "3 Days": "45d",
            "7 Days": "90d",
            "30 Days": "180d"
        }
        return map_lookup.get(horizon, "90d")

# === Indicator Functions ===
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

# === Main Analysis ===
def analyze(ticker: str, horizon: str = "7 Days"):
    history_period = decide_history_period(horizon, ticker, use_llm=False)
    stock = yf.Ticker(ticker)
    df = stock.history(period=history_period, interval="1d")

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
            "vol_spike": False
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

    sma_trend = "Bullish" if latest["SMA5"] > latest["SMA10"] else "Bearish"
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
        "Buying pressure" if latest["CMF"] > 0
        else "Selling pressure" if latest["CMF"] < 0
        else "Neutral"
    )
    obv_signal = "Rising" if latest["OBV"] > df["OBV"].iloc[-2] else "Falling"
    adx_signal = "Strong trend" if latest["ADX"] > 25 else "Weak trend"
    atr_mean = df["ATR"].mean()
    atr_signal = "High volatility" if latest["ATR"] > atr_mean else "Low volatility"

    avg_vol = df["Volume"].rolling(window=5).mean().iloc[-1]
    vol_spike = latest["Volume"] > 1.5 * avg_vol

    summary = {
        "summary": f"{sma_trend} SMA, {macd_signal} MACD, {rsi_signal} RSI, {bollinger_signal}, "
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
        "vol_spike": vol_spike
    }

    

    # === Candlestick Pattern Detection ===
    candlestick_patterns = []
    if len(df_signals) >= 3:
        last = df_signals.iloc[-1]
        prev = df_signals.iloc[-2]
        prev2 = df_signals.iloc[-3]

        # Doji
        if abs(last['Open'] - last['Close']) / (last['High'] - last['Low'] + 1e-10) < 0.1:
            candlestick_patterns.append("Doji")

        # Hammer
        if (last['High'] - last['Low']) > 2 * abs(last['Open'] - last['Close']) and            (last['Close'] - last['Low']) / (last['High'] - last['Low'] + 1e-10) > 0.6:
            candlestick_patterns.append("Hammer")

        # Engulfing
        if (last['Close'] > last['Open'] and
            prev['Close'] < prev['Open'] and
            last['Close'] > prev['Open'] and
            last['Open'] < prev['Close']):
            candlestick_patterns.append("Bullish Engulfing")

        elif (last['Close'] < last['Open'] and
              prev['Close'] > prev['Open'] and
              last['Open'] > prev['Close'] and
              last['Close'] < prev['Open']):
            candlestick_patterns.append("Bearish Engulfing")

    # === Anomaly Alerts ===
    rsi_spike = False
    price_gap = False
    macd_spike = False

    if "RSI" in df_signals.columns and len(df_signals) > 2:
        rsi_diff = df_signals["RSI"].iloc[-1] - df_signals["RSI"].iloc[-2]
        if abs(rsi_diff) > 30:
            rsi_spike = True

    if len(df_signals) > 2:
        open_today = df_signals["Open"].iloc[-1]
        close_yesterday = df_signals["Close"].iloc[-2]
        gap = abs(open_today - close_yesterday) / close_yesterday
        if gap > 0.03:
            price_gap = True

    if "MACD" in df_signals.columns and "Signal" in df_signals.columns and len(df_signals) > 2:
        macd_today = df_signals["MACD"].iloc[-1]
        signal_today = df_signals["Signal"].iloc[-1]
        macd_prev = df_signals["MACD"].iloc[-2]
        signal_prev = df_signals["Signal"].iloc[-2]
        if (macd_prev < signal_prev and macd_today > signal_today) or (macd_prev > signal_prev and macd_today < signal_today):
            if abs(macd_today - signal_today) > 0.5:
                macd_spike = True

    summary["patterns"] = candlestick_patterns
    summary["rsi_spike"] = rsi_spike
    summary["price_gap"] = price_gap
    summary["macd_spike"] = macd_spike

    return summary, df_for_plotting
