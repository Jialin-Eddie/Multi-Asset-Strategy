# Multi-Asset Strategy Dashboard - Design Document

## Executive Summary

Comprehensive Flask-based web dashboard for visualizing strategy research, methodology, performance, and results. Provides interactive analytics for the EMA 126-day trend-following strategy.

---

## 1. Architecture Overview

### Technology Stack

**Backend:**
- **Flask** - Lightweight Python web framework
- **Flask-Caching** - Cache expensive calculations
- **Pandas** - Data processing
- **NumPy** - Numerical computations

**Visualization:**
- **Plotly/Dash** - Interactive JavaScript charts (PRIMARY)
  - Pros: Python-native, highly interactive, professional
  - Cons: Larger bundle size
- **Alternative: Chart.js** - Lightweight JavaScript charting
  - Pros: Fast, simple, smaller footprint
  - Cons: Less Python integration

**Frontend:**
- **HTML5/CSS3** - Structure and styling
- **Bootstrap 5** - Responsive design framework
- **JavaScript** - Interactivity and AJAX
- **Jinja2 Templates** - Server-side rendering

**Data Storage:**
- **CSV Files** - Existing backtest results
- **JSON Cache** - Pre-computed metrics
- **SQLite (Optional)** - Future real-time tracking

### Architecture Pattern

```
┌─────────────────────────────────────────────────────────────┐
│                     CLIENT BROWSER                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  HTML/CSS    │  │  JavaScript  │  │  Plotly.js   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                              │
                    HTTP/AJAX Requests
                              │
┌─────────────────────────────────────────────────────────────┐
│                    FLASK WEB SERVER                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Flask Routes (app.py)                               │  │
│  │  - /              → Dashboard home                   │  │
│  │  - /methodology   → Strategy explanation            │  │
│  │  - /performance   → Performance analytics           │  │
│  │  - /comparison    → Strategy comparison             │  │
│  │  - /risk          → Risk analysis                   │  │
│  │  - /signals       → Signal history                  │  │
│  │  - /api/data      → JSON API endpoints              │  │
│  └──────────────────────────────────────────────────────┘  │
│                              │                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Business Logic Layer                                │  │
│  │  - data_loader.py    → Load CSV results             │  │
│  │  - metrics.py        → Calculate statistics         │  │
│  │  - charts.py         → Generate Plotly charts       │  │
│  │  - cache.py          → Caching layer                │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                    File System Access
                              │
┌─────────────────────────────────────────────────────────────┐
│                       DATA LAYER                            │
│  - outputs/*.csv           → Backtest results               │
│  - data/processed/*.csv    → Historical prices              │
│  - cache/*.json            → Pre-computed metrics           │
│  - RESEARCH_JOURNAL.md     → Documentation                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Page Structure & Content

### 2.1 Dashboard Home (`/`)

**Purpose:** High-level overview and key metrics

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  HEADER: Multi-Asset Trend-Following Strategy               │
│  Navigation: [Home] [Methodology] [Performance] [Risk] ...  │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Total Return│  │Sharpe Ratio │  │ Max Drawdown│         │
│  │   592.6%    │  │    0.819    │  │   -23.89%   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
├─────────────────────────────────────────────────────────────┤
│  MAIN CHART: Cumulative Returns (Strategy vs Benchmark)     │
│  [Interactive Plotly line chart with zoom/pan]              │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────────┐  ┌──────────────────────┐        │
│  │ Recent Performance   │  │  Current Holdings    │        │
│  │ Last 30 days: +2.3% │  │  SPY: 33%            │        │
│  │ Last 90 days: +5.1% │  │  GLD: 33%            │        │
│  │ YTD: +12.4%         │  │  TLT: 33%            │        │
│  └──────────────────────┘  └──────────────────────┘        │
├─────────────────────────────────────────────────────────────┤
│  FOOTER: Data as of [date] | Last updated [timestamp]      │
└─────────────────────────────────────────────────────────────┘
```

**Key Metrics Cards:**
- Total Return (592.6%)
- Annualized Return (9.76%)
- Sharpe Ratio (0.819)
- Sortino Ratio (1.030)
- Max Drawdown (-23.89%)
- Calmar Ratio (0.408)
- Win Rate (53.6%)
- Avg Positions (3.1)

**Charts:**
1. **Cumulative Returns Line Chart** (Interactive)
   - Final Strategy (blue line, thick)
   - Buy & Hold Benchmark (red dashed)
   - Initial Strategy EMA 252d (gray line)
   - X-axis: Date (2005-2025)
   - Y-axis: Portfolio Value ($)
   - Hover tooltips with exact values
   - Zoom/pan controls

2. **Recent Performance Sparklines**
   - 30-day mini chart
   - 90-day mini chart
   - YTD mini chart

**Current Holdings Pie Chart:**
- Show current asset allocation
- Color-coded by asset class
- Percentage labels

---

### 2.2 Methodology Page (`/methodology`)

**Purpose:** Explain strategy logic and research process

**Sections:**

1. **Strategy Overview**
   - Visual flowchart of signal generation
   - EMA calculation explanation
   - Position sizing logic
   - Rebalancing rules

2. **Research Timeline**
   - Interactive timeline showing:
     - Data acquisition → Signal testing → Optimization → Final strategy
   - Click to expand each phase

3. **Signal Generation Diagram**
   ```
   Daily Prices → EMA 126d → Compare (Price > EMA?) → Signal (1 or 0)
   ```
   - Animated SVG or interactive diagram

4. **Optimization Journey**
   - Table showing all tests performed:
     - Signal comparison (5 methods)
     - EMA span optimization (6 parameters)
     - Position sizing comparison
   - Bar chart showing improvement at each step

5. **Asset Universe**
   - Cards for each asset (SPY, TLT, GLD, DBC, VNQ)
   - Shows: Asset class, role in portfolio, characteristics

6. **Key Decisions**
   - Accordion/collapsible sections:
     - Why EMA over SMA?
     - Why 126 days vs 252 days?
     - Why equal weight vs risk parity?
   - Each with supporting charts/data

---

### 2.3 Performance Analytics (`/performance`)

**Purpose:** Deep-dive into strategy performance

**Charts & Visualizations:**

1. **Cumulative Returns (Large)**
   - Multi-line chart comparing all strategies
   - Toggleable series (click legend to show/hide)
   - Shaded recession periods (2008, 2020)

2. **Drawdown Chart**
   - Underwater plot showing drawdown over time
   - Highlight max drawdown period
   - Color-coded severity (green < -10%, yellow -10% to -20%, red > -20%)

3. **Rolling Sharpe Ratio (252-day)**
   - Line chart showing Sharpe evolution
   - Horizontal line at Sharpe = 1.0 (target)
   - Shaded confidence bands

4. **Monthly Returns Heatmap**
   - Calendar heatmap (years on Y, months on X)
   - Color intensity = return magnitude
   - Green for positive, red for negative
   - Tooltip shows exact return %

5. **Annual Returns Bar Chart**
   - Strategy vs Benchmark side-by-side bars
   - Color-coded (green = positive, red = negative)
   - Labels showing exact percentages

6. **Return Distribution**
   - Histogram of daily returns
   - Overlaid normal distribution curve
   - Mark mean and median
   - Show skewness and kurtosis

7. **Performance Metrics Table**
   - Sortable table comparing all strategies
   - Columns: Total Return, Sharpe, Max DD, Calmar, etc.
   - Highlight best values per metric
   - Export to CSV button

8. **Risk-Return Scatter**
   - X-axis: Volatility
   - Y-axis: Annualized Return
   - Bubble size: Sharpe Ratio
   - Color: Strategy type
   - Efficient frontier line (if applicable)

---

### 2.4 Strategy Comparison (`/comparison`)

**Purpose:** Compare final strategy vs alternatives

**Visualizations:**

1. **Side-by-Side Performance Table**
   ```
   | Metric              | Final EMA 126d | EMA 252d | SMA 252d | Buy&Hold |
   |---------------------|----------------|----------|----------|----------|
   | Total Return        | 592.6%        | 514.2%   | 482.7%   | 276.4%   |
   | Sharpe Ratio        | 0.819         | 0.730    | 0.708    | 0.568    |
   | Max Drawdown        | -23.89%       | -23.19%  | -23.19%  | -36.20%  |
   ```
   - Color-coded cells (best = green, worst = red)

2. **Radar Chart (Spider Chart)**
   - Axes: Total Return, Sharpe, Sortino, Calmar, Win Rate, etc.
   - Multiple overlapping polygons (one per strategy)
   - Normalized to 0-100 scale

3. **Cumulative Returns Race**
   - Animated bar chart race (optional, cool visual)
   - Shows portfolio value growing over time
   - Bars represent different strategies

4. **Drawdown Comparison**
   - Overlaid underwater plots
   - All strategies on same chart
   - Highlight divergence periods

5. **Rolling Metrics Comparison**
   - Tabs to switch between:
     - Rolling Sharpe
     - Rolling Volatility
     - Rolling Return
   - All strategies overlaid

6. **Signal Overlap Analysis**
   - Venn diagram or heatmap showing signal agreement
   - When do different methods agree/disagree?

---

### 2.5 Risk Analysis (`/risk`)

**Purpose:** Comprehensive risk assessment

**Visualizations:**

1. **Drawdown Summary**
   - Max drawdown timeline (when did it occur?)
   - Top 5 drawdown periods table
   - Recovery time analysis

2. **Value at Risk (VaR)**
   - Historical VaR calculation
   - 95% and 99% confidence levels
   - Distribution plot with VaR markers

3. **Conditional VaR (CVaR/Expected Shortfall)**
   - Average loss in worst 5% scenarios
   - Tail risk visualization

4. **Volatility Clustering**
   - GARCH-style volatility chart
   - Shows periods of high/low volatility
   - Rolling volatility (30d, 90d, 252d)

5. **Correlation Matrix**
   - Heatmap of asset correlations
   - Dynamic: Can select time period
   - Show how correlations change over time

6. **Beta & Market Sensitivity**
   - Scatter plot: Strategy returns vs SPY returns
   - Regression line showing beta
   - R-squared value

7. **Tail Risk Analysis**
   - Q-Q plot (Quantile-Quantile)
   - Fat tails vs normal distribution
   - Extreme event analysis

8. **Stress Testing**
   - Table showing performance during:
     - 2008 Financial Crisis
     - 2020 COVID Crash
     - 2022 Bear Market
     - Other stress periods
   - Compare strategy DD vs S&P 500 DD

---

### 2.6 Signal History (`/signals`)

**Purpose:** Visualize signal generation and trades

**Visualizations:**

1. **Signal Timeline**
   - Gantt-chart style visualization
   - Each row = one asset (SPY, TLT, GLD, DBC, VNQ)
   - Green bars = signal ON (long position)
   - Gray = signal OFF (flat)
   - X-axis: Time (2005-2025)

2. **Price vs EMA Chart (Per Asset)**
   - Dropdown to select asset
   - Line chart: Price (blue) vs EMA 126d (orange)
   - Shaded regions: Green when signal ON
   - Buy/Sell markers on signal changes

3. **Signal Statistics Table**
   - Per asset:
     - % Time in position
     - Number of trades
     - Average hold duration
     - Win rate per asset

4. **Position Count Over Time**
   - Area chart showing # of active positions
   - Color-coded by count (1-5 positions)
   - Average line overlay

5. **Trade Distribution**
   - Histogram of trade durations
   - Win/loss distribution
   - Entry/exit analysis

6. **Recent Signals Table**
   - Last 20 signal changes
   - Columns: Date, Asset, Action (Buy/Sell), Price, Reason

---

### 2.7 Optimization Results (`/optimization`)

**Purpose:** Show parameter optimization process

**Visualizations:**

1. **EMA Span Optimization**
   - Line chart: Sharpe Ratio vs Span (63d to 378d)
   - Mark optimal span (126d) with star
   - Table showing all tested spans

2. **Signal Method Comparison**
   - Bar chart: Sharpe ratio for each method
   - (SMA, EMA, Abs Mom, Rel Mom, Dual Mom)

3. **Robustness Analysis**
   - Coefficient of Variation (CV) explanation
   - Chart showing CV across parameters
   - Green zone (CV < 10%) vs yellow (10-20%) vs red (> 20%)

4. **Parameter Sensitivity Heatmap**
   - 2D heatmap if testing multiple parameters
   - Example: Span (X) vs Threshold (Y), color = Sharpe

---

### 2.8 Live Monitoring (`/live`) [FUTURE]

**Purpose:** Real-time strategy tracking (if implemented)

**Features:**
- Current positions
- Today's P&L
- Real-time price updates (WebSocket)
- Upcoming rebalancing date
- Alerts/notifications

---

## 3. Visualization Components Library

### 3.1 Chart Types Needed

**Plotly Chart Types:**

1. **Line Charts** (Most common)
   - Cumulative returns
   - Drawdown series
   - Rolling metrics
   - Price vs EMA

2. **Bar Charts**
   - Annual returns
   - Strategy comparison
   - Signal method comparison

3. **Heatmaps**
   - Monthly returns calendar
   - Correlation matrix
   - Parameter sensitivity

4. **Scatter Plots**
   - Risk-return profile
   - Beta analysis

5. **Histograms**
   - Return distribution
   - Trade duration distribution

6. **Pie Charts**
   - Current holdings
   - Asset allocation

7. **Area Charts**
   - Position count over time
   - Underwater plot (filled)

8. **Box Plots**
   - Return distribution by year
   - Drawdown statistics

9. **Radar/Spider Charts**
   - Multi-metric comparison

10. **Candlestick Charts** (Optional)
    - Price action with signals overlay

### 3.2 Interactivity Features

**All Charts Should Have:**
- ✓ Hover tooltips (show exact values)
- ✓ Zoom (box zoom, scroll zoom)
- ✓ Pan (drag to move)
- ✓ Legends (click to show/hide series)
- ✓ Download (PNG, SVG, CSV)
- ✓ Responsive (mobile-friendly)

**Advanced Features:**
- Range slider (select date range)
- Crosshair cursor (compare multiple series)
- Annotations (mark important events)
- Dynamic updates (AJAX reload)

---

## 4. Data Flow & API Design

### 4.1 Backend Data Loading

**Startup (when Flask starts):**
```python
# app.py
def load_all_data():
    """Load all CSV files on startup, cache in memory"""
    data = {
        'prices': pd.read_csv('data/processed/prices_clean.csv'),
        'final_strategy': pd.read_csv('outputs/final_strategy_summary.csv'),
        'ema_optimization': pd.read_csv('outputs/ema_optimization_results.csv'),
        'signal_comparison': pd.read_csv('outputs/signal_comparison.csv'),
        # ... etc
    }
    return data

app_data = load_all_data()  # Global cache
```

**Benefits:**
- Fast page loads (data already in memory)
- No repeated CSV reads
- Can refresh periodically if needed

### 4.2 API Endpoints

**RESTful JSON API for AJAX:**

```python
# API routes for dynamic data fetching

@app.route('/api/performance/cumulative')
def api_cumulative_returns():
    """Return JSON for cumulative returns chart"""
    return jsonify({
        'dates': [...],
        'final_strategy': [...],
        'benchmark': [...],
        'initial_strategy': [...]
    })

@app.route('/api/performance/metrics')
def api_performance_metrics():
    """Return JSON for metrics table"""
    return jsonify({
        'strategies': [
            {'name': 'Final EMA 126d', 'sharpe': 0.819, ...},
            {'name': 'Benchmark', 'sharpe': 0.568, ...}
        ]
    })

@app.route('/api/signals/<asset>')
def api_signal_history(asset):
    """Return signal history for specific asset"""
    return jsonify({
        'dates': [...],
        'prices': [...],
        'ema': [...],
        'signals': [...]
    })

@app.route('/api/risk/drawdown')
def api_drawdown_data():
    """Return drawdown series"""
    return jsonify({
        'dates': [...],
        'drawdown': [...]
    })
```

**Benefits:**
- Separation of concerns (data vs presentation)
- Can use same API for different frontends
- Easy to add caching layer
- Could expose to external tools

### 4.3 Caching Strategy

**Two-Level Cache:**

1. **Memory Cache** (Flask-Caching)
   - Cache expensive calculations (metrics, aggregations)
   - TTL: 1 hour (or until data refresh)
   - Example:
   ```python
   @cache.cached(timeout=3600, key_prefix='all_metrics')
   def calculate_all_metrics():
       # Expensive calculation
       return results
   ```

2. **Pre-computed JSON Cache** (Optional)
   - Save chart data as JSON files on disk
   - Load from cache if available
   - Regenerate on data update
   - Example: `cache/cumulative_returns.json`

---

## 5. UI/UX Design Principles

### 5.1 Design Philosophy

**Goals:**
- Professional & clean (finance industry standard)
- Data-focused (charts take center stage)
- Fast & responsive (< 2s page load)
- Mobile-friendly (responsive design)
- Accessible (WCAG 2.1 AA compliance)

**Color Scheme:**

**Primary Colors:**
- Primary Blue: `#2C3E50` (dark blue, headers)
- Secondary Blue: `#3498DB` (bright blue, links)
- Success Green: `#27AE60` (positive returns)
- Danger Red: `#E74C3C` (negative returns, drawdowns)
- Warning Orange: `#F39C12` (alerts, moderate risk)

**Chart Colors:**
- Final Strategy: `#3498DB` (blue)
- Benchmark: `#E74C3C` (red)
- Alternative Strategies: `#95A5A6` (gray)
- Neutral: `#34495E` (dark gray)

**Background:**
- Main: `#FFFFFF` (white)
- Secondary: `#ECF0F1` (light gray)
- Cards: `#FFFFFF` with shadow

### 5.2 Typography

- **Headers:** Roboto Bold, 24-36px
- **Body:** Roboto Regular, 14-16px
- **Metrics:** Roboto Mono, 18-24px (for numbers)
- **Charts:** Arial, 10-12px (Plotly default)

### 5.3 Layout Grid

**Bootstrap 12-Column Grid:**
```html
<div class="container-fluid">
  <div class="row">
    <div class="col-md-8">  <!-- Main chart (8 columns) -->
    <div class="col-md-4">  <!-- Sidebar metrics (4 columns) -->
  </div>
</div>
```

**Responsive Breakpoints:**
- Desktop: > 1200px (show full layout)
- Tablet: 768px - 1200px (stack some elements)
- Mobile: < 768px (single column)

---

## 6. Implementation Plan

### Phase 1: Foundation (Week 1)
1. ✓ Set up Flask project structure
2. ✓ Create base templates (base.html, navbar)
3. ✓ Implement data loading module
4. ✓ Basic routing (all pages with placeholders)
5. ✓ Bootstrap integration
6. ✓ Deploy locally and test

### Phase 2: Core Visualizations (Week 2)
1. ✓ Dashboard home page
   - Key metrics cards
   - Cumulative returns chart (Plotly)
2. ✓ Performance analytics page
   - Multiple charts (returns, drawdown, rolling Sharpe)
3. ✓ Basic styling and navigation

### Phase 3: Advanced Features (Week 3)
1. ✓ Strategy comparison page
2. ✓ Risk analysis page
3. ✓ Signal history page
4. ✓ API endpoints for dynamic data
5. ✓ Caching implementation

### Phase 4: Polish & Optimization (Week 4)
1. ✓ Methodology page (with diagrams)
2. ✓ Optimization results page
3. ✓ Mobile responsiveness
4. ✓ Performance optimization
5. ✓ Documentation
6. ✓ Testing (cross-browser, mobile)

### Phase 5: Deployment (Optional)
1. ✓ Production server setup (Gunicorn + Nginx)
2. ✓ Domain configuration
3. ✓ SSL certificate
4. ✓ Monitoring setup
5. ✓ CI/CD pipeline (if desired)

---

## 7. File Structure

```
Multi-Asset-Strategy/
├── app/
│   ├── __init__.py              # Flask app factory
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── main.py              # Dashboard, methodology
│   │   ├── performance.py       # Performance page
│   │   ├── comparison.py        # Comparison page
│   │   ├── risk.py              # Risk analysis page
│   │   ├── signals.py           # Signal history page
│   │   └── api.py               # JSON API endpoints
│   ├── services/
│   │   ├── data_loader.py       # Load CSV files
│   │   ├── metrics.py           # Calculate performance metrics
│   │   ├── charts.py            # Generate Plotly charts
│   │   └── cache.py             # Caching utilities
│   ├── templates/
│   │   ├── base.html            # Base template with navbar
│   │   ├── index.html           # Dashboard home
│   │   ├── methodology.html     # Strategy explanation
│   │   ├── performance.html     # Performance analytics
│   │   ├── comparison.html      # Strategy comparison
│   │   ├── risk.html            # Risk analysis
│   │   ├── signals.html         # Signal history
│   │   └── components/
│   │       ├── metric_card.html # Reusable metric card
│   │       ├── chart.html       # Reusable chart container
│   │       └── table.html       # Reusable data table
│   ├── static/
│   │   ├── css/
│   │   │   ├── main.css         # Custom styles
│   │   │   └── bootstrap.min.css
│   │   ├── js/
│   │   │   ├── main.js          # Custom JavaScript
│   │   │   ├── charts.js        # Chart interactions
│   │   │   └── plotly.min.js
│   │   └── images/
│   │       └── logo.png
│   └── config.py                # Configuration settings
├── run.py                       # Flask app entry point
├── requirements.txt             # Python dependencies
└── README_DASHBOARD.md          # Dashboard documentation
```

---

## 8. Dependencies

**requirements.txt additions:**
```
Flask==3.0.0
Flask-Caching==2.1.0
plotly==5.18.0
dash==2.14.2                    # Optional: For more advanced dashboards
gunicorn==21.2.0                # Production server
python-dotenv==1.0.0            # Environment variables
```

---

## 9. Key Decisions Summary

| Decision | Option Chosen | Rationale |
|----------|---------------|-----------|
| **Backend Framework** | Flask | Lightweight, Python-native, easy integration with data science stack |
| **Charting Library** | Plotly | Interactive, professional, Python API, widely used in finance |
| **Frontend Framework** | Bootstrap 5 | Responsive, battle-tested, quick development |
| **Data Storage** | CSV + JSON Cache | Simple, existing format, easy to update |
| **Deployment** | Local first, optional production | Start simple, scale if needed |
| **Styling Approach** | Custom CSS + Bootstrap | Balance between customization and speed |

---

## 10. Success Criteria

**Dashboard must:**
1. ✓ Load in < 2 seconds (excluding large datasets)
2. ✓ Display all key metrics accurately
3. ✓ Provide interactive charts (zoom, pan, hover)
4. ✓ Be responsive (work on mobile/tablet/desktop)
5. ✓ Explain methodology clearly (non-technical audience)
6. ✓ Allow strategy comparison (side-by-side)
7. ✓ Show risk metrics prominently
8. ✓ Be easy to navigate (< 3 clicks to any page)
9. ✓ Look professional (suitable for presentations)
10. ✓ Be maintainable (clean code, documented)

---

## Next Steps

**Before Implementation:**
1. **Get User Approval** on this design
2. **Clarify Priorities**: Which pages are most important?
3. **Decide on Scope**: Full implementation or MVP first?
4. **Confirm Tech Stack**: Plotly vs alternatives?
5. **Deployment Target**: Local only or web hosting?

**Questions for User:**
1. Do you want real-time data updates, or static historical analysis?
2. Should the dashboard be public or password-protected?
3. Do you need export features (PDF reports, Excel downloads)?
4. Is mobile access important, or primarily desktop?
5. Any specific chart types or metrics not covered above?
6. Timeline expectations (quick MVP vs comprehensive build)?

---

**READY TO PROCEED UPON APPROVAL** ✅
