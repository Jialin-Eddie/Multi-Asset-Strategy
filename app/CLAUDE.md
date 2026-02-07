# app/ - Flask 仪表盘应用

Flask 工厂模式，8 个 Blueprint 路由，SimpleCache 1小时 TTL。

## 结构

| 目录/文件 | 功能 |
|-----------|------|
| `__init__.py` | Flask 工厂 (`create_app`)，注册 blueprints + cache |
| `routes/` | 8 个页面路由 |
| `services/` | 数据加载 + 图表生成 |
| `templates/` | Jinja2 HTML 模板 |

## 启动方式

```bash
python run.py  # 项目根目录
```

## 依赖

- Flask, Plotly (图表)
- 读取 `data/processed/prices_clean.csv`
- 运行 EMA 126d 策略实时计算绩效

## 已知问题

- 无认证 (公开访问)
- 无测试覆盖
- 缓存是固定 TTL，非事件驱动

## 变更日志

### 2026-02-07: 初始创建
- **变更**: 创建目录说明文件
