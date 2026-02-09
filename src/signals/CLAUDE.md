# src/signals/ - 信号生成

## 文件说明

| 文件 | 行数 | 功能 | 状态 |
|------|------|------|------|
| `trend_filter.py` | ~351 | 5种趋势信号 (SMA/EMA/绝对/相对/双动量) | 完成, 40+测试 |
| `carry.py` | ~460 | Carry信号 (需FRED API key) | 失败 (IC=-0.031) |
| `regime.py` | ~190 | Regime检测信号 (vol/动量/相关性) | Phase 1 新增 |
| `volatility.py` | ~170 | 波动率结构信号 (期限结构/VoV/均值回归) | Phase 1 新增 |
| `mean_reversion.py` | ~175 | 均值回归信号 (Z-score/RSI/Bollinger) | Phase 1 新增 |
| `composite.py` | ~220 | 信号融合框架 (等权/逆相关/regime条件) | Phase 1 新增 |

## 关键接口

```python
# 趋势/动量 (原有)
generate_signals(prices, method='ema', **kwargs) → pd.DataFrame
# method: 'sma', 'ema', 'absolute', 'relative', 'dual'

# Regime 检测
realized_vol_regime(prices) → pd.DataFrame       # 0.0/0.5/1.0
cross_asset_momentum_regime(prices) → pd.Series   # 0.0/1.0
correlation_regime(prices) → pd.Series            # 0.0/1.0
composite_regime(prices) → pd.Series              # 0.0~1.0
regime_position_scalar(score) → pd.Series         # 0.0~1.0

# 波动率信号
generate_vol_signal(prices, method) → pd.DataFrame
# method: 'term_structure', 'vol_of_vol', 'mean_reversion'

# 均值回归
generate_mr_signal(prices, method) → pd.DataFrame
# method: 'zscore', 'rsi', 'bollinger'

# 信号融合
equal_weight_blend(signals) → pd.DataFrame
inverse_correlation_blend(signals) → pd.DataFrame
regime_conditional_blend(signals, regime_score) → pd.DataFrame
signal_to_binary(signal, threshold=0.5) → pd.DataFrame
signal_correlation_report(signals) → pd.DataFrame
```

## 信号类型分类

| 类别 | 模块 | 与动量相关性 | Alpha来源 |
|------|------|:----------:|-----------|
| 动量/趋势 | `trend_filter.py` | 1.0 (自身) | 价格惯性 |
| Regime | `regime.py` | 低 | 宏观环境变化 |
| 波动率 | `volatility.py` | 低~中 | 波动率均值回归 |
| 均值回归 | `mean_reversion.py` | 负 | 短期价格过冲 |

**关键设计**: 动量(中长期) + 均值回归(短期) 互补；Regime信号在危机时保护组合。

## 生产配置

- **当前使用**: EMA 126d (`generate_signals(prices, method='ema', span=126)`)
- **信号格式**: 连续值 0-1 (新模块) 或 二值 0/1 (trend_filter)
- NaN 表示数据不足

## carry.py 结论

Exp3 验证失败: Mean IC = -0.031 (阈值 >0.10)。根本原因: 缺乏真实 carry 数据 (期货曲线/分红收益率)，代理变量无效。

## 变更日志

### 2026-02-07: 初始创建
- **变更**: 创建目录说明文件
- **错误**: carry.py 用短期动量/滚动收益率作为 carry 代理变量，IC = -0.031 完全无效
- **修复**: Exp3 标记为 FAILED，记录在 EXPERIMENT_03_SUMMARY.md
- **教训**: 代理变量不等于真实信号；缺乏真实数据时应快速失败而非强行拟合

### 2026-02-08: Phase 1 — 信号多元化
- **变更**: 新增4个信号模块 (regime, volatility, mean_reversion, composite)
  - `regime.py`: 3个子信号 (vol regime, cross-asset momentum, correlation) + 复合 + position scalar
  - `volatility.py`: 3个子信号 (term structure, vol-of-vol, mean reversion) + generate_vol_signal
  - `mean_reversion.py`: 3个子信号 (z-score, RSI, bollinger) + generate_mr_signal
  - `composite.py`: 3种融合方法 (equal weight, inverse correlation, regime conditional) + binary转换 + 相关性报告
- **测试**: 62个新测试全部通过 (总计102个信号测试)
- **教训**: 新信号使用连续值 (0-1) 而非二值 (0/1)，提供更细粒度的仓位控制；composite.py的equal_weight_blend用concat+groupby时会丢失index freq元数据
