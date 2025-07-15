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
            if df is None or len(df) < 10:
                out[name.lower()] = {"error": "No data"}
                continue
            close = df["Close"].dropna()
            trends = {}
            for lb in lookbacks:
                if len(close) >= lb:
                    change = (close[-1] - close[-lb]) / close[-lb] * 100
                    trend = (
                        "Uptrend" if change > 2 else
                        "Downtrend" if change < -2 else
                        "Sideways"
                    )
                else:
                    change, trend = np.nan, "N/A"
                trends[f"change_{lb}d_pct"] = float(np.round(change, 3)) if not np.isnan(change) else None
                trends[f"trend_{lb}d"] = trend
                # Add volatility for each window
                trends[f"vol_{lb}d"] = float(np.round(close[-lb:].std(), 3)) if len(close) >= lb else None
            trends["last"] = float(np.round(close[-1], 4))
            out[name] = trends
        except Exception as e:
            out[name] = {"error": str(e)}

    # --- Breadth: What % indices above 50d/200d MA
    breadth = {}
    above_50dma, above_200dma, count = 0, 0, 0
    for name, v in out.items():
        if isinstance(v, dict) and "last" in v and v.get("trend_50d", None) != "N/A":
            last = v["last"]
            symbol = indices[name]
            df = yf.download(symbol, start=start, end=today, interval="1d", auto_adjust=True, progress=False)
            if "Close" in df and len(df["Close"].dropna()) >= 200:
                ma50 = df["Close"].rolling(50).mean().iloc[-1]
                ma200 = df["Close"].rolling(200).mean().iloc[-1]
                if last > ma50:
                    above_50dma += 1
                if last > ma200:
                    above_200dma += 1
                count += 1
    breadth["breadth_above_50dma_pct"] = int(round(above_50dma / count * 100, 0)) if count else None
    breadth["breadth_above_200dma_pct"] = int(round(above_200dma / count * 100, 0)) if count else None

    # --- Risk regime (very simple rules for demo) ---
    vix30 = out.get("VIX", {}).get("change_30d_pct", None)
    spx_trend = out.get("S&P500", {}).get("trend_30d", "N/A")
    risk_regime = (
        "Bearish" if vix30 and vix30 > 10 and spx_trend == "Downtrend" else
        "Bullish" if vix30 and vix30 < -10 and spx_trend == "Uptrend" else
        "Neutral"
    )

    # --- Composite Score ---
    def get_trend(lb, k):
        t = out.get(k, {}).get(f"trend_{lb}d", "N/A")
        return trend_to_score(t)

    # Main indices only (equities for now)
    indices_for_score = ["S&P500", "Nasdaq", "EuroStoxx50", "Nikkei", "HangSeng", "FTSE100"]
    trend_scores = [get_trend(30, k) for k in indices_for_score]

    # VIX: High VIX is bearish
    vix_last = out.get("VIX", {}).get("last", None)
    vix_score = 1 - min(vix_last / 40, 1) if vix_last is not None else 0.5

    # Breadth
    breadth_50 = breadth.get("breadth_above_50dma_pct", 50) / 100
    breadth_200 = breadth.get("breadth_above_200dma_pct", 50) / 100

    # Simple average (you can weight if you want)
    composite_score = float(np.round(np.nanmean(trend_scores + [vix_score, breadth_50, breadth_200]), 3))
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

# For CLI testing only:
if __name__ == "__main__":
    result = ta_global()
    import pprint; pprint.pprint(result)






