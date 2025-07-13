# agents/agent1_core.py

from agents.agent1_stock import analyze as analyze_stock
from agents.agent1_sector import analyze as analyze_sector
from agents.agent1_market import analyze as analyze_market
from agents.agent1_commodities import analyze as analyze_commodities
from agents.agent1_globals import analyze as analyze_globals
from llm_config_agent import generate_meta_config

def run_full_technical_analysis(ticker: str, horizon: str = "7 Days"):
    """
    Run full layered technical analysis using Agent 1.
    Returns structured summary and DataFrame for charting.
    """

    config = generate_meta_config(ticker, horizon)

    # === Agent 1.0: Stock-level technical indicators
    stock_summary, df = analyze_stock(config["ticker"], config["horizon"])

    # === Agent 1.1: Sector-level comparison (e.g. DBS, OCBC)
    sector_summary = analyze_sector(config["ticker"], config["horizon"])

    # === Agent 1.2: Market index (e.g. ^STI)
    market_summary = analyze_market(config["market_index"], config["horizon"])

    # === Agent 1.3: Commodities (e.g. gold, oil)
    commodities_summary = analyze_commodities(config["commodities"], config["horizon"])

    # === Agent 1.4: Global indices (e.g. ^DJI, ^HSI, ^N225)
    globals_summary = analyze_globals(config["global_indices"], config["horizon"])

    # === Final Summary
    final = f"""### 🔎 Final Technical Outlook for {config['ticker']} ({config['horizon']}):\n
- 📈 Stock: {stock_summary['summary']}
- 🏭 Sector: {sector_summary['summary']}
- 📊 Market: {market_summary['summary']}
- 🛢️ Commodities: {commodities_summary['summary']}
- 🌍 Global: {globals_summary['summary']}
"""

    return {
        "stock": stock_summary,
        "sector": sector_summary,
        "market": market_summary,
        "commodities": commodities_summary,
        "globals": globals_summary,
        "final_summary": final
    }, df
