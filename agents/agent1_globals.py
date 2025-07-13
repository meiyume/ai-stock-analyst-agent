# agents/agent1_globals.py

from agents.agent1_stock import analyze as analyze_stock

def analyze(global_index_tickers: list, horizon: str = "7 Days"):
    if not global_index_tickers:
        return {
            "agent": "1.4",
            "summary": "No global indices provided."
        }

    summaries = []
    bullish, bearish = 0, 0

    for idx in global_index_tickers:
        summary, _ = analyze_stock(idx, horizon)
        summaries.append(summary)

        if summary["sma_trend"].lower() == "bullish":
            bullish += 1
        elif summary["sma_trend"].lower() == "bearish":
            bearish += 1

    if bullish > bearish:
        trend = "Positive global macro outlook"
    elif bearish > bullish:
        trend = "Negative global macro outlook"
    else:
        trend = "Neutral global macro outlook"

    return {
        "agent": "1.4",
        "tickers": global_index_tickers,
        "summary": f"{trend} (Bullish: {bullish}, Bearish: {bearish})",
        "details": summaries
    }

