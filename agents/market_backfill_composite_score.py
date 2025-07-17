import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import csv
import yfinance as yf

# --- Define the baskets for Market composite (SGX, Asia, relevant global for comparison) ---
indices_for_score = [
    "^STI",     # Straits Times Index (Singapore)
    "^HSI",     # Hang Seng (Hong Kong)
    "AAXJ",     # Asia ex Japan ETF
    "^N225",    # Nikkei 225 (Japan, for context)
    "^GSPC",    # S&P500 (global/benchmark, for comparison)
]
vix_symbol = "^VIX"

def to_scalar(val):
    if isinstance(val, (pd.Series, np.ndarray, list, tuple)):
        if len(val) == 0:
            return np.nan
        return to_scalar(val[-1])
    return val

def robust_series(series):
    if series is None:
        return pd.Series(dtype=float)
    if isinstance(series, (pd.DataFrame,)):
        if "Close" in series.columns:
            return series["Close"].dropna()
        elif series.shape[1] > 0:
            return series.iloc[:, 0].dropna()
        else:
            return pd.Series(dtype=float)
    if isinstance(series, (pd.Series, list, np.ndarray, tuple)):
        return pd.Series(series).dropna()
    return pd.Series(dtype=float)

def trend_to_score(trend):
    if trend == "Uptrend":
        return 1
    elif trend == "Downtrend":
        return 0
    elif trend == "Sideways":
        return 0.5
    return np.nan

def get_trend(series, lb):
    s = robust_series(series)
    if len(s) < lb:
        return "N/A"
    val_now = to_scalar(s.iloc[-1])
    val_then = to_scalar(s.iloc[-lb])
    if pd.isna(val_now) or pd.isna(val_then):
        return "N/A"
    try:
        val_now = float(val_now)
        val_then = float(val_then)
    except Exception:
        return "N/A"
    if val_then == 0:
        return "N/A"
    change = (val_now - val_then) / val_then * 100
    if change > 2:
        return "Uptrend"
    elif change < -2:
        return "Downtrend"
    else:
        return "Sideways"

def compute_composite_for_date(dt, lookback_days=400):
    start = dt - timedelta(days=lookback_days)
    end = dt + timedelta(days=1)
    ohlc = {}
    for symbol in indices_for_score + [vix_symbol]:
        try:
            df = yf.download(symbol, start=start, end=end, interval="1d", auto_adjust=True, progress=False)
            if df is None or len(df) < 10 or "Close" not in df:
                ohlc[symbol] = pd.Series(dtype=float)
            else:
                ohlc[symbol] = df["Close"].dropna()
        except Exception as e:
            print(f"WARNING: Data error for {symbol} on {dt.strftime('%Y-%m-%d')}: {e}")
            ohlc[symbol] = pd.Series(dtype=float)

    trend_scores = []
    for symbol in indices_for_score:
        s = ohlc.get(symbol, pd.Series(dtype=float))
        t = get_trend(s, 30)
        trend_scores.append(trend_to_score(t))

    vix_series = robust_series(ohlc.get(vix_symbol, pd.Series(dtype=float)))
    vix_last = to_scalar(vix_series.iloc[-1]) if len(vix_series) > 0 else np.nan
    vix_score = 0.5
    if not pd.isna(vix_last):
        try:
            vix_last_val = float(vix_last)
            vix_score = 1 - min(max(vix_last_val, 0) / 40, 1)
        except Exception:
            vix_score = 0.5

    above_50 = []
    above_200 = []
    for symbol in indices_for_score:
        s = robust_series(ohlc.get(symbol, pd.Series(dtype=float)))
        if len(s) >= 50:
            ma_50 = np.nanmean(s[-50:])
            price = to_scalar(s.iloc[-1])
            if not pd.isna(ma_50) and not pd.isna(price):
                above_50.append(float(price) > float(ma_50))
        if len(s) >= 200:
            ma_200 = np.nanmean(s[-200:])
            price = to_scalar(s.iloc[-1])
            if not pd.isna(ma_200) and not pd.isna(price):
                above_200.append(float(price) > float(ma_200))
    breadth_50 = np.mean(above_50) if above_50 else 0.5
    breadth_200 = np.mean(above_200) if above_200 else 0.5

    composite_inputs = trend_scores + [vix_score, breadth_50, breadth_200]
    composite_score = float(np.round(np.nanmean(composite_inputs), 3)) if np.any(pd.notnull(composite_inputs)) else 0.5
    composite_label = (
        "Bullish" if composite_score >= 0.7
        else "Bearish" if composite_score <= 0.3
        else "Neutral"
    )
    risk_regime = composite_label

    return {
        "date": dt.strftime("%Y-%m-%d"),
        "composite_score": composite_score,
        "composite_label": composite_label,
        "risk_regime": risk_regime
    }

# ---- MAIN: Run for past N days ----
N = 60  # Last 60 days; change as needed
results = []

print("Script started")
for i in range(N):
    dt = datetime.today() - timedelta(days=N - i - 1)
    print(f"Calculating for {dt.strftime('%Y-%m-%d')}")
    r = compute_composite_for_date(dt)
    results.append(r)
print("Calculation complete, writing to CSV...")

# --- Write to CSV (overwrites or creates) ---
csv_file = "market_composite_score_history.csv"
with open(csv_file, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["date", "composite_score", "composite_label", "risk_regime"])
    writer.writeheader()
    for r in results:
        writer.writerow(r)

print("Historical market composite score CSV written:", csv_file)
