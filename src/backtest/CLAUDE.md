# src/backtest/ - 回测引擎

## 文件说明

| 文件 | 行数 | 功能 |
|------|------|------|
| `engine.py` | ~483 | 完整回测引擎 + 绩效计算 + regime分类 |

## engine.py 关键函数

| 函数 | 用途 |
|------|------|
| `calculate_strategy_returns()` | 核心回测: 信号→权重→收益→成本扣除 |
| `calculate_performance_metrics()` | Sharpe/Sortino/MaxDD/Calmar/胜率 |
| `calculate_drawdown_series()` | 回撤时间序列 |
| `backtest_strategy()` | 便捷入口: 回测+指标+对标 |
| `classify_regimes()` | SPY ±20% 阈值分 bull/bear/sideways |
| `performance_by_regime()` | 按regime分组的绩效 |
| `extract_trade_log()` | 逐笔交易记录 |

## 关键设计

- 信号 shift(1) 避免前视偏差
- 月初再平衡 (freq='MS')
- 非再平衡日权重随收益漂移 (weight drift)
- 交易成本 = turnover × cost_rate (固定比例)
- 252 交易日/年

## 已知局限

- 成本模型过于简单 (固定 bps, 无动态组件)
- regime 分类用硬编码阈值 (±20%), 无统计基础
- 无滑点模型
- 无 position_size='equal_risk' 的实际实现 (fallback 到 equal_weight)

## 变更日志

### 2026-02-07: 初始创建
- **变更**: 创建目录说明文件
- **教训**: position_size='equal_risk' 参数存在但未实现，调用时静默 fallback 到 equal_weight，应该抛出 NotImplementedError 或明确文档
