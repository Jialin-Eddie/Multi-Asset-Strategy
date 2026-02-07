# src/portfolio/ - 组合优化

## 文件说明

| 文件 | 行数 | 功能 | 状态 |
|------|------|------|------|
| `risk_parity.py` | ~276 | 风险平价权重计算 | 部分完成 |

## risk_parity.py 关键函数

| 函数 | 用途 | 状态 |
|------|------|------|
| `inverse_volatility_weights()` | w_i = (1/vol_i) / Σ(1/vol_j), 60d rolling | 完成 |
| `target_volatility_weights()` | 缩放权重至目标波动率 10%, 杠杆上限 2x | 完成 |
| `equal_risk_contribution_weights()` | **占位符** — 实际调用 inverse_vol | 未实现 |
| `apply_risk_parity_to_signals()` | 便捷入口: 信号 × 风险权重 → 活跃权重 | 完成 |

## 关键问题

- ERC 是假的! 注释写 "approximate solution"，实际就是 inverse vol
- 实测: Risk Parity Sharpe 0.722 vs Equal Weight 0.708，差异 < 0.02 — **说明当前方法无贡献**
- 真正的 ERC 需要 scipy.optimize 求解非线性约束优化
- 项目已有 `riskfolio-lib` 依赖，可直接用 HRP

## 无测试覆盖
