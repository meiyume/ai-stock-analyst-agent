import agents.agent1_stock as agent1_stock
from openai import OpenAI

def get_llm_dual_summary(signals, api_key):
    client = OpenAI(api_key=api_key)
    prompt = f"""
You are a commodities technical analyst and educator.

Given the following aggregated signals for key commodities, write two summaries:
1. Technical Summary: For professionals—precise, indicator-based, context-aware, actionable, and horizon-specific.
2. Plain-English Summary: For non-technical users—no jargon, friendly, analogy-rich, and practical advice.

Signals:
{signals}

Begin with "Technical Summary" and "Plain-English Summary" as section headers.
"""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=800,
        temperature=0.6,
    )
    output = response.choices[0].message.content.strip()
    tech, plain = "", ""
    if "Technical Summary" in output and "Plain-English Summary" in output:
        parts = output.split("Plain-English Summary")
        tech = parts[0].replace("Technical Summary", "").strip()
        plain = parts[1].strip()
    else:
        tech = output
        plain = output
    return tech, plain

def analyze(ticker, company_name=None, horizon="7 Days", lookback_days=None, api_key=None):
    # Example: Aggregate commodities signals
    summary, df = agent1_stock.analyze(ticker, company_name, horizon, lookback_days, api_key)
    signals = summary.copy()
    if api_key:
        tech, plain = get_llm_dual_summary(signals, api_key)
        summary["llm_technical_summary"] = tech
        summary["llm_plain_summary"] = plain
    else:
        summary["llm_technical_summary"] = "No API key provided."
        summary["llm_plain_summary"] = "No API key provided."
    return summary, df


