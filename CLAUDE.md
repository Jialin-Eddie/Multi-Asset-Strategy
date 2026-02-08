# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-Asset Strategy is a quantitative finance research project implementing portfolio optimization and trading strategies across multiple asset classes (equities, bonds, gold, commodities, REITs). The project uses momentum-based trend following, risk budgeting, and reinforcement learning techniques.

## Auditable Phase Delivery (Mandatory)

This project uses a **phase-based auditable delivery system**. Every phase produces three artifacts:

1. **Phase Epic PR** — discussion container with Hard Checklist, decisions, and acceptance results
2. **Annotated Tag** — immutable snapshot on `master` (Scheme C: `v0.3.0-phase03-backtest`)
3. **GitHub Release** — delivery unit with attached assets (report, results, model)

**Core principle: Evidence-first.** No reproduce command / metric / log path = not delivered.

### Naming (Scheme C)
- Tag: `v{X}.{Y}.{Z}-phase{NN}-{short-name}` (e.g., `v0.3.0-phase03-backtest`)
- Release title: `Phase {NN} — {Short Name} (v{X}.{Y}.{Z})`
- Artifact dir: `report/phase{NN}/`

### Artifact Structure (Mandatory)
All phase outputs MUST be under `report/phaseNN/`. Never pollute the repo root.
```
report/
  phase{NN}/
    report.pdf          # Phase report
    results/            # CSV, PNG, metrics.json, logs
    model/              # Checkpoints, weights (if applicable)
    meta/               # Run config, git SHA, env info
```

Artifacts are **NOT committed to git**. They are uploaded as GitHub Release assets only.

### Rules & Agent References
- PhaseOps agent: `.claude/agents/phaseops.md` — enforces process, evidence, and delivery
- PR splitting rules: `.claude/rules/pr-splitting.md` — decision tree for stacked PRs
- Release notes template: `.claude/rules/release-notes-template.md` — required structure
- PR template: `.github/pull_request_template.md` — Hard Checklist + Soft Review Space
- CI automation: `.github/workflows/release-on-tag.yml` — tag push triggers release
- Playbook: `docs/PHASE_OPS_PLAYBOOK.md` — minimal operations guide

## Environment Setup

The project uses Conda for environment management with specific quantitative finance packages.

**Create environment:**
```bash
conda env create -f environment.yml
conda activate multi_as_env
```

**Alternative pip install:**
```bash
pip install -r requirements.txt
```

**Key dependencies:**
- `yfinance` - Market data retrieval
- `riskfolio-lib` - Portfolio optimization and risk budgeting
- `cvxpy/cvxopt` - Convex optimization solvers
- `arch` - GARCH volatility models
- `pyRMT` - Random Matrix Theory for covariance estimation
- `stable-baselines3` - Reinforcement learning algorithms (PPO, DQN, A2C)

## Data Pipeline

**Download market data from Yahoo Finance:**
```bash
python src/data/downloader.py
```
- Fetches price history for universe defined in `config/universe.yaml`
- Saves raw data to `data/raw/multi_asset_prices.csv`
- Default universe: SPY, TLT, GLD, DBC, VNQ
- Default date range: 2006-02-03 to latest

**Clean and preprocess data:**
```bash
python src/data/loader.py
```
- Loads raw CSV from `data/raw/`
- Applies forward/backward fill for missing values
- Drops days with fewer than 3 valid asset prices
- Saves cleaned data to `data/processed/prices_clean.csv`

## Architecture

**Module structure:**
```
src/
├── data/          # Data acquisition and preprocessing
│   ├── downloader.py   # yfinance wrapper to download ETF prices
│   ├── loader.py       # Clean raw data, handle missing values
│   └── validator.py    # Data quality validation
├── signals/       # Trading signal generation
│   ├── trend_filter.py # SMA/EMA momentum indicators
│   └── carry.py        # Carry signal calculation
├── portfolio/     # Portfolio construction
│   └── risk_parity.py  # Risk parity weighting
├── backtest/      # Backtesting engine
│   └── engine.py       # Walk-forward backtest with transaction costs
├── diagnostics/   # Experiment modules
│   └── experiment_03_carry.py
└── utils/         # Shared utilities (planned)
```

**Configuration system:**
- `config/universe.yaml` defines:
  - Asset universe (ticker symbols)
  - Data download parameters (start_date, end_date)
  - Strategy parameters (trend lookback: 252 days, target volatility: 10%)
  - Risk constraints (max weight: 40%, long-only)
  - Rebalancing frequency (monthly)

**Data flow:**
1. `downloader.py` → `data/raw/multi_asset_prices.csv`
2. `loader.py` → `data/processed/prices_clean.csv`
3. Signal modules read from `data/processed/`
4. Portfolio optimization uses signals + risk models
5. Backtest engine evaluates strategy performance

## Key Design Patterns

**Path handling:**
All modules use `pathlib.Path` with relative navigation from `__file__`:
```python
DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
```
This ensures paths work regardless of working directory.

**Data formats:**
- All price data stored as CSV with DatetimeIndex
- Column names are ticker symbols
- Adj Close prices are primary (split/dividend adjusted)

**Module execution:**
Each module includes `if __name__ == "__main__":` blocks for standalone testing.

## Development Workflow

**Jupyter notebooks for research:**
- `notebooks/01_data_exploration.ipynb` - Initial data analysis
- `research_notebook.ipynb` - Ad-hoc experimentation

**Configuration changes:**
Edit `config/universe.yaml` to modify asset universe or strategy parameters. Re-run downloader to fetch new data.

**Adding new signals:**
Implement in `src/signals/` following the pattern: take DataFrame of prices, return DataFrame of signals/scores.

**Running tests:**
```bash
pytest tests/ -v
```

## Scripts

Key scripts in `scripts/`:
- `final_strategy_summary.py` — generates FINAL_STRATEGY_REPORT.txt
- `compare_strategies.py` — strategy comparison
- `compare_all_signals.py` — signal method comparison
- `optimize_ema_span.py` — EMA parameter optimization
- `optimize_sma_lookback.py` — SMA parameter optimization
- `backtest_risk_parity.py` — risk parity vs equal weight

## Web Dashboard

Flask app in `app/` with Plotly visualizations. Run with:
```bash
python run.py
```
