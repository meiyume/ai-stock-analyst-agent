# agents/agent1_sector.py

from agents.agent1_stock import analyze as analyze_stock

def analyze(peer_tickers: list, horizon: str = "7 Days"):
    if not peer_tickers:
        return {
            "agent": "1.1",
            "summary": "No sector peers provided."
        }

    summaries = []
    bullish, bearish = 0, 0

    for peer in peer_tickers:
        summary, _ = analyze_stock(peer, horizon)
        summaries.append(summary)

        if summary["sma_trend"].lower() == "bullish":
            bullish += 1
        elif summary["sma_trend"].lower() == "bearish":
            bearish += 1

    if bullish > bearish:
        trend = "Bullish"
    elif bearish > bullish:
        trend = "Bearish"
    else:
        trend = "Neutral"

    return {
        "agent": "1.1",
        "tickers": peer_tickers,
        "summary": f"{trend} sector outlook (Bullish: {bullish}, Bearish: {bearish})",
        "details": summaries
    }

