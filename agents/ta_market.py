import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def trend_direction(change_pct, threshold=2):
    if pd.isna(change_pct) or change_pct is None:
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

def safe_float(val, default=None, precision=3):
    """Safe float conversion with optional rounding and default fallback."""
    try:
        out = float(val)
        if np.isnan(out):
            return default
        return round(out, precision)
    except Exception:
        return default

def ta_market(lookbacks=[30, 90, 200]):
    baskets = get_market_baskets()
    today = datetime.today()
    start = today - timedelta(days=400)
    out = {}
    all_prices = {}

    for name, ticker in baskets.items():
        try:
            df = yf.download(ticker, start=start, end=today, interval="1d", auto_adjust=True, progress=False)
            # Defensive checks: dataframe type, min rows, 'Close' col
            if not isinstance(df, pd.DataFrame) or len(df) < 10 or "Close" not in df.columns:
                out[name] = {"error": "No data"}
                continue
            close = df["Close"].dropna()
            if isinstance(close, pd.DataFrame):
                close = close.squeeze()
            if close.empty or len(close) < 2:
                out[name] = {"error": "Insufficient close data"}
                continue
            all_prices[name] = close

            signals = {}
            for lb in lookbacks:
                if len(close) >= lb:
                    now = safe_float(close.iloc[-1])
                    then = safe_float(close.iloc[-lb])
                    # Handle missing or zero division
                    if then is None or then == 0:
                        change = np.nan
                        trend = "N/A"
                        vol = None
                    else:
                        change = (now - then) / then * 100 if now is not None else np.nan
                        trend = trend_direction(change)
                        # Defensive: std on enough data and not all same
                        subset = close[-lb:]
                        vol = safe_float(subset.std(), precision=3) if subset.notnull().sum() > 1 else None
                    signals[f"change_{lb}d_pct"] = safe_float(change)
                    signals[f"trend_{lb}d"] = trend
                    signals[f"vol_{lb}d"] = vol
                else:
                    signals[f"change_{lb}d_pct"] = None
                    signals[f"trend_{lb}d"] = "N/A"
                    signals[f"vol_{lb}d"] = None
            # Defensive: last price
            signals["last"] = safe_float(close.iloc[-1])
            out[name] = signals
        except Exception as e:
            out[name] = {"error": f"{type(e).__name__}: {e}"}

    # --- Breadth: % of baskets in uptrend (30d) ---
    uptrend_count = 0
    total_count = 0
    for v in out.values():
        trend = v.get("trend_30d", "N/A")
        if trend == "Uptrend":
            uptrend_count += 1
        if "trend_30d" in v and trend != "N/A":
            total_count += 1
    breadth_30d_pct = int(100 * uptrend_count / total_count) if total_count else None

    # --- Relative rotation (vs S&P 500 or SPY) ---
    rel_perf = {}
    spy_close = all_prices.get("S&P 500", None)
    for name, series in all_prices.items():
        try:
            # Defensive checks
            if spy_close is None or len(series) < 30 or len(spy_close) < 30:
                continue
            series_now = safe_float(series.iloc[-1])
            series_then = safe_float(series.iloc[-30])
            spy_now = safe_float(spy_close.iloc[-1])
            spy_then = safe_float(spy_close.iloc[-30])
            if None in [series_now, series_then, spy_now, spy_then] or series_then == 0 or spy_then == 0:
                continue
            rel = ((series_now - series_then) / series_then) - ((spy_now - spy_then) / spy_then)
            rel_perf[name] = round(rel * 100, 2)
        except Exception:
            continue

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



