import yfinance as yf
import pandas as pd
import numpy as np
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from llm_utils import call_llm  # <<<<<< CENTRALIZED LLM UTILITY

def fetch_data(ticker, lookback_days=30, interval="1d"):
    end_date = pd.Timestamp.today()
    start_date = end_date - pd.Timedelta(days=lookback_days * 2)
    data = yf.download(
        tickers=ticker,
        start=start_date.strftime("%Y-%m-%d"),
        end=end_date.strftime("%Y-%m-%d"),
        interval=interval,
        progress=False
    )
    data = data.reset_index()
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = [
            '_'.join(filter(None, map(str, col))).replace(f"_{ticker}", "")
            for col in data.columns.values
        ]
    return data 

def enforce_date_column(df):
    if 'Date' not in df.columns:
        df = df.reset_index()
        possible = [col for col in df.columns if 'date' in col.lower() or 'time' in col.lower()]
        if possible and possible[0] != 'Date':
            df.rename(columns={possible[0]: 'Date'}, inplace=True)
        elif 'Date' not in df.columns:
            df['Date'] = pd.to_datetime(df.index)
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date').drop_duplicates('Date').reset_index(drop=True)
    return df

def decide_lookback_days(horizon: str):
    try:
        num = int(''.join(filter(str.isdigit, horizon)))
    except:
        num = 7
    lookback_days = max(30, num * 3)
    lookback_days = min(lookback_days, 360)
    return lookback_days

def calculate_indicators(df):
    df['SMA5'] = df['Close'].rolling(window=5).mean()
    df['SMA10'] = df['Close'].rolling(window=10).mean()
    df['Upper'] = df['SMA10'] + 2 * df['Close'].rolling(window=10).std()
    df['Lower'] = df['SMA10'] - 2 * df['Close'].rolling(window=10).std()
    delta = df['Close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    exp12 = df['Close'].ewm(span=12, adjust=False).mean()
    exp26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp12 - exp26
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    df['ATR'] = ranges.max(axis=1).rolling(window=14).mean()
    low_min = df['Low'].rolling(window=14).min()
    high_max = df['High'].rolling(window=14).max()
    df['Stochastic_%K'] = 100 * (df['Close'] - low_min) / (high_max - low_min)
    df['Stochastic_%D'] = df['Stochastic_%K'].rolling(window=3).mean()
    mfv = ((df['Close'] - df['Low']) - (df['High'] - df['Close'])) / (df['High'] - df['Low'] + 1e-9) * df['Volume']
    df['CMF'] = mfv.rolling(window=20).sum() / df['Volume'].rolling(window=20).sum()
    obv = [0]
    for i in range(1, len(df)):
        if df.loc[i, 'Close'] > df.loc[i-1, 'Close']:
            obv.append(obv[-1] + df.loc[i, 'Volume'])
        elif df.loc[i, 'Close'] < df.loc[i-1, 'Close']:
            obv.append(obv[-1] - df.loc[i, 'Volume'])
        else:
            obv.append(obv[-1])
    df['OBV'] = obv
    df['ADX'] = np.nan
    return df

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

def analyze(
    ticker,
    company_name=None,
    horizon="7 Days",
    lookback_days=None,
    api_key=None  # Not used; all LLM logic centralized now
):
    if lookback_days is None:
        lookback_days = decide_lookback_days(horizon)

    df = fetch_data(ticker, lookback_days=lookback_days)
    df = enforce_date_column(df)
    df = calculate_indicators(df)

    indicator_cols = [
        "Open", "High", "Low", "Close", "SMA5", "SMA10", "Upper", "Lower",
        "RSI", "MACD", "Signal", "Volume", "ATR", "Stochastic_%K",
        "Stochastic_%D", "CMF", "OBV", "ADX"
    ]
    for col in indicator_cols:
        if col not in df.columns:
            df[col] = np.nan

    existing_cols = [col for col in indicator_cols if col in df.columns]
    remaining_cols = [c for c in df.columns if c not in existing_cols]
    cols_to_use = [col for col in existing_cols + remaining_cols if col in df.columns]
    df = df[cols_to_use]

    # --- Handle no/empty data robustly ---
    if df.empty or df["Close"].isna().all():
        summary = {
            "summary": f"⚠️ No data available for {ticker}.",
            "sma_trend": "N/A",
            "macd_signal": "N/A",
            "bollinger_signal": "N/A",
            "rsi_signal": "N/A",
            "stochastic_signal": "N/A",
            "cmf_signal": "N/A",
            "obv_signal": "N/A",
            "adx_signal": "N/A",
            "atr_signal": "N/A",
            "vol_spike": False,
            "patterns": [],
            "anomaly_events": [],
            "heatmap_signals": {},
            "composite_risk_score": np.nan,
            "risk_level": "N/A",
            "lookback_days": lookback_days,
            "horizon": horizon,
            "llm_technical_summary": "No LLM report (no data available).",
            "llm_plain_summary": "No LLM report (no data available).",
            "df": df,
            "chart": None
        }
        summary["llm_summary"] = summary["llm_technical_summary"]
        return summary

    # --- Compute signal summaries (simple rules; customize as needed) ---
    sma_trend = "Bullish" if df['SMA5'].iloc[-1] > df['SMA10'].iloc[-1] else "Bearish"
    macd_signal = "Bullish" if df['MACD'].iloc[-1] > df['Signal'].iloc[-1] else "Bearish"
    rsi_signal = (
        "Overbought" if df['RSI'].iloc[-1] > 70 else
        "Oversold" if df['RSI'].iloc[-1] < 30 else
        "Neutral"
    )
    bollinger_signal = (
        "Breakout" if df['Close'].iloc[-1] > df['Upper'].iloc[-1]
        else "Breakdown" if df['Close'].iloc[-1] < df['Lower'].iloc[-1]
        else "Neutral"
    )
    stochastic_signal = (
        "Overbought" if df['Stochastic_%K'].iloc[-1] > 80 else
        "Oversold" if df['Stochastic_%K'].iloc[-1] < 20 else
        "Neutral"
    )
    cmf_signal = "Bullish" if df['CMF'].iloc[-1] > 0 else "Bearish"
    obv_signal = "Up" if df['OBV'].iloc[-1] > df['OBV'].iloc[-10] else "Down"
    adx_signal = "Strong Trend" if df['ADX'].iloc[-1] > 25 else "Weak/No Trend"
    atr_signal = "High Volatility" if df['ATR'].iloc[-1] > df['ATR'].rolling(window=30).mean().iloc[-1] else "Normal"
    vol_spike = bool(df['Volume'].iloc[-1] > df['Volume'].rolling(window=30).mean().iloc[-1] * 1.5)
    patterns = []
    anomaly_events = []

    summary = {
        "summary": f"{sma_trend} SMA, {macd_signal} MACD, {rsi_signal} RSI, {bollinger_signal} Bollinger, "
                   f"{stochastic_signal} Stochastic, {cmf_signal} CMF, {obv_signal} OBV, "
                   f"{adx_signal} ADX, {atr_signal} ATR",
        "sma_trend": sma_trend,
        "macd_signal": macd_signal,
        "bollinger_signal": bollinger_signal,
        "rsi_signal": rsi_signal,
        "stochastic_signal": stochastic_signal,
        "cmf_signal": cmf_signal,
        "obv_signal": obv_signal,
        "adx_signal": adx_signal,
        "atr_signal": atr_signal,
        "vol_spike": vol_spike,
        "patterns": patterns,
        "anomaly_events": anomaly_events,
        "heatmap_signals": {},
        "composite_risk_score": 0.5,
        "risk_level": "Caution",
        "lookback_days": lookback_days,
        "horizon": horizon,
        "df": df
    }

    # LLM Dual Summary (technical & plain-English)
    try:
        signal_keys = [
            "sma_trend", "macd_signal", "bollinger_signal", "rsi_signal",
            "stochastic_signal", "cmf_signal", "obv_signal", "adx_signal",
            "atr_signal", "vol_spike", "patterns", "anomaly_events", "horizon", "risk_level"
        ]
        slim_signals = {k: summary.get(k) for k in signal_keys}
        if isinstance(slim_signals.get("patterns"), list):
            slim_signals["patterns"] = slim_signals["patterns"][:3]
        if isinstance(slim_signals.get("anomaly_events"), list):
            slim_signals["anomaly_events"] = slim_signals["anomaly_events"][:3]
        llm_output = call_llm(
            agent_name="stock",
            input_text=str(slim_signals)
        )
        tech, plain = parse_dual_summary(llm_output)
        summary["llm_technical_summary"] = tech
        summary["llm_plain_summary"] = plain
    except Exception as e:
        summary["llm_technical_summary"] = f"LLM error: {e}"
        summary["llm_plain_summary"] = f"LLM error: {e}"

    summary["llm_summary"] = summary.get("llm_technical_summary", summary["summary"])

    # --- Chart section unchanged ---
    fig = make_subplots(
        rows=9, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        row_heights=[0.36, 0.09, 0.09, 0.09, 0.09, 0.07, 0.07, 0.07, 0.07],
        subplot_titles=[
            "Price (Candlestick, SMA, Bollinger Bands)",
            "Volume",
            "RSI",
            "MACD",
            "Stochastic Oscillator",
            "Chaikin Money Flow (CMF)",
            "On-Balance Volume (OBV)",
            "ATR",
            "ADX"
        ]
    )

    # 1. Candlestick and overlays
    fig.add_trace(go.Candlestick(
        x=df['Date'],
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name='Candlestick'
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=df['Date'], y=df['SMA5'], mode='lines', name='SMA5'
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=df['Date'], y=df['SMA10'], mode='lines', name='SMA10'
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=df['Date'], y=df['Upper'], mode='lines', line=dict(dash='dot'), name='Upper Bollinger'
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=df['Date'], y=df['Lower'], mode='lines', line=dict(dash='dot'), name='Lower Bollinger'
    ), row=1, col=1)

    # 2. Volume
    fig.add_trace(go.Bar(
        x=df['Date'], y=df['Volume'],
        marker_color='rgba(0,100,255,0.4)', name='Volume'
    ), row=2, col=1)

    # 3. RSI
    fig.add_trace(go.Scatter(
        x=df['Date'], y=df['RSI'],
        mode='lines', name='RSI', line=dict(color='orange')
    ), row=3, col=1)
    fig.add_shape(type="line", x0=df['Date'].min(), y0=70, x1=df['Date'].max(), y1=70,
                  line=dict(color="red", width=1, dash="dash"), row=3, col=1)
    fig.add_shape(type="line", x0=df['Date'].min(), y0=30, x1=df['Date'].max(), y1=30,
                  line=dict(color="green", width=1, dash="dash"), row=3, col=1)

    # 4. MACD & Signal
    fig.add_trace(go.Scatter(
        x=df['Date'], y=df['MACD'],
        mode='lines', name='MACD', line=dict(color='blue')
    ), row=4, col=1)
    fig.add_trace(go.Scatter(
        x=df['Date'], y=df['Signal'],
        mode='lines', name='MACD Signal', line=dict(color='purple', dash='dot')
    ), row=4, col=1)

    # 5. Stochastic Oscillator
    fig.add_trace(go.Scatter(
        x=df['Date'], y=df['Stochastic_%K'],
        mode='lines', name='%K', line=dict(color='darkgreen')
    ), row=5, col=1)
    fig.add_trace(go.Scatter(
        x=df['Date'], y=df['Stochastic_%D'],
        mode='lines', name='%D', line=dict(color='magenta', dash='dot')
    ), row=5, col=1)

    # 6. CMF
    fig.add_trace(go.Scatter(
        x=df['Date'], y=df['CMF'],
        mode='lines', name='CMF', line=dict(color='teal')
    ), row=6, col=1)

    # 7. OBV
    fig.add_trace(go.Scatter(
        x=df['Date'], y=df['OBV'],
        mode='lines', name='OBV', line=dict(color='gray')
    ), row=7, col=1)

    # 8. ATR
    fig.add_trace(go.Scatter(
        x=df['Date'], y=df['ATR'],
        mode='lines', name='ATR', line=dict(color='brown')
    ), row=8, col=1)

    # 9. ADX
    fig.add_trace(go.Scatter(
        x=df['Date'], y=df['ADX'],
        mode='lines', name='ADX', line=dict(color='black')
    ), row=9, col=1)

    fig.update_layout(
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=15, r=15, t=40, b=15),
        height=1800
    )
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    fig.update_yaxes(title_text="RSI", row=3, col=1, range=[0, 100])
    fig.update_yaxes(title_text="MACD", row=4, col=1)
    fig.update_yaxes(title_text="Stochastic", row=5, col=1, range=[0, 100])
    fig.update_yaxes(title_text="CMF", row=6, col=1)
    fig.update_yaxes(title_text="OBV", row=7, col=1)
    fig.update_yaxes(title_text="ATR", row=8, col=1)
    fig.update_yaxes(title_text="ADX", row=9, col=1)

    summary["chart"] = fig

    return summary







