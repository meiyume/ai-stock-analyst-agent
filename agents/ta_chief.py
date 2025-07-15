import copy
import pandas as pd
import json

import agents.ta_stock as ta_stock
import agents.ta_sector as ta_sector
import agents.ta_market as ta_market
import agents.ta_commodity as ta_commodity
import agents.ta_global as ta_global
from llm_utils import call_llm

# --- Fields to include for each agent ---
WANTED_KEYS = [
    "summary", "sma_trend", "macd_signal", "bollinger_signal", "rsi_signal",
    "stochastic_signal", "cmf_signal", "obv_signal", "adx_signal", "atr_signal",
    "vol_spike", "patterns", "anomaly_events", "risk_level"
]

def slim_agent(agent_summary, summary_limit=800):
    d = {k: agent_summary.get(k) for k in WANTED_KEYS}
    if isinstance(d.get("patterns"), list):
        d["patterns"] = d["patterns"][:3]
    if isinstance(d.get("anomaly_events"), list):
        d["anomaly_events"] = d["anomaly_events"][:3]
    if isinstance(d.get("summary"), str):
        d["summary"] = d["summary"][:summary_limit]
    return d

def parse_dual_summary(llm_output):
    """
    Splits the LLM output into technical and plain-English summaries.
    Expects output to contain both "Technical Summary" and "Plain-English Summary" as section headers.
    """
    tech, plain = "", ""
    if "Technical Summary" in llm_output and "Plain-English Summary" in llm_output:
        parts = llm_output.split("Plain-English Summary")
        tech = parts[0].replace("Technical Summary", "").strip()
        plain = parts[1].strip()
    else:
        tech = llm_output
        plain = llm_output
    return tech, plain

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
    commodity_summary = ta_commodity.analyze(ticker, company_name, horizon, lookback_days, api_key)
    global_summary = ta_global.ta_global()

    # Compose composite summary (chief = stock for now)
    chief_risk_score = stock_summary.get("composite_risk_score", 50)
    chief_risk_level = stock_summary.get("risk_level", "Moderate")

    results = {
        "stock": stock_summary,
        "sector": sector_summary,
        "market": market_summary,
        "commodity": commodity_summary,
        "global": global_summary,
        "company_name": company_name,
        "ticker": ticker,
        "horizon": horizon,
        "composite_risk_score": chief_risk_score,
        "risk_level": chief_risk_level,
    }

    # --- Prepare slimmed, structured chief input (for auditability & token safety) ---
    chief_signals = {
        "composite_risk_score": chief_risk_score,
        "risk_level": chief_risk_level,
        "horizon": horizon,
        "stock": slim_agent(stock_summary),
        "sector": slim_agent(sector_summary),
        "market": slim_agent(market_summary),
        "commodity": slim_agent(commodity_summary),
        "global": slim_agent(global_summary),
    }
    llm_input = json.dumps(chief_signals, indent=2)

    try:
        llm_output = call_llm(
            agent_name="chief",
            input_text=llm_input
        )
        tech, plain = parse_dual_summary(llm_output)
        results["llm_technical_summary"] = tech
        results["llm_plain_summary"] = plain
        results["llm_summary"] = tech
    except Exception as e:
        results["llm_technical_summary"] = f"LLM error: {e}"
        results["llm_plain_summary"] = f"LLM error: {e}"
        results["llm_summary"] = f"LLM error: {e}"

    return results


