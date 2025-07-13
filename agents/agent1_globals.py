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
        "Positive global macro outlook" if bullish > bearish else
        "Negative global macro outlook" if bearish > bullish else
        "Neutral global macro outlook"
    )

    return {
        "agent": "1.4",
        "tickers": global_index_tickers,
        "summary": f"{trend} (Bullish: {bullish}, Bearish: {bearish})",
        "details": summaries
    }