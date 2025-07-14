from agents.agent1_stock import analyze as analyze_stock

def analyze(index_tickers: list, horizon: str = "7 Days"):
    if not index_tickers:
        return {
            "agent": "1.2",
            "summary": "No market indices provided."
        }

    summaries = []
    bullish, bearish = 0, 0

    for idx in index_tickers:
        try:
            summary, _ = analyze_stock(idx, horizon)
            if summary["sma_trend"] == "N/A":
                continue
            summaries.append(summary)

            if summary["sma_trend"].lower() == "bullish":
                bullish += 1
            elif summary["sma_trend"].lower() == "bearish":
                bearish += 1
        except Exception as e:
            summaries.append({
                "ticker": idx,
                "error": str(e)
            })

    trend = (
        "Bullish" if bullish > bearish else
        "Bearish" if bearish > bullish else
        "Neutral"
    )

    return {
        "agent": "1.2",
        "tickers": index_tickers,
        "summary": f"{trend} market outlook (Bullish: {bullish}, Bearish: {bearish})",
        "details": summaries
    }
