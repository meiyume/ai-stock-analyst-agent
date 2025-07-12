# agents/agent1_stock.py

import yfinance as yf
import pandas as pd
import numpy as np

# === Core Indicator Functions ===

def calculate_sma(df, window):
    return df["Close"].rolling(window=window).mean()

def calculate_ema(df, span):
    return df["Close"].ewm(span=span, adjust=False).mean()

def calculate_macd(df):
    ema12 = calculate_ema(df, 12)
    ema26 = calculate_ema(df, 26)
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal

def calculate_rsi(df, period=14):
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_bollinger_bands(df, window=20, num_std=2):
    sma = calculate_sma(df, window)
    std = df["Close"].rolling(window).std()
    upper = sma + (std * num_std)
    lower = sma - (std * num_std)
    return upper, lower

def calculate_volume_surge(df, window=10):
    avg_volume = df["Volume"].rolling(window=window).mean()
    surge = df["Volume"] / avg_volume
    return surge

# === Summary Interpreter Functions ===

def interpret_rsi(rsi):
    if rsi < 30:
        return "Oversold"
    elif rsi > 70:
        return "Overbought"
    else:
        return "Neutral"

def interpret_macd(macd, signal):
    if macd > signal:
        return "Bullish crossover"
    elif macd < signal:
        return "Bearish crossover"
    else:
        return "Neutral"

def interpret_bollinger(price, lower, upper):
    if price >= upper:
        return "Overbought (touching upper band)"
    elif price <= lower:
        return "Oversold (touching lower band)"
    else:
        return "Within bands"

# === Agent 1.0 Main Function ===

def analyze(ticker: str, horizon: str = "7 Days"):
    df = yf.Ticker(ticker).history(period="60d", interval="1d").reset_index()

    df["SMA_5"] = calculate_sma(df, 5)
    df["SMA_10"] = calculate_sma(df, 10)
    df["SMA_20"] = calculate_sma(df, 20)
    df["EMA_12"] = calculate_ema(df, 12)
    df["EMA_26"] = calculate_ema(df, 26)
    df["MACD"], df["MACD_Signal"] = calculate_macd(df)
    df["RSI"] = calculate_rsi(df)
    df["BB_Upper"], df["BB_Lower"] = calculate_bollinger_bands(df)
    df["Volume_Surge"] = calculate_volume_surge(df)

    latest = df.iloc[-1]

    summary = {
        "agent": "1.0",
        "ticker": ticker,
        "horizon": horizon,
        "sma_trend": "Bullish" if latest["SMA_5"] > latest["SMA_10"] else "Bearish",
        "rsi": interpret_rsi(latest["RSI"]),
        "macd": interpret_macd(latest["MACD"], latest["MACD_Signal"]),
        "bollinger": interpret_bollinger(latest["Close"], latest["BB_Lower"], latest["BB_Upper"]),
        "volume": "Surge" if latest["Volume_Surge"] > 1.5 else "Normal",
        "summary": ""
    }

    summary["summary"] = (
        f"For a {horizon.lower()} outlook on {ticker}: "
        f"SMA shows a {summary['sma_trend']} trend. "
        f"RSI is {summary['rsi'].lower()}. "
        f"MACD shows {summary['macd'].lower()}. "
        f"Bollinger Bands suggest price is {summary['bollinger'].lower()}. "
        f"Volume is {summary['volume'].lower()}."
    )

    return summary, df
