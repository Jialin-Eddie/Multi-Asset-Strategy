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
    monthly_returns = returns.resample('M').apply(lambda x: (1 + x).prod() - 1)

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

    final_annual = final['backtest']['returns'].resample('Y').apply(lambda x: (1 + x).prod() - 1)
    bench_annual = benchmark['backtest']['returns'].resample('Y').apply(lambda x: (1 + x).prod() - 1)

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


def create_regime_timeline_chart(spy_prices, regimes, strategy_value):
    """Create market regime timeline with background shading."""
    fig = go.Figure()

    # Add background shading for regimes
    regime_changes = regimes[regimes != regimes.shift(1)].index.tolist()
    if regimes.index[0] not in regime_changes:
        regime_changes.insert(0, regimes.index[0])
    regime_changes.append(regimes.index[-1])

    for i in range(len(regime_changes) - 1):
        start = regime_changes[i]
        end = regime_changes[i + 1]
        regime = regimes[start]

        color_map = {
            'bull': 'rgba(39, 174, 96, 0.1)',
            'bear': 'rgba(231, 76, 60, 0.1)',
            'sideways': 'rgba(149, 165, 166, 0.05)'
        }

        fig.add_vrect(
            x0=start, x1=end,
            fillcolor=color_map.get(regime, 'rgba(149, 165, 166, 0.05)'),
            layer="below", line_width=0
        )

    # Add strategy equity curve
    fig.add_trace(go.Scatter(
        x=strategy_value.index,
        y=strategy_value.values,
        name='Strategy',
        line=dict(color='#3498DB', width=2.5),
        hovertemplate='<b>Strategy</b><br>Date: %{x|%Y-%m-%d}<br>Value: $%{y:.2f}<extra></extra>'
    ))

    fig.update_layout(
        title='Strategy Performance Across Market Regimes',
        xaxis_title='Date',
        yaxis_title='Portfolio Value ($)',
        hovermode='x unified',
        template='plotly_white',
        height=500,
        showlegend=True
    )

    return fig.to_html(full_html=False, include_plotlyjs='cdn')


def create_var_cvar_chart(var_cvar_data):
    """Create rolling VaR and CVaR chart with multiple confidence levels."""
    fig = go.Figure()

    # Define colors for different confidence levels
    colors = {
        'VaR_95%': '#3498DB',
        'CVaR_95%': '#E74C3C',
        'VaR_99%': '#9B59B6',
        'CVaR_99%': '#E67E22'
    }

    # Add traces for each VaR/CVaR series
    for col in var_cvar_data.columns:
        fig.add_trace(go.Scatter(
            x=var_cvar_data.index,
            y=var_cvar_data[col] * 100,  # Convert to percentage
            name=col,
            line=dict(
                color=colors.get(col, '#95A5A6'),
                width=2 if 'VaR' in col else 1.5,
                dash='solid' if 'VaR' in col else 'dash'
            ),
            hovertemplate=f'<b>{col}</b><br>Date: %{{x|%Y-%m-%d}}<br>Loss: %{{y:.2f}}%<extra></extra>'
        ))

    fig.update_layout(
        title='Rolling Value at Risk (VaR) and Conditional VaR (CVaR)',
        xaxis_title='Date',
        yaxis_title='Daily Loss Threshold (%)',
        hovermode='x unified',
        template='plotly_white',
        height=450,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    # Add reference line at 0
    fig.add_hline(y=0, line_dash="dot", line_color="gray", opacity=0.5)

    return fig.to_html(full_html=False, include_plotlyjs='cdn')


def create_stress_test_chart(stress_tests):
    """Create comparison chart for stress test scenarios."""
    # Filter out None values
    valid_tests = {k: v for k, v in stress_tests.items() if v is not None}

    if not valid_tests:
        return "<p>No stress test data available</p>"

    scenarios = []
    strategy_returns = []
    benchmark_returns = []
    strategy_dds = []
    benchmark_dds = []

    for key, data in valid_tests.items():
        scenarios.append(data['name'])
        strategy_returns.append(data['strategy_return'] * 100)
        benchmark_returns.append(data['benchmark_return'] * 100)
        strategy_dds.append(data['strategy_max_dd'] * 100)
        benchmark_dds.append(data['benchmark_max_dd'] * 100)

    # Create subplots: Returns and Drawdowns
    from plotly.subplots import make_subplots
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('Total Returns During Crisis', 'Maximum Drawdown'),
        specs=[[{"type": "bar"}, {"type": "bar"}]]
    )

    # Returns comparison
    fig.add_trace(
        go.Bar(
            name='Strategy',
            x=scenarios,
            y=strategy_returns,
            marker_color='#3498DB',
            text=[f'{r:.1f}%' for r in strategy_returns],
            textposition='outside',
            hovertemplate='<b>Strategy</b><br>%{x}<br>Return: %{y:.2f}%<extra></extra>'
        ),
        row=1, col=1
    )

    fig.add_trace(
        go.Bar(
            name='Benchmark',
            x=scenarios,
            y=benchmark_returns,
            marker_color='#95A5A6',
            text=[f'{r:.1f}%' for r in benchmark_returns],
            textposition='outside',
            hovertemplate='<b>Benchmark</b><br>%{x}<br>Return: %{y:.2f}%<extra></extra>'
        ),
        row=1, col=1
    )

    # Drawdown comparison
    fig.add_trace(
        go.Bar(
            name='Strategy',
            x=scenarios,
            y=strategy_dds,
            marker_color='#3498DB',
            text=[f'{dd:.1f}%' for dd in strategy_dds],
            textposition='outside',
            showlegend=False,
            hovertemplate='<b>Strategy</b><br>%{x}<br>Max DD: %{y:.2f}%<extra></extra>'
        ),
        row=1, col=2
    )

    fig.add_trace(
        go.Bar(
            name='Benchmark',
            x=scenarios,
            y=benchmark_dds,
            marker_color='#95A5A6',
            text=[f'{dd:.1f}%' for dd in benchmark_dds],
            textposition='outside',
            showlegend=False,
            hovertemplate='<b>Benchmark</b><br>%{x}<br>Max DD: %{y:.2f}%<extra></extra>'
        ),
        row=1, col=2
    )

    fig.update_layout(
        title_text='Stress Test Performance: How the Strategy Handled Major Market Crises',
        height=500,
        template='plotly_white',
        barmode='group',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    fig.update_yaxes(title_text="Return (%)", row=1, col=1)
    fig.update_yaxes(title_text="Drawdown (%)", row=1, col=2)

    return fig.to_html(full_html=False, include_plotlyjs='cdn')


def create_ema_sensitivity_chart(ema_sensitivity_data):
    """Create parameter sensitivity chart showing performance vs EMA window size."""
    if ema_sensitivity_data is None or len(ema_sensitivity_data) == 0:
        return "<p>No EMA sensitivity data available</p>"

    from plotly.subplots import make_subplots

    # Create subplots for different metrics
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Sharpe Ratio vs EMA Window', 'Total Return vs EMA Window',
                       'Max Drawdown vs EMA Window', 'Win Rate vs EMA Window'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )

    # Sharpe Ratio
    fig.add_trace(
        go.Scatter(
            x=ema_sensitivity_data['window'],
            y=ema_sensitivity_data['sharpe_ratio'],
            mode='lines+markers',
            name='Sharpe Ratio',
            line=dict(color='#3498DB', width=3),
            marker=dict(size=8),
            hovertemplate='<b>EMA Window: %{x} days</b><br>Sharpe: %{y:.3f}<extra></extra>'
        ),
        row=1, col=1
    )

    # Total Return
    fig.add_trace(
        go.Scatter(
            x=ema_sensitivity_data['window'],
            y=ema_sensitivity_data['total_return'] * 100,
            mode='lines+markers',
            name='Total Return',
            line=dict(color='#27AE60', width=3),
            marker=dict(size=8),
            hovertemplate='<b>EMA Window: %{x} days</b><br>Return: %{y:.1f}%<extra></extra>'
        ),
        row=1, col=2
    )

    # Max Drawdown
    fig.add_trace(
        go.Scatter(
            x=ema_sensitivity_data['window'],
            y=ema_sensitivity_data['max_drawdown'] * 100,
            mode='lines+markers',
            name='Max Drawdown',
            line=dict(color='#E74C3C', width=3),
            marker=dict(size=8),
            hovertemplate='<b>EMA Window: %{x} days</b><br>Max DD: %{y:.1f}%<extra></extra>'
        ),
        row=2, col=1
    )

    # Win Rate
    fig.add_trace(
        go.Scatter(
            x=ema_sensitivity_data['window'],
            y=ema_sensitivity_data['win_rate'] * 100,
            mode='lines+markers',
            name='Win Rate',
            line=dict(color='#9B59B6', width=3),
            marker=dict(size=8),
            hovertemplate='<b>EMA Window: %{x} days</b><br>Win Rate: %{y:.1f}%<extra></extra>'
        ),
        row=2, col=2
    )

    # Highlight the optimal window (126 days)
    optimal_window = 126
    for row in range(1, 3):
        for col in range(1, 3):
            fig.add_vline(
                x=optimal_window,
                line_dash="dash",
                line_color="green",
                opacity=0.5,
                row=row, col=col
            )

    fig.update_layout(
        title_text='Parameter Sensitivity: How Strategy Performance Varies with EMA Window Size',
        height=700,
        template='plotly_white',
        showlegend=False
    )

    fig.update_xaxes(title_text="EMA Window (days)", row=1, col=1)
    fig.update_xaxes(title_text="EMA Window (days)", row=1, col=2)
    fig.update_xaxes(title_text="EMA Window (days)", row=2, col=1)
    fig.update_xaxes(title_text="EMA Window (days)", row=2, col=2)

    fig.update_yaxes(title_text="Sharpe Ratio", row=1, col=1)
    fig.update_yaxes(title_text="Total Return (%)", row=1, col=2)
    fig.update_yaxes(title_text="Max Drawdown (%)", row=2, col=1)
    fig.update_yaxes(title_text="Win Rate (%)", row=2, col=2)

    return fig.to_html(full_html=False, include_plotlyjs='cdn')
