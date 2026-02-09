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

## 上下文管理规则 (强制)

当对话上下文窗口接近 **50% 容量**时，必须自动执行以下操作：

1. **打 checkpoint**: `git tag -a checkpoint-<描述> -m "..."` 标记当前进度
2. **更新 MEMORY.md**: 将当前项目状态、进行中的任务、未完成工作写入 `/root/.claude/projects/-home-user-Multi-Asset-Strategy/memory/MEMORY.md`
3. **压缩对话**: 主动总结已完成工作，清理冗余上下文，释放窗口空间给后续任务

**判断标准**: 如果你感觉上下文变长、响应变慢、或已经进行了大量工具调用（>50 次），就应该触发 checkpoint + 压缩。不要等到被系统强制截断才处理。

**目的**: 防止关键上下文在自动压缩中丢失。MEMORY.md 是跨会话的持久记忆，checkpoint tag 是代码状态的快照。

## 根目录整洁规则 (强制)

**根目录是项目的门面，必须保持最小化。** 质疑每一个要放在根目录下的新文件。

### 允许存在于根目录的文件类型
- **必要配置**: `CLAUDE.md`, `.gitignore`, `environment.yml`, `requirements.txt`, `setup.py`/`pyproject.toml`
- **项目说明**: `README.md`, `LICENSE`
- **已有评估文档**: `EVALUATION_AND_ROADMAP.md`（历史原因保留）

### 禁止随意在根目录创建的文件
- **临时输出/报告**: 放入 `outputs/` 目录
- **Jupyter notebooks**: 放入 `notebooks/` 目录
- **脚本**: 放入 `scripts/` 目录
- **配置文件**: 放入 `config/` 目录
- **新的 .md 文档**: 除非有强力理由，否则放入 `docs/` 目录

### 创建前必须回答的问题
每次要在根目录创建新文件时，先回答：
1. **这个文件能不能放到某个子目录里？** → 如果可以，放子目录
2. **这个文件是不是所有开发者都需要第一时间看到的？** → 如果不是，不该在根目录
3. **根目录已有类似文件吗？** → 如果有，合并而不是新建

**违反处罚**: 如果在根目录创建了不必要的文件，下次 John 审查时会被标记为 ❌ Reject。

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

## Phase 交付流程 (强制)

每个 Phase 完成后，必须执行以下 GitHub 操作，**不能只 push 代码**：

### 1. GitHub 对象创建清单

| 操作 | 说明 | 命令 |
|------|------|------|
| **Milestone** | 创建并关联到 Phase | `gh api repos/OWNER/REPO/milestones --method POST -f title="Phase N: ..."` |
| **Issues** | 每个模块一个 issue，关联 milestone | `gh issue create --milestone "Phase N: ..."` |
| **PR** | 从 feature branch → master，body 中 `closes #N` 关联 issues | `gh pr create --base master --milestone "..."` |
| **Review** | 在 PR 上运行 John 代码审查并提交 PR Review | 用 GitHub API `POST /pulls/{n}/reviews` |
| **Release** | 打 tag + 创建 release，包含变更说明 | `gh release create vX.Y.Z` |
| **Close** | Issues/Milestone 在 merge 后关闭 | PR body 的 `closes #N` 自动关闭 |

### 2. 前置条件

- **`gh` CLI 需要认证**: 容器环境没有 GitHub API token，只有 git push 代理。需要用户提供 `GH_TOKEN` (Fine-grained PAT)
- **John 的 workflow 需在 master 上**: `.github/workflows/john-review.yml` 只有在 master 分支上才会被 PR 事件触发。新 workflow 必须先 merge 到 master
- **不能对自己的 PR request changes**: GitHub 限制。John 的 review 用 `COMMENT` 事件代替

### 3. John 代码审查要求

John 的审查**必须包含逐行代码评论**，不能只是文件统计。审查内容：
- 具体 bug（NaN 处理、零除、边界条件）
- 性能问题（Python 循环 vs 向量化）
- API 设计缺陷（参数校验、权重归一化）
- 每条评论需附带**修复建议代码**

`scripts/john_review.py` 只做基础统计，**不算真正审查**。真正审查需要读代码并通过 PR Review API 提交 inline comments。

## 已知问题与教训 (Session Log)

### 2026-02-08: Phase 1 交付流程问题

**问题 1: 只 push 代码没有创建 GitHub 对象**
- **现象**: 代码已 push 但 GitHub 上看不到 PR、milestone、issues
- **原因**: 只做了 `git push`，没有调用 GitHub API 创建项目管理对象
- **修复**: 补充了完整的 Phase 交付流程清单（见上方）
- **教训**: **Phase 完成 ≠ 代码 push。必须创建 PR + milestone + issues + review + release**

**问题 2: 容器环境无 GitHub API token**
- **现象**: `gh auth login` 失败，无法创建 PR/issues
- **原因**: 本地 git 代理 (127.0.0.1:53486) 只支持 git smart HTTP 协议，不转发 REST API。GitHub token 存储在代理服务端，子进程不可访问
- **修复**: 用户提供 Fine-grained PAT → `GH_TOKEN` 环境变量
- **教训**: **Claude Code 远程容器中 git push ≠ API access。需要用户提供 PAT**

**问题 3: John workflow 不自动触发**
- **现象**: PR 创建后 John 的 GitHub Actions 审查没有运行
- **原因**: `john-review.yml` 只在 feature branch 上，不在 master 上。GitHub Actions 的 `pull_request` 触发器要求 workflow 在**目标分支**上
- **修复**: 手动运行 John 审查 + 通过 API 提交 PR Review
- **教训**: **新的 workflow 文件必须先 merge 到 master 才能被 PR 事件触发**

**问题 4: John 审查只是文件统计，不是代码审查**
- **现象**: John 只报告了文件数量和 .md/.py 比例，没有审查具体代码
- **原因**: `scripts/john_review.py` 设计为轻量统计工具，不读代码内容
- **修复**: 用 subagent 逐文件审查代码 → 通过 GitHub PR Review API 提交 inline comments
- **教训**: **代码审查必须 review 代码本身。统计指标不等于审查**

**问题 5: 不能对自己的 PR request changes**
- **现象**: `REQUEST_CHANGES` 事件返回 422 错误
- **原因**: GitHub 不允许 PR 创建者对自己的 PR request changes
- **修复**: 改用 `COMMENT` 事件，inline comments 同样可见
- **教训**: **用同一 token 创建 PR + 审查时，只能用 COMMENT 不能用 REQUEST_CHANGES**

**问题 6: 没有 GitHub Release**
- **现象**: 项目没有任何 release/tag
- **修复**: 每个 Phase 完成后创建 release tag
- **教训**: **Release 是项目交付的最终产物，不能遗漏**

## Future Components (Planned)

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
