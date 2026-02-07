# src/signals/ - 信号生成

## 文件说明

| 文件 | 行数 | 功能 | 状态 |
|------|------|------|------|
| `trend_filter.py` | ~351 | 5种趋势信号 (SMA/EMA/绝对/相对/双动量) | 完成, 40+测试 |
| `carry.py` | ~460 | Carry信号 (需FRED API key) | 失败 (IC=-0.031) |

## trend_filter.py 关键接口

```python
generate_signals(prices, method='ema', **kwargs) → pd.DataFrame  # 统一入口
# method: 'sma', 'ema', 'absolute', 'relative', 'dual'
```

5个信号本质都是**价格动量变体**，相关性高，缺乏多元化。

## 生产配置

- **当前使用**: EMA 126d (`generate_signals(prices, method='ema', span=126)`)
- **信号格式**: DataFrame, 值为 0 或 1, NaN 表示数据不足

## carry.py 结论

Exp3 验证失败: Mean IC = -0.031 (阈值 >0.10)。根本原因: 缺乏真实 carry 数据 (期货曲线/分红收益率)，代理变量无效。
