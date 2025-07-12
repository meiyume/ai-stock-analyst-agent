# agents/agent1_market.py

from agents.agent1_stock import analyze as analyze_stock

# === Default index mapping per stock ===
MARKET_INDEX_MAP = {
    "U11.SI": "^STI",
    # Add more stock-to-index mappings if needed
}

def analyze(ticker: str, horizon: str = "7 Days"):
    index_ticker = MARKET_INDEX_MAP.get(ticker, "^STI")

    try:
        summary, _ = analyze_stock(index_ticker, horizon)

        # Interpret market-wide signal
        signal = summary["sma_trend"]
        rsi = summary["rsi"]
        macd = summary["macd"]

        market_summary = (
            f"Market Index: {index_ticker}. "
            f"Trend: **{signal}**, RSI: {rsi}, MACD: {macd}. "
            f"Short-term momentum is {signal.lower()} with RSI indicating {rsi.lower()}."
        )

        return {
            "agent": "1.2",
            "target": index_ticker,
            "summary": market_summary,
            "details": summary
        }

    except Exception as e:
        return {
            "agent": "1.2",
            "summary": f"Failed to analyze index {index_ticker}: {str(e)}"
        }
