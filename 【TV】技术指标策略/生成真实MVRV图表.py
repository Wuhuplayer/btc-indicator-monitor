#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成真实MVRV Z-Score策略可视化图表
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

print("=" * 100)
print("📊 生成真实MVRV Z-Score策略可视化图表")
print("=" * 100)
print()

# 读取数据
print("📂 加载数据...")
portfolio = pd.read_csv('results/真实mvrv_z_portfolio.csv')
trades = pd.read_csv('results/真实mvrv_z_trades.csv')
portfolio_5y = pd.read_csv('results/真实mvrv_z_portfolio_5y.csv')
trades_5y = pd.read_csv('results/真实mvrv_z_trades_5y.csv')

portfolio['date'] = pd.to_datetime(portfolio['date'])
trades['date'] = pd.to_datetime(trades['date'])
portfolio_5y['date'] = pd.to_datetime(portfolio_5y['date'])
trades_5y['date'] = pd.to_datetime(trades_5y['date'])

print(f"✅ 数据加载完成")
print(f"   全周期: {len(portfolio)}天, {len(trades)}笔交易")
print(f"   近5年: {len(portfolio_5y)}天, {len(trades_5y)}笔交易")
print()

# 计算买入持有
initial_capital = 10000
buy_hold = initial_capital * (portfolio['price'] / portfolio['price'].iloc[0])
buy_hold_5y = initial_capital * (portfolio_5y['price'] / portfolio_5y['price'].iloc[0])

# 计算回撤
portfolio['peak'] = portfolio['total_value'].cummax()
portfolio['drawdown'] = (portfolio['total_value'] - portfolio['peak']) / portfolio['peak'] * 100

portfolio_5y['peak'] = portfolio_5y['total_value'].cummax()
portfolio_5y['drawdown'] = (portfolio_5y['total_value'] - portfolio_5y['peak']) / portfolio_5y['peak'] * 100

# ============================================================================
# 全周期图表
# ============================================================================
print("📊 生成全周期图表...")

fig = make_subplots(
    rows=4, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.05,
    row_heights=[0.35, 0.25, 0.2, 0.2],
    subplot_titles=(
        "资金增长曲线 (对数刻度)",
        "真实MVRV Z-Score指标",
        "回撤曲线",
        "BTC价格 + 买卖信号"
    )
)

# === 第1行：资金增长曲线 ===
fig.add_trace(
    go.Scatter(
        x=portfolio['date'],
        y=portfolio['total_value'],
        name='真实MVRV Z策略',
        line=dict(color='#00D9FF', width=3),
        hovertemplate='%{x}<br>策略价值: $%{y:,.0f}<extra></extra>'
    ),
    row=1, col=1
)

fig.add_trace(
    go.Scatter(
        x=portfolio['date'],
        y=buy_hold,
        name='买入持有',
        line=dict(color='#FFD700', width=2, dash='dash'),
        hovertemplate='%{x}<br>买入持有: $%{y:,.0f}<extra></extra>'
    ),
    row=1, col=1
)

# === 第2行：MVRV Z-Score ===
# 背景区域
fig.add_hrect(y0=-4, y1=-1, fillcolor="darkgreen", opacity=0.15, line_width=0, row=2, col=1)
fig.add_hrect(y0=-1, y1=0, fillcolor="green", opacity=0.1, line_width=0, row=2, col=1)
fig.add_hrect(y0=0, y1=2, fillcolor="lightgreen", opacity=0.08, line_width=0, row=2, col=1)
fig.add_hrect(y0=2, y1=4, fillcolor="gray", opacity=0.05, line_width=0, row=2, col=1)
fig.add_hrect(y0=4, y1=6, fillcolor="yellow", opacity=0.1, line_width=0, row=2, col=1)
fig.add_hrect(y0=6, y1=8, fillcolor="orange", opacity=0.12, line_width=0, row=2, col=1)
fig.add_hrect(y0=8, y1=12, fillcolor="red", opacity=0.15, line_width=0, row=2, col=1)

fig.add_trace(
    go.Scatter(
        x=portfolio['date'],
        y=portfolio['z_score'],
        name='MVRV Z-Score',
        line=dict(color='purple', width=2),
        fill='tozeroy',
        fillcolor='rgba(128, 0, 128, 0.2)',
        hovertemplate='%{x}<br>Z-Score: %{y:.2f}<extra></extra>'
    ),
    row=2, col=1
)

# 添加阈值线
fig.add_hline(y=-1.0, line_dash="dot", line_color="darkgreen", annotation_text="极度低估(-1)", row=2, col=1)
fig.add_hline(y=0, line_dash="solid", line_color="gray", annotation_text="低估(0)", row=2, col=1)
fig.add_hline(y=2.0, line_dash="dot", line_color="lightgray", annotation_text="正常(2)", row=2, col=1)
fig.add_hline(y=6.0, line_dash="dot", line_color="orange", annotation_text="高估(6)", row=2, col=1)
fig.add_hline(y=7.0, line_dash="dot", line_color="red", annotation_text="深度高估(7)", row=2, col=1)
fig.add_hline(y=8.0, line_dash="dot", line_color="darkred", annotation_text="极度高估(8)", row=2, col=1)
fig.add_hline(y=9.0, line_dash="dot", line_color="darkred", annotation_text="泡沫(9)", row=2, col=1)

# === 第3行：回撤曲线 ===
fig.add_trace(
    go.Scatter(
        x=portfolio['date'],
        y=portfolio['drawdown'],
        name='回撤',
        fill='tozeroy',
        line=dict(color='red', width=2),
        fillcolor='rgba(255, 0, 0, 0.2)',
        hovertemplate='%{x}<br>回撤: %{y:.2f}%<extra></extra>'
    ),
    row=3, col=1
)

# === 第4行：BTC价格 + 买卖信号 ===
fig.add_trace(
    go.Scatter(
        x=portfolio['date'],
        y=portfolio['price'],
        name='BTC价格',
        line=dict(color='orange', width=2),
        hovertemplate='%{x}<br>BTC: $%{y:,.0f}<extra></extra>'
    ),
    row=4, col=1
)

# 添加买入信号
buy_trades = trades[trades['type'] == 'BUY']
if len(buy_trades) > 0:
    for reason in buy_trades['reason'].unique():
        trades_group = buy_trades[buy_trades['reason'] == reason]
        
        if '极度低估' in reason:
            color = 'darkgreen'
            size = 15
        elif '低估' in reason:
            color = 'green'
            size = 12
        elif '正常偏低' in reason:
            color = 'lightgreen'
            size = 10
        else:
            color = 'lime'
            size = 8
        
        fig.add_trace(
            go.Scatter(
                x=trades_group['date'],
                y=trades_group['price'],
                mode='markers',
                name=reason,
                marker=dict(
                    symbol='triangle-up',
                    size=size,
                    color=color,
                    line=dict(color='white', width=1)
                ),
                hovertemplate='%{x}<br>' + reason + '<br>价格: $%{y:,.0f}<br>Z=%{customdata:.2f}<extra></extra>',
                customdata=trades_group['z_score']
            ),
            row=4, col=1
        )

# 添加卖出信号
sell_trades = trades[trades['type'] == 'SELL']
if len(sell_trades) > 0:
    for reason in sell_trades['reason'].unique():
        trades_group = sell_trades[sell_trades['reason'] == reason]
        
        if '泡沫' in reason:
            color = 'darkred'
            size = 18
        elif '极度高估' in reason:
            color = 'red'
            size = 15
        elif '深度高估' in reason:
            color = 'orangered'
            size = 12
        else:
            color = 'orange'
            size = 10
        
        fig.add_trace(
            go.Scatter(
                x=trades_group['date'],
                y=trades_group['price'],
                mode='markers',
                name=reason,
                marker=dict(
                    symbol='triangle-down',
                    size=size,
                    color=color,
                    line=dict(color='white', width=1)
                ),
                hovertemplate='%{x}<br>' + reason + '<br>价格: $%{y:,.0f}<br>Z=%{customdata:.2f}<extra></extra>',
                customdata=trades_group['z_score']
            ),
            row=4, col=1
        )

# 更新布局
fig.update_layout(
    title={
        'text': '🎯 真实MVRV Z-Score策略 - 全周期<br><sub>总收益: +12,627% (127.3倍) | 最大回撤: -83.14% | 交易次数: 20次 | 数据来源: CoinMetrics</sub>',
        'x': 0.5,
        'xanchor': 'center',
        'font': {'size': 22, 'color': '#00D9FF'}
    },
    height=1400,
    showlegend=True,
    hovermode='x unified',
    template='plotly_dark',
    legend=dict(
        orientation="v",
        yanchor="top",
        y=0.99,
        xanchor="left",
        x=1.01,
        bgcolor='rgba(0,0,0,0.5)'
    )
)

# 更新Y轴
fig.update_yaxes(title_text="资金价值 ($)", type="log", row=1, col=1)
fig.update_yaxes(title_text="MVRV Z-Score", row=2, col=1)
fig.update_yaxes(title_text="回撤 (%)", row=3, col=1)
fig.update_yaxes(title_text="BTC价格 ($)", type="log", row=4, col=1)

# 更新X轴
fig.update_xaxes(title_text="日期", row=4, col=1)

# 保存全周期图表
fig.write_html('results/真实MVRV_Z策略_全周期图表.html', auto_open=False)
print("✅ 全周期图表已生成: results/真实MVRV_Z策略_全周期图表.html")

# ============================================================================
# 近5年图表
# ============================================================================
print("📊 生成近5年图表...")

fig_5y = make_subplots(
    rows=4, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.05,
    row_heights=[0.35, 0.25, 0.2, 0.2],
    subplot_titles=(
        "资金增长曲线 (对数刻度)",
        "真实MVRV Z-Score指标",
        "回撤曲线",
        "BTC价格 + 买卖信号"
    )
)

# === 第1行：资金增长曲线 ===
fig_5y.add_trace(
    go.Scatter(
        x=portfolio_5y['date'],
        y=portfolio_5y['total_value'],
        name='真实MVRV Z策略',
        line=dict(color='#00D9FF', width=3),
        hovertemplate='%{x}<br>策略价值: $%{y:,.0f}<extra></extra>'
    ),
    row=1, col=1
)

fig_5y.add_trace(
    go.Scatter(
        x=portfolio_5y['date'],
        y=buy_hold_5y,
        name='买入持有',
        line=dict(color='#FFD700', width=2, dash='dash'),
        hovertemplate='%{x}<br>买入持有: $%{y:,.0f}<extra></extra>'
    ),
    row=1, col=1
)

# === 第2行：MVRV Z-Score ===
fig_5y.add_hrect(y0=-4, y1=-1, fillcolor="darkgreen", opacity=0.15, line_width=0, row=2, col=1)
fig_5y.add_hrect(y0=-1, y1=0, fillcolor="green", opacity=0.1, line_width=0, row=2, col=1)
fig_5y.add_hrect(y0=0, y1=2, fillcolor="lightgreen", opacity=0.08, line_width=0, row=2, col=1)
fig_5y.add_hrect(y0=2, y1=4, fillcolor="gray", opacity=0.05, line_width=0, row=2, col=1)
fig_5y.add_hrect(y0=4, y1=6, fillcolor="yellow", opacity=0.1, line_width=0, row=2, col=1)
fig_5y.add_hrect(y0=6, y1=8, fillcolor="orange", opacity=0.12, line_width=0, row=2, col=1)
fig_5y.add_hrect(y0=8, y1=12, fillcolor="red", opacity=0.15, line_width=0, row=2, col=1)

fig_5y.add_trace(
    go.Scatter(
        x=portfolio_5y['date'],
        y=portfolio_5y['z_score'],
        name='MVRV Z-Score',
        line=dict(color='purple', width=2),
        fill='tozeroy',
        fillcolor='rgba(128, 0, 128, 0.2)',
        hovertemplate='%{x}<br>Z-Score: %{y:.2f}<extra></extra>'
    ),
    row=2, col=1
)

fig_5y.add_hline(y=-1.0, line_dash="dot", line_color="darkgreen", annotation_text="极度低估(-1)", row=2, col=1)
fig_5y.add_hline(y=0, line_dash="solid", line_color="gray", annotation_text="低估(0)", row=2, col=1)
fig_5y.add_hline(y=6.0, line_dash="dot", line_color="orange", annotation_text="高估(6)", row=2, col=1)
fig_5y.add_hline(y=7.0, line_dash="dot", line_color="red", annotation_text="深度高估(7)", row=2, col=1)
fig_5y.add_hline(y=8.0, line_dash="dot", line_color="darkred", annotation_text="极度高估(8)", row=2, col=1)

# === 第3行：回撤曲线 ===
fig_5y.add_trace(
    go.Scatter(
        x=portfolio_5y['date'],
        y=portfolio_5y['drawdown'],
        name='回撤',
        fill='tozeroy',
        line=dict(color='red', width=2),
        fillcolor='rgba(255, 0, 0, 0.2)',
        hovertemplate='%{x}<br>回撤: %{y:.2f}%<extra></extra>'
    ),
    row=3, col=1
)

# === 第4行：BTC价格 + 买卖信号 ===
fig_5y.add_trace(
    go.Scatter(
        x=portfolio_5y['date'],
        y=portfolio_5y['price'],
        name='BTC价格',
        line=dict(color='orange', width=2),
        hovertemplate='%{x}<br>BTC: $%{y:,.0f}<extra></extra>'
    ),
    row=4, col=1
)

# 添加买入信号（近5年）
buy_trades_5y = trades_5y[trades_5y['type'] == 'BUY']
if len(buy_trades_5y) > 0:
    for reason in buy_trades_5y['reason'].unique():
        trades_group = buy_trades_5y[buy_trades_5y['reason'] == reason]
        
        if '极度低估' in reason:
            color = 'darkgreen'
            size = 15
        elif '低估' in reason:
            color = 'green'
            size = 12
        elif '正常偏低' in reason:
            color = 'lightgreen'
            size = 10
        else:
            color = 'lime'
            size = 8
        
        fig_5y.add_trace(
            go.Scatter(
                x=trades_group['date'],
                y=trades_group['price'],
                mode='markers',
                name=reason,
                marker=dict(
                    symbol='triangle-up',
                    size=size,
                    color=color,
                    line=dict(color='white', width=1)
                ),
                hovertemplate='%{x}<br>' + reason + '<br>价格: $%{y:,.0f}<br>Z=%{customdata:.2f}<extra></extra>',
                customdata=trades_group['z_score']
            ),
            row=4, col=1
        )

# 添加卖出信号（近5年）
sell_trades_5y = trades_5y[trades_5y['type'] == 'SELL']
if len(sell_trades_5y) > 0:
    for reason in sell_trades_5y['reason'].unique():
        trades_group = sell_trades_5y[sell_trades_5y['reason'] == reason]
        
        if '泡沫' in reason:
            color = 'darkred'
            size = 18
        elif '极度高估' in reason:
            color = 'red'
            size = 15
        elif '深度高估' in reason:
            color = 'orangered'
            size = 12
        else:
            color = 'orange'
            size = 10
        
        fig_5y.add_trace(
            go.Scatter(
                x=trades_group['date'],
                y=trades_group['price'],
                mode='markers',
                name=reason,
                marker=dict(
                    symbol='triangle-down',
                    size=size,
                    color=color,
                    line=dict(color='white', width=1)
                ),
                hovertemplate='%{x}<br>' + reason + '<br>价格: $%{y:,.0f}<br>Z=%{customdata:.2f}<extra></extra>',
                customdata=trades_group['z_score']
            ),
            row=4, col=1
        )

# 更新布局
fig_5y.update_layout(
    title={
        'text': '🎯 真实MVRV Z-Score策略 - 近5年<br><sub>总收益: +733% (8.3倍) | 最大回撤: -76.63% | 交易次数: 14次 | 数据来源: CoinMetrics</sub>',
        'x': 0.5,
        'xanchor': 'center',
        'font': {'size': 22, 'color': '#00D9FF'}
    },
    height=1400,
    showlegend=True,
    hovermode='x unified',
    template='plotly_dark',
    legend=dict(
        orientation="v",
        yanchor="top",
        y=0.99,
        xanchor="left",
        x=1.01,
        bgcolor='rgba(0,0,0,0.5)'
    )
)

# 更新Y轴
fig_5y.update_yaxes(title_text="资金价值 ($)", type="log", row=1, col=1)
fig_5y.update_yaxes(title_text="MVRV Z-Score", row=2, col=1)
fig_5y.update_yaxes(title_text="回撤 (%)", row=3, col=1)
fig_5y.update_yaxes(title_text="BTC价格 ($)", type="log", row=4, col=1)

# 更新X轴
fig_5y.update_xaxes(title_text="日期", row=4, col=1)

# 保存近5年图表
fig_5y.write_html('results/真实MVRV_Z策略_近5年图表.html', auto_open=True)
print("✅ 近5年图表已生成: results/真实MVRV_Z策略_近5年图表.html")

print()
print("=" * 100)
print("🎉 图表生成完成！")
print("=" * 100)
print()
print("📊 生成的图表:")
print("  1. results/真实MVRV_Z策略_全周期图表.html")
print("  2. results/真实MVRV_Z策略_近5年图表.html")
print()
print("🔍 图表内容:")
print("  • 资金增长曲线（策略 vs 买入持有）")
print("  • 真实MVRV Z-Score指标（带阈值线）")
print("  • 回撤曲线")
print("  • BTC价格走势 + 买卖信号标注")
print()
print("💡 使用说明:")
print("  • 绿色三角形 = 买入信号")
print("  • 红色三角形 = 卖出信号")
print("  • 三角形大小代表信号强度")
print("  • 鼠标悬停查看详细信息")
print()
print("=" * 100)







