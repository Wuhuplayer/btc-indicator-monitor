#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MVRV Z-Score策略可视化图表
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

# 读取数据
portfolio = pd.read_csv('results/mvrv_z_portfolio.csv')
trades = pd.read_csv('results/mvrv_z_trades.csv')

portfolio['date'] = pd.to_datetime(portfolio['date'])
trades['date'] = pd.to_datetime(trades['date'])

# 计算买入持有
initial_capital = 10000
buy_hold = initial_capital * (portfolio['price'] / portfolio['price'].iloc[0])

# 计算回撤
portfolio['peak'] = portfolio['total_value'].cummax()
portfolio['drawdown'] = (portfolio['total_value'] - portfolio['peak']) / portfolio['peak'] * 100

# 创建子图
fig = make_subplots(
    rows=4, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.05,
    row_heights=[0.4, 0.2, 0.2, 0.2],
    subplot_titles=(
        "资金增长曲线 (对数刻度)",
        "MVRV Z-Score指标",
        "回撤曲线",
        "BTC价格 + 买卖信号"
    )
)

# === 第1行：资金增长曲线 ===
fig.add_trace(
    go.Scatter(
        x=portfolio['date'],
        y=portfolio['total_value'],
        name='MVRV Z策略',
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
fig.add_hrect(y0=-4, y1=-1.5, fillcolor="green", opacity=0.1, line_width=0, row=2, col=1)
fig.add_hrect(y0=-1.5, y1=0, fillcolor="lightgreen", opacity=0.1, line_width=0, row=2, col=1)
fig.add_hrect(y0=0, y1=3, fillcolor="gray", opacity=0.05, line_width=0, row=2, col=1)
fig.add_hrect(y0=3, y1=5, fillcolor="yellow", opacity=0.1, line_width=0, row=2, col=1)
fig.add_hrect(y0=5, y1=10, fillcolor="red", opacity=0.1, line_width=0, row=2, col=1)

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
fig.add_hline(y=-2.0, line_dash="dot", line_color="darkgreen", annotation_text="极度低估(-2)", row=2, col=1)
fig.add_hline(y=-1.5, line_dash="dot", line_color="green", annotation_text="深度低估(-1.5)", row=2, col=1)
fig.add_hline(y=-1.0, line_dash="dot", line_color="lightgreen", annotation_text="低估(-1)", row=2, col=1)
fig.add_hline(y=-0.5, line_dash="dot", line_color="lightgreen", annotation_text="轻度低估(-0.5)", row=2, col=1)
fig.add_hline(y=0, line_dash="solid", line_color="gray", row=2, col=1)
fig.add_hline(y=5.0, line_dash="dot", line_color="red", annotation_text="高估(5)", row=2, col=1)
fig.add_hline(y=6.0, line_dash="dot", line_color="darkred", annotation_text="深度高估(6)", row=2, col=1)

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
    # 按原因分组
    for reason in buy_trades['reason'].unique():
        trades_group = buy_trades[buy_trades['reason'] == reason]
        
        if '极度低估' in reason:
            color = 'darkgreen'
            size = 15
        elif '深度低估' in reason:
            color = 'green'
            size = 12
        elif '低估' in reason:
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
        
        fig.add_trace(
            go.Scatter(
                x=trades_group['date'],
                y=trades_group['price'],
                mode='markers',
                name=reason,
                marker=dict(
                    symbol='triangle-down',
                    size=15,
                    color='red',
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
        'text': '🎯 MVRV Z-Score策略 - 低估买入，高估卖出<br><sub>总收益: +26,060% (261.6倍) | 最大回撤: -74.09% | 交易次数: 35次</sub>',
        'x': 0.5,
        'xanchor': 'center',
        'font': {'size': 24, 'color': '#00D9FF'}
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
fig.update_yaxes(title_text="Z-Score", row=2, col=1)
fig.update_yaxes(title_text="回撤 (%)", row=3, col=1)
fig.update_yaxes(title_text="BTC价格 ($)", type="log", row=4, col=1)

# 更新X轴
fig.update_xaxes(title_text="日期", row=4, col=1)

# 保存
fig.write_html('results/MVRV_Z策略可视化图表.html', auto_open=True)
print("✅ 图表已生成: results/MVRV_Z策略可视化图表.html")

# 生成策略说明
print()
print("=" * 100)
print("📊 MVRV Z-Score策略说明")
print("=" * 100)
print()
print("【策略原理】")
print("MVRV Z-Score = (市值 - 实现市值) / 标准差")
print("衡量BTC相对于其'公允价值'的偏离程度")
print()
print("【买入策略】")
print("  🟢🟢🟢 Z < -2.0: 极度低估，买入20%")
print("  🟢🟢   Z < -1.5: 深度低估，买入30%")
print("  🟢     Z < -1.0: 低估，买入30%")
print("  🟢     Z < -0.5: 轻度低估，买入20%")
print()
print("【卖出策略】")
print("  🔴     Z > 5.0: 高估，卖出20%")
print("  🔴🔴   Z > 6.0: 深度高估，卖出30%")
print("  🔴🔴🔴 Z > 7.0: 极度高估，卖出30%")
print("  🔴🔴🔴 Z > 8.0: 泡沫区，卖出20%")
print()
print("【持有策略】")
print("  ⚪     0 < Z < 5: 正常区间，持有不动")
print()
print("【历史表现】")
print(f"  • 总收益率: +26,060.06%")
print(f"  • 收益倍数: 261.6倍")
print(f"  • 最大回撤: -74.09%")
print(f"  • 交易次数: 35次 (买入32次，卖出3次)")
print(f"  • 胜率: 100% (所有卖出均盈利)")
print(f"  • 平均盈利: +2,397.4%")
print()
print("【策略优势】")
print("  ✅ 超越买入持有 +5,903%")
print("  ✅ 100%胜率，所有卖出均盈利")
print("  ✅ 在市场底部分批买入，降低成本")
print("  ✅ 在市场顶部分批卖出，锁定利润")
print("  ✅ 基于链上数据，更客观")
print()
print("【策略劣势】")
print("  ⚠️  回撤较大(-74%)，需要强大心理承受能力")
print("  ⚠️  卖出机会少(仅3次)，大部分时间持有")
print("  ⚠️  Z > 7的极端高估区间历史上从未出现")
print("  ⚠️  跑输ATR追踪策略约7,864%")
print()
print("【适用人群】")
print("  • 长期价值投资者")
print("  • 能承受大幅回撤的投资者")
print("  • 相信BTC长期价值的HODLer")
print("  • 不喜欢频繁交易的投资者")
print()
print("=" * 100)





