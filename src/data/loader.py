# src/data/loader.py
import pandas as pd
from pathlib import Path

"""
In this module, we clean the data and store it in processed folder.
"""

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
PROC_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"


def load_raw_prices(filename: str = "multi_asset_prices.csv") -> pd.DataFrame:
    """Load raw price CSV into a DataFrame with Date index."""
    path = RAW_DIR / filename
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    df = df.sort_index()
    return df


def preprocess_prices(
    prices: pd.DataFrame,
    min_assets: int = 3,
    drop_na: bool = True,
) -> pd.DataFrame:
    """
    Basic cleaning: drop days with too many missing, forward-fill small gaps.

    Parameters
    ----------
    prices : pd.DataFrame
        Raw price table, columns=tickers.
    min_assets : int
        Require at least this many non-NA assets per day.
    drop_na : bool
        If True, drop dates with fewer than `min_assets` valid prices.

    Returns
    -------
    pd.DataFrame
        Cleaned price table.
    """
    df = prices.copy()

    # at least has min_assets with prices，or delete this row
    if drop_na:
        mask = df.notna().sum(axis=1) >= min_assets
        df = df[mask]

    # forward fill first，then back fill ，fill the NA
    df = df.ffill().bfill()

    PROC_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PROC_DIR / "prices_clean.csv"
    df.to_csv(out_path)
    print(f"Saved cleaned prices to {out_path.resolve()}")

    return df


if __name__ == "__main__":
    prices = load_raw_prices()
    preprocess_prices(prices)
