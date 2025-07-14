from agents.agent1_stock import analyze as analyze_stock
from openai import OpenAI

def get_llm_globals_summary(global_signals, main_ticker, api_key, horizon):
    client = OpenAI(api_key=api_key)
    prompt = f"""
You are a global macro strategist.
- Summarize these global index signals for technical readers: bullish/bearish/neutral %, trends, outliers.
- Then explain for a non-technical audience: what does global market mood mean for someone interested in {main_ticker} over the {horizon} outlook? Should they be confident, cautious, or watchful?
- Offer gentle guidance, but let them decide.
- Format as two sections: "For Technical Readers" and "For Everyone".

Global index signals:
{global_signals}
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

def analyze(global_index_tickers: list, horizon: str = "7 Days", main_ticker: str = None, api_key: str = None):
    if not global_index_tickers:
        return {
            "agent": "1.4-global",
            "summary": "No global indices provided."
        }

    summaries = []
    bullish, bearish, neutral = 0, 0, 0
    trends = []
    anomalies = []

    for idx in global_index_tickers:
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
            summaries.append({"ticker": idx, **summary})
        except Exception as e:
            summaries.append({
                "ticker": idx,
                "error": str(e)
            })

    total = bullish + bearish + neutral
    macro_stats = {
        "bullish_pct": round(100 * bullish / total, 1) if total else 0,
        "bearish_pct": round(100 * bearish / total, 1) if total else 0,
        "num_indices": total,
        "trends": trends,
        "anomalies": anomalies[:5],  # show up to 5
    }

    summary_str = (
        f"Global indices: {global_index_tickers}\n"
        f"Bullish: {bullish} ({macro_stats['bullish_pct']}%), "
        f"Bearish: {bearish} ({macro_stats['bearish_pct']}%)\n"
        f"Trends: {macro_stats['trends']}\n"
        f"Key anomalies: {macro_stats['anomalies']}"
    )

    llm_summary = None
    if api_key is not None:
        llm_summary = get_llm_globals_summary(
            summary_str, main_ticker or "unknown", api_key, horizon
        )

    return {
        "agent": "1.4-global",
        "summary": (
            f"Global macro outlook: "
            f"{bullish} bullish, {bearish} bearish, {neutral} neutral indices."
        ),
        "details": summaries,
        "macro_stats": macro_stats,
        "llm_summary": llm_summary
    }
