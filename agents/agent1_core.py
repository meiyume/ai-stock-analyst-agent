# agents/agent1_core.py

from agents.agent1_stock import analyze as analyze_stock
from agents.agent1_sector import analyze as analyze_sector
from agents.agent1_market import analyze as analyze_market
from agents.agent1_commodities import analyze as analyze_commodities
from agents.agent1_globals import analyze as analyze_globals
from llm_config_agent import generate_meta_config

# Optionally, import your company name fetcher if available:
try:
    from agents.agent1_stock import get_company_name_from_ticker
except ImportError:
    get_company_name_from_ticker = None

def run_full_technical_analysis(ticker: str, horizon: str):
    """
    Orchestrates all agent layers using dynamic, context-aware meta-config.
    Returns a multi-layer results dict and the main stock DataFrame.
    """
    # (Optional) Get company name for better meta-config, else use empty string.
    company_name = ""
    if get_company_name_from_ticker is not None:
        try:
            company_name = get_company_name_from_ticker(ticker)
        except Exception:
            company_name = ""

    # Generate context-aware peer/commodity/global config for all layers:
    meta = generate_meta_config(ticker, company_name)

    # --- Stock Layer (main ticker only, always returns summary and DataFrame)
    stock_summary, df = analyze_stock(ticker, horizon)

    # --- Sector Layer (analyze sector peers list, context-aware)
    sector_peers = meta.get("sector_peers", [])
    sector_summary = analyze_sector(sector_peers, horizon)

    # --- Market Layer (analyze relevant market index tickers)
    market_index = meta.get("market_index", [])
    market_summary = analyze_market(market_index, horizon)

    # --- Commodities Layer (analyze all relevant commodities)
    commodities_list = meta.get("commodities", [])
    commodities_summary = analyze_commodities(commodities_list, horizon)

    # --- Globals Layer (analyze all relevant global indices)
    globals_list = meta.get("globals", [])
    globals_summary = analyze_globals(globals_list, horizon)

    # Optionally, you can add a stitched final outlook, or let frontend/LLM do it.
    # final_summary = generate_final_outlook(stock_summary, sector_summary, market_summary, commodities_summary, globals_summary)

    # Return a unified results dict plus main DataFrame
    return {
        "stock": stock_summary,
        "sector": sector_summary,
        "market": market_summary,
        "commodities": commodities_summary,
        "globals": globals_summary
        # , "final_summary": final_summary  # (Optional)
    }, df

