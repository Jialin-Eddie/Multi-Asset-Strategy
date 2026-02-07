# config/ - 策略配置

## 文件

| 文件 | 功能 |
|------|------|
| `universe.yaml` | 资产宇宙 + 策略参数 + 风险约束 |

## universe.yaml 关键参数

```yaml
universe: [SPY, TLT, GLD, DBC, VNQ]  # 5 ETFs
data:
  start_date: "2006-02-03"  # DBC inception
trend:
  lookback_days: 252
risk:
  target_vol: 0.10       # 10% 年化波动率目标
  rebalance_freq: "M"    # 月度再平衡
constraints:
  max_weight: 0.4        # 单资产最大 40%
  long_only: true
```

## 注意

- 生产策略实际用 EMA 126d (非 yaml 中的 252d lookback)
- yaml 中的 target_vol 和 max_weight 目前仅被 risk_parity.py 部分使用
- 修改后需重新运行 downloader.py 获取新数据
