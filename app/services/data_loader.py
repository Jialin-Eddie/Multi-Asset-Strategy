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

            print("✓ Data loaded successfully")

        except Exception as e:
            print(f"Error loading data: {e}")
            raise

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


# Global data loader instance
_data_loader = None


def get_data_loader() -> DataLoader:
    """Get or create data loader singleton."""
    global _data_loader
    if _data_loader is None:
        _data_loader = DataLoader()
    return _data_loader
