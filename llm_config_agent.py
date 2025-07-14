# llm_config_agent.py

import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Optional fallback config if GPT fails
DEFAULT_META = {
    "sector_peers": [],
    "market_index": "^STI",
    "commodities": [],
    "globals": ["^DJI", "^HSI", "^N225"]
}

def generate_meta_config(ticker: str, company_name: str) -> dict:
    prompt = f"""
You are an expert financial analyst AI.

Given the company:
- Ticker: {ticker}
- Name: {company_name}

Provide the following:
1. Up to 5 SGX ticker peers from the same sector (excluding the input ticker if possible)
2. The main index this stock belongs to (e.g., ^STI)
3. Any related commodities that affect this stock's performance (e.g., oil, gold)
4. 2-3 relevant global indices (e.g., ^DJI, ^HSI, ^N225)

Return only a JSON object with keys: sector_peers, market_index, commodities, globals.
Use SGX or Yahoo Finance-compatible tickers.
NO explanation or commentary.
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )
        reply = response.choices[0].message.content.strip()
        config = eval(reply)
        # Sanity check for keys
        for key in ["sector_peers", "market_index", "commodities", "globals"]:
            if key not in config:
                raise ValueError("Missing key in config")
        return config
    except Exception as e:
        print(f"[LLM Config Agent] Fallback used due to error: {e}")
        return DEFAULT_META
