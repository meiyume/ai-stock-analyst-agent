# agent1_core.py

from agents.agent1_stock import analyze as analyze_stock
from agents.agent1_sector import analyze as analyze_sector
from agents.agent1_market import analyze as analyze_market
from agents.agent1_commodities import analyze as analyze_commodities
from agents.agent1_globals import analyze as analyze_global

def run_full_technical_analysis(ticker: str, horizon: str):
    # Directly pass ticker and horizon
    stock_summary, df = analyze_stock(ticker, horizon)
    sector_summary = analyze_sector(ticker)
    market_summary = analyze_market(ticker)
    commodity_summary = analyze_commodities(ticker)
    global_summary = analyze_global(ticker)

    final_summary = generate_final_outlook(stock_summary, sector_summary, market_summary)

    return {
        "stock": stock_summary,
        "sector": sector_summary,
        "market": market_summary,
        "commodities": commodity_summary,
        "globals": global_summary,
        "final_summary": final_summary
    }, df


def generate_final_outlook(stock, sector, market):
    parts = []

    if stock:
        parts.append(f"📌 Stock: {stock.get('summary', 'N/A')}")
    if sector:
        parts.append(f"🏭 Sector: {sector.get('summary', 'N/A')}")
    if market:
        parts.append(f"📊 Index: {market.get('summary', 'N/A')}")

    if not parts:
        return "⚠️ No technical signals available."
    
    return " \n".join(parts)
