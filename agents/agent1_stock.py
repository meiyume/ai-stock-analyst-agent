# agent1_stock.py

import yfinance as yf
import pandas as pd
import numpy as np

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

    df = df.copy()
    df["SMA_5"] = df["Close"].rolling(window=5).mean()
    df["SMA_10"] = df["Close"].rolling(window=10).mean()

    df["EMA12"] = df["Close"].ewm(span=12, adjust=False).mean()
    df["EMA26"] = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = df["EMA12"] - df["EMA26"]
    df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()

    df["20dSTD"] = df["Close"].rolling(window=20).std()
    df["BB_Upper"] = df["SMA_10"] + 2 * df["20dSTD"]
    df["BB_Lower"] = df["SMA_10"] - 2 * df["20dSTD"]

    df["RSI"] = compute_rsi(df["Close"], 14)

    # === Stochastic Oscillator ===
    low_14 = df["Low"].rolling(window=14).min()
    high_14 = df["High"].rolling(window=14).max()
    df["%K"] = 100 * (df["Close"] - low_14) / (high_14 - low_14 + 1e-10)
    df["%D"] = df["%K"].rolling(window=3).mean()

    # === CMF (Chaikin Money Flow) ===
    mf_multiplier = ((df["Close"] - df["Low"]) - (df["High"] - df["Close"])) / (df["High"] - df["Low"] + 1e-10)
    mf_volume = mf_multiplier * df["Volume"]
    df["CMF"] = mf_volume.rolling(window=20).sum() / df["Volume"].rolling(window=20).sum()

    # === OBV (On-Balance Volume) ===
    df["OBV"] = (np.sign(df["Close"].diff()) * df["Volume"]).fillna(0).cumsum()

    latest = df.iloc[-1]

    # === Signal Interpretation ===
    sma_trend = "Bullish" if latest["SMA_5"] > latest["SMA_10"] else "Bearish"
    macd_signal = "Bullish" if latest["MACD"] > latest["MACD_Signal"] else "Bearish"
    bollinger_signal = (
        "Above upper band" if latest["Close"] > latest["BB_Upper"]
        else "Below lower band" if latest["Close"] < latest["BB_Lower"]
        else "Within band"
    )
    rsi_signal = (
        "Overbought" if latest["RSI"] > 70
        else "Oversold" if latest["RSI"] < 30
        else "Neutral"
    )
    stochastic_signal = (
        "Overbought" if latest["%K"] > 80
        else "Oversold" if latest["%K"] < 20
        else "Neutral"
    )
    cmf_signal = (
        "Buying pressure" if latest["CMF"] > 0
        else "Selling pressure" if latest["CMF"] < 0
        else "Neutral"
    )
    obv_signal = "Uptrend" if df["OBV"].iloc[-1] > df["OBV"].iloc[-2] else "Downtrend"

    avg_vol = df["Volume"].rolling(window=5).mean().iloc[-1]
    vol_spike = latest["Volume"] > 1.5 * avg_vol

    summary = {
        "summary": f"{sma_trend} SMA, {macd_signal} MACD, {rsi_signal} RSI, {stochastic_signal} Stochastic, {bollinger_signal}",
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

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()

    rs = avg_gain / (avg_loss + 1e-10)
    rsi = 100 - (100 / (1 + rs))
    return rsi

