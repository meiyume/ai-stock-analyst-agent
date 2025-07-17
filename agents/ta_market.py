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
        # --- SGX/Asia/ASEAN focused ---
        "Straits Times Index": "^STI",
        "MSCI Singapore ETF": "EWS",
        "FTSE ASEAN 40 (SGX)": "QL1.SI",
        "Hang Seng Index": "^HSI",
        "MSCI Asia ex Japan ETF": "AAXJ",
        "MSCI Emerging Asia ETF": "EEMA",
        "Nikkei 225": "^N225",
        "MSCI China ETF": "MCHI",
        # --- Global/US context ---
        "MSCI World ETF": "URTH",
        "S&P 500": "^GSPC",
        "Nasdaq 100": "^NDX",
        "US Dollar Index": "DX-Y.NYB",
        "Gold": "GC=F",
        "Brent Oil": "BZ=F",
    }

def safe_float(val, default=None, precision=3):
    try:
        out = float(val)
        if np.isnan(out):
            return default
        return round(out, precision)
    except Exception:
        return default

def compute_sma(series, window):
    return series.rolling(window=window, min_periods=1).mean()

def compute_rsi(series, window=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    ma_up = up.rolling(window, min_periods=1).mean()
    ma_down = down.rolling(window, min_periods=1).mean()
    rs = ma_up / ma_down.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi

def compute_macd(series, span1=12, span2=26, signal=9):
    ema1 = series.ewm(span=span1, adjust=False).mean()
    ema2 = series.ewm(span=span2, adjust=False).mean()
    macd = ema1 - ema2
    macd_signal = macd.ewm(span=signal, adjust=False).mean()
    return macd, macd_signal

def compute_zscore(series, window=90):
    mean = series.rolling(window, min_periods=1).mean()
    std = series.rolling(window, min_periods=1).std()
    zscore = (series - mean) / std.replace(0, np.nan)
    return zscore

def ta_market(lookbacks=[30, 90, 200]):
    baskets = get_market_baskets()
    today = datetime.today()
    start = today - timedelta(days=450)
    out = {}
    all_prices = {}
    all_highs = {}
    all_lows = {}
    alert_msgs = []

    for name, ticker in baskets.items():
        try:
            df = yf.download(ticker, start=start, end=today, interval="1d", auto_adjust=True, progress=False)
            if not isinstance(df, pd.DataFrame) or len(df) < 20 or "Close" not in df.columns:
                out[name] = {"error": "No data"}
                continue
            close = df["Close"].dropna()
            if isinstance(close, pd.DataFrame):
                close = close.squeeze()
            if close.empty or len(close) < 20:
                out[name] = {"error": "Insufficient close data"}
                continue
            all_prices[name] = close

            # --- Indicators ---
            sma20 = compute_sma(close, 20)
            sma50 = compute_sma(close, 50)
            sma200 = compute_sma(close, 200)
            rsi = compute_rsi(close, 14)
            macd, macd_sig = compute_macd(close)
            vol_30d = close.rolling(30).std()
            vol_90d = close.rolling(90).std()
            vol_z = compute_zscore(vol_30d, 90)

            # --- New highs/lows ---
            high_30d = close.rolling(30).max()
            low_30d = close.rolling(30).min()
            high_90d = close.rolling(90).max()
            low_90d = close.rolling(90).min()
            high_200d = close.rolling(200).max()
            low_200d = close.rolling(200).min()
            all_highs[name] = {"30d": high_30d, "90d": high_90d, "200d": high_200d}
            all_lows[name] = {"30d": low_30d, "90d": low_90d, "200d": low_200d}

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

            # --- SMA status ---
            curr = safe_float(close.iloc[-1])
            curr_sma50 = safe_float(sma50.iloc[-1])
            curr_sma200 = safe_float(sma200.iloc[-1])
            signals["sma50_status"] = "Above" if curr and curr_sma50 and curr > curr_sma50 else "Below"
            signals["sma200_status"] = "Above" if curr and curr_sma200 and curr > curr_sma200 else "Below"

            # --- RSI (last) ---
            curr_rsi = safe_float(rsi.iloc[-1])
            signals["rsi"] = curr_rsi

            # --- MACD / Signal ---
            curr_macd = safe_float(macd.iloc[-1])
            curr_macd_sig = safe_float(macd_sig.iloc[-1])
            signals["macd"] = curr_macd
            signals["macd_signal"] = curr_macd_sig
            if curr_macd is not None and curr_macd_sig is not None:
                if abs(curr_macd - curr_macd_sig) < 0.05:
                    signals["macd_cross"] = "Crossover"
                else:
                    signals["macd_cross"] = "No"
            else:
                signals["macd_cross"] = "N/A"

            # --- Volatility regime (z-score, last) ---
            curr_volz = safe_float(vol_z.iloc[-1])
            signals["vol_zscore"] = curr_volz

            # --- New high/low status ---
            is_newhigh_30d = (abs(curr - safe_float(high_30d.iloc[-1])) < 1e-3) if curr and len(high_30d) else False
            is_newlow_30d = (abs(curr - safe_float(low_30d.iloc[-1])) < 1e-3) if curr and len(low_30d) else False
            signals["newhigh_30d"] = is_newhigh_30d
            signals["newlow_30d"] = is_newlow_30d

            is_newhigh_90d = (abs(curr - safe_float(high_90d.iloc[-1])) < 1e-3) if curr and len(high_90d) else False
            is_newlow_90d = (abs(curr - safe_float(low_90d.iloc[-1])) < 1e-3) if curr and len(low_90d) else False
            signals["newhigh_90d"] = is_newhigh_90d
            signals["newlow_90d"] = is_newlow_90d

            is_newhigh_200d = (abs(curr - safe_float(high_200d.iloc[-1])) < 1e-3) if curr and len(high_200d) else False
            is_newlow_200d = (abs(curr - safe_float(low_200d.iloc[-1])) < 1e-3) if curr and len(low_200d) else False
            signals["newhigh_200d"] = is_newhigh_200d
            signals["newlow_200d"] = is_newlow_200d

            # --- Last price ---
            signals["last"] = curr

            # --- Alerts (overbought, oversold, high vol, macd cross, new highs/lows) ---
            alerts = []
            if curr_rsi is not None:
                if curr_rsi > 70:
                    alerts.append("Overbought (RSI>70)")
                elif curr_rsi < 30:
                    alerts.append("Oversold (RSI<30)")
            if curr_volz is not None and curr_volz > 2:
                alerts.append("Volatility Spike")
            if signals.get("macd_cross") == "Crossover":
                alerts.append("MACD Cross")
            if is_newhigh_30d or is_newhigh_90d or is_newhigh_200d:
                alerts.append("New High")
            if is_newlow_30d or is_newlow_90d or is_newlow_200d:
                alerts.append("New Low")
            signals["alerts"] = ", ".join(alerts) if alerts else None

            out[name] = signals

            # --- Add basket-level alert msg ---
            if alerts:
                alert_msgs.append(f"{name}: {', '.join(alerts)}")

        except Exception as e:
            out[name] = {"error": f"{type(e).__name__}: {e}"}

    # --- Breadth: % baskets above SMA50/200, in uptrend, at new highs ---
    breadth = {}
    total_baskets = len([v for v in out.values() if "last" in v])
    # % Above SMA50
    n_sma50 = sum(1 for v in out.values() if v.get("sma50_status") == "Above")
    breadth["pct_above_sma50"] = int(100 * n_sma50 / total_baskets) if total_baskets else None
    # % Above SMA200
    n_sma200 = sum(1 for v in out.values() if v.get("sma200_status") == "Above")
    breadth["pct_above_sma200"] = int(100 * n_sma200 / total_baskets) if total_baskets else None
    # % Uptrend (30d)
    n_uptrend = sum(1 for v in out.values() if v.get("trend_30d") == "Uptrend")
    breadth["pct_uptrend_30d"] = int(100 * n_uptrend / total_baskets) if total_baskets else None
    # % New 30d highs
    n_newhigh_30d = sum(1 for v in out.values() if v.get("newhigh_30d"))
    breadth["pct_newhigh_30d"] = int(100 * n_newhigh_30d / total_baskets) if total_baskets else None
    # % New 30d lows
    n_newlow_30d = sum(1 for v in out.values() if v.get("newlow_30d"))
    breadth["pct_newlow_30d"] = int(100 * n_newlow_30d / total_baskets) if total_baskets else None

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
        "breadth": breadth,
        "rel_perf_30d": rel_perf,
        "all_prices": all_prices,
        "alerts": alert_msgs,
    }
    return summary

if __name__ == "__main__":
    result = ta_market()
    import pprint; pprint.pprint(result)





