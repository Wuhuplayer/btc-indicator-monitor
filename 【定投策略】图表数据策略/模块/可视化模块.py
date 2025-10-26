#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BTC图表可视化模块 - 专门处理图表生成
"""

import pandas as pd
import json

class VisualizationModule:
    """可视化模块 - 处理图表和可视化生成"""

    def __init__(self):
        pass

    def generate_chart_data(self, data_folder):
        """生成图表数据"""
        print("🎨 生成可视化数据...")

        try:
            # 优先使用2021年后的数据
            try:
                strategy_df = pd.read_csv(f'{data_folder}/strategy_results_2021.csv')
                portfolio_df = pd.read_csv(f'{data_folder}/backtest_portfolio_2021.csv')
                trades_df = pd.read_csv(f'{data_folder}/backtest_trades_2021.csv')
                print("✅ 使用2021年后的数据")
            except:
                try:
                    strategy_df = pd.read_csv(f'{data_folder}/strategy_results_enhanced.csv')
                    portfolio_df = pd.read_csv(f'{data_folder}/backtest_portfolio_enhanced.csv')
                    trades_df = pd.read_csv(f'{data_folder}/backtest_trades_enhanced.csv')
                    print("✅ 使用增强后的数据")
                except:
                    strategy_df = pd.read_csv(f'{data_folder}/strategy_results.csv')
                    portfolio_df = pd.read_csv(f'{data_folder}/backtest_portfolio.csv')
                    trades_df = pd.read_csv(f'{data_folder}/backtest_trades.csv')
                    print("✅ 使用标准数据")

            # 转换日期格式
            strategy_df['date'] = pd.to_datetime(strategy_df['date'])
            portfolio_df['date'] = pd.to_datetime(portfolio_df['date'])
            trades_df['date'] = pd.to_datetime(trades_df['date'])

            # 仅使用参考图对应的时间范围，避免2012-2020因前向填充导致的平直线
            strategy_df = strategy_df[strategy_df['date'] >= pd.Timestamp('2020-10-01')].copy()

            # 准备图表数据
            dates = strategy_df['date'].dt.strftime('%Y-%m-%d').tolist()
            prices = strategy_df['price'].tolist()
            strategies = strategy_df['strategy_signal'].tolist()
            
            # 计算收益率数据
            initial_price = prices[0]
            returns = [(price / initial_price - 1) * 100 for price in prices]
            
            # 计算策略收益率 - 修正初始值
            initial_value = portfolio_df['portfolio_value'].iloc[0]
            portfolio_returns = []
            for _, row in portfolio_df.iterrows():
                portfolio_returns.append((row['portfolio_value'] / initial_value - 1) * 100)

            # 数据已经是每周一个点，无需采样
            sampled_dates = dates
            sampled_prices = prices
            sampled_strategies = strategies
            sampled_returns = returns
            sampled_portfolio_returns = portfolio_returns
            
            # 准备链上指标数据
            sth_mvrv_data = strategy_df['sth_mvrv'].tolist()
            whale_change_data = strategy_df['whale_holdings_change'].tolist()
            
            # 使用完整LTH数据范围
            lth_raw_data = strategy_df['lth_net_change_30d'].tolist()
            lth_change_data = lth_raw_data  # 不限制范围，显示真实数据

            # 准备交易数据 - 创建交易索引映射
            trades_data = []
            for _, trade in trades_df.iterrows():
                trade_date = trade['date'].strftime('%Y-%m-%d')
                # 找到该日期在采样数据中的索引
                if trade_date in sampled_dates:
                    idx = sampled_dates.index(trade_date)
                    trades_data.append({
                        'index': idx,
                        'date': trade_date,
                        'type': trade['type'],
                        'price': round(trade['price'], 2),
                        'amount': round(trade['amount'], 2),
                        'btc': round(trade['btc_after'], 6),
                        'cash': round(trade['cash_after'], 2)
                    })

            # 计算统计数据
            benchmark_return = (strategy_df['price'].iloc[-1] / strategy_df['price'].iloc[0] - 1)
            
            # 计算实际策略收益率 - 使用已经加载的portfolio_df
            initial_value = portfolio_df['portfolio_value'].iloc[0]  # 使用实际初始值
            final_value = portfolio_df['portfolio_value'].iloc[-1]
            strategy_return = (final_value - initial_value) / initial_value
            
            # 计算买入和卖出统计
            buy_trades = len(trades_df[trades_df['type'].isin(['BUY', 'DCA'])])
            sell_trades = len(trades_df[trades_df['type'] == 'SELL_ALL'])
            
            # 计算风险指标
            import numpy as np
            strategy_returns = portfolio_df['portfolio_value'].pct_change().dropna()
            positive_days = len(strategy_returns[strategy_returns > 0])
            total_days = len(strategy_returns)
            win_rate = positive_days / total_days * 100
            
            # 夏普比率
            annual_return = strategy_returns.mean() * 365
            annual_volatility = strategy_returns.std() * np.sqrt(365)
            sharpe_ratio = (annual_return - 0.02) / annual_volatility
            
            # 最大回撤
            cumulative_max = portfolio_df['portfolio_value'].expanding().max()
            drawdown = (portfolio_df['portfolio_value'] - cumulative_max) / cumulative_max
            max_drawdown = drawdown.min() * 100
            
            # 年化波动率
            volatility = annual_volatility * 100

            # 生成JavaScript数据
            js_content = f"""
// BTC图表策略可视化数据
const chartData = {{
    dates: {json.dumps(sampled_dates)},
    prices: {json.dumps(sampled_prices)},
    strategies: {json.dumps(sampled_strategies)},
    returns: {json.dumps(sampled_returns)},
    portfolio_returns: {json.dumps(sampled_portfolio_returns)},
    trades: {json.dumps(trades_data)},
    strategy_distribution: {json.dumps(strategy_df['strategy_signal'].value_counts().to_dict())},
    // 链上指标数据
    sth_mvrv: {json.dumps(sth_mvrv_data)},
    whale_change: {json.dumps(whale_change_data)},
    lth_change: {json.dumps(lth_change_data)},
    stats: {{
        total_return: {strategy_return:.4f},  // 策略收益率
        benchmark_return: {benchmark_return:.4f},  // 基准收益率
        excess_return: {strategy_return:.4f} - {benchmark_return:.4f},  // 超额收益
        total_trades: {len(trades_df)},  // 总交易次数
        buy_trades: {buy_trades},  // 买入次数
        sell_trades: {sell_trades},  // 卖出次数
        dca_trades: {len(strategy_df[strategy_df['strategy_signal'] == 'DCA'])},  // DCA信号天数
        strategy_return_pct: {strategy_return*100:.2f},  // 策略收益率百分比
        
        // 风险指标
        win_rate: {win_rate:.2f},  // 胜率
        sharpe_ratio: {sharpe_ratio:.4f},  // 夏普比率
        max_drawdown: {max_drawdown:.2f},  // 最大回撤
        volatility: {volatility:.2f}  // 年化波动率
    }}
}};
"""

            # 保存JavaScript数据
            with open('BTC策略可视化数据.js', 'w', encoding='utf-8') as f:
                f.write(js_content)

            print("✅ 图表数据生成完成: BTC策略可视化数据.js")
            return True

        except Exception as e:
            print(f"❌ 图表数据生成失败: {e}")
            return False

    def create_html_chart(self):
        """创建HTML可视化图表"""
        print("🎨 生成HTML图表...")
        
        # 先生成图表数据
        self.generate_chart_data('数字化数据')

        # 加版本号用于强制刷新本地缓存
        cache_bust_version = pd.Timestamp.now().strftime('%Y%m%d%H%M%S')

        html_content = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BTC图表策略可视化</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; color: #333; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        .header { text-align: center; margin-bottom: 30px; color: white; }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
        .header p { font-size: 1.2em; opacity: 0.9; }
        .dashboard { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .stat-card { background: white; border-radius: 15px; padding: 25px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); text-align: center; }
        .stat-card h3 { color: #666; font-size: 1em; margin-bottom: 10px; }
        .stat-card .value { font-size: 2em; font-weight: bold; margin-bottom: 5px; }
        .stat-card .positive { color: #27ae60; }
        .stat-card .negative { color: #e74c3c; }
        .stat-card .neutral { color: #3498db; }
        .charts-container { display: grid; grid-template-columns: 1fr; gap: 30px; }
        .chart-wrapper { background: white; border-radius: 15px; padding: 25px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); height: 800px; display: flex; flex-direction: column; }
        .chart-title { font-size: 1.5em; font-weight: bold; margin-bottom: 20px; color: #333; text-align: center; flex-shrink: 0; }
        .chart-canvas-container { flex: 1; min-height: 0; position: relative; }
        .chart-canvas-container canvas { width: 100% !important; height: 100% !important; }
        .strategy-filter { display: flex; justify-content: center; gap: 15px; margin: 20px 0; flex-shrink: 0; }
        .filter-btn { padding: 10px 20px; border: none; border-radius: 25px; cursor: pointer; font-weight: bold; transition: all 0.3s ease; }
        .filter-btn.active { transform: scale(1.1); box-shadow: 0 5px 15px rgba(0,0,0,0.2); }
        .filter-btn.buy { background: #e74c3c; color: white; }
        .filter-btn.dca { background: #f39c12; color: white; }
        .filter-btn.hold { background: #95a5a6; color: white; }
        .footer { text-align: center; margin-top: 40px; color: white; opacity: 0.8; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 BTC图表策略可视化</h1>
            <p>基于真实图表数据的专业策略分析</p>
        </div>

        <div class="dashboard">
            <div class="stat-card">
                <h3>策略收益</h3>
                <div class="value positive" id="strategy-return">--</div>
            </div>
            <div class="stat-card">
                <h3>基准收益</h3>
                <div class="value neutral" id="benchmark-return">--</div>
            </div>
            <div class="stat-card">
                <h3>超额收益</h3>
                <div class="value" id="excess-return">--</div>
            </div>
            <div class="stat-card">
                <h3>胜率</h3>
                <div class="value neutral" id="win-rate">--</div>
            </div>
            <div class="stat-card">
                <h3>夏普比率</h3>
                <div class="value neutral" id="sharpe-ratio">--</div>
            </div>
            <div class="stat-card">
                <h3>最大回撤</h3>
                <div class="value negative" id="max-drawdown">--</div>
            </div>
            <div class="stat-card">
                <h3>年化波动率</h3>
                <div class="value neutral" id="volatility">--</div>
            </div>
            <div class="stat-card">
                <h3>总交易</h3>
                <div class="value neutral" id="total-trades">--</div>
            </div>
            <div class="stat-card">
                <h3>买入交易</h3>
                <div class="value positive" id="buy-trades">--</div>
            </div>
            <div class="stat-card">
                <h3>卖出交易</h3>
                <div class="value neutral" id="sell-trades">--</div>
            </div>
        </div>

        <div class="charts-container">
            <div class="chart-wrapper">
                <div class="chart-title">📈 BTC价格走势与策略区间</div>
                <div class="strategy-filter">
                    <button class="filter-btn buy active" onclick="toggleStrategy('BUY')">抄底</button>
                    <button class="filter-btn dca active" onclick="toggleStrategy('DCA')">定投</button>
                    <button class="filter-btn hold active" onclick="toggleStrategy('HOLD')">持有</button>
                </div>
                <div class="chart-canvas-container">
                    <canvas id="priceChart"></canvas>
                </div>
            </div>

            <div class="chart-wrapper">
                <div class="chart-title">📊 收益率对比 - 悬浮查看交易详情</div>
                <div class="chart-canvas-container">
                    <canvas id="returnsChart"></canvas>
                </div>
            </div>

            <div class="chart-wrapper">
                <div class="chart-title">📊 策略信号分布</div>
                <div class="chart-canvas-container">
                    <canvas id="strategyChart"></canvas>
                </div>
            </div>

            <div class="chart-wrapper">
                <div class="chart-title">🔶 STH MVRV 指标（短期持有者MVRV）</div>
                <div class="chart-canvas-container">
                    <canvas id="sthMvrvChart"></canvas>
                </div>
            </div>

            <div class="chart-wrapper">
                <div class="chart-title">🐋 巨鲸30天持仓变化</div>
                <div class="chart-canvas-container">
                    <canvas id="whaleChart"></canvas>
                </div>
            </div>

            <div class="chart-wrapper">
                <div class="chart-title">💎 LTH 30天净持仓变化（长期持有者）</div>
                <div class="chart-canvas-container">
                    <canvas id="lthChart"></canvas>
                </div>
            </div>
        </div>

        <div class="footer">
            <p>基于真实专业图表数据 | 数据来源于专业链上指标图表</p>
        </div>
    </div>

    <script src="BTC策略可视化数据.js?v={CACHE_BUST}"></script>
    <script>
        const visibleStrategies = { 'BUY': true, 'DCA': true, 'HOLD': true };

        function toggleStrategy(strategy) {
            visibleStrategies[strategy] = !visibleStrategies[strategy];
            const btn = event.target;
            btn.classList.toggle('active');
            updateCharts();
        }

        function updateStats() {
            document.getElementById('strategy-return').textContent = (chartData.stats.total_return * 100).toFixed(2) + '%';
            document.getElementById('benchmark-return').textContent = (chartData.stats.benchmark_return * 100).toFixed(2) + '%';
            document.getElementById('excess-return').textContent = ((chartData.stats.total_return - chartData.stats.benchmark_return) * 100).toFixed(2) + '%';
            document.getElementById('total-trades').textContent = chartData.stats.total_trades;
            document.getElementById('buy-trades').textContent = chartData.stats.buy_trades;
            document.getElementById('sell-trades').textContent = chartData.stats.sell_trades;
            
            // 风险指标
            document.getElementById('win-rate').textContent = chartData.stats.win_rate.toFixed(2) + '%';
            document.getElementById('sharpe-ratio').textContent = chartData.stats.sharpe_ratio.toFixed(4);
            document.getElementById('max-drawdown').textContent = chartData.stats.max_drawdown.toFixed(2) + '%';
            document.getElementById('volatility').textContent = chartData.stats.volatility.toFixed(2) + '%';

            const excessReturn = chartData.stats.total_return - chartData.stats.benchmark_return;
            const excessElement = document.getElementById('excess-return');
            excessElement.className = 'value ' + (excessReturn > 0 ? 'positive' : 'negative');
        }

        function initCharts() {
            const priceCtx = document.getElementById('priceChart').getContext('2d');
            new Chart(priceCtx, {
                type: 'line',
                data: {
                    labels: chartData.dates,
                    datasets: [{
                        label: 'BTC价格',
                        data: chartData.prices,
                        borderColor: '#3498db',
                        backgroundColor: 'rgba(52, 152, 219, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: true, position: 'top' },
                        tooltip: {
                            mode: 'index',
                            intersect: false,
                            callbacks: {
                                title: function(context) { return '日期: ' + context[0].label; },
                                afterBody: function(context) {
                                    const index = context[0].dataIndex;
                                    const strategy = chartData.strategies[index];
                                    return ['策略信号: ' + strategy];
                                }
                            }
                        }
                    },
                    scales: {
                        y: { beginAtZero: false, title: { display: true, text: '价格 (USD)' } },
                        x: { display: true, title: { display: true, text: '日期' }, ticks: { maxRotation: 45, font: { size: 10 } } }
                    }
                }
            });

            // 收益率对比图表
            const returnsCtx = document.getElementById('returnsChart').getContext('2d');
            new Chart(returnsCtx, {
                type: 'line',
                data: {
                    labels: chartData.dates,
                    datasets: [{
                        label: 'BTC买入持有收益',
                        data: chartData.returns,
                        borderColor: '#3498db',
                        backgroundColor: 'rgba(52, 152, 219, 0.1)',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.1
                    }, {
                        label: '策略收益',
                        data: chartData.portfolio_returns,
                        borderColor: '#e74c3c',
                        backgroundColor: 'rgba(231, 76, 60, 0.1)',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: true, position: 'top' },
                        tooltip: {
                            mode: 'index',
                            intersect: false,
                            callbacks: {
                                title: function(context) { return '日期: ' + context[0].label; },
                                afterBody: function(context) {
                                    const index = context[0].dataIndex;
                                    const strategy = chartData.strategies[index];
                                    let tooltip = ['策略信号: ' + strategy];
                                    
                                    // 查找该日期的交易
                                    const trade = chartData.trades.find(t => t.index === index);
                                    if (trade) {
                                        tooltip.push('');
                                        tooltip.push('交易详情:');
                                        tooltip.push('类型: ' + trade.type);
                                        tooltip.push('价格: $' + trade.price.toLocaleString());
                                        tooltip.push('金额: $' + trade.amount.toLocaleString());
                                        tooltip.push('BTC持仓: ' + trade.btc.toFixed(6));
                                        tooltip.push('现金余额: $' + trade.cash.toLocaleString());
                                    }
                                    
                                    return tooltip;
                                }
                            }
                        }
                    },
                    scales: {
                        y: { 
                            beginAtZero: true, 
                            title: { display: true, text: '收益率 (%)' },
                            ticks: {
                                callback: function(value) {
                                    return value.toFixed(0) + '%';
                                }
                            }
                        },
                        x: { display: true, title: { display: true, text: '日期' }, ticks: { maxRotation: 45, font: { size: 10 } } }
                    }
                }
            });

            const strategyCtx = document.getElementById('strategyChart').getContext('2d');
            new Chart(strategyCtx, {
                type: 'doughnut',
                data: {
                    labels: ['抄底 (BUY)', '定投 (DCA)', '持有 (HOLD)'],
                    datasets: [{
                        data: [
                            chartData.strategy_distribution.BUY || 0,
                            chartData.strategy_distribution.DCA || 0,
                            chartData.strategy_distribution.HOLD || 0
                        ],
                        backgroundColor: ['#e74c3c', '#f39c12', '#95a5a6'],
                        borderWidth: 2,
                        borderColor: '#fff'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'bottom' },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = ((context.parsed / total) * 100).toFixed(1);
                                    return context.label + ': ' + context.parsed + ' 天 (' + percentage + '%)';
                                }
                            }
                        }
                    }
                }
            });

            // STH MVRV 图表
            const sthMvrvCtx = document.getElementById('sthMvrvChart').getContext('2d');
            new Chart(sthMvrvCtx, {
                type: 'line',
                data: {
                    labels: chartData.dates,
                    datasets: [{
                        label: 'STH MVRV',
                        data: chartData.sth_mvrv,
                        borderColor: '#FF6B35',
                        backgroundColor: 'rgba(255, 107, 53, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        // 取消平滑，严格按逐日数据绘制
                        tension: 0,
                        pointRadius: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: true, position: 'top' },
                        tooltip: {
                            mode: 'index',
                            intersect: false
                        }
                    },
                    scales: {
                        y: { 
                            beginAtZero: false, 
                            title: { display: true, text: 'MVRV 值' },
                            min: 0.7,
                            max: 1.6
                        },
                        x: { 
                            display: true, 
                            title: { display: true, text: '日期' }, 
                            ticks: { maxRotation: 45, font: { size: 10 } } 
                        }
                    }
                }
            });

            // 巨鲸持仓变化图表
            const whaleCtx = document.getElementById('whaleChart').getContext('2d');
            new Chart(whaleCtx, {
                type: 'line',
                data: {
                    labels: chartData.dates,
                    datasets: [{
                        label: '巨鲸30天持仓变化 (%)',
                        data: chartData.whale_change.map(v => v * 100),
                        borderColor: '#9B59B6',
                        backgroundColor: 'rgba(155, 89, 182, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: true, position: 'top' },
                        tooltip: {
                            mode: 'index',
                            intersect: false,
                            callbacks: {
                                label: function(context) {
                                    return context.dataset.label + ': ' + context.parsed.y.toFixed(2) + '%';
                                }
                            }
                        }
                    },
                    scales: {
                        y: { 
                            beginAtZero: false, 
                            title: { display: true, text: '持仓变化 (%)' },
                            ticks: {
                                callback: function(value) {
                                    return value.toFixed(1) + '%';
                                }
                            }
                        },
                        x: { 
                            display: true, 
                            title: { display: true, text: '日期' }, 
                            ticks: { maxRotation: 45, font: { size: 10 } } 
                        }
                    }
                }
            });

            // LTH 净持仓变化图表
            const lthCtx = document.getElementById('lthChart').getContext('2d');
            new Chart(lthCtx, {
                type: 'bar',
                data: {
                    labels: chartData.dates,
                    datasets: [{
                        label: 'LTH 30天净持仓变化',
                        data: chartData.lth_change,
                        backgroundColor: chartData.lth_change.map(v => v > 0 ? 'rgba(46, 204, 113, 0.6)' : 'rgba(231, 76, 60, 0.6)'),
                        borderColor: chartData.lth_change.map(v => v > 0 ? '#2ecc71' : '#e74c3c'),
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: true, position: 'top' },
                        tooltip: {
                            mode: 'index',
                            intersect: false,
                            callbacks: {
                                label: function(context) {
                                    return context.dataset.label + ': ' + context.parsed.y.toLocaleString() + ' BTC';
                                }
                            }
                        }
                    },
                    scales: {
                        y: { 
                            beginAtZero: true, 
                            title: { display: true, text: 'BTC数量' },
                            ticks: {
                                callback: function(value) {
                                    return value.toLocaleString();
                                }
                            }
                        },
                        x: { 
                            display: true, 
                            title: { display: true, text: '日期' }, 
                            ticks: { maxRotation: 45, font: { size: 10 } } 
                        }
                    }
                }
            });
        }

        function updateCharts() {
            // 更新图表背景色逻辑可以在这里添加
        }

        document.addEventListener('DOMContentLoaded', function() {
            updateStats();
            initCharts();
        });
    </script>
</body>
</html>
"""

        # 注入版本号，避免 f-string 与 HTML/CSS 花括号冲突
        html_content = html_content.replace('{CACHE_BUST}', cache_bust_version)

        # 保存HTML文件
        with open('BTC策略可视化图表.html', 'w', encoding='utf-8') as f:
            f.write(html_content)

        print("✅ HTML可视化图表生成完成: BTC策略可视化图表.html")

    def run_visualization(self, data_folder):
        """运行完整可视化流程"""
        print("🎨 BTC图表策略可视化大师")
        print("=" * 80)

        # 生成图表数据
        if not self.generate_chart_data(data_folder):
            return False

        # 创建HTML图表
        self.create_html_chart()

        print("\n🎉 可视化生成完成！")
        return True
