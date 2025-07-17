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
    return {
        # --- SGX/Singapore/ASEAN/Asia Focused ---
        "Straits Times Index": "^STI",         # SGX main
        "MSCI Singapore ETF": "EWS",           # US-listed, tracks Singapore
        "FTSE ASEAN 40 (SGX)": "QL1.SI",       # ASEAN regional, SGX-listed
        "Hang Seng Index": "^HSI",             # Hong Kong
        "MSCI Asia ex Japan ETF": "AAXJ",      # Asia ex Japan
        "MSCI Emerging Asia ETF": "EEMA",      # EM Asia
        "Nikkei 225": "^N225",                 # Japan
        "MSCI China ETF": "MCHI",              # China

        # --- Global/US context (for relative rotation etc) ---
        "MSCI World ETF": "URTH",              # Global
        "S&P 500": "^GSPC",                    # US main index
        "Nasdaq 100": "^NDX",                  # US tech
        "US Dollar Index": "DX-Y.NYB",         # Dollar strength
        "Gold": "GC=F",                        # Gold futures
        "Brent Oil": "BZ=F",                   # Brent oil futures
    }

def safe_float(val, default=None, precision=3):
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
                    if then is None or then == 0:
                        change = np.nan
                        trend = "N/A"
                        vol = None
                    else:
                        change = (now - then) / then * 100 if now is not None else np.nan
                        trend = trend_direction(change)
                        subset = close[-lb:]
                        vol = safe_float(subset.std(), precision=3) if subset.notnull().sum() > 1 else None
                    signals[f"change_{lb}d_pct"] = safe_float(change)
                    signals[f"trend_{lb}d"] = trend
                    signals[f"vol_{lb}d"] = vol
                else:
                    signals[f"change_{lb}d_pct"] = None
                    signals[f"trend_{lb}d"] = "N/A"
                    signals[f"vol_{lb}d"] = None
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

    # --- Relative rotation (vs S&P 500 or ^GSPC) ---
    rel_perf = {}
    spx_name = "S&P 500"
    spx_close = all_prices.get(spx_name, None)
    for name, series in all_prices.items():
        try:
            if spx_close is None or len(series) < 30 or len(spx_close) < 30:
                continue
            series_now = safe_float(series.iloc[-1])
            series_then = safe_float(series.iloc[-30])
            spx_now = safe_float(spx_close.iloc[-1])
            spx_then = safe_float(spx_close.iloc[-30])
            if None in [series_now, series_then, spx_now, spx_then] or series_then == 0 or spx_then == 0:
                continue
            rel = ((series_now - series_then) / series_then) - ((spx_now - spx_then) / spx_then)
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




