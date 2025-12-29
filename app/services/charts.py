"""Chart generation service using Plotly."""
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, List


def create_cumulative_returns_chart(strategies: Dict) -> str:
    """Create cumulative returns comparison chart."""
    fig = go.Figure()

    # Add each strategy
    for key, strategy in strategies.items():
        portfolio_value = strategy['backtest']['portfolio_value']
        name = strategy['name']

        # Style based on strategy type
        if 'Final' in name:
            line = dict(color='#3498DB', width=3)
        elif 'Benchmark' in name or 'Buy' in name:
            line = dict(color='#E74C3C', width=2, dash='dash')
        else:
            line = dict(color='#95A5A6', width=2)

        fig.add_trace(go.Scatter(
            x=portfolio_value.index,
            y=portfolio_value.values,
            name=name,
            line=line,
            hovertemplate='<b>%{fullData.name}</b><br>' +
                          'Date: %{x|%Y-%m-%d}<br>' +
                          'Value: $%{y:.2f}<br>' +
                          '<extra></extra>'
        ))

    fig.update_layout(
        title='Cumulative Returns: Strategy vs Benchmark',
        xaxis_title='Date',
        yaxis_title='Portfolio Value ($)',
        hovermode='x unified',
        template='plotly_white',
        height=500,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01
        )
    )

    return fig.to_html(full_html=False, include_plotlyjs='cdn')


def create_drawdown_chart(strategies: Dict) -> str:
    """Create drawdown comparison chart."""
    from src.backtest.engine import calculate_drawdown_series

    fig = go.Figure()

    for key, strategy in strategies.items():
        returns = strategy['backtest']['returns']
        drawdown = calculate_drawdown_series(returns)
        name = strategy['name']

        if 'Final' in name:
            line = dict(color='#3498DB', width=2.5)
        elif 'Benchmark' in name or 'Buy' in name:
            line = dict(color='#E74C3C', width=2, dash='dash')
        else:
            line = dict(color='#95A5A6', width=1.5)

        fig.add_trace(go.Scatter(
            x=drawdown.index,
            y=drawdown.values * 100,
            name=name,
            line=line,
            fill='tozeroy' if 'Final' in name else None,
            fillcolor='rgba(52, 152, 219, 0.1)' if 'Final' in name else None,
            hovertemplate='<b>%{fullData.name}</b><br>' +
                          'Date: %{x|%Y-%m-%d}<br>' +
                          'Drawdown: %{y:.2f}%<br>' +
                          '<extra></extra>'
        ))

    fig.update_layout(
        title='Drawdown Evolution',
        xaxis_title='Date',
        yaxis_title='Drawdown (%)',
        hovermode='x unified',
        template='plotly_white',
        height=400,
        legend=dict(
            yanchor="bottom",
            y=0.01,
            xanchor="left",
            x=0.01
        )
    )

    return fig.to_html(full_html=False, include_plotlyjs='cdn')


def create_rolling_sharpe_chart(strategies: Dict) -> str:
    """Create rolling Sharpe ratio chart."""
    fig = go.Figure()

    for key, strategy in strategies.items():
        if 'Benchmark' in strategy['name']:
            continue  # Skip benchmark for clarity

        returns = strategy['backtest']['returns']
        rolling_sharpe = (
            returns.rolling(252).mean() / returns.rolling(252).std() * np.sqrt(252)
        )
        name = strategy['name']

        if 'Final' in name:
            line = dict(color='#3498DB', width=2.5)
        else:
            line = dict(color='#95A5A6', width=1.5)

        fig.add_trace(go.Scatter(
            x=rolling_sharpe.index,
            y=rolling_sharpe.values,
            name=name,
            line=line,
            hovertemplate='<b>%{fullData.name}</b><br>' +
                          'Date: %{x|%Y-%m-%d}<br>' +
                          'Rolling Sharpe: %{y:.3f}<br>' +
                          '<extra></extra>'
        ))

    # Add target lines
    fig.add_hline(y=0, line_dash="solid", line_color="black", line_width=0.5,
                  annotation_text="Zero", annotation_position="right")
    fig.add_hline(y=1.0, line_dash="dot", line_color="green", line_width=1,
                  annotation_text="Target: 1.0", annotation_position="right")

    fig.update_layout(
        title='Rolling Sharpe Ratio (252-day)',
        xaxis_title='Date',
        yaxis_title='Sharpe Ratio',
        hovermode='x unified',
        template='plotly_white',
        height=400
    )

    return fig.to_html(full_html=False, include_plotlyjs='cdn')


def create_monthly_returns_heatmap(strategy_data: Dict) -> str:
    """Create monthly returns calendar heatmap."""
    returns = strategy_data['backtest']['returns']
    monthly_returns = returns.resample('ME').apply(lambda x: (1 + x).prod() - 1)

    # Create year-month pivot table
    monthly_returns_df = pd.DataFrame({
        'year': monthly_returns.index.year,
        'month': monthly_returns.index.month,
        'return': monthly_returns.values * 100
    })

    pivot = monthly_returns_df.pivot(index='year', columns='month', values='return')

    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
           'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
        y=pivot.index,
        colorscale='RdYlGn',
        zmid=0,
        text=pivot.values,
        texttemplate='%{text:.1f}%',
        textfont={"size": 10},
        colorbar=dict(title="Return (%)"),
        hovertemplate='Year: %{y}<br>Month: %{x}<br>Return: %{z:.2f}%<extra></extra>'
    ))

    fig.update_layout(
        title='Monthly Returns Heatmap',
        xaxis_title='Month',
        yaxis_title='Year',
        template='plotly_white',
        height=500,
        yaxis=dict(autorange='reversed')
    )

    return fig.to_html(full_html=False, include_plotlyjs='cdn')


def create_annual_returns_chart(strategies: Dict) -> str:
    """Create annual returns bar chart comparison."""
    fig = go.Figure()

    # Get final strategy and benchmark
    final = strategies['final']
    benchmark = strategies['benchmark']

    final_annual = final['backtest']['returns'].resample('YE').apply(lambda x: (1 + x).prod() - 1)
    bench_annual = benchmark['backtest']['returns'].resample('YE').apply(lambda x: (1 + x).prod() - 1)

    years = final_annual.index.year

    fig.add_trace(go.Bar(
        name='Final Strategy',
        x=years,
        y=final_annual.values * 100,
        marker_color='#3498DB',
        hovertemplate='Year: %{x}<br>Return: %{y:.2f}%<extra></extra>'
    ))

    fig.add_trace(go.Bar(
        name='Buy & Hold',
        x=years,
        y=bench_annual.values * 100,
        marker_color='#E74C3C',
        opacity=0.7,
        hovertemplate='Year: %{x}<br>Return: %{y:.2f}%<extra></extra>'
    ))

    fig.add_hline(y=0, line_dash="solid", line_color="black", line_width=1)

    fig.update_layout(
        title='Annual Returns Comparison',
        xaxis_title='Year',
        yaxis_title='Annual Return (%)',
        template='plotly_white',
        height=400,
        barmode='group'
    )

    return fig.to_html(full_html=False, include_plotlyjs='cdn')


def create_return_distribution_chart(strategy_data: Dict) -> str:
    """Create return distribution histogram."""
    returns = strategy_data['backtest']['returns'] * 100  # Convert to percentage

    fig = go.Figure()

    fig.add_trace(go.Histogram(
        x=returns.values,
        nbinsx=50,
        name='Daily Returns',
        marker_color='#3498DB',
        opacity=0.7,
        hovertemplate='Return: %{x:.2f}%<br>Count: %{y}<extra></extra>'
    ))

    # Add mean line
    mean_return = returns.mean()
    fig.add_vline(x=mean_return, line_dash="dash", line_color="red", line_width=2,
                  annotation_text=f"Mean: {mean_return:.3f}%",
                  annotation_position="top right")

    fig.update_layout(
        title='Daily Return Distribution',
        xaxis_title='Daily Return (%)',
        yaxis_title='Frequency',
        template='plotly_white',
        height=400,
        showlegend=False
    )

    return fig.to_html(full_html=False, include_plotlyjs='cdn')


def create_holdings_pie_chart(strategy_data: Dict) -> str:
    """Create current holdings pie chart."""
    signals = strategy_data['signals']
    current_signals = signals.iloc[-1]

    # Get active holdings
    active = current_signals[current_signals > 0]

    if len(active) == 0:
        # No current positions
        fig = go.Figure()
        fig.add_annotation(
            text="No Current Positions",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=20)
        )
    else:
        # Equal weight across active positions
        weights = {asset: 1/len(active) for asset in active.index}

        fig = go.Figure(data=[go.Pie(
            labels=list(weights.keys()),
            values=list(weights.values()),
            hovertemplate='<b>%{label}</b><br>Weight: %{value:.1%}<extra></extra>',
            textinfo='label+percent',
            marker=dict(colors=['#3498DB', '#E74C3C', '#F39C12', '#27AE60', '#9B59B6'])
        )])

    fig.update_layout(
        title='Current Holdings',
        template='plotly_white',
        height=300
    )

    return fig.to_html(full_html=False, include_plotlyjs='cdn')
