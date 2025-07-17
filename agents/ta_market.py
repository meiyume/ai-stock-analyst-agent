import yfinance as yf
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os

def trend_to_score(trend):
    if trend == "Uptrend":
        return 1.0
    elif trend == "Downtrend":
        return 0.0
    else:
        return 0.5

def compute_risk_regime(context):
    equities = np.mean([context.get("Straits Times Index", 0), context.get("MSCI Singapore ETF", 0),
                        context.get("MSCI Asia ex Japan ETF", 0), context.get("Hang Seng Index", 0)])
    gold = context.get("Gold", 0)
    usd = context.get("US Dollar Index", 0)
    if equities > 0.5 and gold < 0 and usd < 0:
        return ("Risk-On", "Asia/SGX equities rising, gold and USD falling—risk assets favored.", 1.0)
    elif equities < 0.3 and gold > 0 and usd > 0:
        return ("Risk-Off", "Asia/SGX equities falling, gold and USD rising—risk-off, safety sought.", 0.0)
    else:
        return ("Neutral", "Mixed market signals. No clear regional regime.", 0.5)

def get_anomaly_alerts(context):
    alerts = []
    if context.get("Straits Times Index", 0) > 0.5 and context.get("Gold", 0) > 0:
        alerts.append("⚠️ STI and Gold both rising — Possible flight to safety within a risk-on rally.")
    if context.get("Hang Seng Index", 0) < 0 and context.get("Brent Oil", 0) < 0:
        alerts.append("⚠️ Hang Seng and Oil both falling — Synchronous de-risking in Asia and commodities.")
    if context.get("MSCI Singapore ETF", 0) > 1 and context.get("US Dollar Index", 0) > 0.2:
        alerts.append("⚠️ Singapore equities AND USD both rising — Watch for capital rotation or regional stress.")
    return alerts

def cross_asset_correlation(prices_df, cols=None, lookback=60):
    if cols is None:
        cols = prices_df.columns
    recent_df = prices_df[cols].tail(lookback)
    return recent_df.pct_change().corr()

def get_market_baskets():
    return {
        "Straits Times Index": "^STI",
        "MSCI Singapore ETF": "EWS",
        "FTSE ASEAN 40 (SGX)": "QL1.SI",
        "Hang Seng Index": "^HSI",
        "MSCI Asia ex Japan ETF": "AAXJ",
        "MSCI Emerging Asia ETF": "EEMA",
        "Nikkei 225": "^N225",
        "MSCI China ETF": "MCHI",
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

def load_composite_history(history_file="market_composite_score_history.csv"):
    if not os.path.exists(history_file):
        return None
    try:
        df = pd.read_csv(history_file, parse_dates=["date"])
        df = df.dropna(subset=["date", "composite_score"])
        df["composite_score"] = df["composite_score"].apply(safe_float)
        df["composite_label"] = df["composite_label"].fillna("Neutral")
        return df
    except Exception as e:
        print(f"Error loading {history_file}: {e}")
        return None

def ta_market(lookbacks=[30, 90, 200]):
    baskets = get_market_baskets()
    today = datetime.today()
    start = today - timedelta(days=450)
    out = {}
    all_prices = {}
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

            sma20 = compute_sma(close, 20)
            sma50 = compute_sma(close, 50)
            sma200 = compute_sma(close, 200)
            rsi = compute_rsi(close, 14)
            macd, macd_sig = compute_macd(close)
            vol_30d = close.rolling(30).std()
            vol_90d = close.rolling(90).std()
            vol_z = compute_zscore(vol_30d, 90)

            high_30d = close.rolling(30).max()
            low_30d = close.rolling(30).min()
            high_90d = close.rolling(90).max()
            low_90d = close.rolling(90).min()
            high_200d = close.rolling(200).max()
            low_200d = close.rolling(200).min()

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
                        trend = trend_to_score(change)
                        subset = close[-lb:]
                        vol = safe_float(subset.std(), precision=3) if subset.notnull().sum() > 1 else None
                    signals[f"change_{lb}d_pct"] = safe_float(change)
                    if change is not None and not np.isnan(change):
                        if change > 2:
                            trend_lbl = "Uptrend"
                        elif change < -2:
                            trend_lbl = "Downtrend"
                        else:
                            trend_lbl = "Sideways"
                    else:
                        trend_lbl = "N/A"
                    signals[f"trend_{lb}d"] = trend_lbl
                    signals[f"vol_{lb}d"] = vol
                else:
                    signals[f"change_{lb}d_pct"] = None
                    signals[f"trend_{lb}d"] = "N/A"
                    signals[f"vol_{lb}d"] = None

            curr = safe_float(close.iloc[-1])
            curr_sma50 = safe_float(sma50.iloc[-1])
            curr_sma200 = safe_float(sma200.iloc[-1])
            signals["sma50_status"] = "Above" if curr and curr_sma50 and curr > curr_sma50 else "Below"
            signals["sma200_status"] = "Above" if curr and curr_sma200 and curr > curr_sma200 else "Below"
            curr_rsi = safe_float(rsi.iloc[-1])
            signals["rsi"] = curr_rsi
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
            curr_volz = safe_float(vol_z.iloc[-1])
            signals["vol_zscore"] = curr_volz
            is_newhigh_30d = (abs(curr - safe_float(high_30d.iloc[-1])) < 1e-3) if curr and len(high_30d) else False
            is_newlow_30d = (abs(curr - safe_float(low_30d.iloc[-1])) < 1e-3) if curr and len(low_30d) else False
            is_newhigh_90d = (abs(curr - safe_float(high_90d.iloc[-1])) < 1e-3) if curr and len(high_90d) else False
            is_newlow_90d = (abs(curr - safe_float(low_90d.iloc[-1])) < 1e-3) if curr and len(low_90d) else False
            is_newhigh_200d = (abs(curr - safe_float(high_200d.iloc[-1])) < 1e-3) if curr and len(high_200d) else False
            is_newlow_200d = (abs(curr - safe_float(low_200d.iloc[-1])) < 1e-3) if curr and len(low_200d) else False
            signals["newhigh_30d"] = is_newhigh_30d
            signals["newlow_30d"] = is_newlow_30d
            signals["newhigh_90d"] = is_newhigh_90d
            signals["newlow_90d"] = is_newlow_90d
            signals["newhigh_200d"] = is_newhigh_200d
            signals["newlow_200d"] = is_newlow_200d
            signals["last"] = curr

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
            if alerts:
                alert_msgs.append(f"{name}: {', '.join(alerts)}")

            out[name] = signals

        except Exception as e:
            out[name] = {"error": f"{type(e).__name__}: {e}"}

    # --- Breadth
    breadth = {}
    total_baskets = len([v for v in out.values() if "last" in v])
    n_sma50 = sum(1 for v in out.values() if v.get("sma50_status") == "Above")
    n_sma200 = sum(1 for v in out.values() if v.get("sma200_status") == "Above")
    n_uptrend = sum(1 for v in out.values() if v.get("trend_30d") == "Uptrend")
    n_newhigh_30d = sum(1 for v in out.values() if v.get("newhigh_30d"))
    n_newlow_30d = sum(1 for v in out.values() if v.get("newlow_30d"))
    breadth["pct_above_sma50"] = int(100 * n_sma50 / total_baskets) if total_baskets else None
    breadth["pct_above_sma200"] = int(100 * n_sma200 / total_baskets) if total_baskets else None
    breadth["pct_uptrend_30d"] = int(100 * n_uptrend / total_baskets) if total_baskets else None
    breadth["pct_newhigh_30d"] = int(100 * n_newhigh_30d / total_baskets) if total_baskets else None
    breadth["pct_newlow_30d"] = int(100 * n_newlow_30d / total_baskets) if total_baskets else None

    # --- Relative performance (vs S&P 500)
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

    # --- Cross-asset correlation matrix (last 60 days)
    key_assets = [
        "Straits Times Index", "MSCI Singapore ETF", "Hang Seng Index",
        "MSCI Asia ex Japan ETF", "S&P 500", "US Dollar Index", "Gold", "Brent Oil"
    ]
    prices_df = pd.DataFrame({k: all_prices[k] for k in key_assets if k in all_prices})
    correlation_matrix = None
    if not prices_df.empty and prices_df.shape[1] > 1:
        correlation_matrix = cross_asset_correlation(prices_df, cols=prices_df.columns, lookback=60)
        correlation_matrix = correlation_matrix.round(2)

    # --- Composite score ---
    score_components = []
    if breadth.get("pct_uptrend_30d") is not None:
        score_components.append(breadth["pct_uptrend_30d"] / 100)
    if breadth.get("pct_above_sma50") is not None:
        score_components.append(breadth["pct_above_sma50"] / 100)
    if breadth.get("pct_above_sma200") is not None:
        score_components.append(breadth["pct_above_sma200"] / 100)
    if breadth.get("pct_newhigh_30d") is not None:
        score_components.append(breadth["pct_newhigh_30d"] / 100)
    if breadth.get("pct_newlow_30d") is not None:
        score_components.append(1 - (breadth["pct_newlow_30d"] / 100))
    vol_penalty = 0
    for v in out.values():
        if v.get("vol_zscore", 0) and v.get("vol_zscore") > 2:
            vol_penalty += 0.05
    composite_score = np.nanmean(score_components) - vol_penalty
    composite_score = max(0, min(1, composite_score))
    if composite_score >= 0.7:
        composite_label = "Bullish"
    elif composite_score <= 0.3:
        composite_label = "Bearish"
    else:
        composite_label = "Neutral"

    def get_pct_change(name, days=1):
        series = all_prices.get(name, None)
        if series is not None and len(series) > days:
            try:
                return ((series.iloc[-1] - series.iloc[-1 - days]) / series.iloc[-1 - days]) * 100
            except Exception:
                return 0.0
        return 0.0
    context = {
        "Straits Times Index": get_pct_change("Straits Times Index"),
        "MSCI Singapore ETF": get_pct_change("MSCI Singapore ETF"),
        "Hang Seng Index": get_pct_change("Hang Seng Index"),
        "MSCI Asia ex Japan ETF": get_pct_change("MSCI Asia ex Japan ETF"),
        "Gold": get_pct_change("Gold"),
        "US Dollar Index": get_pct_change("US Dollar Index"),
        "Brent Oil": get_pct_change("Brent Oil"),
    }
    risk_regime, risk_regime_rationale, risk_regime_score = compute_risk_regime(context)
    anomaly_alerts = get_anomaly_alerts(context)

    # --- Load historical composite score for charting ---
    composite_score_history = load_composite_history("market_composite_score_history.csv")

    # --- Summary dict ---
    summary = {
        "as_of": today.strftime("%Y-%m-%d"),
        "out": out,
        "breadth": breadth,
        "rel_perf_30d": rel_perf,
        "all_prices": all_prices,
        "alerts": alert_msgs,
        "composite_score": round(composite_score, 2),
        "composite_label": composite_label,
        "risk_regime": risk_regime,
        "risk_regime_rationale": risk_regime_rationale,
        "risk_regime_score": risk_regime_score,
        "anomaly_alerts": anomaly_alerts,
        "correlation_matrix": correlation_matrix.to_dict() if correlation_matrix is not None else None
    }
    return summary

if __name__ == "__main__":
    result = ta_market()
    import pprint; pprint.pprint(result)






