# src/ - 核心源码

所有业务逻辑代码。路径约定: `Path(__file__).resolve().parents[2]` 指向项目根目录。

## 子模块

| 目录 | 职责 | 状态 |
|------|------|------|
| `data/` | 数据下载、清洗、验证 | 完成 |
| `signals/` | 信号生成 (趋势+carry) | 完成 (carry失败) |
| `backtest/` | 回测引擎 | 完成 |
| `portfolio/` | 组合优化 (风险平价) | 部分 (ERC是占位符) |
| `diagnostics/` | 实验验证框架 | 仅Exp3 |

## 设计规范

- 每个模块都有 `if __name__ == "__main__"` 可独立运行
- 函数签名用 type hints (`pd.DataFrame`, `Dict`, `Optional`)
- 无全局状态，纯函数式设计
- 无 logging 模块 (全部 print)，待改进
