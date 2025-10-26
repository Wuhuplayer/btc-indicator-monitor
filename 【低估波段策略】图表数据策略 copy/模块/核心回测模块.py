#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
核心回测模块 - 趋势交易策略回测引擎
包含：渐进式仓位管理 + 止损止盈 + 评分保护
"""

import pandas as pd
import numpy as np

class TrendBacktestEngine:
    """趋势交易回测引擎"""
    
    def __init__(self, initial_capital=10000, max_loss_per_trade=0.10):
        """
        初始化回测参数
        
        Args:
            initial_capital: 初始资金
            max_loss_per_trade: 每次最大亏损比例（10%）
        """
        self.initial_capital = initial_capital
        self.max_loss_per_trade = max_loss_per_trade  # 10%最大亏损
        
        self.position_levels = {
            'signal_1': 0.33,
            'signal_2': 0.33,
            'signal_3': 0.33
        }
    
    def run_backtest(self, strategy_df):
        """
        运行回测 - 只在3-6分时入场，任何时候都可以止损止盈，评分降低强制平仓
        """
        print()
        print("=" * 100)
        print("🚀 运行回测（3-6分入场 + 止损止盈 + 评分保护）")
        print("=" * 100)
        print()
        
        df = strategy_df.copy()
        
        # 初始化
        cash = self.initial_capital
        btc_holdings = 0.0
        current_positions = {}  # 当前持仓
        position_history = set()  # 历史上曾经建立过的仓位（用于渐进关系判断）
        delayed_signal_2 = None  # 延迟的第二仓信号
        
        portfolio_history = []
        trades = []
        
        # 统计
        score_dist = df['total_score'].value_counts().sort_index()
        print(f"📊 评分分布:")
        for score, count in score_dist.items():
            pct = count / len(df) * 100
            print(f"  {score}分: {count}天 ({pct:.1f}%)")
        
        target_zone_days = ((df['total_score'] >= 3) & (df['total_score'] <= 6)).sum()
        print(f"\n✅ 3-6分（策略执行区）: {target_zone_days}天 ({target_zone_days/len(df)*100:.1f}%)")
        print()
        
        for i in range(len(df)):
            row = df.iloc[i]
            date = row['date']
            price = row['close']
            total_score = row['total_score']
            
            position_value = btc_holdings * price
            total_value = cash + position_value
            
            in_target_zone = (3 <= total_score <= 6)
            
            # 1. 检查止损（任何时候都检查）
            if len(current_positions) > 0:
                positions_to_close = []
                for signal_name, position in list(current_positions.items()):
                    entry_price = position['entry_price']
                    btc_amount = position['btc']
                    
                    current_value = btc_amount * price
                    entry_value = btc_amount * entry_price
                    loss = entry_value - current_value
                    
                    # 避免除零错误
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
                            'reason': f'止损：亏损{loss_percentage*100:.1f}%',
                            'score': total_score
                        })
                        
                        cash += current_value
                        btc_holdings -= btc_amount
                
                for signal_name in positions_to_close:
                    del current_positions[signal_name]
            
            # 2. 检查止盈（任何时候都检查）
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
                        'reason': f"止盈: {row['exit_reason']}",
                        'score': total_score
                    })
                    
                    cash += sell_value
                    btc_holdings = 0.0
                    current_positions = {}
            
            # 3. 处理延迟的第二仓信号（第二天执行）
            if delayed_signal_2 is not None:
                delayed_date, delayed_price = delayed_signal_2
                # 如果不是同一天，且第一仓已经建立过，且第二仓未建仓
                if date != delayed_date and 'signal_1' in position_history and 'signal_2' not in current_positions:
                    if in_target_zone:  # 仍然在目标区间
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
                                    'reason': f'signal_2延迟入场 (评分{total_score}分)',
                                    'score': total_score
                                })
                                
                                cash -= buy_value
                                btc_holdings += btc_amount
                                
                                current_positions['signal_2'] = {
                                    'btc': btc_amount,
                                    'entry_price': price,
                                    'entry_date': date
                                }
                                position_history.add('signal_2')
                
                # 清除延迟信号
                delayed_signal_2 = None
            
            # 4. 检查入场信号（只在3-6分时入场）
            if in_target_zone:
                entry_signal = row['entry_signal']
                if pd.notna(entry_signal) and entry_signal:
                    signals = str(entry_signal).split(',')
                    
                    for signal_name in signals:
                        # 处理延迟信号
                        if signal_name == 'signal_2_delayed':
                            # 延迟信号，标记为第二天执行
                            if delayed_signal_2 is None and 'signal_2' not in current_positions:
                                delayed_signal_2 = (date, price)
                        elif signal_name not in current_positions:
                            # 检查渐进关系（基于历史仓位，而非当前持仓）
                            can_buy = True
                            if signal_name == 'signal_2':
                                # 第二仓需要第一仓曾经建立过
                                if 'signal_1' not in position_history:
                                    can_buy = False
                            elif signal_name == 'signal_3':
                                # 第三仓需要第二仓曾经建立过
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
                                            'reason': f'{signal_name}入场 (评分{total_score}分)',
                                            'score': total_score
                                        })
                                        
                                        cash -= buy_value
                                        btc_holdings += btc_amount
                                        current_positions[signal_name] = {
                                            'btc': btc_amount,
                                            'entry_price': price,
                                            'entry_date': date
                                        }
                                        position_history.add(signal_name)
            
            # 5. 评分保护：如果不在目标区间（<3分）且有持仓，则平仓
            if not in_target_zone and btc_holdings > 0:
                sell_value = btc_holdings * price
                total_cost = sum(pos['btc'] * pos['entry_price'] 
                               for pos in current_positions.values()) if current_positions else btc_holdings * price
                profit = sell_value - total_cost
                
                trades.append({
                    'date': date,
                    'action': 'EXIT_ZONE',
                    'price': price,
                    'btc_amount': btc_holdings,
                    'value': sell_value,
                    'profit': profit,
                    'reason': f"评分降至{total_score}分，退出持仓",
                    'score': total_score
                })
                
                cash += sell_value
                btc_holdings = 0.0
                current_positions = {}
                # 注意：不清空position_history，因为历史仓位记录应该保留
            
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
                'return': (total_value - self.initial_capital) / self.initial_capital * 100,
                'total_score': total_score,
                'in_target_zone': in_target_zone
            })
        
        portfolio_df = pd.DataFrame(portfolio_history)
        trades_df = pd.DataFrame(trades) if len(trades) > 0 else pd.DataFrame()
        
        self.show_backtest_results(portfolio_df, trades_df)
        
        return portfolio_df, trades_df
    
    def show_backtest_results(self, portfolio_df, trades_df):
        """显示回测结果"""
        print()
        print("=" * 100)
        print("📊 回测结果")
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
        
        in_target_days = portfolio_df['in_target_zone'].sum()
        has_position_days = (portfolio_df['btc_holdings'] > 0).sum()
        print(f"📊 时间分布:")
        print(f"  在3-6分区间: {in_target_days}天 ({in_target_days/len(portfolio_df)*100:.1f}%)")
        print(f"  实际持仓天数: {has_position_days}天 ({has_position_days/len(portfolio_df)*100:.1f}%)")
        print()
        
        if len(trades_df) > 0:
            print(f"📊 交易统计:")
            print(f"  总交易次数: {len(trades_df)}")
            
            buy_trades = trades_df[trades_df['action'].str.contains('BUY', na=False)]
            sell_trades = trades_df[trades_df['action'].str.contains('SELL_ALL', na=False)]
            stop_loss_trades = trades_df[trades_df['action'].str.contains('STOP_LOSS', na=False)]
            exit_zone_trades = trades_df[trades_df['action'].str.contains('EXIT_ZONE', na=False)]
            
            print(f"  买入次数: {len(buy_trades)}")
            print(f"  止盈次数: {len(sell_trades)}")
            print(f"  止损次数: {len(stop_loss_trades)}")
            print(f"  评分平仓: {len(exit_zone_trades)}")
            
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
    
    def save_results(self, portfolio_df, trades_df, output_folder='数字化数据'):
        """保存回测结果"""
        portfolio_df.to_csv(f'{output_folder}/final_backtest_portfolio.csv', 
                           index=False, encoding='utf-8-sig')
        if len(trades_df) > 0:
            trades_df.to_csv(f'{output_folder}/final_backtest_trades.csv', 
                            index=False, encoding='utf-8-sig')
        
        print(f"💾 回测结果已保存:")
        print(f"  • {output_folder}/final_backtest_portfolio.csv")
        if len(trades_df) > 0:
            print(f"  • {output_folder}/final_backtest_trades.csv")
        print()


if __name__ == "__main__":
    print("=" * 100)
    print("核心回测模块")
    print("=" * 100)
    print()
    print("功能特点:")
    print("  ✅ 渐进式仓位管理（5% → 25% → 40% → 30%）")
    print("  ✅ 单仓位止损（每次最大亏损$500）")
    print("  ✅ 技术指标止盈（WaveTrend死叉）")
    print("  ✅ 评分保护（评分降至2分以下强制平仓）")
    print()

