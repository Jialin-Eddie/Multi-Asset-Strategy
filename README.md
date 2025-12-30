# Multi-Asset Strategy

Quant research project to build and monitor a cost-aware, walk-forward trend-following allocation across a five-ETF universe (SPY, TLT, GLD, DBC, VNQ). It delivers a reproducible data pipeline, signal library, backtester, and a Flask dashboard.

## Why (Purpose)
- Capture persistent cross-asset trends with disciplined risk and turnover control.
- Enforce walk-forward validation (train/val/test) to avoid overfitting and data snooping.
- Quantify transaction-cost and liquidity drag up front, not as an afterthought.
- Provide transparent, shareable results via a lightweight web dashboard.

## How (Approach)
- **Data pipeline**: Yahoo Finance download → cleaning (FF/BF fill, drop sparse days) → quality checks (inception dates, missingness, anomaly detection). Default start date 2006-02-03 to respect DBC inception.
- **Signals/backtests**: Trend filters (SMA/EMA/momentum) feed a backtester that shifts signals to avoid lookahead, supports monthly/weekly/daily rebalance, equal-weight sizing, and per-trade costs (default 5 bps).
- **Research protocol**: Walk-forward split (Train 2006–2015, Validate 2016–2019, Test 2020–2024), mandatory cost scenarios (5/12/25 bps), and failure criteria (e.g., OOS Sharpe < 0.5, Max DD > 25%, monthly turnover > 100%). Experiments live in `src/diagnostics/` (carry efficacy, transaction costs, covariance stability, volatility forecasting, momentum crash, etc.).
- **Dashboard**: Flask app renders strategy performance, regimes, variants, and research artifacts for review.

## What (Components)
- `config/` — universe, dates, trend/risk params, constraints.
- `data/` — raw/processed/signals (gitkeeps included).
- `src/data/` — downloader, loader, validator.
- `src/signals/` — trend/momentum filters.
- `src/backtest/` — backtest engine, costs/execution helpers.
- `src/portfolio/` — (planned) risk budgeting, vol targeting, constraints.
- `src/diagnostics/` — experiment scripts.
- `app/` — Flask dashboard routes, templates, services.
- `outputs/` — generated analytics/optimizations (optional, gitignored if large).

## Quick Start
- Env: `conda env create -f environment.yml && conda activate multi_as_env` (or `pip install -r requirements.txt`).
- Configure: edit `config/universe.yaml` (universe, start/end dates, trend lookback, target vol, constraints).
- Data:
  - `python src/data/downloader.py`
  - `python src/data/loader.py`
  - (optional) `python src/data/validator.py`
- Research: use notebooks in `notebooks/` or experiments in `src/diagnostics/`.
- Dashboard: `python run.py` → http://127.0.0.1:5000

## Configuration (`config/universe.yaml`)
- `universe`: tickers (default SPY, TLT, GLD, DBC, VNQ).
- `data.start_date` / `data.end_date`: date range (start defaults to 2006-02-03).
- `trend.lookback_days`: momentum window (e.g., 252).
- `risk.target_vol`: target annual vol (for future portfolio module).
- `risk.rebalance_freq`: rebalance cadence (e.g., M).
- `constraints.max_weight`, `constraints.long_only`: risk limits.

## Data Flow
1) Download raw prices → `data/raw/multi_asset_prices.csv`.
2) Clean → `data/processed/prices_clean.csv` (fills, drops sparse days).
3) Signals/backtests consume processed prices; outputs may be saved to `outputs/` for dashboard consumption (e.g., `ema_optimization_results.csv`, `signal_comparison.csv`).

## Signals and Backtesting
- Signals: `src/signals/trend_filter.py` (SMA/EMA, absolute/relative momentum).
- Backtester: `src/backtest/engine.py`
  - Shifts signals by one day, supports monthly/weekly/daily rebalance.
  - Equal-weight sizing; applies transaction costs and tracks turnover.
  - Outputs portfolio value, returns, positions, turnover; helpers for regimes and trade logs.

## Dashboard
- Entry: `run.py`; factory: `app/__init__.py`.
- Pages: landing, dashboard, learn, performance, methodology, lab, regimes, variants (templates in `app/templates/`).
- Data service: `app/services/data_loader.py` loads processed prices, builds final/initial EMA strategies (126d vs 252d), buy-and-hold benchmark, regimes, trade log, and optional optimization outputs from `outputs/`.
- Caching: Flask-Caching SimpleCache (1h TTL).

## Testing and QA
- Data quality: `python src/data/validator.py`.
- Manual dashboard check: `python run.py` and open `/`, `/performance`, `/methodology`, `/regimes`, `/variants`, `/lab`.
- Keep failure criteria (walk-forward, costs, turnover) in experiments/backtests when reporting results.

## Contribution Notes
- Prefer branch + PR workflow; commits should mention walk-forward dates, cost scenario, and whether failure criteria are met (per research guideline).
- Use pathlib relative paths (already applied) and avoid lookahead in signal/backtest code.
