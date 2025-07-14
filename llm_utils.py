"""
llm_utils.py

Unified LLM utility for multi-agent "brain swapping" with agent-to-provider/model/prompt mapping.
Features per-provider concurrency limits, request queues, and robust error handling.
Plug-and-play: agents call call_llm() for all LLM access—configuration is fully centralized.
"""
# llm_utils.py

import os
import threading
import queue
from concurrent.futures import Future

# === PROVIDER CONCURRENCY LIMITS ===

PROVIDER_LIMITS = {
    "openai":   {"max_concurrent": 3, "queue_maxsize": 40},
    "gemini":   {"max_concurrent": 2, "queue_maxsize": 20},
    "claude":   {"max_concurrent": 1, "queue_maxsize": 10},
    # Add more if needed
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

# === PROMPT TEMPLATES ===

PROMPT_TEMPLATES = {
    "chief": """
    You are the Chief AI Investment Analyst for a global asset management firm.
    You will receive a JSON object with the following structure:
    
    {
      "composite_risk_score": float,     # overall composite risk score (0–1)
      "risk_level": string,              # overall risk label
      "horizon": string,                 # outlook horizon (e.g. "7 Days")
      "stock": { ... },                  # signals, summary, risk_level for the stock
      "sector": { ... },                 # signals, summary, risk_level for the sector
      "market": { ... },                 # signals, summary, risk_level for the overall market
      "commodity": { ... },              # signals, summary, risk_level for key commodities
      "global": { ... }                  # signals, summary, risk_level for global factors
    }
    
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
    "market":   "Market overview:\n{input}\nProvide key insights.",
    "commodities": "Commodities report:\n{input}\nHighlight risks and trends.",
    "globals":  "Global economic context:\n{input}\nSummarize impact on markets.",
}

# === AGENT TO BRAIN MAPPING ===

AGENT_BRAINS = {
    "chief": {
        "provider": "openai",
        "model": "gpt-4o",
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
        "provider": "gemini",
        "model": "gemini-1.5-pro",
        "api_key": os.getenv("GEMINI_API_KEY"),
        "prompt_template": PROMPT_TEMPLATES["market"],
    },
    "commodities": {
        "provider": "gemini",
        "model": "gemini-1.5-flash",
        "api_key": os.getenv("GEMINI_API_KEY"),
        "prompt_template": PROMPT_TEMPLATES["commodities"],
    },
    "globals": {
        "provider": "claude",
        "model": "claude-3-opus-20240229",
        "api_key": os.getenv("CLAUDE_API_KEY"),
        "prompt_template": PROMPT_TEMPLATES["globals"],
    },
}

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
