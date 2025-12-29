"""
Carry Signal Calculation with Real Data

This module calculates carry signals using actual market data:
- Bonds: Treasury yields (FRED API)
- Equities: Dividend yields (Yahoo Finance)
- Commodities: Limited (futures curve data not available)

⚠️ REQUIRES:
- FRED API key (free from https://fred.stlouisfed.org/docs/api/api_key.html)
- Set environment variable: FRED_API_KEY=your_key_here
"""

import pandas as pd
import numpy as np
import yfinance as yf
from pathlib import Path
from typing import Dict, Optional, Tuple
import warnings
import os

try:
    from fredapi import Fred
    HAS_FRED = True
except ImportError:
    HAS_FRED = False
    warnings.warn("fredapi not installed. Bond carry will not be available.")


# ============================================================================
# Configuration
# ============================================================================

# TLT (iShares 20+ Year Treasury ETF) characteristics
TLT_DURATION = 17.0  # Modified duration (approximate)
TLT_YIELD_SERIES = 'DGS10'  # 10-year treasury constant maturity rate

# SPY characteristics
SPY_BENCHMARK = 'SPY'

# FRED API key (get free key from https://fred.stlouisfed.org/)
FRED_API_KEY = os.getenv('FRED_API_KEY', None)


# ============================================================================
# Bond Carry (Treasury Yields)
# ============================================================================

def download_treasury_yields(
    start_date: str = '2006-01-01',
    end_date: Optional[str] = None,
    api_key: Optional[str] = None
) -> pd.Series:
    """
    下载国债收益率数据 (FRED)

    Parameters
    ----------
    start_date : str
        起始日期 "YYYY-MM-DD"
    end_date : str, optional
        结束日期，None=最新
    api_key : str, optional
        FRED API key

    Returns
    -------
    pd.Series
        10年期国债收益率 (日频, %)

    Raises
    ------
    ValueError
        如果没有API key
    """
    if not HAS_FRED:
        raise ImportError("fredapi not installed. Run: pip install fredapi")

    if api_key is None:
        api_key = FRED_API_KEY

    if api_key is None:
        raise ValueError(
            "FRED API key required. Get free key from https://fred.stlouisfed.org/\n"
            "Set environment variable: FRED_API_KEY=your_key_here\n"
            "Or pass api_key parameter"
        )

    fred = Fred(api_key=api_key)

    print(f"Downloading 10Y Treasury yields from FRED...")
    yields = fred.get_series(TLT_YIELD_SERIES, observation_start=start_date, observation_end=end_date)

    print(f"Downloaded {len(yields)} observations")
    print(f"Date range: {yields.index.min()} to {yields.index.max()}")

    return yields


def calculate_bond_carry(
    treasury_yields: pd.Series,
    duration: float = TLT_DURATION,
    expected_yield_change: float = 0.0
) -> pd.Series:
    """
    计算债券真实carry

    Carry = Yield - Duration × Expected_Yield_Change

    对于持有期策略，假设yield不变 (expected_yield_change=0)
    则 Carry ≈ Yield

    Parameters
    ----------
    treasury_yields : pd.Series
        国债收益率 (%, 如 2.5 表示2.5%)
    duration : float
        修正久期 (TLT ≈ 17)
    expected_yield_change : float
        预期yield变化 (默认0，假设yield不变)

    Returns
    -------
    pd.Series
        年化carry (小数形式，如0.025表示2.5%)
    """
    # 转换为小数形式
    yield_decimal = treasury_yields / 100.0

    # Carry = yield - duration * expected_yield_change
    carry = yield_decimal - duration * expected_yield_change

    return carry


# ============================================================================
# Equity Carry (Dividend Yields)
# ============================================================================

def download_dividend_yields(
    tickers: list,
    start_date: str = '2006-01-01',
    end_date: Optional[str] = None
) -> pd.DataFrame:
    """
    下载股票/ETF的股息收益率

    ⚠️ yfinance的dividend yield数据质量问题:
    - 不是时间序列，只有最新值
    - 需要从dividends和price手动计算

    Parameters
    ----------
    tickers : list
        股票代码列表
    start_date : str
        起始日期
    end_date : str, optional
        结束日期

    Returns
    -------
    pd.DataFrame
        股息收益率时间序列 (columns=tickers)
    """
    div_yields = pd.DataFrame()

    for ticker in tickers:
        print(f"Downloading dividend data for {ticker}...")

        try:
            # Download stock data
            stock = yf.Ticker(ticker)

            # Get price history
            prices = stock.history(start=start_date, end=end_date)['Close']

            # Get dividend history
            dividends = stock.dividends

            # Filter to date range
            if end_date:
                dividends = dividends[dividends.index <= end_date]

            dividends = dividends[dividends.index >= start_date]

            # Calculate trailing 12-month dividend yield
            # Resample dividends to daily and forward-fill
            div_daily = dividends.resample('D').sum()

            # Rolling 12-month sum of dividends
            trailing_12m_div = div_daily.rolling(window=365, min_periods=30).sum()

            # Align with prices
            aligned_prices = prices.reindex(trailing_12m_div.index, method='ffill')

            # Dividend yield = trailing 12M dividends / current price
            div_yield = trailing_12m_div / aligned_prices

            div_yields[ticker] = div_yield

            print(f"  Success: {len(div_yield.dropna())} observations")
            print(f"  Recent yield: {div_yield.iloc[-1]:.2%}" if len(div_yield) > 0 else "  No data")

        except Exception as e:
            print(f"  Error: {e}")
            div_yields[ticker] = np.nan

    return div_yields


# ============================================================================
# Commodity Carry (Futures Curve)
# ============================================================================

def calculate_commodity_carry_placeholder(
    prices: pd.Series,
    method: str = 'none'
) -> pd.Series:
    """
    商品carry占位符

    ⚠️ 真实商品carry需要期货曲线数据 (front month vs back month prices)
    这些数据需要付费数据源 (Bloomberg, Quandl Futures, etc.)

    Parameters
    ----------
    prices : pd.Series
        商品ETF价格
    method : str
        'none': 返回NaN
        'momentum_proxy': 使用负动量作为粗略代理 (不推荐)

    Returns
    -------
    pd.Series
        Carry估计 (如果method='none'则全为NaN)
    """
    if method == 'none':
        warnings.warn(
            f"Commodity carry not available without futures curve data. "
            f"Returning NaN. Consider using momentum signal instead."
        )
        return pd.Series(np.nan, index=prices.index)

    elif method == 'momentum_proxy':
        warnings.warn(
            "Using negative momentum as rough commodity carry proxy. "
            "This is NOT real carry! Use with extreme caution."
        )
        # 短期动量的负值 (contango市场假设)
        momentum = prices.pct_change(21)
        return -momentum * (252 / 21)

    else:
        raise ValueError(f"Unknown method: {method}")


# ============================================================================
# Unified Carry Calculation
# ============================================================================

def calculate_all_carries_real(
    prices: pd.DataFrame,
    treasury_yields: Optional[pd.Series] = None,
    asset_classes: Optional[Dict[str, str]] = None,
    fred_api_key: Optional[str] = None
) -> pd.DataFrame:
    """
    计算所有资产的真实carry信号

    Parameters
    ----------
    prices : pd.DataFrame
        价格数据
    treasury_yields : pd.Series, optional
        国债收益率 (如果None，自动下载)
    asset_classes : Dict[str, str], optional
        资产类别映射 {'SPY': 'equity', ...}
    fred_api_key : str, optional
        FRED API key

    Returns
    -------
    pd.DataFrame
        Carry信号 (年化收益率)
    """
    if asset_classes is None:
        asset_classes = {
            'SPY': 'equity',
            'TLT': 'bond',
            'GLD': 'commodity',
            'DBC': 'commodity',
            'VNQ': 'equity'
        }

    carries = pd.DataFrame(index=prices.index)

    # 1. 下载国债收益率 (for bonds)
    if treasury_yields is None and any(v == 'bond' for v in asset_classes.values()):
        try:
            treasury_yields = download_treasury_yields(
                start_date=prices.index.min().strftime('%Y-%m-%d'),
                end_date=prices.index.max().strftime('%Y-%m-%d'),
                api_key=fred_api_key
            )
        except Exception as e:
            print(f"Warning: Could not download treasury yields: {e}")
            treasury_yields = None

    # 2. 下载股息收益率 (for equities)
    equity_tickers = [t for t, c in asset_classes.items() if c == 'equity' and t in prices.columns]
    if len(equity_tickers) > 0:
        try:
            div_yields = download_dividend_yields(
                equity_tickers,
                start_date=prices.index.min().strftime('%Y-%m-%d'),
                end_date=prices.index.max().strftime('%Y-%m-%d')
            )
        except Exception as e:
            print(f"Warning: Could not download dividend yields: {e}")
            div_yields = pd.DataFrame()
    else:
        div_yields = pd.DataFrame()

    # 3. 计算每个资产的carry
    for ticker in prices.columns:
        asset_class = asset_classes.get(ticker, 'equity')

        if asset_class == 'bond':
            if treasury_yields is not None:
                # 债券carry = yield
                bond_carry = calculate_bond_carry(treasury_yields)
                # 对齐到价格index
                carries[ticker] = bond_carry.reindex(prices.index, method='ffill')
                print(f"{ticker} (bond): Using real treasury yields")
            else:
                carries[ticker] = np.nan
                print(f"{ticker} (bond): No treasury data available")

        elif asset_class == 'equity':
            if ticker in div_yields.columns:
                # 股票carry = dividend yield
                carries[ticker] = div_yields[ticker]
                print(f"{ticker} (equity): Using real dividend yields")
            else:
                carries[ticker] = np.nan
                print(f"{ticker} (equity): No dividend data available")

        elif asset_class == 'commodity':
            # 商品：没有真实数据
            carries[ticker] = calculate_commodity_carry_placeholder(
                prices[ticker],
                method='none'  # 不使用代理
            )
            print(f"{ticker} (commodity): No futures curve data - carry unavailable")

        else:
            carries[ticker] = np.nan
            print(f"{ticker}: Unknown asset class '{asset_class}'")

    return carries


# ============================================================================
# Utility Functions
# ============================================================================

def validate_carry_data_availability() -> Dict[str, bool]:
    """
    检查carry数据源可用性

    Returns
    -------
    Dict[str, bool]
        {'fred': bool, 'yfinance': bool}
    """
    status = {}

    # Check FRED
    status['fred'] = HAS_FRED and (FRED_API_KEY is not None)

    # Check yfinance (always available if installed)
    try:
        import yfinance
        status['yfinance'] = True
    except ImportError:
        status['yfinance'] = False

    return status


def print_data_availability():
    """打印数据源状态"""
    status = validate_carry_data_availability()

    print("Carry Data Source Availability:")
    print("=" * 60)

    if status['fred']:
        print("[OK] FRED API: Available (Treasury yields)")
    else:
        if not HAS_FRED:
            print("[MISSING] FRED API: Not installed (pip install fredapi)")
        else:
            print("[MISSING] FRED API Key: Set FRED_API_KEY environment variable")
        print("         Get free key: https://fred.stlouisfed.org/")

    if status['yfinance']:
        print("[OK] Yahoo Finance: Available (Dividend yields)")
    else:
        print("[MISSING] yfinance: Not installed (pip install yfinance)")

    print("\nFutures Curve Data:")
    print("[UNAVAILABLE] Commodity futures curves require paid data")
    print("              Sources: Bloomberg, Quandl, CME DataMine")
    print("              Alternative: Use momentum signal for commodities")


# ============================================================================
# Main Execution
# ============================================================================

if __name__ == "__main__":
    print_data_availability()

    # Test if we can calculate carries
    data_dir = Path(__file__).resolve().parents[2] / "data" / "processed"
    prices_path = data_dir / "prices_clean.csv"

    if prices_path.exists():
        print("\n" + "=" * 60)
        print("Testing carry calculation on real data...")
        print("=" * 60)

        prices = pd.read_csv(prices_path, index_col=0, parse_dates=True)

        try:
            carries = calculate_all_carries_real(prices)

            print("\nCarry Signals (Recent):")
            print(carries.tail(10))

            print("\nCarry Statistics:")
            print(carries.describe())

            # 保存
            output_path = data_dir.parent / "signals" / "carry_signals.csv"
            output_path.parent.mkdir(exist_ok=True)
            carries.to_csv(output_path)
            print(f"\nSaved to: {output_path}")

        except Exception as e:
            print(f"\nError calculating carries: {e}")
            print("\nPlease set FRED_API_KEY environment variable:")
            print("  Windows: set FRED_API_KEY=your_key_here")
            print("  Linux/Mac: export FRED_API_KEY=your_key_here")
    else:
        print(f"\nNo price data found at {prices_path}")
