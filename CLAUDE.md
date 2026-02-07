# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-Asset Strategy is a quantitative finance research project implementing portfolio optimization and trading strategies across multiple asset classes (equities, bonds, gold, commodities, REITs). The project uses momentum-based trend following, risk budgeting, and reinforcement learning techniques.

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
- Default date range: 2005-01-01 to latest

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
│   └── loader.py       # Clean raw data, handle missing values
├── signals/       # Trading signal generation
│   └── trend_filter.py # Momentum/trend indicators (in development)
├── portfolio/     # Portfolio construction (planned)
├── backtest/      # Backtesting engine (planned)
├── analytics/     # Performance metrics and visualization (planned)
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

## CLAUDE.md 维护规则 (强制)

每个子目录都有 `CLAUDE.md` 文件，用于快速了解该目录的上下文。

**强制规则: 每次对某个目录的代码做出重大更改时，必须同步更新该目录的 `CLAUDE.md`。**

更新内容必须包含:
1. **变更记录**: 改了什么、为什么改
2. **发现的错误**: 遇到了什么 bug 或问题
3. **修复方法**: 怎么解决的、学到了什么教训

格式: 在对应 CLAUDE.md 的 `## 变更日志` 区域追加条目:
```
### YYYY-MM-DD: 简短描述
- **变更**: 具体改动
- **错误**: 发现的问题 (如有)
- **修复**: 如何解决
- **教训**: 下次如何避免
```

**自动化保障**:
- Git pre-commit hook 会在源文件变更但 CLAUDE.md 未更新时发出警告
- Claude Code PostToolUse hook 在每次 git commit 后提醒更新
- Claude Code Stop hook 在会话结束时检查是否遗漏

## Future Components (Planned)

- **Portfolio optimization:** Risk parity, mean-variance, hierarchical risk parity
- **Backtesting:** Event-driven engine with transaction costs
- **Analytics:** Sharpe ratio, drawdown analysis, factor attribution
- **Reinforcement learning:** DQN/PPO agents for dynamic allocation
