"""
Experiment 3: Carry Signal Validation

测试carry信号对未来收益的预测能力。

WALK-FORWARD DECLARATION:
  Training:   2006-02-03 to 2015-12-31
  Validation: 2016-01-01 to 2019-12-31
  Test:       2020-01-01 to 2024-12-31
  Test Set First Run: [AUTO-FILLED on first execution]

COST SCENARIOS:
  N/A (signal validation only)

FAILURE CRITERIA (defined before running):
  - Mean IC (Information Coefficient) < 0.10 across all assets
  - Any asset IC < 0.05 and not significant
  - Correlation with next month return < 0.15 for >60% of assets
  - Carry strategy (long top carry assets) Sharpe < 0.3
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Tuple, List
from scipy import stats
import json
import warnings

# ============================================================================
# FAILURE CRITERIA (defined before experiment)
# ============================================================================

FAILURE_CRITERIA = {
    'min_mean_ic': 0.10,          # Mean IC across all assets
    'min_individual_ic': 0.05,    # Minimum IC for any asset
    'max_low_corr_pct': 0.60,     # Max % of assets with corr < 0.15
    'min_strategy_sharpe': 0.3,   # Minimum Sharpe for carry strategy
}

# ============================================================================
# Carry Signal Calculation
# ============================================================================

def calculate_bond_carry_proxy(
    prices: pd.Series,
    window: int = 21
) -> pd.Series:
    """
    债券carry代理: 使用短期收益率作为yield代理

    ⚠️ LIMITATION: 真实carry需要yield curve数据
    这里用滚动收益率作为粗略代理

    Parameters
    ----------
    prices : pd.Series
        债券ETF价格 (如TLT)
    window : int
        滚动窗口 (21天 ≈ 1月)

    Returns
    -------
    pd.Series
        Carry proxy (年化)
    """
    # 滚动收益率作为carry代理
    rolling_return = prices.pct_change(window)

    # 年化 (假设252交易日)
    annual_carry = rolling_return * (252 / window)

    return annual_carry


def calculate_commodity_roll_proxy(
    prices: pd.Series,
    window: int = 21
) -> pd.Series:
    """
    商品roll yield代理: 使用动量的负值

    ⚠️ LIMITATION: 真实roll yield需要期货曲线数据
    在contango市场，momentum为负相关于roll yield

    Parameters
    ----------
    prices : pd.Series
        商品ETF价格 (如DBC)
    window : int
        观察窗口

    Returns
    -------
    pd.Series
        Roll yield proxy (负动量)
    """
    # 短期动量的负值作为roll yield代理
    momentum = prices.pct_change(window)

    # Contango市场: momentum负，roll yield负
    # 这里用负动量作为代理（粗略）
    roll_proxy = -momentum * (252 / window)

    return roll_proxy


def calculate_equity_carry_proxy(
    prices: pd.Series,
    window: int = 252
) -> pd.Series:
    """
    股票carry代理: 使用长期平均收益率

    ⚠️ LIMITATION: 真实carry是dividend yield
    ETF数据通常不包含分红，用长期收益率代理

    Parameters
    ----------
    prices : pd.Series
        股票ETF价格
    window : int
        长期窗口 (252天 = 1年)

    Returns
    -------
    pd.Series
        Carry proxy (年化收益率)
    """
    # 使用长期滚动收益率
    annual_return = prices.pct_change(window)

    return annual_return


def calculate_all_carries(
    prices: pd.DataFrame,
    asset_classes: Dict[str, str],
    window: int = 21
) -> pd.DataFrame:
    """
    计算所有资产的carry信号

    Parameters
    ----------
    prices : pd.DataFrame
        价格数据
    asset_classes : Dict[str, str]
        资产类别映射 {'SPY': 'equity', 'TLT': 'bond', ...}
    window : int
        计算窗口

    Returns
    -------
    pd.DataFrame
        Carry信号 (年化)
    """
    carries = pd.DataFrame(index=prices.index)

    for ticker in prices.columns:
        asset_class = asset_classes.get(ticker, 'equity')

        if asset_class == 'bond':
            carries[ticker] = calculate_bond_carry_proxy(prices[ticker], window)
        elif asset_class == 'commodity':
            carries[ticker] = calculate_commodity_roll_proxy(prices[ticker], window)
        elif asset_class == 'equity':
            carries[ticker] = calculate_equity_carry_proxy(prices[ticker], window=252)
        else:
            # Default: use bond proxy
            carries[ticker] = calculate_bond_carry_proxy(prices[ticker], window)

    return carries


# ============================================================================
# Predictive Power Tests
# ============================================================================

def calculate_forward_returns(
    prices: pd.DataFrame,
    horizons: List[int] = [21, 63]
) -> Dict[int, pd.DataFrame]:
    """
    计算未来收益率

    Parameters
    ----------
    prices : pd.DataFrame
        价格数据
    horizons : List[int]
        未来时间段 (21天=1M, 63天=3M)

    Returns
    -------
    Dict[int, pd.DataFrame]
        {horizon: forward_returns}
    """
    forward_returns = {}

    for h in horizons:
        # 未来h天收益率
        fwd_ret = prices.pct_change(h).shift(-h)
        forward_returns[h] = fwd_ret

    return forward_returns


def test_carry_predictive_power(
    carry_signals: pd.DataFrame,
    future_returns: pd.DataFrame,
    min_obs: int = 100
) -> pd.DataFrame:
    """
    测试carry与未来收益的相关性

    Parameters
    ----------
    carry_signals : pd.DataFrame
        Carry信号
    future_returns : pd.DataFrame
        未来收益率
    min_obs : int
        最小观测数

    Returns
    -------
    pd.DataFrame
        相关性统计 (ticker, correlation, p_value, n_obs)
    """
    results = []

    for ticker in carry_signals.columns:
        # 对齐数据
        carry = carry_signals[ticker].dropna()
        fwd_ret = future_returns[ticker].dropna()

        # 共同index
        common_idx = carry.index.intersection(fwd_ret.index)

        if len(common_idx) < min_obs:
            results.append({
                'ticker': ticker,
                'correlation': np.nan,
                'p_value': np.nan,
                'n_obs': len(common_idx),
                'significant': False
            })
            continue

        carry_aligned = carry.loc[common_idx]
        fwd_ret_aligned = fwd_ret.loc[common_idx]

        # Pearson相关性
        corr, pval = stats.pearsonr(carry_aligned, fwd_ret_aligned)

        results.append({
            'ticker': ticker,
            'correlation': corr,
            'p_value': pval,
            'n_obs': len(common_idx),
            'significant': pval < 0.05
        })

    return pd.DataFrame(results)


def calculate_information_coefficient(
    carry_signals: pd.DataFrame,
    future_returns: pd.DataFrame,
    min_obs: int = 100
) -> pd.DataFrame:
    """
    计算Information Coefficient (Spearman rank correlation)

    IC是量化研究的标准指标，衡量信号预测能力

    Parameters
    ----------
    carry_signals : pd.DataFrame
        Carry信号
    future_returns : pd.DataFrame
        未来收益率
    min_obs : int
        最小观测数

    Returns
    -------
    pd.DataFrame
        IC统计 (ticker, IC, IC_std, IC_IR, hit_rate)
    """
    results = []

    for ticker in carry_signals.columns:
        carry = carry_signals[ticker].dropna()
        fwd_ret = future_returns[ticker].dropna()

        common_idx = carry.index.intersection(fwd_ret.index)

        if len(common_idx) < min_obs:
            results.append({
                'ticker': ticker,
                'IC': np.nan,
                'IC_std': np.nan,
                'IC_IR': np.nan,
                'hit_rate': np.nan,
                'n_obs': len(common_idx)
            })
            continue

        carry_aligned = carry.loc[common_idx]
        fwd_ret_aligned = fwd_ret.loc[common_idx]

        # Spearman rank correlation
        ic, _ = stats.spearmanr(carry_aligned, fwd_ret_aligned)

        # 滚动IC (计算IC的稳定性)
        window_ic = []
        min_window = 60  # 最小窗口

        for i in range(min_window, len(common_idx)):
            window_carry = carry_aligned.iloc[i-min_window:i]
            window_ret = fwd_ret_aligned.iloc[i-min_window:i]

            if len(window_carry) >= min_window:
                ic_i, _ = stats.spearmanr(window_carry, window_ret)
                window_ic.append(ic_i)

        ic_std = np.std(window_ic) if len(window_ic) > 0 else np.nan
        ic_ir = ic / ic_std if ic_std > 0 else np.nan

        # Hit rate: carry正确预测方向的比例
        hit_rate = np.mean(np.sign(carry_aligned) == np.sign(fwd_ret_aligned))

        results.append({
            'ticker': ticker,
            'IC': ic,
            'IC_std': ic_std,
            'IC_IR': ic_ir,  # IC Information Ratio
            'hit_rate': hit_rate,
            'n_obs': len(common_idx)
        })

    return pd.DataFrame(results)


# ============================================================================
# Strategy Backtest (Simple Carry Long)
# ============================================================================

def backtest_carry_strategy(
    carry_signals: pd.DataFrame,
    prices: pd.DataFrame,
    top_n: int = 2,
    rebalance_freq: str = 'M'
) -> Tuple[pd.Series, Dict[str, float]]:
    """
    回测简单carry策略: 做多top N carry资产

    Parameters
    ----------
    carry_signals : pd.DataFrame
        Carry信号
    prices : pd.DataFrame
        价格数据
    top_n : int
        做多资产数量
    rebalance_freq : str
        再平衡频率 ('M'=月度)

    Returns
    -------
    Tuple[pd.Series, Dict]
        (策略收益率序列, 绩效指标)
    """
    # 计算日收益率
    returns = prices.pct_change()

    # 月末再平衡点
    rebalance_dates = carry_signals.resample('ME').last().index  # 'ME' = month end

    # 持仓权重
    weights = pd.DataFrame(0.0, index=returns.index, columns=returns.columns)

    for date in rebalance_dates:
        if date not in carry_signals.index:
            continue

        # 当前carry信号
        current_carry = carry_signals.loc[date].dropna()

        if len(current_carry) == 0:
            continue

        # 选择top N
        top_assets = current_carry.nlargest(top_n).index

        # 等权重
        weight = 1.0 / len(top_assets)

        # 填充权重直到下一个再平衡日
        next_dates = returns.index[returns.index >= date]
        if len(rebalance_dates[rebalance_dates > date]) > 0:
            next_rebal = rebalance_dates[rebalance_dates > date][0]
            fill_dates = next_dates[next_dates < next_rebal]
        else:
            fill_dates = next_dates

        for asset in top_assets:
            weights.loc[fill_dates, asset] = weight

    # 计算策略收益
    strategy_returns = (weights.shift(1) * returns).sum(axis=1)

    # 绩效指标
    total_return = (1 + strategy_returns).prod() - 1
    annual_return = (1 + total_return) ** (252 / len(strategy_returns)) - 1
    annual_vol = strategy_returns.std() * np.sqrt(252)
    sharpe = annual_return / annual_vol if annual_vol > 0 else 0

    max_dd = (strategy_returns.cumsum() - strategy_returns.cumsum().expanding().max()).min()

    metrics = {
        'total_return': total_return,
        'annual_return': annual_return,
        'annual_volatility': annual_vol,
        'sharpe_ratio': sharpe,
        'max_drawdown': max_dd,
        'n_trades': len(rebalance_dates)
    }

    return strategy_returns, metrics


# ============================================================================
# Failure Criteria Check
# ============================================================================

def check_failure_criteria(
    ic_results: pd.DataFrame,
    corr_results_1m: pd.DataFrame,
    strategy_metrics: Dict[str, float]
) -> Dict[str, any]:
    """
    检查失败标准

    Returns
    -------
    Dict
        {'passed': bool, 'failures': List[str], 'metrics': Dict}
    """
    failures = []

    # 1. Mean IC检查
    mean_ic = ic_results['IC'].mean()
    if mean_ic < FAILURE_CRITERIA['min_mean_ic']:
        failures.append(
            f"Mean IC = {mean_ic:.3f} < {FAILURE_CRITERIA['min_mean_ic']:.3f}"
        )

    # 2. Individual IC检查
    low_ic = ic_results[ic_results['IC'] < FAILURE_CRITERIA['min_individual_ic']]
    if len(low_ic) > 0:
        failures.append(
            f"{len(low_ic)} assets with IC < {FAILURE_CRITERIA['min_individual_ic']}"
        )

    # 3. 低相关性占比检查
    low_corr_pct = (corr_results_1m['correlation'] < 0.15).mean()
    if low_corr_pct > FAILURE_CRITERIA['max_low_corr_pct']:
        failures.append(
            f"{low_corr_pct:.1%} assets with corr < 0.15 (threshold: {FAILURE_CRITERIA['max_low_corr_pct']:.1%})"
        )

    # 4. 策略Sharpe检查
    if strategy_metrics['sharpe_ratio'] < FAILURE_CRITERIA['min_strategy_sharpe']:
        failures.append(
            f"Strategy Sharpe = {strategy_metrics['sharpe_ratio']:.2f} < {FAILURE_CRITERIA['min_strategy_sharpe']:.2f}"
        )

    passed = len(failures) == 0

    return {
        'passed': passed,
        'failures': failures,
        'metrics': {
            'mean_ic': mean_ic,
            'low_corr_pct': low_corr_pct,
            'strategy_sharpe': strategy_metrics['sharpe_ratio']
        }
    }


# ============================================================================
# Main Experiment
# ============================================================================

def run_experiment_3() -> Dict[str, any]:
    """
    运行Experiment 3: Carry信号验证

    Returns
    -------
    Dict
        完整实验结果
    """
    print("=" * 80)
    print("EXPERIMENT 3: Carry Signal Validation")
    print("=" * 80)

    # 加载数据
    data_path = Path(__file__).resolve().parents[2] / "data" / "processed" / "prices_clean.csv"
    prices = pd.read_csv(data_path, index_col=0, parse_dates=True)

    print(f"\nData loaded: {prices.shape[0]} days, {prices.shape[1]} assets")
    print(f"Date range: {prices.index.min()} to {prices.index.max()}")

    # 资产类别定义
    asset_classes = {
        'SPY': 'equity',
        'TLT': 'bond',
        'GLD': 'commodity',  # 黄金特殊，无carry
        'DBC': 'commodity',
        'VNQ': 'equity'
    }

    # 1. 计算carry信号
    print("\n[1/5] Calculating carry signals...")
    carry_signals = calculate_all_carries(prices, asset_classes, window=21)
    print(f"Carry signals shape: {carry_signals.shape}")
    print("\nCarry signal statistics (recent):")
    print(carry_signals.tail().describe())

    # 2. 计算未来收益率
    print("\n[2/5] Calculating forward returns...")
    forward_returns = calculate_forward_returns(prices, horizons=[21, 63])
    print(f"Forward returns calculated for {len(forward_returns)} horizons")

    # 3. 测试预测能力 (1月)
    print("\n[3/5] Testing predictive power (1-month horizon)...")
    corr_results_1m = test_carry_predictive_power(
        carry_signals,
        forward_returns[21],
        min_obs=100
    )
    print("\nCorrelation with 1M forward returns:")
    print(corr_results_1m)

    # 4. 计算IC
    print("\n[4/5] Calculating Information Coefficient...")
    ic_results = calculate_information_coefficient(
        carry_signals,
        forward_returns[21],
        min_obs=100
    )
    print("\nInformation Coefficient (IC):")
    print(ic_results)

    # 5. 回测carry策略
    print("\n[5/5] Backtesting carry strategy...")
    strategy_returns, strategy_metrics = backtest_carry_strategy(
        carry_signals,
        prices,
        top_n=2,
        rebalance_freq='M'
    )

    print("\nCarry Strategy Performance:")
    for key, value in strategy_metrics.items():
        print(f"  {key}: {value:.4f}")

    # 检查失败标准
    print("\n" + "=" * 80)
    print("FAILURE CRITERIA CHECK")
    print("=" * 80)

    failure_check = check_failure_criteria(
        ic_results,
        corr_results_1m,
        strategy_metrics
    )

    if failure_check['passed']:
        print("\n[PASS] All failure criteria met - Carry signal is viable")
    else:
        print("\n[FAIL] Experiment failed - Carry signal not viable")
        print("\nFailures:")
        for failure in failure_check['failures']:
            print(f"  - {failure}")

    # 汇总结果
    results = {
        'experiment_id': '03',
        'experiment_name': 'Carry Signal Validation',
        'timestamp': pd.Timestamp.now().isoformat(),
        'data_range': {
            'start': prices.index.min().isoformat(),
            'end': prices.index.max().isoformat(),
            'n_days': len(prices)
        },
        'correlation_1m': corr_results_1m.to_dict('records'),
        'information_coefficient': ic_results.to_dict('records'),
        'strategy_performance': strategy_metrics,
        'failure_check': failure_check,
        'failure_criteria': FAILURE_CRITERIA
    }

    return results


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    results = run_experiment_3()

    # 保存结果
    output_dir = Path(__file__).resolve().parents[2] / "outputs" / "experiments"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
    output_path = output_dir / f"exp_03_carry_validation_{timestamp}.json"

    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n\nResults saved to: {output_path}")

    # 打印最终结论
    print("\n" + "=" * 80)
    print("CONCLUSION")
    print("=" * 80)

    if results['failure_check']['passed']:
        print("\n[PASS] Carry signal shows predictive power and passes viability tests.")
        print("  Recommendation: Include carry in multi-signal strategy.")
    else:
        print("\n[FAIL] Carry signal fails viability tests.")
        print("  Recommendation: Do NOT use carry signal, or redesign calculation.")
        print("\n  Key issues:")
        for failure in results['failure_check']['failures']:
            print(f"    - {failure}")
