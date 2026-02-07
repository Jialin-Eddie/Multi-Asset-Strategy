# data/ - 数据存储

## 目录结构

| 子目录 | 内容 | 来源 |
|--------|------|------|
| `raw/` | 原始下载价格 (`multi_asset_prices.csv`) | `src/data/downloader.py` |
| `processed/` | 清洗后价格 (`prices_clean.csv`) | `src/data/loader.py` |
| `signals/` | 预计算信号 (`carry_signals.csv`) | `src/diagnostics/` |

## 数据格式

- CSV, DatetimeIndex, 列名 = ticker symbols (SPY, TLT, GLD, DBC, VNQ)
- Adj Close 价格 (含分红/拆股调整)
- 日期范围: 2006-02-03 至 2025-01-07
- 约 4900 个交易日

## 数据质量

- 缺失率 < 5% (ffill/bfill 处理后为 0)
- 无极端价格异常 (Z-score < 5σ)
- DBC inception 2006-02-03 已验证

## 变更日志

### 2026-02-07: 初始创建
- **变更**: 创建目录说明文件
