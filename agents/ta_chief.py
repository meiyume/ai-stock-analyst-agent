import copy
import pandas as pd

import agents.ta_stock as ta_stock
import agents.ta_sector as ta_sector
import agents.ta_market as ta_market
import agents.ta_commodity as ta_commodity
import agents.ta_global as ta_global

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
            stock = ta_stock.yf.Ticker(ticker)
            info = stock.info
            company_name = info.get("longName", ticker)
        except Exception:
            company_name = ticker

    # --- Get all agent outputs (each is always a dict) ---
    stock_summary = ta_stock.analyze(ticker, company_name, horizon, lookback_days, api_key)
    sector_summary = ta_sector.analyze(ticker, company_name, horizon, lookback_days, api_key)
    market_summary = ta_market.analyze(ticker, company_name, horizon, lookback_days, api_key)
    commodities_summary = ta_commodity.analyze(ticker, company_name, horizon, lookback_days, api_key)
    globals_summary = ta_global.analyze(ticker, company_name, horizon, lookback_days, api_key)

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
            from agents.ta_stock import get_llm_dual_summary
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

