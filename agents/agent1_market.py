# agents/agent1_market.py

from agents.agent1_stock import analyze as analyze_stock

def analyze(index_ticker: str, horizon: str = "7 Days"):
    try:
        summary, _ = analyze_stock(index_ticker, horizon)
        if summary["sma_trend"] == "N/A":
            return {
                "agent": "1.2",
                "target": index_ticker,
                "summary": f"⚠️ No market data available for {index_ticker}.",
                "details": summary
            }

        return {
            "agent": "1.2",
            "target": index_ticker,
            "summary": f"Market index {index_ticker}: {summary['summary']}",
            "details": summary
        }

    except Exception as e:
        return {
            "agent": "1.2",
            "target": index_ticker,
            "summary": f"⚠️ Error analyzing market index {index_ticker}:_
