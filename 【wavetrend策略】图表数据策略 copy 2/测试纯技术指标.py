#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
纯技术指标回测 - 不考虑评分系统，纯粹基于WaveTrend等技术指标交易
"""

import sys
import pandas as pd
from pathlib import Path

sys.path.append(str(Path(__file__).parent / '模块'))

from 核心策略模块 import TrendTradingStrategy
from 数据模块 import DataModule

class PureTechnicalBacktest:
    """纯技术指标回测引擎"""
    
    def __init__(self, initial_capital=10000, max_loss_per_trade=0.10):
        self.initial_capital = initial_capital
        self.max_loss_per_trade = max_loss_per_trade
        
        self.position_levels = {
            'signal_1': 0.33,
            'signal_2': 0.33,
            'signal_3': 0.33
        }
    
    def run_backtest(self, strategy_df):
        """运行回测 - 纯技术指标，无评分限制"""
        print()
        print("=" * 100)
        print("🚀 纯技术指标回测（无评分限制）")
        print("=" * 100)
        print()
        
        df = strategy_df.copy()
        
        # 初始化
        cash = self.initial_capital
        btc_holdings = 0.0
        current_positions = {}
        position_history = set()
        delayed_signal_2 = None
        
        portfolio_history = []
        trades = []
        
        for i in range(len(df)):
            row = df.iloc[i]
            date = row['date']
            price = row['close']
            
            position_value = btc_holdings * price
            total_value = cash + position_value
            
            # 1. 检查止损（任何时候都检查）
            if len(current_positions) > 0:
                positions_to_close = []
                for signal_name, position in list(current_positions.items()):
                    entry_price = position['entry_price']
                    btc_amount = position['btc']
                    
                    current_value = btc_amount * price
                    entry_value = btc_amount * entry_price
                    loss = entry_value - current_value
                    
                    if entry_value > 0:
                        loss_percentage = loss / entry_value
                    else:
                        loss_percentage = 0
                    
                    if loss_percentage >= self.max_loss_per_trade:
                        positions_to_close.append(signal_name)
                        
                        trades.append({
                            'date': date,
                            'action': f'STOP_LOSS_{signal_name}',
                            'price': price,
                            'btc_amount': btc_amount,
                            'value': current_value,
                            'profit': -loss,
                            'reason': f'止损：亏损{loss_percentage*100:.1f}%'
                        })
                        
                        cash += current_value
                        btc_holdings -= btc_amount
                
                for signal_name in positions_to_close:
                    del current_positions[signal_name]
            
            # 2. 检查止盈信号
            if row['exit_signal']:
                if btc_holdings > 0:
                    sell_value = btc_holdings * price
                    total_cost = sum(pos['btc'] * pos['entry_price'] 
                                   for pos in current_positions.values()) if current_positions else 0
                    profit = sell_value - total_cost
                    
                    trades.append({
                        'date': date,
                        'action': 'SELL_ALL',
                        'price': price,
                        'btc_amount': btc_holdings,
                        'value': sell_value,
                        'profit': profit,
                        'reason': f"止盈: {row['exit_reason']}"
                    })
                    
                    cash += sell_value
                    btc_holdings = 0.0
                    current_positions = {}
                    # 重置仓位历史，因为已经全部平仓
                    position_history = set()
            
            # 3. 处理延迟的第二仓信号
            if delayed_signal_2 is not None:
                delayed_date, delayed_price = delayed_signal_2
                if date != delayed_date and 'signal_1' in position_history and 'signal_2' not in current_positions:
                    position_size = self.position_levels.get('signal_2', 0)
                    if position_size > 0:
                        buy_value = total_value * position_size
                        
                        if buy_value > 0 and cash >= buy_value:
                            btc_amount = buy_value / price
                            
                            trades.append({
                                'date': date,
                                'action': 'BUY_signal_2',
                                'price': price,
                                'btc_amount': btc_amount,
                                'value': buy_value,
                                'profit': 0,
                                'reason': 'signal_2延迟入场'
                            })
                            
                            cash -= buy_value
                            btc_holdings += btc_amount
                            
                            current_positions['signal_2'] = {
                                'btc': btc_amount,
                                'entry_price': price,
                                'entry_date': date
                            }
                            position_history.add('signal_2')
                
                delayed_signal_2 = None
            
            # 4. 检查入场信号（无评分限制）
            entry_signal = row['entry_signal']
            if pd.notna(entry_signal) and entry_signal:
                signals = str(entry_signal).split(',')
                
                for signal_name in signals:
                    if signal_name == 'signal_2_delayed':
                        if delayed_signal_2 is None and 'signal_2' not in current_positions:
                            delayed_signal_2 = (date, price)
                    elif signal_name not in current_positions:
                        # 检查渐进关系
                        can_buy = True
                        if signal_name == 'signal_2':
                            if 'signal_1' not in position_history:
                                can_buy = False
                        elif signal_name == 'signal_3':
                            if 'signal_2' not in position_history:
                                can_buy = False
                        
                        if can_buy:
                            position_size = self.position_levels.get(signal_name, 0)
                            if position_size > 0:
                                buy_value = total_value * position_size
                                
                                if buy_value > 0 and cash >= buy_value:
                                    btc_amount = buy_value / price
                                    
                                    trades.append({
                                        'date': date,
                                        'action': f'BUY_{signal_name}',
                                        'price': price,
                                        'btc_amount': btc_amount,
                                        'value': buy_value,
                                        'profit': 0,
                                        'reason': f'{signal_name}入场'
                                    })
                                    
                                    cash -= buy_value
                                    btc_holdings += btc_amount
                                    current_positions[signal_name] = {
                                        'btc': btc_amount,
                                        'entry_price': price,
                                        'entry_date': date
                                    }
                                    position_history.add(signal_name)
            
            # 记录投资组合历史
            position_value = btc_holdings * price
            total_value = cash + position_value
            
            portfolio_history.append({
                'date': date,
                'price': price,
                'cash': cash,
                'btc_holdings': btc_holdings,
                'position_value': position_value,
                'total_value': total_value,
                'return': (total_value - self.initial_capital) / self.initial_capital * 100
            })
        
        portfolio_df = pd.DataFrame(portfolio_history)
        trades_df = pd.DataFrame(trades) if len(trades) > 0 else pd.DataFrame()
        
        self.show_results(portfolio_df, trades_df)
        
        return portfolio_df, trades_df
    
    def show_results(self, portfolio_df, trades_df):
        """显示回测结果"""
        print()
        print("=" * 100)
        print("📊 纯技术指标回测结果")
        print("=" * 100)
        print()
        
        final_value = portfolio_df['total_value'].iloc[-1]
        total_return = (final_value - self.initial_capital) / self.initial_capital * 100
        max_value = portfolio_df['total_value'].max()
        min_value = portfolio_df['total_value'].min()
        
        portfolio_df['peak'] = portfolio_df['total_value'].cummax()
        portfolio_df['drawdown'] = (portfolio_df['total_value'] - portfolio_df['peak']) / portfolio_df['peak'] * 100
        max_drawdown = portfolio_df['drawdown'].min()
        
        print(f"💰 初始资金: ${self.initial_capital:,.2f}")
        print(f"💰 最终价值: ${final_value:,.2f}")
        print(f"📈 总收益率: {total_return:.2f}%")
        print(f"📈 最高价值: ${max_value:,.2f}")
        print(f"📉 最低价值: ${min_value:,.2f}")
        print(f"📉 最大回撤: {max_drawdown:.2f}%")
        print()
        
        has_position_days = (portfolio_df['btc_holdings'] > 0).sum()
        print(f"📊 持仓天数: {has_position_days}天 ({has_position_days/len(portfolio_df)*100:.1f}%)")
        print()
        
        if len(trades_df) > 0:
            print(f"📊 交易统计:")
            print(f"  总交易次数: {len(trades_df)}")
            
            buy_trades = trades_df[trades_df['action'].str.contains('BUY', na=False)]
            sell_trades = trades_df[trades_df['action'].str.contains('SELL_ALL', na=False)]
            stop_loss_trades = trades_df[trades_df['action'].str.contains('STOP_LOSS', na=False)]
            
            print(f"  买入次数: {len(buy_trades)}")
            print(f"  止盈次数: {len(sell_trades)}")
            print(f"  止损次数: {len(stop_loss_trades)}")
            
            profit_trades = trades_df[trades_df['profit'] > 0]
            loss_trades = trades_df[trades_df['profit'] < 0]
            
            if len(profit_trades) > 0:
                print(f"\n  💰 盈利交易: {len(profit_trades)}次")
                print(f"     总盈利: ${profit_trades['profit'].sum():,.2f}")
                print(f"     平均盈利: ${profit_trades['profit'].mean():,.2f}")
            
            if len(loss_trades) > 0:
                print(f"\n  📉 亏损交易: {len(loss_trades)}次")
                print(f"     总亏损: ${loss_trades['profit'].sum():,.2f}")
                print(f"     平均亏损: ${loss_trades['profit'].mean():,.2f}")
            
            completed_trades = trades_df[trades_df['profit'] != 0]
            if len(completed_trades) > 0:
                win_rate = len(profit_trades) / len(completed_trades) * 100
                print(f"\n  🎯 胜率: {win_rate:.2f}%")
        
        print()
        print("=" * 100)


def main():
    print("=" * 100)
    print("🎯 纯技术指标回测测试")
    print("=" * 100)
    print()
    
    # 1. 加载数据
    print("【步骤1】加载数据...")
    data_module = DataModule()
    price_data = data_module.get_price_data()
    
    chart_data = data_module.digitize_chart_data()
    chart_data['date'] = pd.to_datetime(chart_data['date'])
    full_data = price_data.merge(chart_data, on='date', how='left')
    full_data = full_data.ffill().bfill()
    
    # 加载评分（仅用于对比显示）
    try:
        score_df = pd.read_csv('数字化数据/正确评分数据.csv')
        score_df['date'] = pd.to_datetime(score_df['date'])
        scored_data = full_data.merge(
            score_df[['date', 'total_score']], 
            on='date', how='left'
        )
        scored_data = scored_data.ffill().bfill()
    except:
        scored_data = full_data
        scored_data['total_score'] = 0
    
    print()
    
    # 2. 运行策略生成信号
    print("【步骤2】生成技术指标信号...")
    strategy = TrendTradingStrategy()
    strategy_results = strategy.run_strategy(scored_data)
    print()
    
    # 3. 运行纯技术指标回测
    print("【步骤3】运行纯技术指标回测...")
    backtest = PureTechnicalBacktest(initial_capital=10000, max_loss_per_trade=0.10)
    portfolio_df, trades_df = backtest.run_backtest(strategy_results)
    
    # 4. 对比买入持有
    print("【步骤4】对比买入持有...")
    print("-" * 100)
    start_price = scored_data.iloc[0]['close']
    end_price = scored_data.iloc[-1]['close']
    hold_return = (end_price / start_price - 1) * 100
    strategy_return = (portfolio_df['total_value'].iloc[-1] / 10000 - 1) * 100
    
    print(f"\n📊 最终对比:")
    print(f"  买入持有: {hold_return:.2f}%")
    print(f"  纯技术指标策略: {strategy_return:.2f}%")
    print(f"  差距: {(strategy_return - hold_return):.2f}%")
    print()
    
    # 保存结果
    portfolio_df.to_csv('数字化数据/pure_technical_portfolio.csv', index=False, encoding='utf-8-sig')
    if len(trades_df) > 0:
        trades_df.to_csv('数字化数据/pure_technical_trades.csv', index=False, encoding='utf-8-sig')
    
    print("✅ 结果已保存:")
    print("  • 数字化数据/pure_technical_portfolio.csv")
    print("  • 数字化数据/pure_technical_trades.csv")
    print()


if __name__ == "__main__":
    main()

