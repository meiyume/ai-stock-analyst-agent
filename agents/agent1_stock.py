# agent1_stock.py

import yfinance as yf
import pandas as pd
import numpy as np

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

def analyze(ticker: str, horizon: str = "7 Days"):
    stock = yf.Ticker(ticker)
    df = stock.history(period="30d", interval="1d")

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
            "vol_spike": False
        }, df

    # === Indicators ===
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

    df = df.dropna()
    latest = df.iloc[-1]

    # === Signals ===
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

    avg_vol = df["Volume"].rolling(window=5).mean().iloc[-1]
    vol_spike = latest["Volume"] > 1.5 * avg_vol

    summary = {
        "summary": f"{sma_trend} SMA, {macd_signal} MACD, {rsi_signal} RSI, {bollinger_signal}, "
                   f"{stochastic_signal} Stochastic, {cmf_signal} CMF, {obv_signal} OBV",
        "sma_trend": sma_trend,
        "macd_signal": macd_signal,
        "bollinger_signal": bollinger_signal,
        "rsi_signal": rsi_signal,
        "stochastic_signal": stochastic_signal,
        "cmf_signal": cmf_signal,
        "obv_signal": obv_signal,
        "vol_spike": vol_spike
    }

    return summary, df
