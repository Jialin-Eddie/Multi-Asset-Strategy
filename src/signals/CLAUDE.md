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

## 变更日志

### 2026-02-07: 初始创建
- **变更**: 创建目录说明文件
- **错误**: carry.py 用短期动量/滚动收益率作为 carry 代理变量，IC = -0.031 完全无效
- **修复**: Exp3 标记为 FAILED，记录在 EXPERIMENT_03_SUMMARY.md
- **教训**: 代理变量不等于真实信号；缺乏真实数据时应快速失败而非强行拟合
