"""
llm_utils.py

Unified LLM utility for multi-agent "brain swapping" with agent-to-provider/model/prompt mapping.
Features per-provider concurrency limits, request queues, and robust error handling.
Plug-and-play: agents call call_llm() for all LLM access—configuration is fully centralized.
"""

import os
import threading
import queue
import pandas as pd
import numpy as np
from concurrent.futures import Future
    
# === PROVIDER CONCURRENCY LIMITS ===

PROVIDER_LIMITS = {
    "openai":   {"max_concurrent": 3, "queue_maxsize": 40},
    "gemini":   {"max_concurrent": 2, "queue_maxsize": 20},
    "claude":   {"max_concurrent": 1, "queue_maxsize": 10},
}

# === PROVIDER QUEUES & SEMAPHORES SETUP ===

_provider_queues = {}
_provider_semaphores = {}

def _provider_worker(provider):
    sem = _provider_semaphores[provider]
    q = _provider_queues[provider]
    while True:
        try:
            req_fn, args, kwargs, fut = q.get()
            with sem:
                try:
                    result = req_fn(*args, **kwargs)
                    fut.set_result(result)
                except Exception as e:
                    fut.set_exception(e)
                finally:
                    q.task_done()
        except Exception as e:
            print(f"[llm_utils] {provider} worker error: {e}")
            print(traceback.format_())

# --- Initialize queues, semaphores, workers ---
for provider, lim in PROVIDER_LIMITS.items():
    q = queue.Queue(maxsize=lim["queue_maxsize"])
    sem = threading.Semaphore(lim["max_concurrent"])
    _provider_queues[provider] = q
    _provider_semaphores[provider] = sem
    for _ in range(lim["max_concurrent"]):
        t = threading.Thread(target=_provider_worker, args=(provider,), daemon=True)
        t.start()

# === LLM PROVIDER WRAPPERS ===

def call_openai(model, prompt, api_key, temperature=0.2, max_tokens=1024):
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()

def call_gemini(model, prompt, api_key, **kwargs):
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    model_obj = genai.GenerativeModel(model)
    response = model_obj.generate_content(prompt)
    return response.text.strip()

def call_claude(model, prompt, api_key, **kwargs):
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=1024,
        temperature=0.2,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text.strip()

# === UNIVERSAL SAFE INPUTS ===

def safe_llm_input(obj, max_list_len=100, max_dict_len=100):
    """
    Recursively convert all elements to JSON-safe types for LLM input.
    - Converts DataFrames to list of dicts (max N rows)
    - Converts numpy objects to float/int
    - Trims lists/dicts to avoid huge payloads
    - Converts all keys to str
    """
    if isinstance(obj, pd.DataFrame):
        return obj.tail(max_list_len).to_dict(orient="records")
    elif isinstance(obj, (pd.Series, list, tuple, set)):
        return [safe_llm_input(x, max_list_len, max_dict_len) for x in list(obj)[:max_list_len]]
    elif isinstance(obj, dict):
        return {str(k): safe_llm_input(v, max_list_len, max_dict_len)
                for k, v in list(obj.items())[:max_dict_len]}
    elif isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    elif isinstance(obj, (np.ndarray,)):
        return obj.tolist()
    elif isinstance(obj, (bytes, bytearray)):
        return str(obj)
    elif isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    else:
        try:
            return str(obj)
        except Exception:
            return "UNSERIALIZABLE_OBJECT"
# === ESSENTIALS INPUT ===
def build_llm_market_summary(mkt_summary):
    """
    Build a minimal, LLM-friendly market summary dict for AI explanations.
    Only keeps the most essential and recent fields for fast, reliable LLM responses.
    """
    composite_score_history = mkt_summary.get("composite_score_history")
    # If DataFrame, convert to list of dicts (last 3 rows)
    if isinstance(composite_score_history, pd.DataFrame):
        history_data = composite_score_history.tail(3).to_dict(orient="records")
    elif isinstance(composite_score_history, list):
        history_data = composite_score_history[-3:]
    else:
        history_data = []

    result = {
        "composite_score": mkt_summary.get("composite_score"),
        "composite_label": mkt_summary.get("composite_label"),
        "risk_regime": mkt_summary.get("risk_regime"),
        "alerts": mkt_summary.get("alerts", [])[:2],
        "as_of": mkt_summary.get("as_of"),
        "breadth": mkt_summary.get("breadth", {}),
        "composite_score_history": history_data,
        "relative_performance": dict(list(mkt_summary.get("rel_perf_30d", {}).items())[:3]) if "rel_perf_30d" in mkt_summary else {},
        "anomaly_alerts": mkt_summary.get("anomaly_alerts", [])[:2],
    }
    return result

# === PROMPT TEMPLATES ===

PROMPT_TEMPLATES = {
    "chief": """
    You are the Chief AI Investment Analyst for a global asset management firm.
    You will receive a JSON object with the following structure:
    {{
      "composite_risk_score": float,     # overall composite risk score (0–1)
      "risk_level": string,              # overall risk label
      "horizon": string,                 # outlook horizon (e.g. "7 Days")
      "stock": {{ ... }},                # signals, summary, risk_level for the stock
      "sector": {{ ... }},               # signals, summary, risk_level for the sector
      "market": {{ ... }},               # signals, summary, risk_level for the overall market
      "commodity": {{ ... }},            # signals, summary, risk_level for key commodities
      "global": {{ ... }}                # signals, summary, risk_level for global factors
    }}
    {input}
    Each agent (stock, sector, market, commodity, global) provides:
    - a "summary" string,
    - risk level,
    - signals like "sma_trend", "macd_signal", "bollinger_signal", "rsi_signal",
      "stochastic_signal", "cmf_signal", "obv_signal", "adx_signal", "atr_signal",
      "vol_spike", "patterns" (max 3), "anomaly_events" (max 3), etc.
    Your tasks:
    1. **Validation:** For each agent, cross-check the summary against its signals. Flag any summaries that are unsupported or inconsistent with the signals, and explain how you adjusted your confidence or weighting.
    2. **Weighting:** Dynamically weigh the input of each agent depending on the strength, consensus, or contradiction among their signals.
    3. **Grand Outlook:**
        - Write a **Technical Summary** for analysts. Begin with the explicit outlook horizon (e.g. "Technical 7-Day Outlook: ..."). Integrate signals, highlight composite risk, and call out any red/green flags. Be dense and professional.
        - Write a **Plain-English Summary** for executives. Begin with the horizon ("In the next 7 days, ..."). Use simple language. Emphasize major opportunities, warnings, and actionable recommendations.
        - Explicitly state the overall risk level, and mention any “red flags” or “green lights” for investors.
    Be transparent: Briefly explain how you weighed/adjusted agent opinions, and call out any hallucinations, inconsistencies, or notable disagreements.
    Format your output exactly as:
    Technical Summary:
    ...
    Plain-English Summary:
    ...
    """,

    "stock":    "Technical analysis for {ticker}:\n{input}\nSummarize in plain English.",
    "sector":   "Sector performance summary:\n{input}\nExplain main drivers.",
    
    "market": """
    You are the Chief Technical Analyst for an Asia/SGX-focused fund.
    
    You will receive a JSON summary containing:
    - Today's composite score and risk regime
    - The last 60 days of composite score history
    - Breadth statistics (how many indices above SMA50/SMA200)
    - Relative performance vs S&P 500
    - Alerts (anomalies, regime shifts)
    - Cross-asset correlation
    
    Your job:
    1. Write a concise market technical outlook in plain English, for a busy executive. Mention key shifts (bullish/neutral/bearish), regime changes, breadth, any unusual correlations, and alert on big risks.
    2. If market conditions are especially strong or risky, call them out explicitly.
    3. End with an action-oriented bullet ("What to watch next week" or "AI Outlook").
    4. Output BOTH:
       - a Markdown summary for the dashboard (max 150 words)
       - a structured JSON object:
         {{
            "headline": "...",
            "summary": "...",
            "regime": "...",
            "outlook": "...",
            "risk_level": "...",
            "action": "..."
         }}
    Input:
    {input}
    """,

    "commodities": "Commodities report:\n{input}\nHighlight risks and trends.",
    
    "global": """
    You are a world-class macro technical analyst with the ability to interpret not only current global market conditions, but also the likely persistence and forward risk/outlook for each major trend.
    
    You will receive a JSON summary of current global volatility, trend, major indices, FX rates, yields, commodities, breadth, and risk regime. For each signal (trend or regime), consider both its **lookback window** (e.g., 30d = short-term, 90d = medium-term, 200d = long-term) and **recent price action** to infer how likely the trend is to persist into the near future. If a trend is based on the 200-day window, note that it is more likely to persist unless a recent reversal is detected.
    
    {input}
    
    Your tasks:
    1. Write a dense, forward-looking technical global macro summary for professional investors.
        - Clearly state the explicit **outlook horizon** (“In the next 7 days...”) at the start.
        - Highlight the current technical regime, strongest uptrends and downtrends, key macro risks, and expected duration or persistence of each major signal.
        - Call out any changes in trend, cross-market divergences, or volatility shifts.
    
    2. Write a plain-English summary for executives or non-technical readers.
        - Start with the outlook horizon (“In the coming week…” or “Looking ahead…”)
        - Emphasize risk regime, what’s trending, and any actionable implications.
        - If a trend is likely short-lived (e.g., based only on a 30-day window), say so. If a trend is likely persistent (200d), explain why.
    
    3. State the lookback windows analyzed (30, 90, 200 days) and explain how they inform your view of trend persistence.
    
    4. Explicitly list “Potential Red Flags” (risks, downtrends, or volatility spikes) and “Potential Green Lights” (sustained uptrends or positive regimes), *including your confidence in whether they are likely to persist or reverse soon.*
    
    5. Reference the news section if provided.
    
    6. In a final section, explain *in 2-4 sentences*:
    - Why the composite market score is **{composite_label}**.
    - And why the risk regime is **{risk_regime}**.
    Reference key drivers such as: which indices or assets are up/down, breadth readings, volatility, and any notable divergences.
    Clearly justify both labels using specific facts from the summary. If the regime is Neutral, mention what is mixed or uncertain.

    **Output format:**
    
    Technical Summary  
    [Professional, dense technical analysis – including trend persistence, horizon, and explicit risk regime]
    
    Plain-English Summary  
    [Executive summary for non-technical readers – clarity on which signals are likely to last and why]
    
    Lookback Windows Analyzed: [list windows]
    
    Potential Red Flags:  
    [List, with note on expected persistence]
    
    Potential Green Lights:  
    [List, with note on expected persistence]
    
    Explanation:  
    [Short “why {composite_label}” justification, referencing data and key drivers]
    [Short “why {risk_regime}” justification, referencing data and key drivers]
    
    Reference the news section for any timely or external drivers not visible in the technicals.
    """,
    }

# === AGENT TO BRAIN MAPPING ===

AGENT_BRAINS = {
    "chief": {
        "provider": "openai",
        "model": "gpt-3.5-turbo",
        "api_key": os.getenv("OPENAI_API_KEY"),
        "prompt_template": PROMPT_TEMPLATES["chief"],
    },
    "stock": {
        "provider": "openai",
        "model": "gpt-3.5-turbo",
        "api_key": os.getenv("OPENAI_API_KEY"),
        "prompt_template": PROMPT_TEMPLATES["stock"],
    },
    "sector": {
        "provider": "openai",
        "model": "gpt-4o",
        "api_key": os.getenv("OPENAI_API_KEY"),
        "prompt_template": PROMPT_TEMPLATES["sector"],
    },
    "market": {
        "provider": "openai",
        "model": "gpt-3.5-turbo",
        "api_key": os.getenv("OPENAI_API_KEY"),
        "prompt_template": PROMPT_TEMPLATES["market"],
    },
    "commodities": {
        "provider": "gemini",
        "model": "gemini-1.5-flash",
        "api_key": os.getenv("GEMINI_API_KEY"),
        "prompt_template": PROMPT_TEMPLATES["commodities"],
    },
    "global": {
        "provider": "openai",
        "model": "gpt-3.5-turbo",
        "api_key": os.getenv("OPENAI_API_KEY"),
        "prompt_template": PROMPT_TEMPLATES["global"],
    },
}

# === PATCH OPENAI API KEYS FROM STREAMLIT SECRETS IF AVAILABLE ===

try:
    import streamlit as st
    OPENAI_KEY = st.secrets["OPENAI_API_KEY"]
except Exception:
    OPENAI_KEY = os.getenv("OPENAI_API_KEY")

for agent, config in AGENT_BRAINS.items():
    if config.get("provider") == "openai":
        config["api_key"] = OPENAI_KEY

# === MAIN ENTRYPOINT ===

REQUEST_TIMEOUT = 60  # seconds

def call_llm(agent_name, input_text, prompt_vars=None, override_prompt=None, **kwargs):
    """
    agent_name: e.g., 'stock', 'chief', etc.
    input_text: main content to analyze/summarize
    prompt_vars: dict, extra vars for prompt template (e.g., {'ticker': 'A17U.SI'})
    override_prompt: str, if you want to override the default template
    kwargs: provider/model-specific extra arguments
    """
    brain = AGENT_BRAINS[agent_name]
    provider = brain["provider"]
    model = brain["model"]
    api_key = brain["api_key"]

    prompt_template = override_prompt or brain["prompt_template"]
    prompt_vars = prompt_vars or {}
    prompt_vars["input"] = input_text
    prompt = prompt_template.format(**prompt_vars)

    # Pick correct function
    if provider == "openai":
        fn = call_openai
        fn_args = (model, prompt, api_key)
    elif provider == "gemini":
        fn = call_gemini
        fn_args = (model, prompt, api_key)
    elif provider == "claude":
        fn = call_claude
        fn_args = (model, prompt, api_key)
    else:
        raise ValueError(f"Unknown provider: {provider}")

    # Enqueue in provider's queue
    fut = Future()
    q = _provider_queues[provider]
    try:
        q.put((fn, fn_args, kwargs, fut), timeout=5)
    except queue.Full:
        raise RuntimeError(f"{provider} LLM request queue is full. Please try again later.")

    try:
        return fut.result(timeout=REQUEST_TIMEOUT)
    except Exception as e:
        raise e
