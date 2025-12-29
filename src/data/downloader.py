# src/data/downloader.py
#read data from yhoo and store it into the raw directory
import yfinance as yf
import pandas as pd
from pathlib import Path
from typing import List, Union
import time
import pandas_datareader as pdr

"""
In this module, we extract data from yfinance to get daily data.
And store them in the raw folder
"""

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


def download_history(
    tickers: Union[str, List[str]],
    start: str = "2005-01-01",
    end: str | None = None,
    auto_adjust: bool = True,
) -> pd.DataFrame:
    """
    Download daily price history for a list of tickers and save as CSV.

    Parameters
    ----------
    tickers : list[str]
        List of ticker symbols, e.g. ["SPY", "TLT"].
    start : str
        Start date "YYYY-MM-DD".
    end : str | None
        End date "YYYY-MM-DD" or None for latest.
    auto_adjust : bool
        Use adjusted close if True.

    Returns
    -------
    pd.DataFrame
        Price DataFrame (Adj Close or Close).
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    price_field = "Adj Close" if auto_adjust else "Close"

    # Convert single ticker to list for uniform handling
    if isinstance(tickers, str):
        tickers = [tickers]

    # Download tickers one at a time with delays to avoid rate limits
    ticker_dfs = {}
    failed_tickers = []

    for i, ticker in enumerate(tickers):
        try:
            print(f"Downloading {ticker} ({i+1}/{len(tickers)})...")

            # Use Ticker API instead of download() - different endpoint
            ticker_obj = yf.Ticker(ticker)
            data = ticker_obj.history(start=start, end=end, auto_adjust=auto_adjust)

            if data.empty:
                print(f"  Warning: No data returned for {ticker}")
                failed_tickers.append(ticker)
                continue

            # Ticker.history() returns Close column (already adjusted if auto_adjust=True)
            if 'Close' in data.columns:
                ticker_dfs[ticker] = data['Close']
            else:
                print(f"  Warning: No price data for {ticker}")
                failed_tickers.append(ticker)
                continue

            print(f"  Success: {len(data)} rows downloaded")

            # Add delay between requests to avoid rate limiting (except for last ticker)
            if i < len(tickers) - 1:
                time.sleep(2)

        except Exception as e:
            print(f"  Error downloading {ticker}: {e}")
            failed_tickers.append(ticker)

    if not ticker_dfs:
        raise ValueError("No data downloaded for any ticker!")

    # Combine all ticker dataframes
    df = pd.DataFrame(ticker_dfs)

    if failed_tickers:
        print(f"\nFailed to download: {failed_tickers}")

    csv_path = DATA_DIR / "multi_asset_prices.csv"
    df.to_csv(csv_path)
    print(f"Saved prices to {csv_path.resolve()}")

    return df


def download_history_stooq(
    tickers: Union[str, List[str]],
    start: str = "2005-01-01",
    end: str | None = None,
) -> pd.DataFrame:
    """
    Download daily price history using Stooq data source (alternative to Yahoo Finance).

    Parameters
    ----------
    tickers : list[str]
        List of ticker symbols, e.g. ["SPY", "TLT"].
    start : str
        Start date "YYYY-MM-DD".
    end : str | None
        End date "YYYY-MM-DD" or None for latest.

    Returns
    -------
    pd.DataFrame
        Price DataFrame with Close prices.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Convert single ticker to list
    if isinstance(tickers, str):
        tickers = [tickers]

    ticker_dfs = {}
    failed_tickers = []

    for i, ticker in enumerate(tickers):
        try:
            print(f"Downloading {ticker} from Stooq ({i+1}/{len(tickers)})...")

            # Stooq uses US ticker format
            data = pdr.DataReader(ticker, 'stooq', start=start, end=end)

            if data.empty:
                print(f"  Warning: No data returned for {ticker}")
                failed_tickers.append(ticker)
                continue

            # Stooq returns data in reverse chronological order, so sort it
            data = data.sort_index()

            if 'Close' in data.columns:
                ticker_dfs[ticker] = data['Close']
                print(f"  Success: {len(data)} rows downloaded")
            else:
                print(f"  Warning: No Close price for {ticker}")
                failed_tickers.append(ticker)
                continue

            # Small delay between requests
            if i < len(tickers) - 1:
                time.sleep(1)

        except Exception as e:
            print(f"  Error downloading {ticker}: {e}")
            failed_tickers.append(ticker)

    if not ticker_dfs:
        raise ValueError("No data downloaded for any ticker!")

    # Combine all ticker dataframes
    df = pd.DataFrame(ticker_dfs)

    if failed_tickers:
        print(f"\nFailed to download: {failed_tickers}")

    csv_path = DATA_DIR / "multi_asset_prices.csv"
    df.to_csv(csv_path)
    print(f"\nSaved prices to {csv_path.resolve()}")

    return df


if __name__ == "__main__":
    # Read from config file
    import yaml
    config_path = Path(__file__).resolve().parents[2] / "config" / "universe.yaml"

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    universe = config['universe']
    start_date = config['data']['start_date']
    end_date = config['data']['end_date']

    print(f"Loading configuration from {config_path}")
    print(f"Universe: {universe}")
    print(f"Date range: {start_date} to {end_date or 'latest'}\n")

    # Use Stooq as alternative data source (Yahoo Finance is rate-limited)
    print("Using Stooq data source (alternative to Yahoo Finance)\n")
    download_history_stooq(universe, start=start_date, end=end_date)



