# Research Protocol: Multi-Asset Strategy Development

**版本**: 1.0
**日期**: 2024-12-20
**目的**: 建立严格的研究方法论，防止过拟合、数据窥探和不可复现的结果

---

## 核心原则 (The Three Reins)

所有策略开发和实验必须遵守以下三条铁律，**无例外**：

### 🔒 原则 1: 强制 Walk-Forward 验证

**要求**:
- 任何参数选择必须基于**训练集+验证集**，测试集只能看一次
- 测试集表现作为最终报告，不得用于调参
- 明确记录每个时间窗口的用途

**实施标准**:

```
时间轴划分 (以2006-2024数据为例):

Training Window (样本内优化):
  • 2006-01 至 2015-12 (10年)
  • 用途: 参数优化、信号测试、模型训练

Validation Window (样本外调优):
  • 2016-01 至 2019-12 (4年)
  • 用途: 参数选择、模型选择、策略组合
  • 允许: 在多个候选参数中选择最优
  • 禁止: 基于验证集结果修改训练逻辑

Test Window (严格样本外):
  • 2020-01 至 2024-12 (5年)
  • 用途: 最终性能报告
  • 规则: 只能运行一次，结果不得用于任何调整

⚠️ "只看一次"规则:
  • 测试集结果首次生成后立即记录时间戳
  • 任何后续测试集运行必须注明原因并保留历史记录
  • 如果测试集被"污染"(多次查看并调参)，必须获取新的测试数据
```

**Walk-Forward 滚动验证** (用于参数稳定性测试):

```
Anchored Walk-Forward (锚定起点):
  Train: 2006-2010 → Validate: 2011 → Test: 2012
  Train: 2006-2012 → Validate: 2013 → Test: 2014
  Train: 2006-2014 → Validate: 2015 → Test: 2016
  ...

Rolling Walk-Forward (滚动窗口):
  Train: 2006-2010 → Validate: 2011 → Test: 2012
  Train: 2008-2012 → Validate: 2013 → Test: 2014
  Train: 2010-2014 → Validate: 2015 → Test: 2016
  ...
```

**文档要求**:
每个实验必须在代码注释中明确声明：
```python
# WALK-FORWARD DECLARATION
# Training:   2006-01-01 to 2015-12-31
# Validation: 2016-01-01 to 2019-12-31
# Test:       2020-01-01 to 2024-12-31
# Test Set First Run: [timestamp to be filled on first execution]
```

**违规示例** (严禁):
- ❌ "测试集Sharpe不理想，我调整lookback从6M到9M再跑一次"
- ❌ "2020年表现差，我把测试集改成2021-2024"
- ❌ "在全样本上优化参数，然后说这是样本外测试"

---

### 💰 原则 2: 强制成本敏感性分析

**要求**:
- 所有策略必须在**至少3档成本假设**下测试
- 交易成本必须包含**动态成分** (随市场状态变化)
- 必须计算并报告**盈亏平衡成本**

**成本模型定义**:

```python
# 三档成本场景 (单位: bps, 1bps = 0.01%)

Scenario 1: 乐观 (Optimistic) - 小规模/高流动性时期
  • Base spread:        3 bps
  • Market impact:      0 bps (假设规模很小)
  • Month-end premium:  0 bps
  • Total:              3-5 bps

Scenario 2: 基准 (Baseline) - 正常市场条件
  • Base spread:        8 bps
  • Market impact:      2-5 bps (取决于成交量)
  • Month-end premium:  3 bps
  • Total:              10-15 bps

Scenario 3: 保守 (Conservative) - 压力/早期时期
  • Base spread:        15 bps (2006-2010 DBC/VNQ spread很大)
  • Market impact:      5-10 bps
  • Month-end premium:  5 bps
  • Crisis surcharge:   +10 bps (VIX > 30时)
  • Total:              20-35 bps
```

**动态成本组件** (必须实现至少一个):

1. **波动率调整** (优先):
```python
def dynamic_spread(base_spread_bps, current_vol, normal_vol=0.15):
    """Spread在高波动时扩大"""
    vol_multiplier = current_vol / normal_vol
    return base_spread_bps * vol_multiplier
```

2. **成交量调整**:
```python
def market_impact(trade_size, avg_daily_volume, volatility):
    """Square-root market impact model"""
    participation_rate = trade_size / avg_daily_volume
    impact_bps = 10 * np.sqrt(participation_rate) * (volatility / 0.15)
    return impact_bps
```

3. **时间调整**:
```python
def month_end_premium(trade_date):
    """月末最后5天流动性溢价"""
    if trade_date.day >= 25:
        return 5  # bps
    return 0
```

**报告要求**:

每个实验必须生成成本敏感性表格:

```
Cost Sensitivity Analysis
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Scenario      Cost(bps)  Ann.Cost%  Sharpe  MaxDD   ROI%
────────────────────────────────────────────────────────
Optimistic        5       0.6%      1.15   -12%    8.5%
Baseline         12       1.4%      0.85   -14%    6.2%
Conservative     25       3.0%      0.35   -16%    2.1%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Break-even Cost: 18 bps
  → 策略在成本超过18bps时无法盈利
  → 如果realistic成本>18bps，策略不可行
```

**失败标准**:
- ❌ 如果基准成本下Sharpe < 0.5 → 策略失败
- ❌ 如果盈亏平衡成本 < 15bps → 策略过于脆弱
- ❌ 如果乐观vs保守Sharpe差异>100% → 对成本过度敏感

---

### ⛔ 原则 3: 必须明确定义失败标准

**要求**:
- 在运行实验**之前**写下失败标准
- 失败标准必须是**可量化**的阈值
- 达到失败标准时，停止优化并记录失败原因

**通用失败标准** (适用所有策略):

```yaml
Performance Failures:
  - OOS Sharpe Ratio < 0.5
  - OOS Sharpe / IS Sharpe < 0.7  (样本外衰减>30%)
  - Max Drawdown > 25%
  - Worst monthly return < -15%
  - Negative returns in >40% of months

Concentration Failures:
  - 超过50%收益来自单一年份
  - 超过50%收益来自单一资产
  - 超过70%收益来自top 3个月
  - 单一资产权重在>30%时间超过60%

Robustness Failures:
  - 参数变化±20%导致Sharpe变化>50%
  - 测试集任意连续3年Sharpe < 0
  - 策略在3个以上regime中失效(Sharpe<0.3)
  - Walk-forward测试中>40%窗口OOS为负收益

Cost/Turnover Failures:
  - 月均Turnover > 100%
  - 盈亏平衡成本 < 15bps
  - 基准成本(12bps)下净收益 < 3%/年

Data Quality Failures:
  - 任何资产缺失率 > 5%
  - 协方差矩阵条件数 > 100 在超过30%时间
  - 波动率预测误差 > 50% 在超过10%时间
```

**实验特定失败标准** (示例):

```python
# Experiment 1: 协方差估计
FAILURE_CRITERIA = {
    'max_condition_number_pct': 0.30,  # 30%时间病态
    'max_weight_uncertainty': 0.10,    # 权重标准差>10%
    'max_correlation_error': 0.30      # 相关性误差>0.3
}

# Experiment 3: Carry信号
FAILURE_CRITERIA = {
    'min_signal_correlation': 0.15,    # IC < 0.15
    'min_sharpe_ratio': 0.5,           # Carry策略Sharpe < 0.5
    'max_negative_carry_pct': 0.40     # >40%资产负carry
}

# Experiment 4: Momentum crash
FAILURE_CRITERIA = {
    'max_single_month_loss': -0.20,    # 单月亏损>-20%
    'min_high_vol_sharpe': 0.0,        # VIX>30时Sharpe<0
    'max_left_skewness': -1.0          # 左偏度<-1
}
```

**实施流程**:

1. **实验前**：在实验文件顶部声明失败标准
```python
# FAILURE CRITERIA (defined before running experiment)
FAIL_IF = {
    'oos_sharpe': {'operator': '<', 'threshold': 0.5},
    'max_drawdown': {'operator': '>', 'threshold': 0.25},
    'turnover': {'operator': '>', 'threshold': 1.0}  # 100%/月
}
```

2. **实验后**：自动检查失败标准
```python
def check_failure_criteria(results: dict, criteria: dict) -> dict:
    failures = {}
    for metric, rule in criteria.items():
        actual = results[metric]
        threshold = rule['threshold']
        op = rule['operator']

        if op == '<' and actual < threshold:
            failures[metric] = f"FAIL: {actual:.3f} < {threshold}"
        elif op == '>' and actual > threshold:
            failures[metric] = f"FAIL: {actual:.3f} > {threshold}"

    return failures
```

3. **失败处理**：
```python
if failures:
    print("❌ EXPERIMENT FAILED - Criteria not met:")
    for metric, msg in failures.items():
        print(f"   {metric}: {msg}")

    # 记录失败并停止优化
    log_failure(experiment_id, failures, timestamp)
    raise ExperimentFailure("Strategy does not meet minimum viability criteria")
```

---

## 实施检查清单

在运行任何实验前，确认以下所有项目：

### ✅ Walk-Forward 检查
- [ ] 训练/验证/测试窗口已明确定义
- [ ] 参数优化只使用训练+验证集
- [ ] 测试集代码路径有时间戳记录机制
- [ ] Walk-forward窗口定义清晰(anchored或rolling)
- [ ] 所有时间切分点有注释说明选择理由

### ✅ 成本敏感性检查
- [ ] 定义了至少3档成本场景(乐观/基准/保守)
- [ ] 实现了至少1个动态成本组件(波动率或成交量)
- [ ] 计算并报告盈亏平衡成本
- [ ] 生成成本敏感性表格(Sharpe vs Cost)
- [ ] 历史不同时期使用不同spread假设(2006 vs 2020)

### ✅ 失败标准检查
- [ ] 失败标准在实验运行前定义(写在代码开头)
- [ ] 所有阈值都是可量化的数字
- [ ] 实现了自动失败检测函数
- [ ] 达到失败标准时有明确的停止机制
- [ ] 失败结果会被记录(不能隐瞒)

---

## 文档和版本控制要求

### Git Commit 规范

所有研究相关的commit必须包含：

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

**Type标签**:
- `experiment:` 新实验或实验修改
- `data:` 数据下载、清洗、验证
- `fix:` Bug修复
- `docs:` 文档更新
- `refactor:` 代码重构(不改变逻辑)

**示例**:
```
experiment: Add momentum crash detection (Exp 4)

Implemented regime-conditional momentum testing with VIX thresholds.
Tested momentum performance across low/med/high volatility regimes.

Walk-Forward: Train 2006-2015, Val 2016-2019, Test 2020-2024
Cost Scenario: Baseline (12bps)
Failure Criteria: Met - High vol Sharpe = -0.15 (threshold: 0.0)

Results Summary:
- OOS Sharpe: 0.42 (FAIL: < 0.5)
- Max Drawdown: -28% (FAIL: > 25%)
- VIX>30 Sharpe: -0.15 (FAIL: < 0.0)

Conclusion: Momentum strategy fails in high volatility regimes.
Recommendation: Add volatility filter or regime switching.
```

### 实验日志

每个实验运行后，自动生成日志文件：

```
outputs/experiments/exp_04_momentum_crash_20241220_143022.json
{
  "experiment_id": "04",
  "timestamp": "2024-12-20T14:30:22",
  "walk_forward": {
    "train": "2006-01-01 to 2015-12-31",
    "validation": "2016-01-01 to 2019-12-31",
    "test": "2020-01-01 to 2024-12-31",
    "test_first_run": "2024-12-20T14:30:22"
  },
  "cost_scenario": "baseline",
  "failure_criteria": {
    "oos_sharpe": {"threshold": 0.5, "actual": 0.42, "status": "FAIL"},
    "max_drawdown": {"threshold": 0.25, "actual": 0.28, "status": "FAIL"}
  },
  "results": {
    "sharpe_ratio": 0.42,
    "max_drawdown": -0.28,
    "total_return": 0.34,
    ...
  }
}
```

---

## 常见陷阱和审查要点

### 🚨 Walk-Forward 陷阱

| 陷阱 | 示例 | 如何避免 |
|------|------|----------|
| 隐性数据泄露 | 用全样本计算Z-score归一化 | 归一化参数只用训练集 |
| 前视偏差 | `df.ffill()`在整个数据集上操作 | 按时间顺序逐步填充 |
| 幸存者偏差 | 只测试当前存在的ETF | 检查历史上市日期 |
| 参数窥探 | "试了10组参数，选最好的报告" | 记录所有尝试，或用验证集选择 |

### 🚨 成本陷阱

| 陷阱 | 示例 | 如何避免 |
|------|------|----------|
| 静态成本假设 | 所有时期用5bps | 2006年和2024年成本差异巨大 |
| 忽略冲击成本 | 只算spread | 大额交易有market impact |
| 忽略时机成本 | 假设随时能以收盘价成交 | 月末流动性枯竭，spread扩大 |
| 乐观偏差 | 只测试最低成本 | 必须测试保守成本 |

### 🚨 失败标准陷阱

| 陷阱 | 示例 | 如何避免 |
|------|------|----------|
| 事后调整标准 | "Sharpe 0.48也不错，改成>0.45" | 标准写死在实验代码开头 |
| 选择性报告 | 只展示通过测试的结果 | 失败实验也必须记录 |
| 模糊标准 | "策略应该表现不错" | 用数字: "Sharpe > 0.5" |
| 忽略集中度 | 只看Sharpe不看收益分布 | 加入集中度失败标准 |

---

## 附录: 快速参考

### 最小可行测试 (MVT) 模板

```python
"""
Experiment X: [Name]

WALK-FORWARD DECLARATION:
  Training:   2006-01-01 to 2015-12-31
  Validation: 2016-01-01 to 2019-12-31
  Test:       2020-01-01 to 2024-12-31
  Test Set First Run: [AUTO-FILLED]

COST SCENARIOS:
  Optimistic:  5 bps
  Baseline:    12 bps
  Conservative: 25 bps
  Dynamic Component: Volatility-adjusted spread

FAILURE CRITERIA:
  - OOS Sharpe < 0.5
  - Max Drawdown > 25%
  - Cost Break-even < 15bps
  - [Experiment-specific criteria]
"""

def run_experiment_X():
    # 1. Load data (验证质量)
    data = load_validated_data()

    # 2. 时间切分
    train, val, test = split_walk_forward(data, TRAIN_END, VAL_END)

    # 3. 在训练集优化
    optimal_params = optimize_on_train(train)

    # 4. 在验证集选择
    final_params = select_on_validation(val, optimal_params)

    # 5. 在测试集运行一次 (带时间戳)
    test_results = run_test_once(test, final_params)

    # 6. 成本敏感性
    for cost_scenario in ['optimistic', 'baseline', 'conservative']:
        results[cost_scenario] = apply_costs(test_results, cost_scenario)

    # 7. 检查失败标准
    failures = check_failure_criteria(results, FAILURE_CRITERIA)

    # 8. 记录和返回
    log_experiment(experiment_id='X', results=results, failures=failures)

    return results, failures
```

---

## 版本历史

- **v1.0** (2024-12-20): 初始版本，建立三大核心原则
  - Walk-forward强制要求
  - 成本敏感性分析标准
  - 失败标准定义规范

---

**签名**: 本协议适用于所有Multi-Asset Strategy项目的研究工作，无例外。
