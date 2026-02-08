# src/risk/ - 风险叠加层

## 文件说明

| 文件 | 行数 | 功能 |
|------|------|------|
| `overlay.py` | ~230 | 风险叠加层: 回撤控制 + 波动率缩放 |
| `__init__.py` | 0 | 包初始化 |

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

## 已知局限

- apply_risk_overlay 与 engine.py 的回测循环有代码重复
- 回撤控制是逐日检查但只在再平衡日调整仓位
- 无 correlation circuit breaker 实现 (仅文档声明)

## 变更日志

### 2026-02-08: 初始创建
- **变更**: 创建 overlay.py — Phase 0 风险叠加层
- **设计**: 两级回撤控制 + 可选波动率缩放, 独立于信号层
- **教训**: apply_risk_overlay 内部重新实现了回测循环而非复用 engine.py, 未来应重构为可组合的回测管道
