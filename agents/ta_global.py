import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

def fetch_yf(symbol, period="13mo", interval="1d"):
    data = yf.download(symbol, period=period, interval=interval, progress=False)
    return data

def compute_pct_change(series, periods):
    if len(series) < periods + 1:
        return np.nan
    return (series.iloc[-1] / series.iloc[-(periods + 1)] - 1) * 100

def compute_rolling_vol(series, window):
    returns = series.pct_change()
    vol = returns.rolling(window=window).std().iloc[-1]
    if pd.isna(vol):
        return np.nan
    return vol * np.sqrt(252)  # annualized

def compute_trend(series, window):
    ma = series.rolling(window).mean()
    if pd.isna(ma.iloc[-1]):
        return "Unknown"
    return "Uptrend" if series.iloc[-1] > ma.iloc[-1] else "Downtrend"

def compute_breadth(indices, window):
    above_ma = 0
    valid = 0
    for s in indices:
        try:
            if len(s) >= window:
                ma = s.rolling(window).mean()
                if s.iloc[-1] > ma.iloc[-1]:
                    above_ma += 1
                valid += 1
        except:
            continue
    if valid == 0:
        return np.nan
    return (above_ma / valid) * 100

def ta_global():
    # --- Define symbols (all free via yfinance) ---
    SYMBOLS = {
        "VIX": "^VIX",
        "S&P500": "^GSPC",
        "Nasdaq": "^IXIC",
        "EuroStoxx50": "^STOXX50E",
        "Nikkei": "^N225",
        "HangSeng": "^HSI",
        "FTSE100": "^FTSE",
        "US10Y": "^TNX",
        "US2Y": "^IRX",
        "DXY": "DX-Y.NYB",
        "USD_SGD": "USDSGD=X",
        "USD_JPY": "JPY=X",
        "EUR_USD": "EURUSD=X",
        "USD_CNH": "USDCNH=X",
        "Gold": "GC=F",
        "Oil_Brent": "BZ=F",
        "Oil_WTI": "CL=F",
        "Copper": "HG=F",
    }

    WINDOWS = [30, 90, 200]  # Standard global lookback windows

    out = {}
    data = {}

    # --- Download all data ---
    for key, symbol in SYMBOLS.items():
        try:
            d = fetch_yf(symbol, period="13mo", interval="1d")
            if d.empty:
                d = fetch_yf(symbol, period="60d", interval="1d")
            data[key] = d
        except Exception as e:
            pass

    # --- Compute metrics for each asset & window ---
    for key, d in data.items():
        try:
            close = d["Close"].dropna()
            metrics = {}
            for win in WINDOWS:
                suffix = f"{win}d"
                metrics[f"change_{suffix}_pct"] = compute_pct_change(close, win)
                metrics[f"vol_{suffix}"] = compute_rolling_vol(close, win)
                metrics[f"trend_{suffix}"] = compute_trend(close, win)
            metrics["last"] = float(close.iloc[-1])
            out[key] = metrics
        except Exception as e:
            pass

    # --- Breadth: percent above 50/200 MA for major indices ---
    major_indices = [data[k]["Close"].dropna() for k in ["S&P500", "Nasdaq", "EuroStoxx50", "Nikkei", "HangSeng", "FTSE100"] if k in data and not data[k].empty]
    breadth = {}
    for win in [50, 200]:
        breadth[f"breadth_above_{win}dma_pct"] = compute_breadth(major_indices, window=win)

    # --- Composite risk regime (simple logic) ---
    try:
        vix_30d = out["VIX"]["last"]
        spx_trend = out["S&P500"]["trend_30d"]
        if vix_30d >= 25 or spx_trend == "Downtrend":
            risk_regime = "Risk-Off"
        elif vix_30d <= 15 and spx_trend == "Uptrend":
            risk_regime = "Risk-On"
        else:
            risk_regime = "Neutral"
    except:
        risk_regime = "Unknown"

    # --- News placeholder (for future news agents) ---
    news_summary = "No news data yet. (Reserved for future global/regional/local news agent summary.)"

    # --- Output summary dict ---
    summary = {
        "as_of": datetime.now().strftime("%Y-%m-%d"),
        "lookbacks": WINDOWS,
        **{k.lower(): v for k, v in out.items()},
        **breadth,
        "risk_regime": risk_regime,
        "news": news_summary,
    }

    return summary

# No print or Streamlit here; for frontend integration!




