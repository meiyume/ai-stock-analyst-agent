import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

def fetch_yf(symbol, period="13mo", interval="1d"):
    print(f"Downloading {symbol} ...", flush=True)
    data = yf.download(symbol, period=period, interval=interval, progress=False)
    print(f"{symbol} rows: {len(data)}", flush=True)
    return data

def get_close_series(d):
    # Defensive: try Close, then Adj Close, always return a Series or None
    if "Close" in d and isinstance(d["Close"], pd.Series) and not d["Close"].dropna().empty:
        return d["Close"].dropna()
    elif "Adj Close" in d and isinstance(d["Adj Close"], pd.Series) and not d["Adj Close"].dropna().empty:
        return d["Adj Close"].dropna()
    else:
        return None

def compute_pct_change(series, periods):
    if series is None or len(series) < periods + 1:
        return np.nan
    return (series.iloc[-1] / series.iloc[-(periods + 1)] - 1) * 100

def compute_rolling_vol(series, window):
    if series is None or len(series) < window + 1:
        return np.nan
    returns = series.pct_change()
    vol = returns.rolling(window=window).std().iloc[-1]
    if pd.isna(vol):
        return np.nan
    return vol * np.sqrt(252)

def compute_trend(series, window):
    if series is None or len(series) < window:
        return "Unknown"
    ma = series.rolling(window).mean()
    val = ma.iloc[-1]
    if pd.isna(val):
        return "Unknown"
    return "Uptrend" if series.iloc[-1] > val else "Downtrend"

def compute_breadth(indices, window):
    above_ma = 0
    valid = 0
    for s in indices:
        if s is None or len(s) < window:
            continue
        ma = s.rolling(window).mean()
        val = ma.iloc[-1]
        if pd.isna(val):
            continue
        if s.iloc[-1] > val:
            above_ma += 1
        valid += 1
    if valid == 0:
        return np.nan
    return (above_ma / valid) * 100

def ta_global():
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

    WINDOWS = [30, 90, 200]

    out = {}
    data = {}

    print("\n---- Starting downloads ----\n", flush=True)
    for key, symbol in SYMBOLS.items():
        try:
            d = fetch_yf(symbol, period="13mo", interval="1d")
            if d.empty:
                print(f"WARNING: {symbol} ({key}) is empty!", flush=True)
                d = fetch_yf(symbol, period="60d", interval="1d")
                if d.empty:
                    print(f"ERROR: {symbol} ({key}) is STILL empty after fallback.", flush=True)
            data[key] = d
        except Exception as e:
            print(f"ERROR downloading {key} ({symbol}): {e}", flush=True)

    print("\n---- Checking key symbols ----", flush=True)
    for key in ["S&P500", "VIX"]:
        if key in data:
            print(f"{key} rows: {len(data[key])}, latest: {data[key].index[-1] if not data[key].empty else 'EMPTY'}", flush=True)

    for key, d in data.items():
        try:
            close = get_close_series(d)
            if close is None:
                print(f"WARNING: No usable Close/Adj Close for {key}")
                continue
            metrics = {}
            for win in WINDOWS:
                suffix = f"{win}d"
                metrics[f"change_{suffix}_pct"] = compute_pct_change(close, win)
                metrics[f"vol_{suffix}"] = compute_rolling_vol(close, win)
                metrics[f"trend_{suffix}"] = compute_trend(close, win)
            metrics["last"] = float(close.iloc[-1]) if not close.empty else np.nan
            out[key] = metrics
        except Exception as e:
            print(f"ERROR computing metrics for {key}: {e}", flush=True)

    # Build major_indices list of price series
    major_indices = [
        get_close_series(data[k])
        for k in ["S&P500", "Nasdaq", "EuroStoxx50", "Nikkei", "HangSeng", "FTSE100"]
        if k in data and get_close_series(data[k]) is not None
    ]
    breadth = {}
    for win in [50, 200]:
        b = compute_breadth(major_indices, window=win)
        print(f"Breadth {win}d: {b}", flush=True)
        breadth[f"breadth_above_{win}dma_pct"] = b

    try:
        vix_30d = out.get("VIX", {}).get("last", np.nan)
        spx_trend = out.get("S&P500", {}).get("trend_30d", "Unknown")
        print(f"VIX latest: {vix_30d}, SPX 30d trend: {spx_trend}", flush=True)
        if not np.isnan(vix_30d) and (vix_30d >= 25 or spx_trend == "Downtrend"):
            risk_regime = "Risk-Off"
        elif not np.isnan(vix_30d) and vix_30d <= 15 and spx_trend == "Uptrend":
            risk_regime = "Risk-On"
        else:
            risk_regime = "Neutral"
    except Exception as e:
        print(f"Risk regime calc error: {e}", flush=True)
        risk_regime = "Unknown"

    news_summary = "No news data yet. (Reserved for future global/regional/local news agent summary.)"

    summary = {
        "as_of": datetime.now().strftime("%Y-%m-%d"),
        "lookbacks": WINDOWS,
        **{k.lower(): v for k, v in out.items()},
        **breadth,
        "risk_regime": risk_regime,
        "news": news_summary,
    }

    print("\n---- Global Agent Output ----", flush=True)
    for k, v in summary.items():
        print(f"{k}: {v}", flush=True)

    return summary

if __name__ == "__main__":
    ta_global()




