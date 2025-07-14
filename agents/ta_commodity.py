import agents.ta_stock as ta_stock
import copy
import plotly.io as pio
from llm_utils import call_llm

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

def analyze(ticker, company_name=None, horizon="7 Days", lookback_days=None, api_key=None):
    try:
        summary = copy.deepcopy(
            ta_stock.analyze(ticker, company_name, horizon, lookback_days, api_key)
        )
        if "chart" in summary and summary["chart"] is not None:
            try:
                summary["chart"] = pio.from_json(summary["chart"].to_json())
            except Exception:
                summary["chart"] = None
        signals = summary.copy()
        keys = [
            "sma_trend", "macd_signal", "bollinger_signal", "rsi_signal",
            "stochastic_signal", "cmf_signal", "obv_signal", "adx_signal",
            "atr_signal", "vol_spike", "patterns", "anomaly_events", "horizon", "risk_level"
        ]
        slim_signals = {k: signals.get(k) for k in keys}
        if isinstance(slim_signals.get("patterns"), list):
            slim_signals["patterns"] = slim_signals["patterns"][:3]
        if isinstance(slim_signals.get("anomaly_events"), list):
            slim_signals["anomaly_events"] = slim_signals["anomaly_events"][:3]
        try:
            llm_output = call_llm(
                agent_name="commodity",
                input_text=str(slim_signals)
            )
            tech, plain = parse_dual_summary(llm_output)
            summary["llm_technical_summary"] = tech
            summary["llm_plain_summary"] = plain
        except Exception as e:
            summary["llm_technical_summary"] = f"LLM error: {e}"
            summary["llm_plain_summary"] = f"LLM error: {e}"

        summary["llm_summary"] = summary.get("llm_technical_summary", summary.get("summary", ""))
        return summary
    except Exception as e:
        import pandas as pd
        return {
            "summary": f"⚠️ Commodity agent failed: {e}",
            "llm_technical_summary": f"Commodity agent error: {e}",
            "llm_plain_summary": f"Commodity agent error: {e}",
            "llm_summary": f"Commodity agent error: {e}",
            "risk_level": "N/A",
            "df": pd.DataFrame(),
            "chart": None,
        }





