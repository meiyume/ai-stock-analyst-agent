# agents/agent1_core.py

import yfinance as yf
from llm_config_agent import generate_meta_config
from agents.agent1_stock import analyze as analyze_stock
from agents.agent1_sector import analyze as analyze_sector
from agents.agent1_market import analyze as analyze_market
from agents.agent1_commodities import analyze as analyze_commodities
from agents.agent1_globals import analyze as analyze_globals

def run_full_technical_analysis(ticker: str, horizon: str = "7 Days"):
    company_name = yf.Ticker(ticker).info.get("longName", ticker)
    meta = generate_meta_config(ticker, company_name)

    results = {}
    stock_summary, stock_df = analyze_stock(ticker, horizon)
    results["stock"] = stock_summary

    results["sector"] = analyze_sector(meta.get("sector_peers", []), horizon)
    results["market"] = analyze_market(meta.get("market_index", "^STI"), horizon)
    results["commodities"] = analyze_commodities(meta.get("commodities", []), horizon)
    results["globals"] = analyze_globals(meta.get("globals", []), horizon)

    # === Final summary string
    combined_summary = f"### 🔎 Final Technical Outlook for {ticker} ({horizon}):\n\n"
    combined_summary += f"- 📈 Stock: {stock_summary['summary']}\n"
    combined_summary += f"- 🏭 Sector: {results['sector'].get('summary')}\n"
    combined_summary += f"- 📊 Market: {results['market'].get('summary')}\n"
    combined_summary += f"- 🛢️ Commodities: {results['commodities'].get('summary')}\n"
    combined_summary += f"- 🌍 Global: {results['globals'].get('summary')}\n"

    results["final_summary"] = combined_summary
    return results, stock_df
