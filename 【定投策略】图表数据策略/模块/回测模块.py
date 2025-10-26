#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BTC图表回测模块 - 专门处理回测逻辑
"""

import pandas as pd
import numpy as np

class BacktestModule:
    """回测模块 - 处理投资组合回测"""

    def __init__(self, initial_capital=10000):
        self.initial_capital = initial_capital

    def load_strategy_data(self, data_folder):
        """加载策略数据"""
        try:
            # 优先使用增强后的策略数据
            try:
                df = pd.read_csv(f'{data_folder}/strategy_results_enhanced.csv')
                print(f"✅ 加载增强策略数据: {len(df)} 条记录")
            except:
                df = pd.read_csv(f'{data_folder}/strategy_results.csv')
                print(f"✅ 加载策略数据: {len(df)} 条记录")
            
            df['date'] = pd.to_datetime(df['date'])
            return df
        except:
            print("❌ 请先运行策略分析生成数据")
            return None

    def run_backtest(self, data_folder):
        """运行回测"""
        print("🚀 开始回测...")
        
        # 加载策略数据
        df = self.load_strategy_data(data_folder)
        if df is None:
            return
        
        # 从2021年开始回测
        df = df[df['date'] >= '2021-01-01']
        print(f"📅 回测时间范围: 2021年1月1日 - {df['date'].max().strftime('%Y年%m月%d日')}")
        print(f"📊 回测数据点: {len(df)} 天")
        
        # 如果策略数据没有价格列，尝试从其他文件获取
        if 'price' not in df.columns:
            try:
                # 尝试从complete_strategy_results.csv获取价格
                price_df = pd.read_csv(f'{data_folder}/complete_strategy_results.csv')
                if 'price' in price_df.columns:
                    df = df.merge(price_df[['date', 'price']], on='date', how='left')
                    print("✅ 已从complete_strategy_results.csv获取价格数据")
                else:
                    print("❌ 无法获取价格数据")
                    return
            except:
                print("❌ 无法获取价格数据")
                return

        cash = self.initial_capital
        btc_holdings = 0
        portfolio_value = cash

        trades = []
        portfolio_history = []

        for i, row in df.iterrows():
            date = row['date']
            price = row['price']
            strategy_signal = row['strategy_signal']

            # 执行交易逻辑 - 严格按照策略图片规则
            signal = str(strategy_signal).strip()  # 确保信号字符串干净
            
            if signal == "BUY" and cash > 0:
                # 抄底时间段：买入可用现金的80%，最多$5000
                buy_amount = min(cash * 0.8, 5000)
                if buy_amount >= 100:  # 至少买入$100
                    btc_bought = buy_amount / price
                    cash -= buy_amount
                    btc_holdings += btc_bought

                    trades.append({
                        'date': date,
                        'type': 'BUY',
                        'price': price,
                        'amount': buy_amount,
                        'btc': btc_bought,
                        'cash_after': cash,
                        'btc_after': btc_holdings
                    })

            elif signal == "DCA" and cash > 0:
                # 定投时间段：买入可用现金的40%，最多$2000
                buy_amount = min(cash * 0.4, 2000)
                if buy_amount >= 100:  # 至少买入$100
                    btc_bought = buy_amount / price
                    cash -= buy_amount
                    btc_holdings += btc_bought

                    trades.append({
                        'date': date,
                        'type': 'DCA',
                        'price': price,
                        'amount': buy_amount,
                        'btc': btc_bought,
                        'cash_after': cash,
                        'btc_after': btc_holdings
                    })

            elif signal == "SELL" and btc_holdings > 0:
                # 卖出时间段：全部卖出BTC
                sell_amount = btc_holdings * price
                cash += sell_amount

                trades.append({
                    'date': date,
                    'type': 'SELL_ALL',
                    'price': price,
                    'amount': sell_amount,
                    'btc': btc_holdings,
                    'cash_after': cash,
                    'btc_after': 0
                })

                btc_holdings = 0

            elif signal == "HOLD":
                # 持有时间段：不进行任何交易
                pass

            # 计算当前投资组合价值
            current_portfolio_value = cash + (btc_holdings * price)

            # 记录投资组合历史
            portfolio_history.append({
                'date': date,
                'price': price,
                'cash': cash,
                'btc_holdings': btc_holdings,
                'portfolio_value': current_portfolio_value,
                'signal': strategy_signal  # 记录策略信号
            })

        # 创建结果DataFrame
        trades_df = pd.DataFrame(trades)
        portfolio_df = pd.DataFrame(portfolio_history)

        # 保存结果
        trades_df.to_csv(f'{data_folder}/backtest_trades.csv', index=False)
        portfolio_df.to_csv(f'{data_folder}/backtest_portfolio.csv', index=False)
        
        print(f"✅ 回测完成: {len(trades)} 次交易")
        print(f"💾 结果已保存: {data_folder}/backtest_*.csv")

        return {
            'trades': trades_df,
            'portfolio_history': portfolio_df,
            'final_value': portfolio_df['portfolio_value'].iloc[-1],
            'total_return': (portfolio_df['portfolio_value'].iloc[-1] - self.initial_capital) / self.initial_capital
        }

    def show_backtest_results(self, results, data_folder):
        """显示回测结果"""
        if results is None:
            return

        trades_df = results['trades']
        portfolio_df = results['portfolio_history']

        print("\n💰 回测结果:")
        print(f"  初始资金: ${self.initial_capital:,.2f}")
        print(f"  最终价值: ${results['final_value']:,.2f}")
        print(f"  总收益率: {results['total_return']:.2%}")

        # 基准收益
        benchmark_return = (portfolio_df['price'].iloc[-1] - portfolio_df['price'].iloc[0]) / portfolio_df['price'].iloc[0]
        print(f"  基准收益: {benchmark_return:.2%}")
        print(f"  超额收益: {results['total_return'] - benchmark_return:.2%}")

        # 交易统计
        if len(trades_df) > 0:
            buy_trades = trades_df[trades_df['type'].isin(['BUY', 'DCA'])]
            sell_trades = trades_df[trades_df['type'] == 'SELL_ALL']

            print(f"\n🔄 交易统计:")
            print(f"  买入交易: {len(buy_trades)} 次")
            print(f"  卖出交易: {len(sell_trades)} 次")
            print(f"  总交易次数: {len(trades_df)} 次")

        # 最大回撤
        portfolio_values = portfolio_df['portfolio_value'].values
        peak = np.maximum.accumulate(portfolio_values)
        drawdown = (peak - portfolio_values) / peak
        max_drawdown = np.max(drawdown)

        print(f"\n📉 风险指标:")
        print(f"  最大回撤: {max_drawdown:.2%}")

        # 保存结果
        trades_df.to_csv(f'{data_folder}/backtest_trades.csv', index=False)
        portfolio_df.to_csv(f'{data_folder}/backtest_portfolio.csv', index=False)

        print(f"\n💾 回测结果已保存: {data_folder}/backtest_*.csv")

    def run_complete_backtest(self, data_folder):
        """运行完整回测流程"""
        print("🚀 BTC图表策略回测大师")
        print("=" * 80)

        # 加载策略数据
        df = self.load_strategy_data(data_folder)
        if df is None:
            return None

        # 运行回测
        results = self.run_backtest(df)

        # 显示结果
        self.show_backtest_results(results, data_folder)

        return results
