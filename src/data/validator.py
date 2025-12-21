"""
数据质量验证模块

确保数据符合RESEARCH_PROTOCOL.md中的要求：
- ETF inception dates检查
- 数据完整性验证（缺失率<5%）
- 异常价格检测
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
import warnings

# 已知ETF上市日期（人工验证）
ETF_INCEPTION_DATES = {
    'SPY': '1993-01-22',
    'TLT': '2002-07-26',
    'GLD': '2004-11-18',
    'VNQ': '2004-09-29',
    'DBC': '2006-02-03',  # ⚠️ 最晚上市
}

# 早期流动性阈值（日均成交量）
LIQUIDITY_THRESHOLD = 100_000  # 10万股


def validate_etf_inception_dates(
    tickers: List[str],
    start_date: str
) -> pd.DataFrame:
    """
    检查ETF上市日期与请求日期的匹配性

    Parameters
    ----------
    tickers : List[str]
        ETF ticker列表
    start_date : str
        请求的起始日期 "YYYY-MM-DD"

    Returns
    -------
    pd.DataFrame
        验证结果，包含ticker, inception_date, requested_start, actual_start, is_valid
    """
    results = []

    for ticker in tickers:
        inception = ETF_INCEPTION_DATES.get(ticker, None)

        if inception is None:
            warnings.warn(f"⚠️ {ticker} 上市日期未知，请人工验证")
            actual_start = start_date
            is_valid = False
        else:
            actual_start = max(start_date, inception)
            is_valid = (start_date >= inception)

        results.append({
            'ticker': ticker,
            'inception_date': inception,
            'requested_start': start_date,
            'actual_start': actual_start,
            'is_valid': is_valid,
            'days_gap': (pd.Timestamp(actual_start) - pd.Timestamp(start_date)).days if not is_valid else 0
        })

    df = pd.DataFrame(results)

    # 打印警告
    invalid = df[~df['is_valid']]
    if len(invalid) > 0:
        print("\n[FAIL] Data request date earlier than ETF inception:")
        print(invalid[['ticker', 'inception_date', 'requested_start', 'days_gap']])
        print(f"\nRecommendation: Use {df['actual_start'].max()} as start date")
    else:
        print("[PASS] All ETF inception dates validated")

    return df


def check_data_completeness(
    prices: pd.DataFrame,
    max_missing_rate: float = 0.05
) -> Dict[str, float]:
    """
    计算每个资产的缺失率

    FAILURE CRITERIA (from RESEARCH_PROTOCOL.md):
        - 任何资产缺失率 > 5%

    Parameters
    ----------
    prices : pd.DataFrame
        价格数据，index=date, columns=tickers
    max_missing_rate : float
        允许的最大缺失率（默认5%）

    Returns
    -------
    Dict[str, float]
        {ticker: missing_rate}
    """
    missing_rates = {}

    print("\nData Completeness Check:")
    print("=" * 60)

    for ticker in prices.columns:
        missing_count = prices[ticker].isna().sum()
        total_count = len(prices)
        missing_rate = missing_count / total_count
        missing_rates[ticker] = missing_rate

        status = "[PASS]" if missing_rate <= max_missing_rate else "[FAIL]"
        print(f"{status} {ticker:6s}: {missing_rate:6.2%} missing ({missing_count}/{total_count} days)")

    # 检查失败标准
    failures = {k: v for k, v in missing_rates.items() if v > max_missing_rate}
    if failures:
        print(f"\n[FAIL] {len(failures)} assets exceed {max_missing_rate:.1%} missing rate")
        print("Violates RESEARCH_PROTOCOL.md data quality standards")
    else:
        print(f"\n[PASS] All assets missing rate < {max_missing_rate:.1%}")

    return missing_rates


def detect_price_anomalies(
    prices: pd.DataFrame,
    z_threshold: float = 5.0
) -> pd.DataFrame:
    """
    识别异常价格波动（可能的数据错误）

    方法：检测日收益率的Z-score，超过阈值视为异常

    Parameters
    ----------
    prices : pd.DataFrame
        价格数据
    z_threshold : float
        Z-score阈值（默认5，即5倍标准差）

    Returns
    -------
    pd.DataFrame
        异常记录 (date, ticker, return, z_score)
    """
    returns = prices.pct_change()
    anomalies = []

    print("\nPrice Anomaly Detection (Z-score method):")
    print("=" * 60)

    for ticker in prices.columns:
        ret = returns[ticker].dropna()
        mean = ret.mean()
        std = ret.std()

        z_scores = (ret - mean) / std
        outliers = z_scores[z_scores.abs() > z_threshold]

        if len(outliers) > 0:
            print(f"[WARN] {ticker}: Found {len(outliers)} anomalous days")
            for date, z in outliers.items():
                anomalies.append({
                    'date': date,
                    'ticker': ticker,
                    'return': ret[date],
                    'z_score': z
                })

    df_anomalies = pd.DataFrame(anomalies)

    if len(df_anomalies) == 0:
        print("[PASS] No extreme price anomalies detected")
    else:
        print(f"\nFound {len(df_anomalies)} anomalies, manual review recommended:")
        print(df_anomalies.sort_values('z_score', key=abs, ascending=False).head(10))

    return df_anomalies


def compare_data_sources(
    source1: pd.DataFrame,
    source2: pd.DataFrame,
    max_divergence: float = 0.02
) -> pd.DataFrame:
    """
    对比两个数据源的价格差异

    Parameters
    ----------
    source1, source2 : pd.DataFrame
        两个数据源的价格数据
    max_divergence : float
        允许的最大价格偏离（默认2%）

    Returns
    -------
    pd.DataFrame
        差异统计 (ticker, mean_diff, max_diff, dates_diverge)
    """
    # 对齐index和columns
    common_dates = source1.index.intersection(source2.index)
    common_tickers = source1.columns.intersection(source2.columns)

    s1 = source1.loc[common_dates, common_tickers]
    s2 = source2.loc[common_dates, common_tickers]

    # 计算相对差异
    rel_diff = (s1 - s2).abs() / s1

    results = []
    print("\nData Source Comparison:")
    print("=" * 60)

    for ticker in common_tickers:
        diff = rel_diff[ticker].dropna()
        mean_diff = diff.mean()
        max_diff = diff.max()
        diverge_count = (diff > max_divergence).sum()

        status = "[PASS]" if max_diff < max_divergence else "[WARN]"
        print(f"{status} {ticker:6s}: avg_diff {mean_diff:.3%}, max_diff {max_diff:.3%}, {diverge_count} days exceed threshold")

        results.append({
            'ticker': ticker,
            'mean_diff': mean_diff,
            'max_diff': max_diff,
            'dates_diverge': diverge_count
        })

    return pd.DataFrame(results)


def run_full_validation(
    prices: pd.DataFrame,
    tickers: List[str],
    start_date: str
) -> Dict[str, any]:
    """
    运行完整的数据质量验证流程

    按照RESEARCH_PROTOCOL.md的要求验证：
    1. ETF上市日期
    2. 数据完整性（缺失率<5%）
    3. 价格异常检测

    Parameters
    ----------
    prices : pd.DataFrame
        价格数据
    tickers : List[str]
        ETF列表
    start_date : str
        请求的起始日期

    Returns
    -------
    Dict
        验证结果汇总
    """
    print("=" * 80)
    print("Data Quality Validation")
    print("Following RESEARCH_PROTOCOL.md standards")
    print("=" * 80)

    results = {}

    # 1. ETF上市日期验证
    print("\n[1/3] ETF上市日期验证...")
    inception_check = validate_etf_inception_dates(tickers, start_date)
    results['inception_dates'] = inception_check

    # 2. 数据完整性检查
    print("\n[2/3] 数据完整性检查...")
    missing_rates = check_data_completeness(prices, max_missing_rate=0.05)
    results['missing_rates'] = missing_rates

    # 3. 价格异常检测
    print("\n[3/3] 价格异常检测...")
    anomalies = detect_price_anomalies(prices, z_threshold=5.0)
    results['anomalies'] = anomalies

    # 总结
    print("\n" + "=" * 80)
    print("Validation Summary:")

    all_passed = True

    if not inception_check['is_valid'].all():
        print("[FAIL] ETF inception date check: FAILED")
        all_passed = False
    else:
        print("[PASS] ETF inception date check: PASSED")

    if any(v > 0.05 for v in missing_rates.values()):
        print("[FAIL] Data completeness check: FAILED (some assets >5% missing)")
        all_passed = False
    else:
        print("[PASS] Data completeness check: PASSED")

    if len(anomalies) > 10:
        print(f"[WARN] Price anomaly detection: WARNING (found {len(anomalies)} anomalies, manual review needed)")
    else:
        print("[PASS] Price anomaly detection: PASSED")

    if all_passed:
        print("\n[SUCCESS] All data quality checks passed, ready for research experiments")
    else:
        print("\n[WARNING] Data quality issues detected, please fix before continuing")

    print("=" * 80)

    results['validation_passed'] = all_passed

    return results


if __name__ == "__main__":
    # 运行数据验证
    from loader import load_raw_prices

    print("Loading data...")
    prices = load_raw_prices()

    tickers = prices.columns.tolist()
    start_date = "2005-01-01"

    results = run_full_validation(prices, tickers, start_date)

    # 保存验证报告
    output_dir = Path(__file__).resolve().parents[2] / "outputs" / "data_quality"
    output_dir.mkdir(parents=True, exist_ok=True)

    report_path = output_dir / f"validation_report_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.json"

    # 转换为可序列化格式
    report = {
        'timestamp': pd.Timestamp.now().isoformat(),
        'validation_passed': results['validation_passed'],
        'inception_dates': results['inception_dates'].to_dict('records'),
        'missing_rates': results['missing_rates'],
        'anomalies_count': len(results['anomalies'])
    }

    import json
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\nValidation report saved: {report_path}")
