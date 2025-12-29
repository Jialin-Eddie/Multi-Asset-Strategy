# FRED API Setup Guide

获取免费的FRED API密钥以下载真实国债收益率数据。

## Step 1: 注册FRED账户

1. 访问: https://fred.stlouisfed.org/
2. 点击右上角 "Sign In" → "Create Account"
3. 填写信息注册（免费，30秒完成）

## Step 2: 获取API Key

1. 登录后，访问: https://fredaccount.stlouisfed.org/apikeys
2. 点击 "Request API Key"
3. 填写简单表单（随便填，审核立即通过）
4. 获得32位API key (类似: `abcd1234efgh5678ijkl9012mnop3456`)

## Step 3: 设置环境变量

### Windows (PowerShell)
```powershell
# 临时设置 (当前session有效)
$env:FRED_API_KEY="your_api_key_here"

# 永久设置
[System.Environment]::SetEnvironmentVariable('FRED_API_KEY', 'your_api_key_here', 'User')

# 验证
echo $env:FRED_API_KEY
```

### Windows (CMD)
```cmd
# 临时设置
set FRED_API_KEY=your_api_key_here

# 验证
echo %FRED_API_KEY%
```

### Linux/Mac
```bash
# 临时设置
export FRED_API_KEY="your_api_key_here"

# 永久设置 (添加到 ~/.bashrc 或 ~/.zshrc)
echo 'export FRED_API_KEY="your_api_key_here"' >> ~/.bashrc
source ~/.bashrc

# 验证
echo $FRED_API_KEY
```

## Step 4: 测试连接

```bash
# 运行carry signal测试
cd Multi-Asset-Strategy
python src/signals/carry.py
```

**预期输出:**
```
Carry Data Source Availability:
============================================================
[OK] FRED API: Available (Treasury yields)
[OK] Yahoo Finance: Available (Dividend yields)
...
Downloading 10Y Treasury yields from FRED...
Downloaded XXXX observations
```

## 如果遇到问题

### 错误: "FRED API key required"
- 检查环境变量是否设置: `echo $env:FRED_API_KEY` (PowerShell)
- 重启terminal/IDE使环境变量生效

### 错误: "API key is invalid"
- 确认API key没有多余空格
- 确认在FRED网站上key状态是"Active"

### 错误: "Rate limit exceeded"
- FRED免费tier限制: 120 requests/minute
- 我们的代码一次只请求1个序列，不会超限

## 数据说明

### 我们下载的数据

| 数据源 | FRED代码 | 说明 | 频率 |
|--------|---------|------|------|
| 10-Year Treasury | DGS10 | 10年期国债到期收益率 | 日频 |

### 数据质量

- **更新频率**: 每工作日
- **历史长度**: 1962年至今
- **缺失值**: 周末/节假日无数据（我们会forward-fill）
- **单位**: 百分比 (如 2.5 表示 2.5%)

## 替代方案 (如果不想注册FRED)

### 选项1: 使用pandas-datareader的FRED接口
```python
import pandas_datareader as pdr
yields = pdr.DataReader('DGS10', 'fred', start='2006-01-01')
```
⚠️ 仍需FRED API key

### 选项2: 手动下载CSV
1. 访问: https://fred.stlouisfed.org/series/DGS10
2. 点击 "Download" → CSV
3. 保存到 `data/external/DGS10.csv`
4. 修改代码读取本地CSV

### 选项3: 使用其他数据源
- Yahoo Finance: `^TNX` (10-year yield ticker)
- Quandl: `FRED/DGS10`
- 缺点: 数据质量可能不如FRED官方

## 费用

FRED API **完全免费**，无隐藏费用。

限制:
- 120 requests/minute
- 无每日限额
- 无需信用卡

我们的使用量远低于限制（每次运行只请求1-2个序列）。
