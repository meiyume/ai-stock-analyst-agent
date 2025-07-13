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
        try:
            summary, _ = analyze_stock(peer, horizon)
            if summary["sma_trend"] == "N/A":
                continue
            summaries.append(summary)

            if summary["sma_trend"].lower() == "bullish":
                bullish += 1
            elif summary["sma_trend"].lower() == "bearish":
                bearish += 1
        except Exception as e:
            summaries.append({
                "ticker": peer,
                "error": str(e)
            })

    trend = "Bullish" if bullish > bearish else "Bearish" if bearish > bullish else "Neutral"

    return {
        "agent": "1.1",
        "tickers": peer_tickers,
        "summary": f"{trend} sector outlook (Bullish: {bullish}, Bearish: {bearish})",
        "details": summaries
    }