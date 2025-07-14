import yfinance as yf
import agents.agent1_stock as agent1_stock
import agents.agent1_sector as agent1_sector
import agents.agent1_market as agent1_market
import agents.agent1_commodities as agent1_commodities
import agents.agent1_globals as agent1_globals

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
    stock_summary, stock_df = agent1_stock.analyze(
        ticker, company_name, horizon, lookback_days=lookback_days, api_key=api_key
    )

    # --- 2. Sector analysis ---
    sector_summary, sector_df = agent1_sector.analyze(
        ticker, company_name, horizon, lookback_days=lookback_days, api_key=api_key
    )

    # --- 3. Market analysis ---
    market_summary, market_df = agent1_market.analyze(
        ticker, company_name, horizon, lookback_days=lookback_days, api_key=api_key
    )

    # --- 4. Commodities analysis ---
    commodities_summary, commodities_df = agent1_commodities.analyze(
        ticker, company_name, horizon, lookback_days=lookback_days, api_key=api_key
    )

    # --- 5. Global Macro analysis ---
    globals_summary, globals_df = agent1_globals.analyze(
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


