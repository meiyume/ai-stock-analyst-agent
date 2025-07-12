# agents/agent1_sector.py

from agents.agent1_stock import analyze as analyze_stock

# === Mapping of stock tickers to sector peers ===
SECTOR_PEERS = {
    "U11.SI": ["C6L.SI"],  # SIA (Singapore Airlines) → SIA Engineering
    # Add more mappings as needed
}

def analyze(ticker: str, horizon: str = "7 Days"):
    peers = SECTOR_PEERS.get(ticker, [])
    if not peers:
        return {
            "agent": "1.1",
            "summary": f"No sector peers found for {ticker}."
        }

    peer_summaries = []
    bullish, bearish = 0, 0

    for peer in peers:
        summary, _ = analyze_stock(peer, horizon)
        peer_summaries.append(summary)

        if summary["sma_trend"].lower() == "bullish":
            bullish += 1
        elif summary["sma_trend"].lower() == "bearish":
            bearish += 1

    # Determine overall sector trend
    if bullish > bearish:
        sector_trend = "Bullish"
    elif bearish > bullish:
        sector_trend = "Bearish"
    else:
        sector_trend = "Neutral"

    # Create layer-level summary
    summary_text = (
        f"{len(peers)} sector peer(s) analyzed for {ticker}. "
        f"Overall trend is **{sector_trend}** "
        f"(Bullish: {bullish}, Bearish: {bearish})."
    )

    return {
        "agent": "1.1",
        "target_peers": peers,
        "summary": summary_text,
        "details": peer_summaries
    }
