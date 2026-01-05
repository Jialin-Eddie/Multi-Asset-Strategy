"""Data loading service for dashboard."""
import pandas as pd
from pathlib import Path
from typing import Dict
import json

# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class DataLoader:
    """Load and cache all strategy data."""

    def __init__(self):
        self.data = {}
        self._load_all_data()

    def _load_all_data(self):
        """Load all CSV files into memory."""
        try:
            # Historical prices
            self.data['prices'] = pd.read_csv(
                PROJECT_ROOT / 'data' / 'processed' / 'prices_clean.csv',
                index_col=0,
                parse_dates=True
            )

            # Final strategy results (need to recalculate)
            from src.signals.trend_filter import generate_signals
            from src.backtest.engine import calculate_strategy_returns, calculate_performance_metrics

            prices = self.data['prices']

            # Final strategy: EMA 126d
            final_signals = generate_signals(prices, method='ema', span=126)
            final_backtest = calculate_strategy_returns(
                prices, final_signals,
                transaction_cost=0.0005,
                rebalance_frequency='M'
            )
            final_metrics = calculate_performance_metrics(final_backtest['returns'])

            self.data['final_strategy'] = {
                'signals': final_signals,
                'backtest': final_backtest,
                'metrics': final_metrics,
                'name': 'Final Strategy (EMA 126d)'
            }

            # Initial strategy: EMA 252d
            initial_signals = generate_signals(prices, method='ema', span=252)
            initial_backtest = calculate_strategy_returns(
                prices, initial_signals,
                transaction_cost=0.0005,
                rebalance_frequency='M'
            )
            initial_metrics = calculate_performance_metrics(initial_backtest['returns'])

            self.data['initial_strategy'] = {
                'signals': initial_signals,
                'backtest': initial_backtest,
                'metrics': initial_metrics,
                'name': 'Initial Strategy (EMA 252d)'
            }

            # Benchmark: Buy & Hold
            benchmark_signals = pd.DataFrame(1.0, index=prices.index, columns=prices.columns)
            benchmark_backtest = calculate_strategy_returns(
                prices, benchmark_signals,
                transaction_cost=0.0,
                rebalance_frequency='M'
            )
            benchmark_metrics = calculate_performance_metrics(benchmark_backtest['returns'])

            self.data['benchmark'] = {
                'signals': benchmark_signals,
                'backtest': benchmark_backtest,
                'metrics': benchmark_metrics,
                'name': 'Buy & Hold'
            }

            # Load optimization results if available
            try:
                self.data['ema_optimization'] = pd.read_csv(
                    PROJECT_ROOT / 'outputs' / 'ema_optimization_results.csv'
                )
            except FileNotFoundError:
                self.data['ema_optimization'] = None

            try:
                self.data['signal_comparison'] = pd.read_csv(
                    PROJECT_ROOT / 'outputs' / 'signal_comparison.csv'
                )
            except FileNotFoundError:
                self.data['signal_comparison'] = None

            # Pre-compute regime classification
            from src.backtest.engine import classify_regimes, performance_by_regime, extract_trade_log

            spy_prices = prices['SPY']
            self.data['regimes'] = classify_regimes(spy_prices)
            self.data['regime_performance'] = performance_by_regime(
                final_backtest['returns'],
                self.data['regimes']
            )

            # Pre-compute trade log
            self.data['trade_log'] = extract_trade_log(
                final_signals,
                prices
            )

            # Pre-compute rolling VaR/CVaR
            from src.backtest.engine import calculate_rolling_var_cvar
            self.data['var_cvar'] = calculate_rolling_var_cvar(
                final_backtest['returns'],
                window=252,
                confidence_levels=[0.95, 0.99]
            )

            # Pre-compute stress test scenarios
            self.data['stress_tests'] = self._compute_stress_tests(
                prices, final_backtest, benchmark_backtest
            )

            # Pre-compute EMA sensitivity analysis
            self.data['ema_sensitivity'] = self._compute_ema_sensitivity(prices)

            print("Data loaded successfully")

        except Exception as e:
            print(f"Error loading data: {e}")
            raise

    def _compute_stress_tests(self, prices, final_backtest, benchmark_backtest) -> Dict:
        """
        Compute performance during major stress test scenarios.

        Returns dict with 3 scenarios: covid, crisis_2008, rate_shock_2022
        """
        from src.backtest.engine import calculate_performance_metrics

        scenarios = {
            'covid': {
                'name': 'COVID-19 Crash',
                'start': '2020-02-19',
                'end': '2020-03-23',
                'description': 'SPY -34% in 33 days, fastest bear market in history'
            },
            'crisis_2008': {
                'name': '2008 Financial Crisis',
                'start': '2007-10-09',
                'end': '2009-03-09',
                'description': '18-month bear market, SPY -56% peak-to-trough'
            },
            'rate_shock_2022': {
                'name': '2022 Rate Shock',
                'start': '2022-01-03',
                'end': '2022-10-12',
                'description': 'Stocks AND bonds down (TLT -31%, SPY -18%)'
            }
        }

        results = {}
        for key, scenario in scenarios.items():
            try:
                # Filter returns for this period
                strategy_returns = final_backtest['returns'][scenario['start']:scenario['end']]
                benchmark_returns = benchmark_backtest['returns'][scenario['start']:scenario['end']]
                spy_returns = prices['SPY'][scenario['start']:scenario['end']].pct_change()

                # Calculate metrics for this period
                strategy_metrics = calculate_performance_metrics(strategy_returns)
                benchmark_metrics = calculate_performance_metrics(benchmark_returns)

                # Get SPY drawdown
                spy_cumulative = (1 + spy_returns).cumprod()
                spy_dd = (spy_cumulative / spy_cumulative.cummax() - 1).min()

                results[key] = {
                    'name': scenario['name'],
                    'start': scenario['start'],
                    'end': scenario['end'],
                    'description': scenario['description'],
                    'strategy_return': strategy_metrics['total_return'],
                    'benchmark_return': benchmark_metrics['total_return'],
                    'strategy_max_dd': strategy_metrics['max_drawdown'],
                    'benchmark_max_dd': benchmark_metrics['max_drawdown'],
                    'spy_max_dd': spy_dd,
                    'days': len(strategy_returns),
                    'outperformance': strategy_metrics['total_return'] - benchmark_metrics['total_return']
                }
            except Exception as e:
                print(f"Warning: Could not compute stress test {key}: {e}")
                results[key] = None

        return results

    def _compute_ema_sensitivity(self, prices) -> pd.DataFrame:
        """
        Compute strategy performance across different EMA window sizes.

        Tests windows: 63, 84, 105, 126, 147, 168, 189, 210, 252, 315, 378 days
        (approximately 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 18 months)

        Returns DataFrame with columns: window, total_return, sharpe_ratio, max_drawdown, win_rate
        """
        from src.signals.trend_filter import generate_signals
        from src.backtest.engine import backtest_strategy, calculate_performance_metrics

        # EMA windows to test (in trading days, ~21 per month)
        ema_windows = [63, 84, 105, 126, 147, 168, 189, 210, 252, 315, 378]

        results = []
        for window in ema_windows:
            try:
                # Generate signals with this EMA window
                signals = generate_signals(prices, method='ema', span=window)

                # Run backtest
                backtest_result = backtest_strategy(
                    prices=prices,
                    signals=signals,
                    benchmark_returns=prices.pct_change().mean(axis=1),
                    transaction_cost=0.0005,
                    rebalance_frequency='M'
                )

                # Extract key metrics
                metrics = backtest_result['performance_metrics']
                results.append({
                    'window': window,
                    'months': window / 21,  # Approximate months
                    'total_return': metrics['total_return'],
                    'sharpe_ratio': metrics['sharpe_ratio'],
                    'max_drawdown': metrics['max_drawdown'],
                    'win_rate': metrics['win_rate']
                })
            except Exception as e:
                print(f"Warning: Could not compute EMA sensitivity for window {window}: {e}")

        return pd.DataFrame(results)

    def get_prices(self) -> pd.DataFrame:
        """Get historical prices."""
        return self.data['prices']

    def get_strategy_data(self, strategy='final') -> Dict:
        """Get strategy backtest data."""
        if strategy == 'final':
            return self.data['final_strategy']
        elif strategy == 'initial':
            return self.data['initial_strategy']
        elif strategy == 'benchmark':
            return self.data['benchmark']
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

    def get_all_strategies(self) -> Dict:
        """Get all strategy data."""
        return {
            'final': self.data['final_strategy'],
            'initial': self.data['initial_strategy'],
            'benchmark': self.data['benchmark']
        }

    def get_optimization_results(self) -> pd.DataFrame:
        """Get EMA optimization results."""
        return self.data.get('ema_optimization')

    def get_signal_comparison(self) -> pd.DataFrame:
        """Get signal method comparison results."""
        return self.data.get('signal_comparison')

    def get_regimes(self) -> pd.Series:
        """Get market regime classification."""
        return self.data.get('regimes')

    def get_regime_performance(self) -> pd.DataFrame:
        """Get performance metrics by regime."""
        return self.data.get('regime_performance')

    def get_trade_log(self) -> pd.DataFrame:
        """Get trade-level log."""
        return self.data.get('trade_log')

    def get_var_cvar(self) -> pd.DataFrame:
        """Get rolling VaR/CVaR series."""
        return self.data.get('var_cvar')

    def get_stress_tests(self) -> Dict:
        """Get stress test scenario results."""
        return self.data.get('stress_tests')

    def get_ema_sensitivity(self) -> pd.DataFrame:
        """Get EMA parameter sensitivity analysis."""
        return self.data.get('ema_sensitivity')


# Global data loader instance
_data_loader = None


def get_data_loader() -> DataLoader:
    """Get or create data loader singleton."""
    global _data_loader
    if _data_loader is None:
        _data_loader = DataLoader()
    return _data_loader
