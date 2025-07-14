import copy
import pandas as pd

import agents.agent1_stock as agent1_stock
import agents.agent1_sector as agent1_sector
import agents.agent1_market as agent1_market
import agents.agent1_commodities as agent1_commodities
import agents.agent1_globals as agent1_globals

def run_full_technical_analysis(
    ticker: str,
    company_name: str = None,
    horizon: str = "7 Days",
    lookback_days: int = None,
    api_key: str = None
):
    # --- Auto-fetch company name if not provided ---
    if not company_name:
        try:
            stock = agent1_stock.yf.Ticker(ticker)
            info = stock.info
            company_name = info.get("longName", ticker)
        except Exception:
            company_name = ticker

    # --- Get all agent outputs (each is always a dict) ---
    stock_summary = agent1_stock.analyze(ticker, company_name, horizon, lookback_days, api_key)
    sector_summary = agent1_sector.analyze(ticker, company_name, horizon, lookback_days, api_key)
    market_summary = agent1_market.analyze(ticker, company_name, horizon, lookback_days, api_key)
    commodities_summary = agent1_commodities.analyze(ticker, company_name, horizon, lookback_days, api_key)
    globals_summary = agent1_globals.analyze(ticker, company_name, horizon, lookback_days, api_key)

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

    # === Chief Grand Outlook LLM Summary PATCH ===
    if api_key:
        chief_signals = {
            "composite_risk_score": chief_risk_score,
            "risk_level": chief_risk_level,
            "horizon": horizon,
            "stock_summary": stock_summary.get("summary"),
            "sector_summary": sector_summary.get("summary"),
            "market_summary": market_summary.get("summary"),
            "commodities_summary": commodities_summary.get("summary"),
            "globals_summary": globals_summary.get("summary"),
        }
        try:
            # Adjust import path if get_llm_dual_summary is elsewhere
            from agents.agent1_stock import get_llm_dual_summary
            tech, plain = get_llm_dual_summary(chief_signals, api_key)
            results["llm_technical_summary"] = tech
            results["llm_plain_summary"] = plain
        except Exception as e:
            results["llm_technical_summary"] = f"LLM error: {e}"
            results["llm_plain_summary"] = f"LLM error: {e}"
    else:
        results["llm_technical_summary"] = "No technical summary available."
        results["llm_plain_summary"] = "No plain-English summary available."
    # === End PATCH ===

    return results

