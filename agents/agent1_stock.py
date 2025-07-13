import numpy as np
import pandas as pd
from agents.patterns import detect_candlestick_patterns

# === Risk weightings for each signal ===
weights = {
    "SMA Trend": 0.1,
    "MACD": 0.15,
    "RSI": 0.15,
    "Volume": 0.1,
    "ATR": 0.1,
    "Pattern": 0.1,
    "ADX": 0.1,
    "Stochastic": 0.1,
    "CMF": 0.05,
    "OBV": 0.05,
}

def compute_indicators(df):
    df = df.copy()
    # SMA
    df["SMA5"] = df["Close"].rolling(5).mean()
    df["SMA10"] = df["Close"].rolling(10).mean()

    # MACD
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()

    # RSI
    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    df["RSI"] = 100 - (100 / (1 + rs))

    # Bollinger Bands (for display)
    df["Upper"] = df["SMA10"] + 2 * df["Close"].rolling(10).std()
    df["Lower"] = df["SMA10"] - 2 * df["Close"].rolling(10).std()

    # ATR
    high_low = df["High"] - df["Low"]
    high_close = np.abs(df["High"] - df["Close"].shift())
    low_close = np.abs(df["Low"] - df["Close"].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["ATR"] = tr.rolling(14).mean()

    # ADX (simple implementation)
    up_move = df["High"].diff()
    down_move = -df["Low"].diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
    tr = pd.concat([
        df["High"] - df["Low"],
        np.abs(df["High"] - df["Close"].shift()),
        np.abs(df["Low"] - df["Close"].shift())
    ], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()
    plus_di = 100 * pd.Series(plus_dm).rolling(14).sum() / atr
    minus_di = 100 * pd.Series(minus_dm).rolling(14).sum() / atr
    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
    df["ADX"] = dx.rolling(14).mean()

    # Stochastic Oscillator
    low_min = df["Low"].rolling(14).min()
    high_max = df["High"].rolling(14).max()
    df["Stochastic_%K"] = 100 * (df["Close"] - low_min) / (high_max - low_min)
    df["Stochastic_%D"] = df["Stochastic_%K"].rolling(3).mean()

    # CMF (Chaikin Money Flow)
    mfv = ((df["Close"] - df["Low"]) - (df["High"] - df["Close"])) / (df["High"] - df["Low"]).replace(0, np.nan)
    mfv = mfv * df["Volume"]
    df["CMF"] = mfv.rolling(20).sum() / df["Volume"].rolling(20).sum()

    # OBV
    obv = [0]
    for i in range(1, len(df)):
        if df["Close"].iloc[i] > df["Close"].iloc[i-1]:
            obv.append(obv[-1] + df["Volume"].iloc[i])
        elif df["Close"].iloc[i] < df["Close"].iloc[i-1]:
            obv.append(obv[-1] - df["Volume"].iloc[i])
        else:
            obv.append(obv[-1])
    df["OBV"] = obv

    return df

def run_full_technical_analysis(ticker, outlook_horizon):
    df = fetch_data(ticker, outlook_horizon)  # You must define fetch_data elsewhere!
    df = compute_indicators(df)
    summary = {}

    # Latest values (last row)
    latest = df.iloc[-1]

    # Patterns
    patterns = detect_candlestick_patterns(df)
    summary["patterns"] = patterns

    # Volume spike
    vol_spike = df["Volume"].iloc[-1] > df["Volume"].rolling(20).mean().iloc[-1] * 1.5
    summary["vol_spike"] = vol_spike

    # === Heatmap Signal Status (guaranteed full set) ===
    heatmap_signals = {}
    risk_score = 0.0

    # SMA Trend
    if "SMA5" in latest and "SMA10" in latest:
        if latest["SMA5"] > latest["SMA10"]:
            heatmap_signals["SMA Trend"] = "Bullish"
        elif latest["SMA5"] < latest["SMA10"]:
            heatmap_signals["SMA Trend"] = "Bearish"
        else:
            heatmap_signals["SMA Trend"] = "Neutral"
    else:
        heatmap_signals["SMA Trend"] = "Neutral"

    # MACD
    if "MACD" in df.columns and "Signal" in df.columns:
        macd = df["MACD"].iloc[-1]
        signal = df["Signal"].iloc[-1]
        if macd > signal:
            heatmap_signals["MACD"] = "Bullish Crossover"
            macd_score = 0
        else:
            heatmap_signals["MACD"] = "Bearish Crossover"
            macd_score = 1
        risk_score += weights["MACD"] * macd_score
    else:
        heatmap_signals["MACD"] = "Neutral"

    # RSI
    if "RSI" in latest:
        rsi = latest["RSI"]
        if rsi > 70:
            heatmap_signals["RSI"] = "Overbought"
            rsi_score = 1
        elif rsi < 30:
            heatmap_signals["RSI"] = "Oversold"
            rsi_score = 0
        else:
            heatmap_signals["RSI"] = "Neutral"
            rsi_score = 0.5
        risk_score += weights["RSI"] * rsi_score
    else:
        heatmap_signals["RSI"] = "Neutral"

    # Volume
    heatmap_signals["Volume"] = "Spike" if vol_spike else "Normal"
    risk_score += weights["Volume"] * (0.5 if vol_spike else 0)

    # ATR
    if "ATR" in latest:
        atr = latest["ATR"]
        atr_avg = df["ATR"].mean()
        if atr > 1.5 * atr_avg:
            heatmap_signals["ATR"] = "High Volatility"
            risk_score += weights["ATR"] * 0.5
        else:
            heatmap_signals["ATR"] = "Stable"
    else:
        heatmap_signals["ATR"] = "Neutral"

    # Pattern
    pattern_count = len(patterns)
    if pattern_count > 0:
        heatmap_signals["Pattern"] = patterns[0]
        risk_score += weights["Pattern"] * 0.3
    else:
        heatmap_signals["Pattern"] = "None"

    # ADX
    if "ADX" in latest:
        adx = latest["ADX"]
        if adx > 25:
            heatmap_signals["ADX"] = "Strong Trend"
        else:
            heatmap_signals["ADX"] = "Weak Trend"
            risk_score += weights["ADX"] * 0.3
    else:
        heatmap_signals["ADX"] = "Neutral"

    # Stochastic
    if "Stochastic_%K" in latest:
        stoch = latest["Stochastic_%K"]
        if stoch > 80:
            heatmap_signals["Stochastic"] = "Overbought"
            risk_score += weights["Stochastic"] * 0.5
        elif stoch < 20:
            heatmap_signals["Stochastic"] = "Oversold"
        else:
            heatmap_signals["Stochastic"] = "Neutral"
    else:
        heatmap_signals["Stochastic"] = "Neutral"

    # CMF
    if "CMF" in latest:
        cmf = latest["CMF"]
        if cmf > 0:
            heatmap_signals["CMF"] = "Buying Pressure"
        elif cmf < 0:
            heatmap_signals["CMF"] = "Selling Pressure"
        else:
            heatmap_signals["CMF"] = "Neutral"
    else:
        heatmap_signals["CMF"] = "Neutral"

    # OBV
    if "OBV" in latest and len(df) > 1:
        if latest["OBV"] > df["OBV"].iloc[-2]:
            heatmap_signals["OBV"] = "Bullish Divergence"
        elif latest["OBV"] < df["OBV"].iloc[-2]:
            heatmap_signals["OBV"] = "Bearish Divergence"
        else:
            heatmap_signals["OBV"] = "Neutral"
    else:
        heatmap_signals["OBV"] = "Neutral"

    # === Final summary output ===
    summary["heatmap_signals"] = heatmap_signals
    summary["composite_risk_score"] = round(risk_score, 2)
    summary["risk_level"] = (
        "Low" if risk_score < 0.34 else "Caution" if risk_score < 0.67 else "High"
    )

    # Attach more analysis as needed (sector, market, etc.)
    results = {
        "stock": summary,
        # Add other analysis blocks here if needed
    }
    return results, df

# Reminder: You must implement or import your fetch_data() and patterns module.

