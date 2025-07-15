import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import llm_utils

def analyze(
    ticker,
    company_name=None,
    horizon="7 Days",
    lookback_days=None,
    api_key=None,
):
    """
    Perform technical analysis on a single stock and return summary dict.
    """
    # --- Data Load ---
    stock = yf.Ticker(ticker)
    hist = stock.history(period="1y", interval="1d")
    if hist.empty:
        return {"error": f"No data for ticker {ticker}"}

    # --- Determine lookback window if not provided ---
    if lookback_days is None:
        if "30" in horizon:
            lookback_days = 90
        elif "7" in horizon:
            lookback_days = 30
        elif "3" in horizon:
            lookback_days = 14
        elif "1" in horizon:
            lookback_days = 5
        else:
            lookback_days = 30
    hist = hist.tail(lookback_days)

    # --- Compute indicators ---
    def sma(series, window):
        return series.rolling(window).mean()

    def rsi(series, window=14):
        delta = series.diff()
        up = delta.clip(lower=0)
        down = -1 * delta.clip(upper=0)
        ma_up = up.rolling(window).mean()
        ma_down = down.rolling(window).mean()
        rs = ma_up / ma_down
        return 100 - (100 / (1 + rs))

    def macd(series, fast=12, slow=26, signal=9):
        exp1 = series.ewm(span=fast, adjust=False).mean()
        exp2 = series.ewm(span=slow, adjust=False).mean()
        macd_line = exp1 - exp2
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        hist = macd_line - signal_line
        return macd_line, signal_line, hist

    def bollinger(series, window=20, num_std=2):
        sma_ = sma(series, window)
        std = series.rolling(window).std()
        upper = sma_ + (num_std * std)
        lower = sma_ - (num_std * std)
        return upper, lower

    close = hist["Close"]

    result = {
        "ticker": ticker,
        "company_name": company_name or ticker,
        "as_of": str(hist.index[-1].date()),
        "lookback_days": lookback_days,
        "close_last": float(close.iloc[-1]),
        "sma_7": float(sma(close, 7).iloc[-1]),
        "sma_14": float(sma(close, 14).iloc[-1]),
        "sma_30": float(sma(close, 30).iloc[-1]),
        "rsi_14": float(rsi(close, 14).iloc[-1]),
        "macd": float(macd(close)[0].iloc[-1]),
        "macd_signal": float(macd(close)[1].iloc[-1]),
        "macd_hist": float(macd(close)[2].iloc[-1]),
        "bollinger_upper": float(bollinger(close)[0].iloc[-1]),
        "bollinger_lower": float(bollinger(close)[1].iloc[-1]),
        # Add more indicators as needed
        "raw_history": hist.reset_index().to_dict(orient="list"),
    }

    # --- Compose LLM Summary ---
    try:
        summaries = llm_utils.run_llm(
            agent="stock",
            input=result,
            api_key=api_key,
            horizon=horizon,
        )
        result.update(summaries)
    except Exception as e:
        result["llm_error"] = str(e)

    return result
