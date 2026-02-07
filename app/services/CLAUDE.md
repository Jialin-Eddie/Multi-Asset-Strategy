# app/services/ - 仪表盘服务层

## 文件说明

| 文件 | 行数 | 功能 |
|------|------|------|
| `data_loader.py` | ~175 | 加载价格数据，运行 EMA 策略，缓存结果 |
| `charts.py` | ~100+ | Plotly 图表生成 (权益曲线, 饼图, 回撤) |

## data_loader.py 关键逻辑

- 读取 `data/processed/prices_clean.csv`
- 运行 EMA 126d 策略 (生产配置)
- 同时计算 EMA 252d (对比) 和 Buy & Hold (基准)
- 预计算 regime 分类和 trade log
- 结果缓存到 Flask SimpleCache (1h TTL)

## 注意

- 数据加载是同步的，首次访问会有延迟
- 策略参数硬编码在 data_loader 中，非配置驱动
