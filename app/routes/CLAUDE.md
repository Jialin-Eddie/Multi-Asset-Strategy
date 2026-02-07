# app/routes/ - Flask Blueprint 路由

## 页面一览

| 文件 | 路径 | 行数 | 功能 |
|------|------|------|------|
| `landing.py` | `/` | ~20 | 着陆页 |
| `dashboard.py` | `/dashboard` | ~61 | 主仪表盘: 指标+图表+持仓 |
| `performance.py` | `/performance` | ~54 | 绩效分析页 |
| `methodology.py` | `/methodology` | ~137 | 策略方法论说明 |
| `regimes.py` | `/regimes` | ~44 | 市场 regime 分析 |
| `variants.py` | `/variants` | ~78 | 策略变体对比 (初始/最终/基准) |
| `learn.py` | `/learn` | ~21 | 教育内容 (stub) |
| `lab.py` | `/lab` | ~47 | 研究实验接口 |

## 通用模式

- 每个路由通过 `services/data_loader.py` 获取数据
- 图表用 `services/charts.py` 生成 Plotly JSON
- 模板在 `templates/` 下同名 HTML
