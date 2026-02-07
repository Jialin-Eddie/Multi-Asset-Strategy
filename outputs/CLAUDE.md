# outputs/ - 实验结果与报告

所有脚本和实验的输出文件。

## 结果文件

| 文件 | 来源 | 内容 |
|------|------|------|
| `sma_optimization_results.csv` | `scripts/optimize_sma_lookback.py` | 6组SMA窗口绩效 |
| `ema_optimization_results.csv` | `scripts/optimize_ema_span.py` | 6组EMA span绩效 |
| `signal_comparison.csv` | `scripts/compare_all_signals.py` | 5种信号横向对比 |
| `strategy_comparison.csv` | `scripts/compare_strategies.py` | SMA/Dual/B&H对比 |
| `risk_parity_comparison.csv` | `scripts/backtest_risk_parity.py` | EW vs RP |
| `final_strategy_summary.csv` | `scripts/final_strategy_summary.py` | **最终生产策略** |
| `FINAL_STRATEGY_REPORT.txt` | 同上 | 文本版报告 |

## 子目录

| 目录 | 内容 |
|------|------|
| `experiments/` | 实验 JSON 结果 (目前仅 Exp3) |
| `data_quality/` | 数据验证 JSON 报告 |

## 关键数据点 (最终策略)

- Sharpe 0.82, Ann Return 9.76%, MaxDD -23.89%
- 策略: EMA 126d, 等权, 月度再平衡, 5bps 成本
