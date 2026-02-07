# app/templates/ - Jinja2 HTML 模板

## 模板结构

- `base.html` — 基础布局 (导航栏, CSS/JS 引入)
- 其余模板继承 `base.html`，对应 `routes/` 中同名路由

| 模板 | 对应路由 |
|------|----------|
| `landing.html` | `/` |
| `dashboard.html` | `/dashboard` |
| `performance.html` | `/performance` |
| `methodology.html` | `/methodology` |
| `regimes.html` | `/regimes` |
| `variants.html` | `/variants` |
| `learn.html` | `/learn` |
| `lab.html` | `/lab` |
| `index.html` | 旧版首页 (可能已弃用) |

## 变更日志

### 2026-02-07: 初始创建
- **变更**: 创建目录说明文件
