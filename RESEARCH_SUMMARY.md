# Research Framework Summary

**日期**: 2024-12-20
**状态**: 基础框架已建立，数据质量检查完成

---

## ✅ 已完成工作

### 1. 研究方法论建立 (RESEARCH_PROTOCOL.md)

建立了**三条核心铁律**，确保所有研究工作的严谨性：

#### 🔒 原则 1: 强制 Walk-Forward 验证
- **要求**: 明确定义训练集(2006-2015)、验证集(2016-2019)、测试集(2020-2024)
- **规则**: 测试集只能看一次，结果必须记录时间戳
- **目的**: 防止过拟合和数据窥探

**时间划分**:
```
Training:   2006-01-01 to 2015-12-31 (10年) - 参数优化
Validation: 2016-01-01 to 2019-12-31 (4年)  - 参数选择
Test:       2020-01-01 to 2024-12-31 (5年)  - 最终报告(只看一次)
```

#### 💰 原则 2: 强制成本敏感性分析
- **要求**: 所有策略必须测试3档成本(乐观5bps/基准12bps/保守25bps)
- **动态成本**: 必须包含波动率或成交量驱动的成本变化
- **盈亏平衡**: 必须计算并报告策略的盈亏平衡成本

**成本场景**:
```
乐观 (Optimistic):      5 bps  - 小规模/高流动性
基准 (Baseline):       12 bps  - 正常市场条件
保守 (Conservative):   25 bps  - 压力/早期时期
```

#### ⛔ 原则 3: 必须明确失败标准
- **要求**: 在实验运行前定义量化的失败标准
- **自动检测**: 实现失败标准自动检查函数
- **透明记录**: 失败结果必须记录，不能隐瞒

**通用失败标准**:
```
- OOS Sharpe < 0.5
- Max Drawdown > 25%
- 月均Turnover > 100%
- 盈亏平衡成本 < 15bps
- 超过50%收益来自单一年份或资产
```

---

### 2. 数据质量验证 (src/data/validator.py)

实现了完整的数据质量检查流程，遵循RESEARCH_PROTOCOL.md标准：

**验证项目**:
1. ✅ ETF上市日期检查 - 确保不使用上市前数据
2. ✅ 数据完整性检查 - 缺失率必须<5%
3. ✅ 价格异常检测 - Z-score方法识别数据错误

**验证结果 (2024-12-20 07:30)**:
```
[FAIL] ETF inception date check: FAILED
  - DBC上市日期: 2006-02-03 (晚于请求的2005-01-01)
  - 建议: 使用2006-02-03作为起始日期

[PASS] Data completeness check: PASSED
  - 所有资产缺失率 < 5%

[PASS] Price anomaly detection: PASSED
  - 未发现极端价格异常
```

**关键发现**:
- ❌ **数据时间范围问题**: 当前配置使用2005-01-01起始，但DBC在2006-02-03才上市
- ✅ **修正建议**: 更新`config/universe.yaml`的`start_date`为`2006-02-03`

---

### 3. 项目文档更新 (CLAUDE.md)

更新了项目架构文档，包含：
- 环境设置和依赖说明
- 数据管道命令(下载/清洗)
- 模块结构和设计模式
- 开发工作流程

---

## 📋 实验矩阵设计

已设计10个关键实验，覆盖策略的所有潜在失败点：

| 优先级 | 实验 | 目标 | 失败标准 |
|--------|------|------|----------|
| P0 | Exp 1: 协方差估计稳定性 | 检测risk budgeting可行性 | 条件数>100占比>30% |
| P0 | Exp 2: 波动率预测精度 | 验证vol targeting有效性 | 预测误差>50%占比>10% |
| P1 | Exp 3: Carry信号有效性 | 快速排除无效信号 | IC<0.15 |
| P1 | Exp 4: Momentum崩盘风险 | 识别尾部风险 | VIX>30时Sharpe<0 |
| P0 | Exp 5: 交易成本影响 | 确定策略可行性 | 基准成本下Sharpe<0.5 |
| P1 | Exp 6: 策略拥挤度 | 检测crowding风险 | 与CTA指数相关性>0.7 |
| P0 | Exp 7: 参数稳定性 | Walk-forward验证 | 最优参数变化>50% |
| P1 | Exp 8: Regime非平稳性 | 检测策略衰减 | 2020-2024 Sharpe<0.3 |
| P2 | Exp 9: 杠杆约束 | 验证vol targeting可行性 | 需求杠杆>2x占比>20% |
| P2 | Exp 10: 样本外泛化 | 检测data snooping | 替代宇宙Sharpe<0.3 |

---

## 🎯 下一步行动计划

### 立即执行 (Phase 1: 数据基础)

1. **修复数据时间范围**
   ```bash
   # 更新config/universe.yaml
   data:
     start_date: "2006-02-03"  # 改为DBC上市日期

   # 重新下载数据
   python src/data/downloader.py
   python src/data/loader.py

   # 重新验证
   python src/data/validator.py
   ```

2. **运行Experiment 3 (Carry信号验证)**
   - 目的: 快速确定carry信号是否有效
   - 如果carry无效(IC<0.15)，可以早点放弃这个信号
   - 实现: `src/diagnostics/experiment_03_carry.py`

3. **运行Experiment 5 (交易成本分析)**
   - 目的: 了解成本对策略的影响上限
   - 计算盈亏平衡成本
   - 实现: `src/diagnostics/experiment_05_transaction_costs.py`

### 后续执行 (Phase 2: 核心风险)

4. **Experiment 1 (协方差稳定性)**
   - 检测risk budgeting是否可行
   - 实现协方差矩阵条件数测试

5. **Experiment 2 (波动率预测)**
   - 验证vol targeting的有效性
   - 测试realized vol vs GARCH vs EWMA

6. **Experiment 4 (Momentum崩盘)**
   - 识别已知crash期(2009-03, 2020-03)的表现
   - 分regime测试momentum有效性

### 最后验证 (Phase 3-4: 稳健性检验)

7-10. 参数稳定性、Regime分析、杠杆约束、样本外泛化测试

---

## 📝 代码框架已设计

完整的模块结构和函数签名已定义：

```
src/
├── data/
│   ├── validator.py          ✅ 已实现
│   ├── loader.py              ✅ 已存在
│   └── downloader.py          ✅ 已存在
│
├── signals/
│   ├── momentum.py            📋 待实现
│   ├── carry.py               📋 待实现
│   └── composite.py           📋 待实现
│
├── portfolio/
│   ├── risk_budgeting.py      📋 待实现
│   ├── volatility_targeting.py 📋 待实现
│   └── constraints.py         📋 待实现
│
├── backtest/
│   ├── engine.py              📋 待实现
│   ├── costs.py               📋 待实现
│   └── execution.py           📋 待实现
│
├── diagnostics/               ⭐ 核心实验层
│   ├── experiment_01_covariance.py      📋 待实现
│   ├── experiment_02_volatility.py      📋 待实现
│   ├── experiment_03_carry.py           🎯 优先
│   ├── experiment_04_momentum_crash.py  📋 待实现
│   ├── experiment_05_transaction_costs.py 🎯 优先
│   └── ...
│
└── analytics/
    ├── performance.py         📋 待实现
    └── visualization.py       📋 待实现
```

---

## ⚠️ 关键注意事项

### 必须遵守的规则

1. **Walk-Forward规则**
   - 任何参数选择只能用训练集+验证集
   - 测试集结果首次生成后立即记录时间戳
   - 禁止: "测试集表现不好，调整参数再跑一次"

2. **成本现实化**
   - 所有回测必须测试3档成本
   - DBC和VNQ在2006-2010年spread远大于现在
   - 必须包含月末流动性溢价(+5bps)

3. **失败标准执行**
   - 在代码开头写死失败标准
   - 实现自动检测函数
   - 达到失败标准时停止优化并记录

### Git Commit规范

所有研究commit必须包含：
```
<type>: <subject>

<body>

Walk-Forward: [Train/Val/Test dates]
Cost Scenario: [Optimistic/Baseline/Conservative]
Failure Criteria: [Met/Not Met - details]

Results Summary:
- OOS Sharpe: X.XX
- Max Drawdown: XX%
- Cost Breakeven: XX bps
```

---

## 🎓 学到的教训

1. **数据第一**: 在做任何策略优化前，必须先验证数据质量
2. **失败比成功重要**: 找出策略失败的方式比找到"有效"参数更有价值
3. **成本会杀死策略**: 很多在理论上有效的策略在考虑真实成本后无法盈利
4. **测试集是神圣的**: 一旦查看测试集结果，就不能再用它来调参

---

## 📞 下一步选择

**你现在可以：**

**选项A: 修复数据时间范围** (推荐先做)
```bash
# 更新起始日期到2006-02-03
# 重新下载和清洗数据
# 重新验证数据质量
```

**选项B: 开始实验3 (Carry验证)**
```bash
# 实现carry信号计算
# 测试与未来收益的相关性
# 快速判断carry是否值得使用
```

**选项C: 开始实验5 (成本分析)**
```bash
# 实现交易成本模型
# 计算不同成本假设下的表现
# 确定策略的成本容忍度
```

**你想从哪个开始？**
