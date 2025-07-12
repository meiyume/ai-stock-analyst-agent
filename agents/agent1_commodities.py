# agents/agent1_commodities.py

from agents.agent1_stock import analyze as analyze_stock

# === Commodity relevance mapping per stock ===
COMMODITY_MAP = {
    "U11.SI": ["BZ=F", "CL=F"],  # Brent and WTI crude for Singapore Airlines
    # Add more if needed
}

def analyze(ticker: str, horizon: str = "7 Days"):
    commodities = COMMODITY_MAP.get(ticker, [])

    if not commodities:
        return {
            "agent": "1.3",
            "summary": f"No commodity mapping found for {ticker}."
        }

    summaries = []
    rising, falling = 0, 0

    for com in commodities:
        summary, _ = analyze_stock(com, horizon)
        summaries.append(summary)

        # Interpret simple trend for now based on SMA
        if summary["sma_trend"].lower() == "bullish":
            rising += 1
        elif summary["sma_trend"].lower() == "bearish":
            falling += 1

    if rising > falling:
        risk_effect = "Negative impact (rising commodity prices)"
    elif falling > rising:
        risk_effect = "Positive impact (declining commodity prices)"
    else:
        risk_effect = "Neutral commodity impact"

    summary_text = (
        f"Analyzed {len(commodities)} commodity futures. "
        f"{risk_effect}. (Bullish: {rising}, Bearish: {falling})"
    )

    return {
        "agent": "1.3",
        "target_commodities": commodities,
        "summary": summary_text,
        "details": summaries
    }
