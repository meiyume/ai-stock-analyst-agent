# agents/agent1_globals.py

from agents.agent1_stock import analyze as analyze_stock

# === Default global indices per stock ===
GLOBAL_INDICES_MAP = {
    "U11.SI": ["^DJI", "^N225", "^HSI"],  # Dow, Nikkei, Hang Seng
    # Add more stock → global index maps if needed
}

def analyze(ticker: str, horizon: str = "7 Days"):
    indices = GLOBAL_INDICES_MAP.get(ticker, ["^DJI", "^N225", "^HSI"])
    summaries = []
    bullish, bearish = 0, 0

    for idx in indices:
        summary, _ = analyze_stock(idx, horizon)
        summaries.append(summary)

        if summary["sma_trend"].lower() == "bullish":
            bullish += 1
        elif summary["sma_trend"].lower() == "bearish":
            bearish += 1

    if bullish > bearish:
        sentiment = "Global macro sentiment is positive"
    elif bearish > bullish:
        sentiment = "Global macro sentiment is negative"
    else:
        sentiment = "Global macro sentiment is neutral"

    summary_text = (
        f"Analyzed {len(indices)} major global indices. "
        f"{sentiment} (Bullish: {bullish}, Bearish: {bearish})"
    )

    return {
        "agent": "1.4",
        "target_indices": indices,
        "summary": summary_text,
        "details": summaries
    }
