# agents/agent1_core.py

from agents.agent1_stock import analyze as analyze_stock
from agents.agent1_sector import analyze as analyze_sector
# Future: from agents.agent1_market import analyze as analyze_market
# Future: from agents.agent1_commodities import analyze as analyze_commodities

# Predefined mapping: stock → sector, index, commodities, global indices
LAYER_MAP = {
    "U11.SI": {
        "sector_peers": ["C6L.SI"],  # SIA Engineering
        "market_index": "^STI",
        "commodities": ["BZ=F"],     # Brent Crude
        "globals": ["^DJI", "^N225", "^HSI"]
    },
    # Add more mappings as needed
}

def run_full_technical_analysis(ticker: str, horizon: str = "7 Days"):
    results = {}
    
    # === 1.0 Stock Layer ===
    stock_summary, stock_df = analyze_stock(ticker, horizon)
    results["stock"] = stock_summary

    # === Placeholder for future layers ===
    results["sector"] = {"summary": "Sector analysis not yet implemented."}
    results["market"] = {"summary": "Market index analysis not yet implemented."}
    results["commodities"] = {"summary": "Commodity analysis not yet implemented."}
    results["globals"] = {"summary": "Global indices analysis not yet implemented."}

    # === Combined Summary ===
    results["final_summary"] = (
        f"Primary stock analysis:\n{stock_summary['summary']}\n\n"
        "Other layers (sector, market, global) will be integrated in future updates."
    )

    return results, stock_df
