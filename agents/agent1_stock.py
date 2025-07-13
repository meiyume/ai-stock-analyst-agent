import yfinance as yf
import pandas as pd
import numpy as np

# === Indicator Computations (manual, no ta lib) ===

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

# === Candlestick Pattern Detection ===
def detect_candlestick_patterns(df):
    patterns = []
    if len(df) < 2:
        return patterns
    last = df.iloc[-1]
    prev = df.iloc[-2]

    # Doji
    body = abs(last['Open'] - last['Close'])
    candle_range = last['High'] - last['Low']
    if candle_range > 0 and body / candle_range < 0.1:
        patterns.append("Doji")

    # Bullish Engulfing
    if (last['Close'] > last['Open']) and (prev['Close'] < prev['Open']) and \
       (last['Open'] < prev['Close']) and (last['Close'] > prev['Open']):
        patterns.append("Bullish Engulfing")

    # Bearish Engulfing
    if (last['Close'] < last['Open']) and (prev['Close'] > prev['Open']) and \
       (last['Open'] > prev['Close']) and (last['Close'] < prev['Open']):
        patterns.append("Bearish Engulfing")

    # Add more as desired!
    return patterns

# === Anomaly Detection ===
def detect_anomalies(df):
    anomalies = []
    if len(df) < 2:
        return anomalies
    # RSI Spike
    if abs(df['RSI'].iloc[-1] - df['RSI'].iloc[-2]) > 15:
        anomalies.append("RSI Spike")
    # MACD Spike
    if abs(df['MACD'].iloc[-1] - df['MACD'].iloc[-2]) > 0.5:
        anomalies.append("MACD Spike")
    # Price Gap
    if abs(df['Open'].iloc[-1] - df['Close'].iloc[-2]) > 0.02 * df['Close'].iloc[-2]:
        anomalies.append("Price Gap")
    return anomalies

# === Main Analysis ===
def analyze(ticker: str, horizon: str = "7 Days"):
    stock = yf.Ticker(ticker)
    df = stock.history(period="180d", interval="1d")

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
            "anomalies": []
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

    # === Technical Text Signals for Summary Layer (not used in heatmap) ===
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

    # === Pattern and Anomaly Detection ===
    patterns = detect_candlestick_patterns(df_signals)
    anomalies = detect_anomalies(df_signals)

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
        "vol_spike": vol_spike,
        "patterns": patterns,
        "anomalies": anomalies
    }

    # === Heatmap Signal Status (all 10 indicators always included) ===
    heatmap_signals = {}

    # SMA Trend
    heatmap_signals["SMA Trend"] = "Bullish" if latest["SMA5"] > latest["SMA10"] else "Bearish"

    # MACD
    heatmap_signals["MACD"] = "Bullish Crossover" if latest["MACD"] > latest["Signal"] else "Bearish Crossover"

    # RSI
    rsi = latest["RSI"]
    if rsi > 70:
        heatmap_signals["RSI"] = "Overbought"
    elif rsi < 30:
        heatmap_signals["RSI"] = "Oversold"
    else:
        heatmap_signals["RSI"] = "Neutral"

    # Volume
    heatmap_signals["Volume"] = "Spike" if vol_spike else "Normal"

    # ATR
    atr = latest["ATR"]
    atr_avg = df["ATR"].mean()
    heatmap_signals["ATR"] = "High Volatility" if atr > 1.5 * atr_avg else "Stable"

    # Pattern
    heatmap_signals["Pattern"] = patterns[0] if patterns else "None"

    # ADX
    heatmap_signals["ADX"] = "Strong Trend" if latest["ADX"] > 25 else "Weak Trend"

    # Stochastic
    stoch = latest["Stochastic_%K"]
    if stoch > 80:
        heatmap_signals["Stochastic"] = "Overbought"
    elif stoch < 20:
        heatmap_signals["Stochastic"] = "Oversold"
    else:
        heatmap_signals["Stochastic"] = "Neutral"

    # CMF
    cmf = latest["CMF"]
    if cmf > 0:
        heatmap_signals["CMF"] = "Buying Pressure"
    elif cmf < 0:
        heatmap_signals["CMF"] = "Selling Pressure"
    else:
        heatmap_signals["CMF"] = "Neutral"

    # OBV
    if latest["OBV"] > df["OBV"].iloc[-2]:
        heatmap_signals["OBV"] = "Bullish Divergence"
    elif latest["OBV"] < df["OBV"].iloc[-2]:
        heatmap_signals["OBV"] = "Bearish Divergence"
    else:
        heatmap_signals["OBV"] = "Neutral"

    # === Composite Risk Score and Level ===
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

    risk_score = 0
    risk_mapping = {
        "Bullish": 0, "Bullish Crossover": 0, "Oversold": 0,
        "Normal": 0, "Stable": 0, "Strong Trend": 0, "Overbought": 1,
        "Bearish": 1, "Bearish Crossover": 1, "Spike": 0.5,
        "Weak Trend": 0.5, "High Volatility": 0.5,
        "Buying Pressure": 0, "Selling Pressure": 1, "Neutral": 0.5,
        "Bullish Divergence": 0, "Bearish Divergence": 1,
        "None": 0.5
    }
    for k, v in heatmap_signals.items():
        risk_score += weights.get(k, 0.1) * risk_mapping.get(v, 0.5)
    risk_score = round(risk_score, 2)
    if risk_score < 0.34:
        risk_level = "Low"
    elif risk_score < 0.67:
        risk_level = "Caution"
    else:
        risk_level = "High"

    summary["heatmap_signals"] = heatmap_signals
    summary["composite_risk_score"] = risk_score
    summary["risk_level"] = risk_level

    return summary, df_for_plotting


