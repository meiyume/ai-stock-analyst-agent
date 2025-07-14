import yfinance as yf
from agents.agent1_stock import analyze as analyze_stock
from agents.agent1_sector import analyze as analyze_sector
from agents.agent1_market import analyze as analyze_market
from agents.agent1_commodities import analyze as analyze_commodities
from agents.agent1_globals import analyze as analyze_globals

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
    lookback_days: int = None,
    api_key: str = None
):
    # --- Auto-fetch company name if not provided ---
    if not company_name:
        company_name = get_company_name_from_ticker(ticker)

    meta = {
        "sector": None,
        "market_index": None,
        "commodities": None,
        "globals": None,
    }

    # --- 1. Stock-level analysis ---
    stock_summary, stock_df = analyze_stock(
        ticker, company_name, horizon, lookback_days=lookback_days, api_key=api_key
    )

    # --- 2. Sector analysis ---
    sector_summary, sector_df = analyze_sector(
        ticker, company_name, horizon, lookback_days=lookback_days, api_key=api_key
    )

    # --- 3. Market analysis ---
    market_summary, market_df = analyze_market(
        ticker, company_name, horizon, lookback_days=lookback_days, api_key=api_key
    )

    # --- 4. Commodities analysis ---
    commodities_summary, commodities_df = analyze_commodities(
        ticker, company_name, horizon, lookback_days=lookback_days, api_key=api_key
    )

    # --- 5. Global Macro analysis ---
    globals_summary, globals_df = analyze_globals(
        ticker, company_name, horizon, lookback_days=lookback_days, api_key=api_key
    )

    results = {
        "stock": stock_summary,
        "sector": sector_summary,
        "market": market_summary,
        "commodities": commodities_summary,
        "globals": globals_summary,
        "stock_df": stock_df,
        "sector_df": sector_df,
        "market_df": market_df,
        "commodities_df": commodities_df,
        "globals_df": globals_df,
        "meta": meta,  # Reserved for future use/display
        "company_name": company_name,
        "ticker": ticker,
        "horizon": horizon,
    }

    return results


