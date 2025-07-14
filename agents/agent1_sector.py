import agents.agent1_stock as agent1_stock
from openai import OpenAI
import copy
import plotly.io as pio

def get_llm_dual_summary(signals, api_key):
    client = OpenAI(api_key=api_key)
    prompt = f"""
You are a sector technical analyst and educator.

Given the following aggregated signals for the sector, write two summaries:
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
    try:
        summary = copy.deepcopy(agent1_stock.analyze(ticker, company_name, horizon, lookback_days, api_key))
        if "chart" in summary and summary["chart"] is not None:
            try:
                summary["chart"] = pio.from_json(summary["chart"].to_json())
            except Exception:
                summary["chart"] = None
        signals = summary.copy()
        if api_key:
            keys = [
                "sma_trend", "macd_signal", "bollinger_signal", "rsi_signal",
                "stochastic_signal", "cmf_signal", "obv_signal", "adx_signal",
                "atr_signal", "vol_spike", "patterns", "anomaly_events", "horizon", "risk_level"
            ]
            slim_signals = {k: signals.get(k) for k in keys}
            # Limit pattern/anomaly lists to the first 3 items, if present
            if isinstance(slim_signals.get("patterns"), list):
                slim_signals["patterns"] = slim_signals["patterns"][:3]
            if isinstance(slim_signals.get("anomaly_events"), list):
                slim_signals["anomaly_events"] = slim_signals["anomaly_events"][:3]
            tech, plain = get_llm_dual_summary(slim_signals, api_key)
            summary["llm_technical_summary"] = tech
            summary["llm_plain_summary"] = plain
        else:
            summary["llm_technical_summary"] = "No API key provided."
            summary["llm_plain_summary"] = "No API key provided."
        summary["llm_summary"] = summary.get("llm_technical_summary", summary.get("summary", ""))
        return summary
    except Exception as e:
        return {
            "summary": f"⚠️ Globals agent failed: {e}",
            "llm_technical_summary": f"Globals agent error: {e}",
            "llm_plain_summary": f"Globals agent error: {e}",
            "llm_summary": f"Globals agent error: {e}",
            "risk_level": "N/A",
            "df": pd.DataFrame(),
            "chart": None,
        }


