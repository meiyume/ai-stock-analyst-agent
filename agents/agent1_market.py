from agents.agent1_stock import analyze as analyze_stock
from openai import OpenAI

def get_llm_market_summary(market_signals, main_ticker, api_key, horizon):
    client = OpenAI(api_key=api_key)
    prompt = f"""
You are a professional market strategist.
- Summarize these market index signals for technical readers (bullish/bearish %, key trends, outliers, correlations to {main_ticker}).
- Then, explain for a non-technical reader: is the overall market looking positive, negative, or uncertain for the {horizon} outlook? 
- Offer gentle, practical guidance for someone trading {main_ticker}, but let them decide.
- Format as two sections: "For Technical Readers" and "For Everyone".

Market signals:
{market_signals}
Main stock: {main_ticker}
Outlook horizon: {horizon}
"""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=600,
        temperature=0.5,
    )
    return response.choices[0].message.content.strip()

def analyze(index_tickers: list, horizon: str = "7 Days", main_ticker: str = None, api_key: str = None):
    if not index_tickers:
        return {
            "agent": "1.2-market",
            "summary": "No market indices provided."
        }

    index_summaries = []
    bullish, bearish, neutral = 0, 0, 0
    trends = []
    anomalies = []

    for idx in index_tickers:
        try:
            summary, _ = analyze_stock(idx, horizon)
            trend = summary.get("sma_trend", "N/A").lower()
            if trend == "bullish":
                bullish += 1
            elif trend == "bearish":
                bearish += 1
            else:
                neutral += 1
            trends.append(f"{idx}: {summary.get('sma_trend', 'N/A')}")
            anomalies.extend(summary.get("anomaly_events", []))
            index_summaries.append({"ticker": idx, **summary})
        except Exception as e:
            index_summaries.append({"ticker": idx, "error": str(e)})

    total = bullish + bearish + neutral
    market_stats = {
        "bullish_pct": round(100 * bullish / total, 1) if total else 0,
        "bearish_pct": round(100 * bearish / total, 1) if total else 0,
        "num_indices": total,
        "trends": trends,
        "anomalies": anomalies[:5],  # show up to 5
    }

    summary_str = (
        f"Market indices: {index_tickers}\n"
        f"Bullish: {bullish} ({market_stats['bullish_pct']}%), "
        f"Bearish: {bearish} ({market_stats['bearish_pct']}%)\n"
        f"Trends: {market_stats['trends']}\n"
        f"Key anomalies: {market_stats['anomalies']}"
    )

    llm_summary = None
    if api_key is not None:
        llm_summary = get_llm_market_summary(
            summary_str, main_ticker or "unknown", api_key, horizon
        )

    return {
        "agent": "1.2-market",
        "summary": f"Market outlook: {bullish} bullish, {bearish} bearish indices.",
        "details": index_summaries,
        "market_stats": market_stats,
        "llm_summary": llm_summary
    }

