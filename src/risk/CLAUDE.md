# src/risk/ - 风险叠加层

## 文件说明

| 文件 | 行数 | 功能 |
|------|------|------|
| `overlay.py` | ~230 | 风险叠加层: 回撤控制 + 波动率缩放 |
| `beta_hedge.py` | ~260 | Beta 对冲: rolling beta 计算 + 权重调整 + 完整回测 |
| `__init__.py` | ~12 | 包初始化, 导出所有公共函数 |

## overlay.py 关键函数

| 函数 | 用途 |
|------|------|
| `drawdown_scalar()` | 两级回撤控制: -10% → 50%仓位, -20% → 0% |
| `volatility_scalar()` | 目标波动率缩放: target_vol / realized_vol |
| `apply_risk_overlay()` | 完整回测循环 + 风险控制叠加 |

## 关键设计

- 独立于信号层 — 可叠加到任何策略之上
- 两级回撤控制 (threshold_1/threshold_2) 而非硬切
- 波动率缩放有上限 (max_leverage) 和下限 (min_scalar) 防止极端值
- apply_risk_overlay 内部实现了完整的回测循环 (与 engine.py 结构类似)
- 月初再平衡 + weight drift + 交易成本

## beta_hedge.py 关键函数

| 函数 | 用途 |
|------|------|
| `compute_beta(asset_returns, benchmark_returns, lookback)` | rolling(lookback).cov / rolling(lookback).var; NaN 前 lookback-1 行 |
| `beta_hedge_weights(weights, betas, hedge_ratio)` | 按 beta/avg_beta 比例削减权重, clip lower=0, 保持原总权重 |
| `apply_beta_hedge_overlay(prices, signals, ...)` | 完整回测 + drawdown/vol 控制 + beta hedge |

## 已知局限

- apply_risk_overlay 与 engine.py 的回测循环有代码重复
- 回撤控制是逐日检查但只在再平衡日调整仓位
- 无 correlation circuit breaker 实现 (仅文档声明)

## 变更日志

### 2026-02-08: 初始创建
- **变更**: 创建 overlay.py — Phase 0 风险叠加层
- **设计**: 两级回撤控制 + 可选波动率缩放, 独立于信号层
- **教训**: apply_risk_overlay 内部重新实现了回测循环而非复用 engine.py, 未来应重构为可组合的回测管道

### 2026-02-14: 新增 Beta 对冲模块
- **变更**: 创建 beta_hedge.py — rolling beta 估计 + 权重调整 + 完整回测循环
- **设计**: compute_beta 用 rolling cov/var 向量化实现; beta_hedge_weights 按 beta/avg_beta 比例削减高 beta 资产权重; apply_beta_hedge_overlay 在 combined_scalar 之后、turnover 计算之前应用 beta 对冲
- **架构**: 独立模块，不修改 overlay.py，避免回归风险
- **__init__.py**: 从空文件更新为导出 src.risk 全部 6 个公共函数
