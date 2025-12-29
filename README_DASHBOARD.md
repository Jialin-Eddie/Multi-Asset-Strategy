# Multi-Asset Strategy Dashboard

Interactive web dashboard for visualizing the EMA 126-day trend-following strategy performance, methodology, and analytics.

## Features

**MVP Dashboard includes:**
- **Dashboard Home**: Key metrics, cumulative returns, current holdings
- **Performance Analytics**: Comprehensive charts (drawdown, rolling Sharpe, monthly heatmap, annual returns, distribution)
- **Methodology**: Strategy explanation, research timeline, asset universe, key decisions

## Quick Start

### 1. Install Dependencies

```bash
cd Multi-Asset-Strategy
conda activate multi_as_env
pip install -r requirements_dashboard.txt
```

### 2. Run Dashboard

```bash
python run.py
```

### 3. Access Dashboard

Open your browser and navigate to:
- **Dashboard Home**: http://127.0.0.1:5000/
- **Performance**: http://127.0.0.1:5000/performance
- **Methodology**: http://127.0.0.1:5000/methodology

## Technology Stack

- **Backend**: Flask 3.0
- **Charts**: Plotly 5.18 (interactive JavaScript visualizations)
- **Frontend**: Bootstrap 5 + HTML/CSS
- **Data**: Pandas + NumPy
- **Caching**: Flask-Caching (1-hour TTL)

## Project Structure

```
app/
├── __init__.py              # Flask app factory
├── routes/
│   ├── main.py              # Dashboard home
│   ├── performance.py       # Performance analytics
│   └── methodology.py       # Strategy explanation
├── services/
│   ├── data_loader.py       # Load CSV files & backtest data
│   └── charts.py            # Generate Plotly charts
├── templates/
│   ├── base.html            # Base template with navbar
│   ├── index.html           # Dashboard home
│   ├── performance.html     # Performance page
│   └── methodology.html     # Methodology page
└── static/
    ├── css/                 # Custom CSS (in base.html)
    ├── js/                  # Custom JavaScript (if needed)
    └── images/              # Images/logos

run.py                       # Flask app entry point
```

## Features Detail

### Dashboard Home
- **Key Metrics Cards**: Total Return (592.6%), Sharpe (0.82), Max DD (-23.9%), Calmar, Annualized Return, Sortino, Volatility, Win Rate
- **Cumulative Returns Chart**: Interactive line chart comparing Final Strategy vs Initial Strategy vs Buy & Hold
- **Current Holdings**: Pie chart + list of active positions
- **Recent Performance**: 30-day, 90-day, YTD returns

### Performance Analytics
- **Strategy Comparison Table**: Side-by-side metrics for all strategies
- **Cumulative Returns**: Multi-line interactive chart
- **Drawdown Evolution**: Underwater plot with fill
- **Rolling Sharpe**: 252-day rolling Sharpe ratio
- **Monthly Heatmap**: Calendar heatmap of monthly returns (color-coded)
- **Annual Returns**: Bar chart comparing strategy vs benchmark
- **Return Distribution**: Histogram of daily returns

### Methodology
- **Strategy Overview**: Visual explanation of signal, sizing, rebalancing, costs
- **Asset Universe**: Table with ticker, name, asset class, role
- **Research Timeline**: Chronological research phases with outcomes
- **Key Decisions**: Accordion with Q&A (Why EMA? Why 126d? Why equal weight?)
- **Optimization Results**: Summary of EMA span optimization
- **Production Readiness**: Checklist of validation steps

## Chart Interactivity

All Plotly charts include:
- ✓ Hover tooltips (exact values on mouseover)
- ✓ Zoom (box select, scroll wheel)
- ✓ Pan (drag to move)
- ✓ Legend (click to show/hide series)
- ✓ Download (PNG, SVG via toolbar)
- ✓ Responsive (adapts to screen size)

## Data Loading

Dashboard loads data on startup:
1. Historical prices from `data/processed/prices_clean.csv`
2. Recalculates backtest for Final Strategy (EMA 126d)
3. Recalculates backtest for Initial Strategy (EMA 252d)
4. Recalculates backtest for Buy & Hold benchmark
5. Loads optimization results (if available)

**Caching:** All calculations cached for 1 hour (Flask-Caching)

## Performance

- **First Load**: ~5-10 seconds (data loading + backtest calculations)
- **Subsequent Loads**: < 1 second (cached)
- **Page Navigation**: < 500ms (cached data)

## Troubleshooting

**Problem: ModuleNotFoundError**
```bash
# Solution: Add project root to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/path/to/Multi-Asset-Strategy"
```

**Problem: Data not loading**
```bash
# Ensure CSV files exist:
ls data/processed/prices_clean.csv
ls outputs/ema_optimization_results.csv
```

**Problem: Charts not displaying**
- Check browser console for JavaScript errors
- Ensure Plotly CDN is accessible: https://cdn.plotly.com/
- Try different browser (Chrome, Firefox, Edge)

**Problem: Port 5000 already in use**
```bash
# Use different port
python run.py --port 5001
```

## Development Mode

Dashboard runs in debug mode by default:
- Auto-reload on file changes
- Detailed error messages
- Flask debugger enabled

**For production deployment**, change in `run.py`:
```python
app.run(debug=False, host='0.0.0.0', port=80)
```

## Future Enhancements

**Phase 2 (potential additions):**
- Risk Analysis page (VaR, CVaR, correlation matrix, stress testing)
- Signal History page (signal timeline, trade log)
- Comparison page (radar charts, side-by-side analysis)
- API endpoints (/api/data for JSON responses)
- Real-time data updates (WebSocket)
- User authentication (password protection)
- Export features (PDF reports, Excel downloads)

## Screenshots

_(Screenshots would be included here after dashboard is running)_

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review Flask logs in terminal
3. Check browser console for errors
4. Verify data files exist and are readable

## License

Internal research project - not for distribution

---

**Built with Flask + Plotly | EMA 126-day Signal | Equal Weight Sizing | Monthly Rebalancing**
