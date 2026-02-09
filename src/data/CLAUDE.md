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

## 变更日志

### 2026-02-07: 初始创建
- **变更**: 创建目录说明文件
- **错误**: 早期 start_date 设为 2005-01-01，但 DBC 2006-02-03 才上市，导致 survivorship bias
- **修复**: 更新 config/universe.yaml start_date 为 2006-02-03，validator.py 检查 inception dates
- **教训**: 永远先验证数据质量再做任何策略测试
