# agents/agent1_core.py

from agents.agent1_stock import analyze as analyze_stock
from agents.agent1_sector import analyze as analyze_sector
from agents.agent1_market import analyze as analyze_market
from agents.agent1_commodities import analyze as analyze_commodities
from agents.agent1_globals import analyze as analyze_globals

def run_full_technical_analysis(ticker: str, horizon: str = "7 Days"):
    results = {}

    # === Sub-agent results ===
    stock_summary, stock_df = analyze_stock(ticker, horizon)
    results["stock"] = stock_summary
    results["sector"] = analyze_sector(ticker, horizon)
    results["market"] = analyze_market(ticker, horizon)
    results["commodities"] = analyze_commodities(ticker, horizon)
    results["globals"] = analyze_globals(ticker, horizon)

    # === Strategic Final Summary ===
    signals = [
        ("📈 Stock", stock_summary["sma_trend"]),
        ("🏭 Sector", results["sector"].get("summary", "")),
        ("📊 Market", results["market"].get("summary", "")),
        ("🛢️ Commodities", results["commodities"].get("summary", "")),
        ("🌍 Global", results["globals"].get("summary", ""))
    ]

    combined_summary = f"### 🔎 Final Technical Outlook for {ticker} ({horizon}):\n\n"
    combined_summary += f"- {stock_summary['summary']}\n"
    for label, val in signals[1:]:
        combined_summary += f"- {label}: {val}\n"

    results["final_summary"] = combined_summary
    return results, stock_df
