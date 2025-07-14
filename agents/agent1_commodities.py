from agents.agent1_stock import analyze as analyze_stock
from openai import OpenAI

def get_llm_commodities_summary(commodity_signals, main_ticker, api_key, horizon):
    client = OpenAI(api_key=api_key)
    prompt = f"""
You are a commodities strategist.
- Summarize these commodity signals for technical readers: how many are rising, how many are falling, key trends, major anomalies.
- Then explain for a non-technical audience: What do these commodity trends mean for someone interested in {main_ticker} over the {horizon} outlook? Should they be confident, cautious, or watchful?
- Offer gentle guidance, but let them decide.
- Format as two sections: "For Technical Readers" and "For Everyone".

Commodity signals:
{commodity_signals}
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

def analyze(commodity_tickers: list, horizon: str = "7 Days", main_ticker: str = None, api_key: str = None):
    if not commodity_tickers:
        return {
            "agent": "1.3-commodities",
            "summary": "No commodities provided."
        }

    summaries = []
    rising, falling, neutral = 0, 0, 0
    trends = []
    anomalies = []

    for com in commodity_tickers:
        try:
            summary, _ = analyze_stock(com, horizon)
            trend = summary.get("sma_trend", "N/A").lower()
            if trend == "bullish":
                rising += 1
            elif trend == "bearish":
                falling += 1
            else:
                neutral += 1
            trends.append(f"{com}: {summary.get('sma_trend', 'N/A')}")
            anomalies.extend(summary.get("anomaly_events", []))
            summaries.append({"ticker": com, **summary})
        except Exception as e:
            summaries.append({
                "ticker": com,
                "error": str(e)
            })

    total = rising + falling + neutral
    impact = (
        "Negative impact (rising commodity prices)" if rising > falling else
        "Positive impact (falling commodity prices)" if falling > rising else
        "Neutral impact"
    )

    commodity_stats = {
        "rising_pct": round(100 * rising / total, 1) if total else 0,
        "falling_pct": round(100 * falling / total, 1) if total else 0,
        "num_commodities": total,
        "trends": trends,
        "anomalies": anomalies[:5],  # up to 5
        "impact": impact
    }

    summary_str = (
        f"Commodities: {commodity_tickers}\n"
        f"Rising: {rising} ({commodity_stats['rising_pct']}%), "
        f"Falling: {falling} ({commodity_stats['falling_pct']}%)\n"
        f"Trends: {commodity_stats['trends']}\n"
        f"Key anomalies: {commodity_stats['anomalies']}"
    )

    llm_summary = None
    if api_key is not None:
        llm_summary = get_llm_commodities_summary(
            summary_str, main_ticker or "unknown", api_key, horizon
        )

    return {
        "agent": "1.3-commodities",
        "summary": f"Commodities outlook: {impact}. (Rising: {rising}, Falling: {falling})",
        "details": summaries,
        "commodity_stats": commodity_stats,
        "llm_summary": llm_summary
    }
