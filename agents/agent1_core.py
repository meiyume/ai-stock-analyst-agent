import yfinance as yf
import agents.agent1_stock as agent1_stock
import agents.agent1_sector as agent1_sector
import agents.agent1_market as agent1_market
import agents.agent1_commodities as agent1_commodities
import agents.agent1_globals as agent1_globals

# Import enforce_date_column utility from stock agent
from agents.agent1_stock import enforce_date_column

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
    if not company_name:
        company_name = get_company_name_from_ticker(ticker)

    # --- 1. Stock-level analysis ---
    stock_summary = agent1_stock.analyze(
        ticker, company_name, horizon, lookback_days=lookback_days, api_key=api_key
    )
    # Enforce clean Date column if a DataFrame is present
    if 'df' in stock_summary:
        stock_summary['df'] = enforce_date_column(stock_summary['df'])

    # --- 2. Sector analysis ---
    sector_summary = agent1_sector.analyze(
        ticker, company_name, horizon, lookback_days=lookback_days, api_key=api_key
    )
    if 'df' in sector_summary:
        sector_summary['df'] = enforce_date_column(sector_summary['df'])

    # --- 3. Market analysis ---
    market_summary = agent1_market.analyze(
        ticker, company_name, horizon, lookback_days=lookback_days, api_key=api_key
    )
    if 'df' in market_summary:
        market_summary['df'] = enforce_date_column(market_summary['df'])

    # --- 4. Commodities analysis ---
    commodities_summary = agent1_commodities.analyze(
        ticker, company_name, horizon, lookback_days=lookback_days, api_key=api_key
    )
    if 'df' in commodities_summary:
        commodities_summary['df'] = enforce_date_column(commodities_summary['df'])

    # --- 5. Global Macro analysis ---
    globals_summary = agent1_globals.analyze(
        ticker, company_name, horizon, lookback_days=lookback_days, api_key=api_key
    )
    if 'df' in globals_summary:
        globals_summary['df'] = enforce_date_column(globals_summary['df'])

    # Compose composite summary (chief = stock for now)
    chief_llm_summary = stock_summary.get("llm_summary", stock_summary.get("llm_technical_summary", "No summary."))
    chief_risk_score = stock_summary.get("composite_risk_score", 50)
    chief_risk_level = stock_summary.get("risk_level", "Moderate")

    results = {
        "llm_summary": chief_llm_summary,
        "composite_risk_score": chief_risk_score,
        "risk_level": chief_risk_level,
        "stock": stock_summary,
        "sector": sector_summary,
        "market": market_summary,
        "commodities": commodities_summary,
        "globals": globals_summary,
        "company_name": company_name,
        "ticker": ticker,
        "horizon": horizon,
    }

    return results
