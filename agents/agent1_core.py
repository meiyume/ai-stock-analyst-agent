import os
import yfinance as yf

from agents.agent1_stock import analyze as analyze_stock
from agents.agent1_sector import analyze as analyze_sector
from agents.agent1_market import analyze as analyze_market
from agents.agent1_commodities import analyze as analyze_commodities
from agents.agent1_globals import analyze as analyze_globals
from llm_config_agent import generate_meta_config

def get_company_name_from_ticker(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return info.get("longName", ticker)
    except Exception:
        return ticker

def run_full_technical_analysis(
    ticker: str,
    company_name: str = None,
    horizon: str = "7 Days",
    api_key: str = None
):
    """
    Unified orchestrator for all Agent 1 sub-agents.
    Returns a dict with summaries for stock, sector, market, commodities, globals (with lookback_days set by LLM per layer).
    """
    if api_key is None:
        api_key = os.getenv("OPENAI_API_KEY", "")

    # --- Auto-fetch company name if not provided ---
    if not company_name:
        company_name = get_company_name_from_ticker(ticker)

    # --- 1. Get peer/index/universe config from meta-agent (LLM) ---
    meta = generate_meta_config(ticker, company_name)
    sector_peers = [ticker] + [peer for peer in meta.get("sector_peers", []) if peer != ticker]
    market_index = meta.get("market_index", ["^STI"])
    if isinstance(market_index, str):
        market_index = [market_index]
    commodities_list = meta.get("commodities", [])
    globals_list = meta.get("globals", [])

    # --- 2. Stock-level analysis (default to 30, LLM can adjust if you wish) ---
    stock_summary, stock_df = analyze_stock(ticker, horizon, api_key=api_key)

    # --- 3. Sector analysis (LLM decides lookback) ---
    sector_summary = analyze_sector(
        sector_peers, horizon, main_ticker=ticker, api_key=api_key
    )

    # --- 4. Market analysis (LLM decides lookback) ---
    market_summary = analyze_market(
        market_index, horizon, main_ticker=ticker, api_key=api_key
    )

    # --- 5. Commodities analysis (LLM decides lookback) ---
    commodities_summary = analyze_commodities(
        commodities_list, horizon, main_ticker=ticker, api_key=api_key
    )

    # --- 6. Global Macro (LLM decides lookback) ---
    globals_summary = analyze_globals(
        globals_list, horizon, main_ticker=ticker, api_key=api_key
    )

    # --- 7. Assemble everything for Streamlit/frontend/Agent 2 ---
    results = {
        "stock": stock_summary,
        "sector": sector_summary,
        "market": market_summary,
        "commodities": commodities_summary,
        "globals": globals_summary,
        "stock_df": stock_df,
        "sector_peers": sector_peers,
        "market_index": market_index,
        "commodities_list": commodities_list,
        "globals_list": globals_list,
        "meta": meta,
        "company_name": company_name,
        "ticker": ticker,
        "horizon": horizon
    }
    return results

