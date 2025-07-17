# data_utils.py

import pandas as pd
import yfinance as yf

# Define universal columns for platform-wide consistency
UNIVERSAL_COLUMNS = [
    "date", "open", "high", "low", "close", "adj_close", "volume", "ticker"
]

def enforce_1d_column(series_or_df):
    """
    Ensures input is a 1D pandas Series, even if given a DataFrame or ndarray.
    """
    # If it's a DataFrame, take first column
    if isinstance(series_or_df, pd.DataFrame):
        return series_or_df.iloc[:, 0]
    # If it's a numpy array, squeeze to 1D
    if hasattr(series_or_df, "ndim") and series_or_df.ndim > 1 and series_or_df.shape[1] == 1:
        return pd.Series(series_or_df.ravel())
    return series_or_df

def fetch_clean_yfinance(
    ticker,
    start,
    end=None,
    interval="1d",
    min_points=20,
    auto_adjust=False
):
    """
    Download and clean OHLCV data from yfinance for the given ticker.
    - Returns a DataFrame with universal column names, DatetimeIndex, and a ticker column.
    - Always includes all UNIVERSAL_COLUMNS (fills with pd.NA if missing).
    - Returns: (DataFrame, None) on success; (None, error_msg) on failure.
    """
    end = end or pd.Timestamp.today()
    try:
        df = yf.download(
            ticker,
            start=start,
            end=end,
            interval=interval,
            auto_adjust=auto_adjust,
            progress=False,
        )

        # Defensive: flatten MultiIndex columns (rare, but happens)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = ["_".join(str(c) for c in col if c and c != "None") for col in df.columns.values]

        # Normalize columns: case-insensitive match for OHLCV
        colmap = {}
        for c in df.columns:
            lc = c.lower()
            if "open" == lc:
                colmap[c] = "open"
            elif "high" == lc:
                colmap[c] = "high"
            elif "low" == lc:
                colmap[c] = "low"
            elif lc == "close" or (lc.startswith("close") and "adj" not in lc):
                colmap[c] = "close"
            elif "adj close" in lc or "adjclose" in lc:
                colmap[c] = "adj_close"
            elif "volume" in lc:
                colmap[c] = "volume"
        df = df.rename(columns=colmap)

        # Add missing universal columns
        for col in UNIVERSAL_COLUMNS:
            if col not in df.columns:
                df[col] = pd.NA

        # Only keep universal columns
        df = df[UNIVERSAL_COLUMNS]
        # Ensure DatetimeIndex, add 'date' as a column
        df.index = pd.to_datetime(df.index)
        df = df.reset_index(drop=False).rename(columns={"index": "date"})
        df["ticker"] = ticker

        # Defensive: flatten any column that might be a DataFrame or multidim object
        for col in UNIVERSAL_COLUMNS:
            df[col] = enforce_1d_column(df[col])

        # Drop all-NaN rows in 'close', 'open', etc.
        df = df.dropna(subset=["close"], how="all")
        # Fill missing values if possible (forward fill)
        df = df.fillna(method="ffill")

        # Check for enough valid points
        if len(df) < min_points:
            return None, f"Insufficient data for {ticker} (only {len(df)} points)"

        # Defensive: remove still-empty rows
        df = df.dropna(subset=["close"], how="any")

        # If still empty, return error
        if df.empty:
            return None, f"No usable data for {ticker}"

        return df, None
    except Exception as e:
        return None, f"Data error for {ticker}: {e}"

# Optionally: batch fetch, to/from csv helpers, or other data source wrappers

if __name__ == "__main__":
    # Simple self-test
    df, err = fetch_clean_yfinance("ES3.SI", start="2023-01-01")
    if err:
        print("Error:", err)
    else:
        print(df.head())

