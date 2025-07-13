# agent1_core.py

from agents.agent1_stock import analyze as analyze_stock
from agents.agent1_sector import analyze as analyze_sector
from agents.agent1_market import analyze as analyze_market
from agents.agent1_commodities import analyze as analyze_commodities
from agents.agent1_globals import analyze as analyze_globals
from llm_config_agent import generate_meta_config

def run_full_technical_analysis(ticker: str, horizon: str = "7 Days"):
    config = generate_meta_config(ticker)

    # === Agent 1.0: Stock-Level Technical Analysis ===
    stock_summary, df = analyze_stock(ticker, horizon)

    # === Agent 1.1: Sector Peers ===
    sector_summary = {
        "agent": "1.1",
        "tickers": config["sector"],
        "summary": "N/A",
        "details": []
    }
    bullish, bearish = 0, 0
    for peer in config["sector"]:
        result, _ = analyze_stock(peer, horizon)
        if result["sma_trend"] == "Bullish":
            bullish += 1
        elif result["sma_trend"] == "Bearish":
            bearish += 1
        sector_summary["details"].append(result)
    sector_summary["summary"] = f"Bullish sector outlook (Bullish: {bullish}, Bearish: {bearish})"

    # === Agent 1.2: Market Index ===
    market_summary, _ = analyze_market(config["market"], horizon)

    # === Agent 1.3: Commodities ===
    commodity_summary = {
        "agent": "1.3",
        "tickers": config["commodities"],
        "summary": "N/A",
        "details": []
    }
    bull, bear = 0, 0
    for com in config["commodities"]:
        result, _ = analyze_stock(com, horizon)
        if result["sma_trend"] == "Bullish":
            bull += 1
        elif result["sma_trend"] == "Bearish":
            bear += 1
        commodity_summary["details"].append(result)
    commodity_summary["summary"] = f"Neutral impact. (Bullish: {bull}, Bearish: {bear})"

    # === Agent 1.4: Global Indices ===
    global_summary = {
        "agent": "1.4",
        "tickers": config["globals"],
        "summary": "N/A",
        "details": []
    }
    bull, bear = 0, 0
    for idx in config["globals"]:
        result, _ = analyze_stock(idx, horizon)
        if result["sma_trend"] == "Bullish":
            bull += 1
        elif result["sma_trend"] == "Bearish":
            bear += 1
        global_summary["details"].append(result)
    global_summary["summary"] = f"Negative global macro outlook (Bullish: {bull}, Bearish: {bear})"

    # === Final Layered Summary ===
    final_summary = f"""### 🔎 Final Technical Outlook for {ticker} ({horizon}):
- 📈 Stock: {stock_summary['summary']}
- 🏭 Sector: {sector_summary['summary']}
- 📊 Market: {market_summary['summary']}
- 🛢️ Commodities: {commodity_summary['summary']}
- 🌍 Global: {global_summary['summary']}
"""

    return {
        "stock": stock_summary,
        "sector": sector_summary,
        "market": {
            "agent": "1.2",
            "target": config["market"],
            "summary": market_summary["summary"],
            "details": market_summary
        },
        "commodities": commodity_summary,
        "globals": global_summary,
        "final_summary": final_summary
    }, df
