import yfinance as yf
import numpy as np
import pandas as pd
import os
import csv
from datetime import datetime, timedelta

def trend_to_score(trend):
    if trend == "Uptrend":
        return 1.0
    elif trend == "Downtrend":
        return 0.0
    else:
        return 0.5

def compute_risk_regime(context):
    """
    Determines 'Risk-On', 'Risk-Off', or 'Neutral' regime from global asset moves.
    """
    equities = np.mean([
        context.get("S&P500", 0),
        context.get("Nasdaq", 0)
    ])
    bonds = context.get("US10Y", 0)
    vix = context.get("VIX", 0)
    dxy = context.get("DXY", 0)
    gold = context.get("Gold", 0)
    # Rule-based logic—customize as needed!
    if equities > 0 and bonds < 0 and vix < 0 and dxy < 0:
        return ("Bullish", "Equities rising, bonds/vix/dxy falling—risk assets favored.", 1.0)
    elif equities < 0 and bonds > 0 and vix > 0 and dxy > 0:
        return ("Bearish", "Equities falling, bonds/vix/dxy rising—risk-off, safety sought.", 0.0)
    else:
        return ("Neutral", "Mixed cross-asset signals. Market regime unclear.", 0.5)

def get_anomaly_alerts(context):
    """
    Flags unusual or contradictory asset moves.
    """
    alerts = []
    # Equities up + VIX up: rare, often signals stress regime
    if context.get("S&P500", 0) > 0 and context.get("VIX", 0) > 0:
        alerts.append("⚠️ Equities and VIX both rising — Market may be entering a stress regime!")
    if context.get("S&P500", 0) < 0 and context.get("Gold", 0) < 0:
        alerts.append("⚠️ Both Equities and Gold falling — Synchronous de-risking.")
    if context.get("Nasdaq", 0) > 1 and context.get("US10Y", 0) > 0.2:
        alerts.append("⚠️ Tech stocks AND bond yields rising — 'good' growth, but monitor for inflation/rotation risk.")
    # Add more rules as you discover useful patterns!
    return alerts

def cross_asset_correlation(prices_df, cols=None, lookback=60):
    """
    Returns a correlation DataFrame for selected assets over lookback window.
    """
    if cols is None:
        cols = prices_df.columns
    recent_df = prices_df[cols].tail(lookback)
    return recent_df.pct_change().corr()

def ta_global():
    indices = {
        # Major equity indices
        "S&P500": "^GSPC",
        "Nasdaq": "^IXIC",
        "EuroStoxx50": "^STOXX50E",
        "Nikkei": "^N225",
        "HangSeng": "^HSI",
        "FTSE100": "^FTSE",
        "DJIA": "^DJI",
        "STI": "^STI",
        # Volatility indices
        "VIX": "^VIX",
        "V2X": "^V2TX",
        "MOVE": "^MOVE",
        # FX rates
        "DXY": "DX-Y.NYB",
        "USD_SGD": "USDSGD=X",
        "USD_JPY": "JPY=X",
        "EUR_USD": "EURUSD=X",
        "USD_CNH": "USDCNH=X",
        "GBP_USD": "GBPUSD=X",
        "AUD_USD": "AUDUSD=X",
        "USD_KRW": "KRW=X",
        "USD_HKD": "HKD=X",
        # Bond yields
        "US10Y": "^TNX",
        "US2Y": "^IRX",
        "DE10Y": "^DE10Y",
        "JP10Y": "^JP10Y",
        "SG10Y": "^SG10Y",
        # Commodities
        "Gold": "GC=F",
        "Silver": "SI=F",
        "Oil_Brent": "BZ=F",
        "Oil_WTI": "CL=F",
        "Copper": "HG=F",
        "NatGas": "NG=F",
        "Corn": "ZC=F",
        "Wheat": "ZW=F",
    }
    asset_classes = {
        # ... (unchanged, see your original)
        "S&P500": "Index", "Nasdaq": "Index", "EuroStoxx50": "Index", "Nikkei": "Index", "HangSeng": "Index", "FTSE100": "Index", "DJIA": "Index", "STI": "Index",
        "VIX": "Volatility", "V2X": "Volatility", "MOVE": "Volatility",
        "DXY": "FX", "USD_SGD": "FX", "USD_JPY": "FX", "EUR_USD": "FX", "USD_CNH": "FX", "GBP_USD": "FX", "AUD_USD": "FX", "USD_KRW": "FX", "USD_HKD": "FX",
        "US10Y": "Bond", "US2Y": "Bond", "DE10Y": "Bond", "JP10Y": "Bond", "SG10Y": "Bond",
        "Gold": "Commodity", "Silver": "Commodity", "Oil_Brent": "Commodity", "Oil_WTI": "Commodity", "Copper": "Commodity", "NatGas": "Commodity", "Corn": "Commodity", "Wheat": "Commodity",
    }
    lookbacks = [30, 90, 200]
    out = {}
    today = datetime.today()
    start = today - timedelta(days=400)
    # For correlation, store all price series (Close) here
    all_prices = {}

    for name, symbol in indices.items():
        try:
            df = yf.download(symbol, start=start, end=today, interval="1d", auto_adjust=True, progress=False)
            if df is None or len(df) < 10 or "Close" not in df:
                out[name] = {"error": "No data", "class": asset_classes.get(name, "Other")}
                continue
            close = df["Close"].dropna()
            if isinstance(close, pd.DataFrame):
                close = close.squeeze()
            all_prices[name] = close  # For correlation matrix
            trends = {}
            for lb in lookbacks:
                if len(close) >= lb:
                    val_now = close.iloc[-1]
                    val_then = close.iloc[-lb]
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
            try:
                trends["last"] = float(np.round(close.iloc[-1], 4)) if len(close) > 0 else None
            except Exception:
                trends["last"] = None
            trends["class"] = asset_classes.get(name, "Other")
            out[name] = trends
        except Exception as e:
            out[name] = {"error": str(e), "class": asset_classes.get(name, "Other")}

    # --- Breadth: % indices above 50d/200d MA
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

    # --- Cross-asset daily % changes for regime and anomaly logic ---
    def get_pct_change(key, days=1):
        series = all_prices.get(key, None)
        if series is not None and len(series) > days:
            try:
                return ((series.iloc[-1] - series.iloc[-1 - days]) / series.iloc[-1 - days]) * 100
            except Exception:
                return 0.0
        return 0.0

    context = {
        "S&P500": get_pct_change("S&P500"),
        "Nasdaq": get_pct_change("Nasdaq"),
        "US10Y": get_pct_change("US10Y"),
        "VIX": get_pct_change("VIX"),
        "DXY": get_pct_change("DXY"),
        "Gold": get_pct_change("Gold"),
    }

    # --- Risk regime (modular, robust) ---
    risk_regime, risk_regime_rationale, risk_regime_score = compute_risk_regime(context)

    # --- Smart anomaly alerts ---
    anomaly_alerts = get_anomaly_alerts(context)

    # --- Cross-asset correlation heatmap (last 60 days, major assets) ---
    major_assets = ["S&P500", "Nasdaq", "US10Y", "VIX", "DXY", "Gold", "Oil_Brent", "Copper"]
    prices_df = pd.DataFrame({k: all_prices[k] for k in major_assets if k in all_prices})
    correlation_matrix = None
    if not prices_df.empty and prices_df.shape[1] > 1:
        correlation_matrix = cross_asset_correlation(prices_df, cols=prices_df.columns, lookback=60)
        correlation_matrix = correlation_matrix.round(2)

    # --- Composite Score (unchanged) ---
    def get_trend(lb, k):
        t = out.get(k, {}).get(f"trend_{lb}d", "N/A")
        return trend_to_score(t)

    indices_for_score = ["S&P500", "Nasdaq", "EuroStoxx50", "Nikkei", "HangSeng", "FTSE100"]
    trend_scores = [get_trend(30, k) for k in indices_for_score]
    vix_last = out.get("VIX", {}).get("last", None)
    vix_score = 1 - min(vix_last / 40, 1) if vix_last is not None and vix_last >= 0 else 0.5
    breadth_50 = breadth.get("breadth_above_50dma_pct", 50) / 100 if breadth.get("breadth_above_50dma_pct") is not None else 0.5
    breadth_200 = breadth.get("breadth_above_200dma_pct", 50) / 100 if breadth.get("breadth_above_200dma_pct") is not None else 0.5

    composite_inputs = trend_scores + [vix_score, breadth_50, breadth_200]
    composite_score = float(np.round(np.nanmean(composite_inputs), 3)) if np.any(pd.notnull(composite_inputs)) else 0.5
    composite_label = (
        "Bullish" if composite_score >= 0.7
        else "Bearish" if composite_score <= 0.3
        else "Neutral"
    )

    # --- Persist composite score history to CSV ---
    history_file = "composite_score_history.csv"
    today_str = today.strftime("%Y-%m-%d")
    write_row = True
    if os.path.exists(history_file):
        with open(history_file, "r") as f:
            lines = f.readlines()
            last = lines[-1] if lines else ""
            if last and last.startswith(today_str):
                write_row = False
    if write_row:
        with open(history_file, "a", newline="") as f:
            writer = csv.writer(f)
            if os.stat(history_file).st_size == 0:
                writer.writerow(["date", "composite_score", "composite_label", "risk_regime"])
            writer.writerow([
                today_str,
                composite_score if composite_score is not None else "",
                composite_label if composite_label else "",
                risk_regime if risk_regime else "",
            ])

    # --- Summary dict ---
    summary = {
        "as_of": today.strftime("%Y-%m-%d"),
        "lookbacks": lookbacks,
        "out": out,
        "breadth": breadth,
        "risk_regime": risk_regime,
        "risk_regime_rationale": risk_regime_rationale,
        "risk_regime_score": risk_regime_score,
        "composite_score": composite_score,
        "composite_label": composite_label,
        "anomaly_alerts": anomaly_alerts,
        "correlation_matrix": correlation_matrix.to_dict() if correlation_matrix is not None else None,
        "news": "No news data yet. (Reserved for future global/regional/local news agent summary.)"
    }
    return summary

if __name__ == "__main__":
    result = ta_global()
    import pprint; pprint.pprint(result)





