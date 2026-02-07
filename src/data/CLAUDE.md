# src/data/ - 数据管道

## 文件说明

| 文件 | 行数 | 功能 | 关键函数 |
|------|------|------|----------|
| `downloader.py` | ~200 | Yahoo Finance + Stooq 双源下载 | `download_history()`, `download_history_stooq()` |
| `loader.py` | ~64 | 清洗预处理 (ffill/bfill, 缺失过滤) | `load_raw_prices()`, `preprocess_prices()` |
| `validator.py` | ~362 | 数据质量检查 (inception日期, 异常检测) | `run_full_validation()` |

## 数据流

```
downloader.py → data/raw/multi_asset_prices.csv
loader.py     → data/processed/prices_clean.csv
validator.py  → outputs/data_quality/*.json
```

## 注意事项

- downloader 有 2 秒速率限制避免被封
- 起始日期 2006-02-03 (DBC inception)
- validator 硬编码了 ETF inception dates 防止 survivorship bias
