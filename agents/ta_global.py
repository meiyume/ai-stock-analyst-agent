import yfinance as yf
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def trend_to_score(trend):
    if trend == "Uptrend":
        return 1.0
    elif trend == "Downtrend":
        return 0.0
    else:
        return 0.5

def ta_global():
    # List of indices to fetch
    indices = {
        "S&P500": "^GSPC",
        "VIX": "^VIX",
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
    lookbacks = [30, 90, 200]
    out = {}
    today = datetime.today()
    start = today - timedelta(days=400)

    for name, symbol in indices.items():
        try:
            df = yf.download(symbol, start=start, end=today, interval="1d", auto_adjust=True, progress=False)
            if df is None or len(df) < 10 or "Close" not in df:
                out[name] = {"error": "No data"}
                continue
            close = df["Close"].dropna()
            # Ensure close is a Series and not accidentally a DataFrame
            if isinstance(close, pd.DataFrame):
                close = close.squeeze()
            trends = {}
            for lb in lookbacks:
                if len(close) >= lb:
                    val_now = close.iloc[-1]
                    val_then = close.iloc[-lb]
                    # Force both to float to avoid pandas Series ambiguity bug
                    try:
                        val_now = float(val_now)
                    except Exception:
                        val_now = np.nan
                    try:
                        val_then = float(val_then)
                    except Exception:
                        val_then = np.nan
                    if not pd.isna(val_now) and not pd.isna(val_then) and val_then != 0:
                        change = (val_now - val_then) / val_then * 100
                        trend = (
                            "Uptrend" if change > 2 else
                            "Downtrend" if change < -2 else
                            "Sideways"
                        )
                    else:
                        change, trend = np.nan, "N/A"
                else:
                    change, trend = np.nan, "N/A"
                trends[f"change_{lb}d_pct"] = float(np.round(change, 3)) if not pd.isna(change) else None
                trends[f"trend_{lb}d"] = trend
                trends[f"vol_{lb}d"] = (
                    float(np.round(close[-lb:].std(), 3))
                    if len(close) >= lb and close[-lb:].notnull().sum() > 1 else None
                )
            # Last close price
            try:
                trends["last"] = float(np.round(close.iloc[-1], 4)) if len(close) > 0 else None
            except Exception:
                trends["last"] = None
            out[name] = trends
        except Exception as e:
            out[name] = {"error": str(e)}

    # --- Breadth: What % indices above 50d/200d MA
    breadth = {}
    above_50dma, above_200dma, count = 0, 0, 0
    for name, v in out.items():
        if isinstance(v, dict) and "last" in v and v.get("last") is not None:
            last = v["last"]
            symbol = indices[name]
            try:
                df_breadth = yf.download(symbol, start=start, end=today, interval="1d", auto_adjust=True, progress=False)
                close_breadth = df_breadth["Close"].dropna()
                if isinstance(close_breadth, pd.DataFrame):
                    close_breadth = close_breadth.squeeze()
                if len(close_breadth) >= 200:
                    ma50 = close_breadth.rolling(50).mean().iloc[-1]
                    ma200 = close_breadth.rolling(200).mean().iloc[-1]
                    # Ensure MAs are floats
                    try:
                        ma50 = float(ma50)
                    except Exception:
                        ma50 = np.nan
                    try:
                        ma200 = float(ma200)
                    except Exception:
                        ma200 = np.nan
                    if pd.notnull(ma50) and last > ma50:
                        above_50dma += 1
                    if pd.notnull(ma200) and last > ma200:
                        above_200dma += 1
                    count += 1
            except Exception:
                continue
    breadth["breadth_above_50dma_pct"] = int(round(above_50dma / count * 100, 0)) if count else None
    breadth["breadth_above_200dma_pct"] = int(round(above_200dma / count * 100, 0)) if count else None

    # --- Risk regime (very simple rules for demo) ---
    vix30 = out.get("VIX", {}).get("change_30d_pct", None)
    spx_trend = out.get("S&P500", {}).get("trend_30d", "N/A")
    risk_regime = (
        "Bearish" if vix30 is not None and vix30 > 10 and spx_trend == "Downtrend" else
        "Bullish" if vix30 is not None and vix30 < -10 and spx_trend == "Uptrend" else
        "Neutral"
    )

    # --- Composite Score ---
    def get_trend(lb, k):
        t = out.get(k, {}).get(f"trend_{lb}d", "N/A")
        return trend_to_score(t)

    indices_for_score = ["S&P500", "Nasdaq", "EuroStoxx50", "Nikkei", "HangSeng", "FTSE100"]
    trend_scores = [get_trend(30, k) for k in indices_for_score]

    # VIX: High VIX is bearish
    vix_last = out.get("VIX", {}).get("last", None)
    vix_score = 1 - min(vix_last / 40, 1) if vix_last is not None and vix_last >= 0 else 0.5

    # Breadth
    breadth_50 = breadth.get("breadth_above_50dma_pct", 50) / 100 if breadth.get("breadth_above_50dma_pct") is not None else 0.5
    breadth_200 = breadth.get("breadth_above_200dma_pct", 50) / 100 if breadth.get("breadth_above_200dma_pct") is not None else 0.5

    composite_inputs = trend_scores + [vix_score, breadth_50, breadth_200]
    composite_score = float(np.round(np.nanmean(composite_inputs), 3)) if np.any(pd.notnull(composite_inputs)) else 0.5
    composite_label = (
        "Bullish" if composite_score >= 0.7
        else "Bearish" if composite_score <= 0.3
        else "Neutral"
    )

    # --- Summary dict ---
    summary = {
        "as_of": today.strftime("%Y-%m-%d"),
        "lookbacks": lookbacks,
        "out": out,
        "breadth": breadth,
        "risk_regime": risk_regime,
        "composite_score": composite_score,
        "composite_label": composite_label,
        "news": "No news data yet. (Reserved for future global/regional/local news agent summary.)"
    }
    return summary

if __name__ == "__main__":
    result = ta_global()
    import pprint; pprint.pprint(result)








