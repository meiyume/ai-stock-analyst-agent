import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def trend_direction(change_pct, threshold=2):
    if pd.isna(change_pct):
        return "N/A"
    if change_pct > threshold:
        return "Uptrend"
    elif change_pct < -threshold:
        return "Downtrend"
    else:
        return "Sideways"

def get_market_baskets():
    # Define market/sector/factor tickers here
    return {
        "S&P 500": "SPY",
        "Nasdaq 100": "QQQ",
        "EuroStoxx 50": "FEZ",
        "Nikkei 225": "EWJ",
        "FTSE 100": "EWU",
        "Hang Seng": "EWH",
        "Emerging Mkts": "EEM",
        "US Tech": "XLK",
        "US Financials": "XLF",
        "US Energy": "XLE",
        "US Industrials": "XLI",
        "US Healthcare": "XLV",
        "US Utilities": "XLU",
        "US Value": "IVE",
        "US Growth": "IVW",
        "US Small Cap": "IWM",
        "US Bonds": "AGG",
        "Gold": "GLD",
        "Oil": "USO",
    }

def ta_market(lookbacks=[30, 90, 200]):
    baskets = get_market_baskets()
    today = datetime.today()
    start = today - timedelta(days=400)
    out = {}
    all_prices = {}

    for name, ticker in baskets.items():
        try:
            df = yf.download(ticker, start=start, end=today, interval="1d", auto_adjust=True, progress=False)
            if df is None or len(df) < 10 or "Close" not in df:
                out[name] = {"error": "No data"}
                continue
            close = df["Close"].dropna()
            all_prices[name] = close
            signals = {}
            for lb in lookbacks:
                if len(close) >= lb:
                    now = close.iloc[-1]
                    then = close.iloc[-lb]
                    change = (now - then) / then * 100 if then != 0 else np.nan
                    signals[f"change_{lb}d_pct"] = float(np.round(change, 3))
                    signals[f"trend_{lb}d"] = trend_direction(change)
                    signals[f"vol_{lb}d"] = float(np.round(close[-lb:].std(), 3))
                else:
                    signals[f"change_{lb}d_pct"] = None
                    signals[f"trend_{lb}d"] = "N/A"
                    signals[f"vol_{lb}d"] = None
            signals["last"] = float(np.round(close.iloc[-1], 3)) if len(close) > 0 else None
            out[name] = signals
        except Exception as e:
            out[name] = {"error": str(e)}

    # --- Breadth: % of baskets in uptrend (30d) ---
    uptrend_count = 0
    total_count = 0
    for v in out.values():
        if v.get("trend_30d", "N/A") == "Uptrend":
            uptrend_count += 1
        if "trend_30d" in v:
            total_count += 1
    breadth_30d_pct = int(100 * uptrend_count / total_count) if total_count else None

    # --- Relative rotation (vs S&P 500 or SPY) ---
    rel_perf = {}
    spy_close = all_prices.get("S&P 500", None)
    if spy_close is not None:
        for name, series in all_prices.items():
            # 30d relative: basket 30d change - SPY 30d change
            if len(series) >= 30 and len(spy_close) >= 30:
                rel = ((series.iloc[-1] - series.iloc[-30]) / series.iloc[-30]) - ((spy_close.iloc[-1] - spy_close.iloc[-30]) / spy_close.iloc[-30])
                rel_perf[name] = float(np.round(rel * 100, 2))

    summary = {
        "as_of": today.strftime("%Y-%m-%d"),
        "out": out,
        "breadth_30d_pct": breadth_30d_pct,
        "rel_perf_30d": rel_perf,
        "all_prices": all_prices,
    }
    return summary

if __name__ == "__main__":
    result = ta_market()
    import pprint; pprint.pprint(result)


