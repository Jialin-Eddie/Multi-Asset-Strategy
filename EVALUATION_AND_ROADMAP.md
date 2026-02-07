# Multi-Asset Strategy: 深度评估与发展路线图

**评估日期**: 2026-02-07
**评估范围**: 代码质量、策略表现、研究方法论、架构成熟度、发展潜力

---

## 第一部分: 项目现状评估

### 1.1 总体评分

| 维度 | 评分 (1-10) | 说明 |
|------|:-----------:|------|
| **研究方法论** | 9/10 | Walk-forward + 成本敏感性 + 失败标准，接近机构级 |
| **数据管道** | 8/10 | 完整的下载-清洗-验证流程，inception date 检查到位 |
| **信号生成** | 6/10 | 5种趋势信号可用，但carry失败，缺乏非动量类信号 |
| **回测引擎** | 7/10 | 功能完整但偏简单，缺少滑点模型和事件驱动细节 |
| **组合优化** | 4/10 | 仅有inverse vol近似，ERC是占位符，缺真正的优化器 |
| **风险管理** | 3/10 | 无止损、无回撤控制、无波动率动态调仓 |
| **测试覆盖** | 5/10 | 信号模块覆盖好，portfolio/app/backtest 无测试 |
| **仪表盘** | 7/10 | Flask 8页应用，数据加载+可视化+缓存 |
| **文档质量** | 9/10 | RESEARCH_PROTOCOL.md 是教科书级别 |
| **生产就绪度** | 4/10 | 无 CI/CD、无实盘接口、无监控告警 |

**综合评级: B+ (有扎实基础，但距离机构级量化策略仍有显著差距)**

---

### 1.2 策略表现诊断

#### 核心绩效指标

```
策略: EMA 126d Equal-Weight Monthly Rebalance (5bps cost)

                    最终策略    Buy & Hold    改善幅度
──────────────────────────────────────────────────────
年化收益              9.76%       6.59%       +48%
年化波动率           11.92%      11.59%       +2.8%
Sharpe Ratio         0.82        0.57        +44%
Sortino Ratio        1.03        0.72        +43%
最大回撤            -23.89%     -36.20%      +34%
Calmar Ratio         0.41        0.18        +128%
胜率                53.59%      54.72%       -2.1%
平均持仓资产数       3.12        5.00        -37.6%
```

#### 诊断结论

**优势:**
- Sharpe 0.82 超过通用失败阈值 (0.5)，处于可用区间
- 最大回撤 -23.89% 刚好在 25% 阈值内 (边缘通过)
- Calmar Ratio 显著优于被动策略 (0.41 vs 0.18)
- 波动率与基准相当，但收益更高 — 说明信号有选择能力

**隐患:**
- **回撤接近失败线**: -23.89% vs -25% 阈值，仅 1.1% 余量，任何参数漂移都可能突破
- **Sharpe 低于 1.0**: 机构级策略通常要求 Sharpe > 1.0 才考虑配置
- **胜率略低于被动**: 53.59% vs 54.72%，说明信号过滤掉了一些正收益交易
- **Risk Parity 未带来改善**: Equal Weight Sharpe 0.71 vs Risk Parity 0.72，几乎无差异 — 说明当前 inverse vol 方法过于粗糙
- **Carry 信号失败** (IC = -0.031): 原计划的多信号融合路径受阻

#### 信号有效性排名

```
排名  信号类型              Sharpe   MaxDD     评价
─────────────────────────────────────────────────────
1     EMA 252d             0.730   -23.19%   基准线，表现稳定
2     Relative Mom (top3)  0.728   -26.30%   Sharpe相近但回撤更大
3     SMA 252d             0.708   -23.19%   经典方法，略逊EMA
4     Absolute Mom          0.651   -26.30%   选择性不够强
5     Dual Mom (top2)      0.584   -39.47%   集中度过高，回撤危险
6     Buy & Hold           0.568   -36.20%   被动基准
```

所有信号都是**动量/趋势**类 — 存在严重的同质化风险。当动量因子整体失效 (如 2009 年 3 月反转) 时，没有任何对冲。

---

### 1.3 架构评估

#### 已实现模块 (可用)

| 模块 | 文件 | 代码行数 | 质量 | 备注 |
|------|------|----------|------|------|
| 数据下载 | `src/data/downloader.py` | ~200 | 良好 | Yahoo + Stooq 双源 |
| 数据清洗 | `src/data/loader.py` | ~64 | 良好 | ffill/bfill + 缺失过滤 |
| 数据验证 | `src/data/validator.py` | ~362 | 优秀 | inception检查 + anomaly检测 |
| 趋势信号 | `src/signals/trend_filter.py` | ~351 | 良好 | 5种方法，接口统一 |
| Carry信号 | `src/signals/carry.py` | ~460 | 中等 | FRED集成但实际数据不足 |
| 回测引擎 | `src/backtest/engine.py` | ~483 | 良好 | 成本+换手+regime分析 |
| 风险平价 | `src/portfolio/risk_parity.py` | ~276 | 中等 | ERC是近似值 |
| 实验框架 | `src/diagnostics/` | ~1文件 | 中等 | 仅Exp3实现 |
| Flask仪表盘 | `app/` | ~800+ | 良好 | 8 blueprints, 服务层分离 |

#### 缺失模块 (10个实验中仅完成1个)

```
计划实验矩阵:
  ✅ Exp 3: Carry信号验证 — 已完成 (FAILED)
  ❌ Exp 1: 协方差估计稳定性 (P0) — 未实现
  ❌ Exp 2: 波动率预测精度 (P0) — 未实现
  ❌ Exp 4: Momentum崩盘风险 (P1) — 未实现
  ❌ Exp 5: 交易成本影响 (P0) — 未实现
  ❌ Exp 6: 策略拥挤度 (P1) — 未实现
  ❌ Exp 7: 参数稳定性 (P0) — 未实现
  ❌ Exp 8: Regime非平稳性 (P1) — 未实现
  ❌ Exp 9: 杠杆约束 (P2) — 未实现
  ❌ Exp 10: 样本外泛化 (P2) — 未实现
```

#### 代码质量观察

**正面:**
- 一致使用 `pathlib.Path` 进行路径处理
- 函数签名清晰，参数有默认值
- `if __name__ == "__main__"` 模式统一
- 错误处理在数据层比较完善

**需改进:**
- `risk_parity.py` 中 ERC 注释为 "placeholder"，使用 inverse vol 代替 — 需明确标注或实现真正的优化
- `engine.py` 的 regime 分类用简单百分比阈值 (±20%)，缺乏统计基础
- 无 type hints (PEP 484) — 对量化代码尤其重要
- 无 logging 模块 — 全部用 print()

---

## 第二部分: 核心问题与风险

### 2.1 策略层面的根本性问题

#### 问题 1: 信号同质化 (Critical)

所有5个信号都是**价格动量**的变体 (SMA/EMA/Absolute/Relative/Dual)。这意味着:

- **相关性极高**: 当动量因子失效时，所有信号同时失败
- **无对冲机制**: 2009年3月、2020年3月的V型反转中，所有趋势信号都会被反向截断
- **Alpha来源单一**: 整个策略本质上是 "trend following on multi-asset ETFs"

**根本原因**: Carry信号 (唯一的非动量信号) 已验证失败，项目目前没有替代的非动量 alpha 来源。

#### 问题 2: 最大回撤边缘通过 (High)

-23.89% 的最大回撤距离 -25% 的失败阈值仅有 1.11% 余量。这意味着:

- 参数微调 (如 lookback 从 126 变为 130) 可能导致回撤突破阈值
- 未来市场波动加大 (如 2022 年式通胀冲击 + 加息) 可能突破
- 当前策略**没有回撤控制层** — 纯信号驱动，无熔断机制

#### 问题 3: 组合优化形同虚设 (High)

Risk Parity (Sharpe 0.72) vs Equal Weight (Sharpe 0.71) 差异 < 0.01:

- 说明 inverse vol 近似法不是真正的风险平价
- Equal Risk Contribution 需要迭代优化器 (目前是占位符)
- 真正的 HRP 或 Black-Litterman 可能产生显著差异
- **结论**: 当前"风险平价"模块实际没有贡献 alpha

#### 问题 4: 未完成的实验矩阵 (Medium)

10个计划实验仅完成1个。P0优先级的实验 (协方差稳定性、波动率预测、交易成本、参数稳定性) 全部未做:

- 无法确认策略在不同成本假设下是否仍然可行
- 参数稳定性未验证 — 126天EMA可能只是在此数据集上恰好最优
- 缺乏 walk-forward 滚动验证

### 2.2 技术层面的问题

| 问题 | 严重度 | 说明 |
|------|--------|------|
| 无 CI/CD | Medium | 代码修改无自动测试保障 |
| portfolio/app 无测试 | Medium | 核心组合逻辑零覆盖 |
| 无 type hints | Low | 量化代码应有严格类型 |
| 全部 print() 无 logging | Low | 无法控制日志级别 |
| Flask 无认证 | Low | 仪表盘公开可访问 |
| 无数据版本控制 | Medium | CSV文件变更无追踪 |

---

## 第三部分: 发展路线图

### 阶段 0: 补齐基础 (Foundation)

> 目标: 完成P0实验，确认策略生存能力

#### 0.1 完成剩余 P0 实验

**Exp 5: 交易成本影响分析** (最高优先级)

当前策略仅在 5bps 下测试。必须验证:
- 12bps (baseline) 下 Sharpe 是否仍 > 0.5
- 25bps (conservative) 下策略是否仍能盈利
- 盈亏平衡成本是多少
- 实现动态成本模型 (波动率调整 spread)

```python
# 关键实现
src/diagnostics/experiment_05_transaction_costs.py
  - 三档成本场景 (5/12/25 bps)
  - 动态成本: spread = base * (current_vol / normal_vol)
  - 月末流动性溢价 (+5bps)
  - 输出: 成本敏感性表格 + 盈亏平衡成本
```

**Exp 7: 参数稳定性 (Walk-Forward 滚动验证)**

验证 EMA 126d 是否是 robust 的选择:
- Anchored walk-forward: Train 逐步扩大，观察最优参数是否漂移
- Rolling walk-forward: 固定窗口，观察参数随时间变化
- 检查标准: 最优参数变化 > 50% → 失败

```python
# 关键实现
src/diagnostics/experiment_07_parameter_stability.py
  - 5个walk-forward窗口
  - 每个窗口独立优化 EMA span
  - 输出: 最优参数时间序列 + 稳定性指标
```

**Exp 1: 协方差估计稳定性**

为后续真正的风险平价做准备:
- 测试 rolling covariance 的条件数
- 比较: 简单 rolling vs 指数加权 vs Ledoit-Wolf shrinkage vs RMT
- 确定哪种方法最稳定

**Exp 2: 波动率预测精度**

为 volatility targeting 做准备:
- 比较: Rolling std vs EWMA vs GARCH(1,1) vs Realized Vol
- 评价指标: QLIKE, MSE, 预测方向准确率
- 选择最优波动率估计器

#### 0.2 回撤控制层 (Risk Overlay)

当前策略无任何下行保护。需实现:

```python
# src/risk/overlay.py

class RiskOverlay:
    """独立于信号的风险管理层"""

    def drawdown_control(self, portfolio_value, peak_value, threshold=-0.15):
        """当回撤达到 threshold 时，削减仓位 50%"""
        drawdown = (portfolio_value - peak_value) / peak_value
        if drawdown < threshold:
            return 0.5  # 保留50%仓位
        return 1.0

    def volatility_scaling(self, current_vol, target_vol=0.10, max_leverage=1.5):
        """根据当前波动率缩放总仓位"""
        scale = target_vol / current_vol
        return min(scale, max_leverage)

    def correlation_filter(self, correlation_matrix, threshold=0.85):
        """当资产相关性急剧上升时发出警告"""
        # 危机时期相关性趋1，分散化失效
        avg_corr = correlation_matrix.values[np.triu_indices_from(
            correlation_matrix, k=1)].mean()
        return avg_corr < threshold
```

---

### 阶段 1: 信号多元化 (Signal Diversification)

> 目标: 打破动量单一依赖，引入正交信号

#### 1.1 宏观 Regime 信号

最重要的非动量信号来源:

```python
# src/signals/regime.py

class RegimeSignal:
    """基于宏观指标的 regime 检测"""

    def vix_regime(self, vix_data, thresholds=(15, 25)):
        """低波/正常/高波 三状态"""

    def yield_curve_regime(self, us10y, us2y):
        """正常/平坦/倒挂 — 衰退领先指标"""

    def cross_asset_momentum_regime(self, asset_returns):
        """多资产同向下跌 = risk-off"""

    def composite_regime(self):
        """融合多个 regime 信号"""
```

**为什么重要**: 在 risk-off regime 中，trend following 信号应该更保守 (降低仓位)，而非盲目跟随信号。2020-03 的 V 型反转就是典型案例 — 趋势信号在底部发出做空信号，但市场随即暴力反弹。

#### 1.2 波动率信号

与动量低相关的独立 alpha 来源:

```python
# src/signals/volatility.py

class VolatilitySignal:
    """基于波动率结构的信号"""

    def vol_term_structure(self, short_vol, long_vol):
        """短期 vol > 长期 vol → contango → 看跌"""

    def vol_of_vol(self, realized_vol_series):
        """波动率的波动率上升 → 不确定性加剧 → 减仓"""

    def vol_risk_premium(self, implied_vol, realized_vol):
        """VRP = IV - RV, 高 VRP → 市场定价恐惧 → 可能反转"""
```

#### 1.3 价值/均值回归信号

作为动量的天然对冲:

```python
# src/signals/mean_reversion.py

class MeanReversionSignal:
    """在短期内与动量方向相反的信号"""

    def relative_value(self, prices, lookback=21):
        """短期 (1个月) Z-score: 偏离均值越大，回归概率越高"""

    def rsi_signal(self, prices, period=14):
        """RSI > 70 超买 → 减仓; RSI < 30 超卖 → 加仓"""
```

**关键设计**: 动量信号 (中长期) + 均值回归信号 (短期) 的组合通常能提升 Sharpe 0.1-0.3，因为两者在不同时间尺度上互补。

#### 1.4 信号融合框架

```python
# src/signals/composite.py

class SignalComposite:
    """多信号融合 — 核心是确保信号间低相关"""

    def equal_weight_blend(self, signals: dict):
        """等权融合 — 最 robust 的方法"""

    def inverse_correlation_blend(self, signals: dict, lookback=252):
        """相关性越低的信号权重越高"""

    def regime_conditional_blend(self, signals: dict, regime: str):
        """不同 regime 下使用不同的信号组合"""
        # risk-off: 降低动量权重，提高 regime 信号权重
        # risk-on: 动量为主
```

---

### 阶段 2: 组合优化升级 (Portfolio Construction)

> 目标: 从 equal-weight 升级到真正的风险预算

#### 2.1 真正的 Equal Risk Contribution

替换当前的 inverse vol 占位符:

```python
# src/portfolio/erc.py
import scipy.optimize as sco

def equal_risk_contribution(cov_matrix, budget=None):
    """
    真正的 ERC 优化 — 每个资产贡献相同的组合风险
    使用 scipy.minimize 求解非线性约束优化
    """
    n = cov_matrix.shape[0]
    if budget is None:
        budget = np.ones(n) / n

    def risk_contribution_error(weights):
        port_vol = np.sqrt(weights @ cov_matrix @ weights)
        marginal_risk = cov_matrix @ weights
        risk_contrib = weights * marginal_risk / port_vol
        target_contrib = budget * port_vol
        return np.sum((risk_contrib - target_contrib) ** 2)

    constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]
    bounds = [(0.01, 0.40)] * n  # 遵守 max_weight: 40% 约束
    result = sco.minimize(risk_contribution_error,
                          x0=np.ones(n)/n,
                          method='SLSQP',
                          bounds=bounds,
                          constraints=constraints)
    return result.x
```

#### 2.2 Hierarchical Risk Parity (HRP)

利用项目已有的 `riskfolio-lib` 依赖:

```python
import riskfolio as rp

def hierarchical_risk_parity(returns):
    """
    HRP 不需要协方差矩阵求逆 — 对条件数不敏感
    特别适合小样本 (5 assets) 场景
    """
    port = rp.Portfolio(returns=returns)
    port.assets_stats(method_mu='hist', method_cov='hist')
    weights = port.optimization(model='HRP',
                                codependence='pearson',
                                rm='MV',
                                leaf_order=True)
    return weights
```

#### 2.3 Black-Litterman 融合

将信号转化为 "views"，与市场均衡结合:

```python
def black_litterman_weights(market_caps, cov_matrix, signal_views, confidence):
    """
    信号 → 观点 → BL后验 → 最优权重
    好处: 即使信号很弱 (低confidence), 也不会偏离均衡太远
    """
```

---

### 阶段 3: 强化学习动态配置 (RL Allocation)

> 目标: 利用已安装的 stable-baselines3 构建自适应配置代理

#### 3.1 环境设计

```python
# src/rl/trading_env.py
import gymnasium as gym

class MultiAssetTradingEnv(gym.Env):
    """
    State:  [价格特征, 信号特征, 组合特征, 市场regime]
    Action: [5个资产的目标权重] (连续空间)
    Reward: risk-adjusted return - transaction cost
    """

    def __init__(self, prices, signals, cost_bps=12):
        self.observation_space = gym.spaces.Box(
            low=-np.inf, high=np.inf, shape=(25,))  # 5 assets * 5 features
        self.action_space = gym.spaces.Box(
            low=0, high=0.4, shape=(5,))  # long-only, max 40%

    def step(self, action):
        weights = action / action.sum()  # 归一化
        ret = (weights * self.next_returns).sum()
        cost = self.calculate_turnover_cost(weights)
        reward = ret - cost
        # Sharpe-like reward shaping
        ...
```

#### 3.2 训练策略

```python
from stable_baselines3 import PPO

# 关键: 只在 Train window 训练，Val window 做 early stopping
model = PPO("MlpPolicy", env,
            learning_rate=3e-4,
            n_steps=2048,
            batch_size=64,
            n_epochs=10,
            gamma=0.99)

model.learn(total_timesteps=500_000)
```

**RL 的风险:**
- 过拟合风险极高 — 必须严格 walk-forward
- 样本效率低 — 19年日频数据约4900条，对 RL 来说偏少
- 建议: 先用 RL 做 "position sizing overlay"，而非完全替代规则信号
- 混合方法: 规则信号决定方向 → RL 决定仓位大小

---

### 阶段 4: 生产化 (Production Readiness)

> 目标: 从研究项目转变为可部署的系统

#### 4.1 CI/CD Pipeline

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: conda-incubator/setup-miniconda@v3
      - run: conda env create -f environment.yml
      - run: conda activate multi_as_env && pytest tests/ -v --cov=src
      - run: mypy src/ --ignore-missing-imports
```

#### 4.2 实盘对接层

```python
# src/execution/paper_trade.py

class PaperTrader:
    """纸上交易 — 每月生成目标权重，与实际执行分离"""

    def generate_monthly_orders(self):
        """
        每月第一个交易日:
        1. 下载最新价格
        2. 计算信号
        3. 计算目标权重
        4. 生成 rebalance orders
        5. 邮件/Slack 通知
        """

    def track_paper_performance(self):
        """记录纸上交易表现，与回测比较"""
```

#### 4.3 监控告警

```python
# src/monitoring/alerts.py

class StrategyMonitor:
    """实时策略健康监控"""

    def check_drawdown(self, threshold=-0.15):
        """回撤超阈值时告警"""

    def check_signal_divergence(self, backtest_signal, live_signal):
        """实盘信号与回测信号不一致时告警"""

    def check_vol_spike(self, current_vol, threshold_multiplier=2.0):
        """波动率突增时告警"""

    def daily_health_report(self):
        """每日策略健康报告"""
```

---

## 第四部分: 优先级排序与依赖关系

### 推荐执行顺序

```
                    [当前位置: EMA 126d Equal-Weight]
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
           [阶段 0: 补齐基础]      [测试补全]
           Exp 5: 成本分析         portfolio tests
           Exp 7: 参数稳定性       backtest tests
           Risk overlay 层         type hints
                    │
                    ▼
           [阶段 1: 信号多元化]
           Regime 信号
           Vol 信号
           信号融合框架
                    │
                    ▼
           [阶段 2: 组合优化]
           真正的 ERC
           HRP (via riskfolio-lib)
           Vol targeting
                    │
                    ▼
           [阶段 3: RL 动态配置]
           Trading Env
           PPO 训练
           混合策略
                    │
                    ▼
           [阶段 4: 生产化]
           CI/CD
           Paper trading
           监控告警
```

### 预期收益估算

| 改进项 | 预期 Sharpe 提升 | 预期 MaxDD 改善 | 信心水平 |
|--------|:-----------------:|:----------------:|:--------:|
| Risk overlay (回撤控制+vol scaling) | +0.05~0.10 | 3~5% | 高 |
| Regime 信号融合 | +0.10~0.20 | 2~4% | 中高 |
| 真正的 ERC/HRP 优化 | +0.05~0.10 | 1~3% | 中 |
| Vol + 均值回归信号 | +0.05~0.15 | 1~2% | 中 |
| RL position sizing | +0.00~0.15 | 0~3% | 低 |
| **组合效应** | **+0.15~0.40** | **5~12%** | **中** |

保守估计: 完成阶段 0-2 后，Sharpe 从 0.82 → 1.0~1.1，MaxDD 从 -23.9% → -18%~-20%。

---

## 第五部分: 总结

### 项目的核心优势

1. **方法论纪律性**: RESEARCH_PROTOCOL.md 定义的 walk-forward + 成本敏感性 + 失败标准是该项目最大的资产。绝大多数个人量化项目缺乏这种纪律。
2. **诚实的失败报告**: Experiment 3 (Carry) 的失败被完整记录而非隐藏，说明项目遵循科学方法而非结果导向。
3. **完整的端到端流程**: 从数据下载到仪表盘可视化，pipeline 已贯通。

### 项目的核心风险

1. **单因子依赖**: 所有 alpha 来自价格动量一个来源。这是最大的系统性风险。
2. **回撤余量不足**: 距离失败阈值仅 1.1%，缺乏安全边际。
3. **实验完成度低**: 10个计划实验仅完成1个，许多关键假设未验证。

### 最关键的下一步

**如果只做一件事**: 实现 Risk Overlay 层 (回撤控制 + 波动率缩放)。这是投入产出比最高的改进 — 不需要新信号、不需要新优化器，只需要在现有策略上加一层风险管理。

**如果做三件事**:
1. Risk Overlay
2. Regime 信号 (VIX + yield curve) 融合
3. 完成 Exp 5 (交易成本) 和 Exp 7 (参数稳定性)

这三项完成后，策略会从 "可用但脆弱" 变为 "可靠且有安全边际"。
