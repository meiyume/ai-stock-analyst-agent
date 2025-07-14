import pandas as pd
from agents.agent1_stock import analyze as analyze_stock
from openai import OpenAI

def get_llm_sector_summary(sector_signals, main_ticker, api_key, horizon):
    client = OpenAI(api_key=api_key)
    prompt = f"""
You are a professional sector-level equity analyst.
- First, summarize these peer signals for technical readers. Use correct finance/quant terms and connect signals (bullish %, bearish %, leader/laggard, anomalies). 
- Next, explain for a non-technical reader in plain language: Is the sector healthy? Is their stock leading, lagging, or in the middle? Should they feel confident or cautious for the {horizon} outlook?
- Include gentle directional advice, but let the reader decide.
- Format as two sections: "For Technical Readers" and "For Everyone".

Peer signals:
{sector_signals}
Main stock: {main_ticker}
Outlook horizon: {horizon}
"""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=700,
        temperature=0.5,
    )
    return response.choices[0].message.content.strip()

def analyze(peer_tickers: list, horizon: str = "7 Days", main_ticker: str = None, api_key: str = None):
    if not peer_tickers:
        return {
            "agent": "1.1-sector",
            "summary": "No sector peers found for analysis."
        }

    peer_summaries = []
    bullish, bearish, neutral = 0, 0, 0
    overbought, oversold = 0, 0
    sector_patterns = []
    anomalies = []
    leader, laggard = None, None
    highest_score, lowest_score = -float('inf'), float('inf')

    for ticker in peer_tickers:
        try:
            summary, _ = analyze_stock(ticker, horizon)
            # Calculate composite score for leadership
            score = (
                (1 if summary.get("sma_trend", "").lower() == "bullish" else 0) +
                (1 if summary.get("macd_signal", "").lower() == "bullish" else 0) +
                (1 if summary.get("rsi_signal", "").lower() == "overbought" else 0) * -1 +
                (1 if summary.get("stochastic_signal", "").lower() == "bullish" else 0)
            )
            if score > highest_score:
                highest_score = score
                leader = ticker
            if score < lowest_score:
                lowest_score = score
                laggard = ticker

            # Count sector trends
            if summary.get("sma_trend", "").lower() == "bullish":
                bullish += 1
            elif summary.get("sma_trend", "").lower() == "bearish":
                bearish += 1
            else:
                neutral += 1

            if summary.get("rsi_signal", "").lower() == "overbought":
                overbought += 1
            if summary.get("rsi_signal", "").lower() == "oversold":
                oversold += 1

            sector_patterns.extend(summary.get("patterns", []))
            anomalies.extend(summary.get("anomaly_events", []))
            peer_summaries.append({"ticker": ticker, **summary})
        except Exception as e:
            peer_summaries.append({"ticker": ticker, "error": str(e)})

    total = bullish + bearish + neutral
    sector_stats = {
        "bullish_pct": round(100 * bullish / total, 1) if total else 0,
        "bearish_pct": round(100 * bearish / total, 1) if total else 0,
        "overbought": overbought,
        "oversold": oversold,
        "leader": leader,
        "laggard": laggard,
        "num_peers": total,
        "sector_patterns": list(set(sector_patterns)),
        "anomalies": anomalies[:5],  # show up to 5 key anomalies
    }

    summary_str = (
        f"Sector peers: {peer_tickers}\n"
        f"Bullish: {bullish} ({sector_stats['bullish_pct']}%), "
        f"Bearish: {bearish} ({sector_stats['bearish_pct']}%), "
        f"Overbought: {overbought}, Oversold: {oversold}\n"
        f"Leader: {leader}, Laggard: {laggard}\n"
        f"Sector-wide patterns: {sector_stats['sector_patterns']}\n"
        f"Key anomalies: {sector_stats['anomalies']}"
    )

    # LLM sector summary (optional: only if api_key supplied)
    llm_summary = None
    if api_key is not None:
        llm_summary = get_llm_sector_summary(
            summary_str, main_ticker or leader, api_key, horizon
        )

    return {
        "agent": "1.1-sector",
        "summary": f"Sector technicals — {bullish} bullish, {bearish} bearish, leader: {leader}, laggard: {laggard}. Overbought: {overbought}, Oversold: {oversold}.",
        "details": peer_summaries,
        "sector_stats": sector_stats,
        "llm_summary": llm_summary
    }



