from agents.agent1_stock import analyze as analyze_stock

def analyze(commodity_tickers: list, horizon: str = "7 Days"):
    if not commodity_tickers:
        return {
            "agent": "1.3",
            "summary": "No commodities provided."
        }

    summaries = []
    rising, falling = 0, 0

    for com in commodity_tickers:
        try:
            summary, _ = analyze_stock(com, horizon)
            if summary["sma_trend"] == "N/A":
                continue
            summaries.append(summary)

            if summary["sma_trend"].lower() == "bullish":
                rising += 1
            elif summary["sma_trend"].lower() == "bearish":
                falling += 1
        except Exception as e:
            summaries.append({
                "ticker": com,
                "error": str(e)
            })

    effect = (
        "Negative impact (rising commodity prices)" if rising > falling else
        "Positive impact (falling commodity prices)" if falling > rising else
        "Neutral impact"
    )

    return {
        "agent": "1.3",
        "tickers": commodity_tickers,
        "summary": f"{effect}. (Bullish: {rising}, Bearish: {falling})",
        "details": summaries
    }