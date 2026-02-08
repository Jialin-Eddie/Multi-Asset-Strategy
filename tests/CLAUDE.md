# tests/ - 测试套件

使用 pytest 框架。

## 结构

| 文件/目录 | 内容 |
|-----------|------|
| `conftest.py` | 6 个共享 fixture (合成数据) |
| `test_signals/test_trend_filter.py` | 12 个测试类, 40+ 测试用例 |
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

- ✅ `src/signals/trend_filter.py` — 充分覆盖
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
