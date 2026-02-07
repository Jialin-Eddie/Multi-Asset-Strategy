# scripts/ - 分析脚本

一次性研究脚本，用于参数优化和策略对比。均可独立运行。

## 文件说明

| 文件 | 功能 | 关键结论 |
|------|------|----------|
| `optimize_sma_lookback.py` | SMA 6 组窗口 (63-378d) 对比 | **252d 最优** |
| `optimize_ema_span.py` | EMA 6 组 span 对比 | **126d 最优** (非252!) |
| `compare_all_signals.py` | 5种信号方法横向对比 | EMA 252d 综合最佳 |
| `backtest_risk_parity.py` | 等权 vs 风险平价 | 差异极小 (<0.02 Sharpe) |
| `compare_strategies.py` | SMA vs Dual vs B&H | SMA > Dual > B&H |
| `final_strategy_summary.py` | 最终生产策略汇总 | EMA 126d PRODUCTION READY |
| `john_review.py` | John 代码审查 agent (本地版) | 复杂度评分+自动检查 |
| `alex_report.py` | Alex 管理汇报 agent | 自动生成周报+执行摘要 |

## 运行方式

```bash
python scripts/optimize_ema_span.py
```

## 输出

结果保存到 `outputs/` 目录下对应的 CSV 文件。

## 变更日志

### 2026-02-07: 初始创建
- **变更**: 创建目录说明文件
- **教训**: compare_all_signals.py 结论说 EMA 252d 最佳，但 optimize_ema_span.py 发现 126d 更优 — 两个脚本结论不一致，以后续优化脚本为准

### 2026-02-07: 添加 John 代码审查 agent
- **变更**: 新增 `john_review.py` — 本地 PR 审查工具，检查新文件数、.md/.py 比例、占位符等
- **用法**: `python scripts/john_review.py --branch` 或 `--pr <number>`

### 2026-02-07: 添加 Alex 管理汇报 agent
- **变更**: 新增 `alex_report.py` — 从项目数据自动生成管理层可读的状态报告
- **用法**: `python scripts/alex_report.py` (周报) 或 `--summary` (执行摘要)
- **教训**: 技术指标需要翻译成业务语言才能让管理层理解项目价值
