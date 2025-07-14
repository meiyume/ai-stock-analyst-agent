# agents/agent1_stock.py

import yfinance as yf
import pandas as pd
import numpy as np
from openai import OpenAI

def enforce_date_column(df):
    if 'Date' not in df.columns:
        df = df.reset_index()
        possible = [col for col in df.columns if 'date' in col.lower() or 'time' in col.lower()]
        if possible and possible[0] != 'Date':
            df.rename(columns={possible[0]: 'Date'}, inplace=True)
        elif 'Date' not in df.columns:
            df['Date'] = pd.to_datetime(df.index)
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date').drop_duplicates('Date').reset_index(drop=True)
    return df

# ... [other compute_*, fetch_data, etc. functions unchanged] ...

def analyze(
    ticker: str,
    horizon: str = "7 Days",
    lookback_days: int = 30,
    api_key: str = None
):
    """
    Run full technical, anomaly, risk, and LLM summary analysis for a single stock/index/commodity.
    Returns (summary, df).
    """
    df = fetch_data(ticker, lookback_days=lookback_days)
    df = enforce_date_column(df)
    if df.empty:
        summary = {
            "summary": f"⚠️ No data available for {ticker}.",
            "sma_trend": "N/A",
            "macd_signal": "N/A",
            "bollinger_signal": "N/A",
            "rsi_signal": "N/A",
            "stochastic_signal": "N/A",
            "cmf_signal": "N/A",
            "obv_signal": "N/A",
            "adx_signal": "N/A",
            "atr_signal": "N/A",
            "vol_spike": False,
            "patterns": [],
            "anomaly_events": [],
            "heatmap_signals": {},
            "lookback_days": lookback_days
        }
        # Add empty LLM summary
        summary["llm_summary"] = "No LLM report (no data available)."
        return summary, df

    # === [all indicator and signal calculations unchanged] ===
    # (insert the unchanged calculation code here from your latest version)

    # [ ... all code for technicals, heatmap, composite score, etc. ... ]
    # (for brevity, not repeating all code. Use your current calculations here.)

    # === Composite Risk Score and Final Summary ===
    summary = {
        "summary": f"{sma_trend} SMA, {macd_signal} MACD, {rsi_signal} RSI, {bollinger_signal} Bollinger, "
                   f"{stochastic_signal} Stochastic, {cmf_signal} CMF, {obv_signal} OBV, "
                   f"{adx_signal} ADX, {atr_signal} ATR",
        "sma_trend": sma_trend,
        "macd_signal": macd_signal,
        "bollinger_signal": bollinger_signal,
        "rsi_signal": rsi_signal,
        "stochastic_signal": stochastic_signal,
        "cmf_signal": cmf_signal,
        "obv_signal": obv_signal,
        "adx_signal": adx_signal,
        "atr_signal": atr_signal,
        "vol_spike": vol_spike,
        "patterns": patterns,
        "anomaly_events": anomaly_events,
        "heatmap_signals": heatmap_signals,
        "composite_risk_score": round(risk_score, 2),
        "risk_level": risk_level,
        "lookback_days": lookback_days,
        "horizon": horizon  # For LLM prompt
    }

    # === LLM summary (ALWAYS include, just like other agents) ===
    if api_key:
        try:
            summary["llm_summary"] = get_llm_summary(summary, api_key)
        except Exception as e:
            summary["llm_summary"] = f"LLM error: {e}"
    else:
        summary["llm_summary"] = "No API key provided for LLM summary."

    return summary, df

def run_full_technical_analysis(ticker, horizon, lookback_days=30, api_key=None):
    return analyze(ticker, horizon, lookback_days=lookback_days, api_key=api_key)

def get_llm_summary(signals, api_key):
    client = OpenAI(api_key=api_key)
    prompt = f"""
You are an expert technical analyst for a leading financial institution.

Based on the following technical signals and anomalies, do the following:
- First, write a detailed summary for technical readers (using precise, professional terminology and concise reasoning). For each indicator, explain not just the signal, but also why it matters right now. Connect supporting indicators together (e.g., “Rising OBV + bullish MACD reinforces uptrend…”). Summarize the overall risk or opportunity, and recommend what a technical analyst should watch for in the next few sessions. Include actionable insight or a forward-looking caution. Use a confident, objective tone. 
- Explicitly frame all your conclusions and recommendations in terms of the provided outlook horizon: {signals.get('horizon', 'the next few days')}.
- Then, write a second summary for non-technical readers. Imagine you are explaining it to a grandparent with no finance background:
    - Start your summary with this phrase (customized for the horizon): "If you are looking at this stock outlook over {signals.get('horizon', 'the next few days')}, here’s what you should know:"
    - Avoid technical terms and acronyms unless you give a short, simple explanation.
    - Use analogies and plain language.
    - Give gentle, practical advice for someone considering buying or selling for the chosen outlook horizon ({signals.get('horizon', 'the next few days')}).
    - Clearly mention if things look good for buying, if caution is advised, or if it might be wise to hold off, and explain why in simple terms.
    - Focus on helping the reader make a simple decision for the chosen time frame, but let them decide if they want to buy or sell based on their own needs and comfort.
    - Always explain the risk in plain language.
    - Make it warm, clear, and friendly.
    - Absolutely no jargon!
    - Be sure your advice is specific to the provided outlook horizon.

Here are the signals:
SMA Trend: {signals.get('sma_trend')}
MACD: {signals.get('macd_signal')}
RSI: {signals.get('rsi_signal')}
Bollinger Bands: {signals.get('bollinger_signal')}
Stochastic: {signals.get('stochastic_signal')}
CMF: {signals.get('cmf_signal')}
OBV: {signals.get('obv_signal')}
ADX: {signals.get('adx_signal')}
ATR: {signals.get('atr_signal')}
Volume Spike: {signals.get('vol_spike')}
Candlestick Patterns: {signals.get('patterns')}
Key Anomalies: {signals.get('anomaly_events')}
Outlook Horizon: {signals.get('horizon', 'the next few days')}

Write two clearly separated sections, each starting with a clear title:
- For Technical Readers
- For Grandmas and Grandpas

Do not number or prefix the titles with any numbers or colons.
Just start each section with the title on its own line.
"""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=700,
        temperature=0.6,
    )
    return response.choices[0].message.content.strip()






