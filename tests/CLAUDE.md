# tests/ - 测试套件

使用 pytest 框架。

## 结构

| 文件/目录 | 内容 |
|-----------|------|
| `conftest.py` | 6 个共享 fixture (合成数据) |
| `test_signals/test_trend_filter.py` | 12 个测试类, 40+ 测试用例 |
| `test_signals/test_regime.py` | 5 个测试类, 17 个测试: regime信号 |
| `test_signals/test_volatility.py` | 4 个测试类, 14 个测试: vol信号 |
| `test_signals/test_mean_reversion.py` | 4 个测试类, 15 个测试: 均值回归信号 |
| `test_signals/test_composite.py` | 5 个测试类, 16 个测试: 信号融合 |
| `test_data/` | 仅 `__init__.py`，无实际测试 |
| `test_risk/test_overlay.py` | 17 个测试: drawdown_scalar + vol_scalar + apply_risk_overlay |

## conftest.py Fixtures

| Fixture | 说明 |
|---------|------|
| `sample_prices` | 300天合成数据 (SPY涨/TLT跌/GLD横盘) |
| `simple_uptrend` | 确定性线性上涨 |
| `simple_downtrend` | 确定性线性下跌 |
| `prices_with_nan` | 含缺失值的数据 |
| `short_history` | 10天极短数据 |
| `cross_sectional_data` | 5资产不同动量特征 |

## 覆盖情况

- ✅ `src/signals/trend_filter.py` — 充分覆盖 (40+测试)
- ✅ `src/signals/regime.py` — 17 测试
- ✅ `src/signals/volatility.py` — 14 测试
- ✅ `src/signals/mean_reversion.py` — 15 测试
- ✅ `src/signals/composite.py` — 16 测试
- ✅ `src/risk/overlay.py` — 17 测试 (drawdown/vol/overlay)
- ❌ `src/backtest/engine.py` — 无测试
- ❌ `src/portfolio/risk_parity.py` — 无测试
- ❌ `app/` — 无测试

## 运行

```bash
pytest tests/ -v
```

## 变更日志

### 2026-02-07: 初始创建
- **变更**: 创建目录说明文件
- **教训**: backtest/engine.py 和 portfolio/risk_parity.py 零测试覆盖是重大隐患，新功能开发前应先补测试

### 2026-02-08: 添加 risk overlay 测试
- **变更**: 新增 `test_risk/test_overlay.py` — 17 个测试覆盖 drawdown_scalar, volatility_scalar, apply_risk_overlay
- **错误**: 初版测试用价格阈值 (< 135) 判断回撤, 但忽略了早期上涨前低价也低于阈值
- **修复**: 改用实际 drawdown 计算 (expanding max) 来判断是否处于回撤状态
- **教训**: 测试回撤时必须用 drawdown 百分比而非绝对价格, 否则会把非回撤期的低价误判

### 2026-02-08: Phase 1 信号测试
- **变更**: 新增 4 个测试模块 (test_regime, test_volatility, test_mean_reversion, test_composite), 共 62 个新测试
- **错误**: equal_weight_blend 的 concat+groupby 丢失 index freq 元数据导致 assert_frame_equal 失败; vol_spike 测试窗口选取不当
- **修复**: 用 assert_array_almost_equal 替代 assert_frame_equal; 调整 vol_spike 测试窗口到 transition period
- **教训**: pandas concat+groupby 会丢失 DatetimeIndex 的 freq 属性; vol 信号测试需要选择正确的时间窗口 (transition vs steady state)
