# Multi-Asset Strategy

Quantitative research and dashboard for trend-following and risk-managed allocation across a five-ETF universe (SPY, TLT, GLD, DBC, VNQ). The project bundles data pipeline, signal generation, backtesting, and a Flask dashboard for monitoring results.

## Quick Start
- Clone and create env: `conda env create -f environment.yml` then `conda activate multi_as_env` (or `pip install -r requirements.txt`).
- Configure universe/dates in `config/universe.yaml` (default start date 2006-02-03 to respect DBC inception).
- Download & clean data:
  - `python src/data/downloader.py`
  - `python src/data/loader.py`
  - (optional) `python src/data/validator.py` to run data quality checks.
- Run research/backtests from notebooks in `notebooks/` or scripts in `src/diagnostics/`.
- Launch dashboard: `python run.py` → http://127.0.0.1:5000

## Data & Signals
- Raw prices: `data/raw/multi_asset_prices.csv` (Yahoo Finance).
- Cleaned prices: `data/processed/prices_clean.csv` (FF/BF fill, drops days with <3 assets).
- Trend signals: `src/signals/trend_filter.py` provides SMA/EMA and momentum variants.
- Sample signals: `data/signals/carry_signals.csv` (staging).

## Backtesting
- Core engine: `src/backtest/engine.py`
  - Shifts signals by 1 day to avoid lookahead, supports monthly/weekly/daily rebalance.
  - Equal-weight sizing; applies transaction costs (default 5 bps).
  - Outputs portfolio value, returns, positions, turnover.
- Metrics & regime views: `classify_regimes`, `performance_by_regime`, `extract_trade_log` (see `app/services/data_loader.py` and `src/backtest/engine.py`).

## Dashboard (Flask)
- App entry: `run.py`; factory in `app/__init__.py`.
- Routes/pages: landing, dashboard, learn, performance, methodology, lab, regimes, variants (templates in `app/templates/`).
- Data service: `app/services/data_loader.py` loads cleaned prices, builds final/initial EMA strategies (126d vs 252d), benchmark buy & hold, regime classification, trade log, and optional optimization outputs under `outputs/`.
- Caching: Flask-Caching SimpleCache with 1h TTL.

## Research Protocol (key rules)
- Walk-forward split: Train 2006–2015, Validate 2016–2019, Test 2020–2024; test set only viewed once and timestamped.
- Cost sensitivity: always report optimistic/baseline/conservative costs (5/12/25 bps) and profit-cost breakeven.
- Failure criteria examples: OOS Sharpe < 0.5, Max Drawdown > 25%, monthly turnover > 100%, profit-cost < 15 bps, >50% PnL from a single year or asset.
- Experiment suite lives in `src/diagnostics/` (carry efficacy, transaction costs, covariance stability, volatility forecasting, momentum crash, etc.).

## Repo Layout
```
config/           # Universe, dates, risk params, constraints
data/             # raw/ processed/ signals/ (gitkeeps)
notebooks/        # research exploration
src/
  data/           # downloader, loader, validator
  signals/        # trend/momentum filters
  backtest/       # engine, costs, execution
  portfolio/      # (planned) risk budgeting, vol targeting, constraints
  diagnostics/    # experiment scripts
app/              # Flask dashboard routes, templates, services
outputs/          # generated analytics/optimizations (gitignored if large)
```

## Typical Workflow
1) Adjust `config/universe.yaml` if universe or dates change.
2) `python src/data/downloader.py` → `python src/data/loader.py` → `python src/data/validator.py`.
3) Iterate on signals in `src/signals/` and backtests via notebooks or `src/diagnostics/`.
4) Produce outputs (e.g., `outputs/ema_optimization_results.csv`) for the dashboard to display.
5) Launch `python run.py` to review dashboard pages.

## Testing & QA
- Data quality: `python src/data/validator.py`.
- Manual dashboard check: run `python run.py` and open `/`, `/performance`, `/methodology`, `/regimes`, `/variants`, `/lab`.
- Keep walk-forward and cost/turnover failure criteria in code or experiment configs.

## Contributing
- Prefer branch + PR workflow; commits should note walk-forward dates, cost scenario, and whether failure criteria are met (per research guideline).
- Use relative `pathlib` paths (already applied) for portability; avoid lookahead in signals/backtests.

