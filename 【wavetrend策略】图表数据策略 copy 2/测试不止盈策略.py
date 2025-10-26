#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
不止盈策略 - wt1<-40金叉入场，只设止损，不设止盈，让利润奔跑
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path

sys.path.append(str(Path(__file__).parent / '模块'))

from 数据模块 import DataModule

class NoTakeProfitStrategy:
    """不止盈策略 - 只止损，不止盈"""
    
    def __init__(self):
        self.rsi_period = 14
        self.wavetrend_period = 10
        self.adx_period = 14
    
    def calculate_indicators(self, df):
        """计算技术指标"""
        print("📊 计算技术指标...")
        df = df.copy()
        
        # WaveTrend
        n1 = 10  # Channel Length
        n2 = 21  # Average Length
        
        hlc3 = (df['high'] + df['low'] + df['close']) / 3
        esa = hlc3.ewm(span=n1, adjust=False).mean()
        d = (hlc3 - esa).abs().ewm(span=n1, adjust=False).mean()
        ci = (hlc3 - esa) / (0.015 * d)
        
        tci = ci.ewm(span=n2, adjust=False).mean()  # EMA - TradingView标准
        df['wt1'] = tci
        df['wt2'] = df['wt1'].rolling(window=4).mean()  # SMA
        
        print("✅ 技术指标计算完成")
        return df
    
    def generate_signals(self, df):
        """生成交易信号 - 只在wt1<-40时金叉入场，不设止盈"""
        print("🎯 生成交易信号...")
        df = df.copy()
        df['entry_signal'] = False
        df['entry_reason'] = ''
        
        for i in range(1, len(df)):
            # 入场信号：wt1 < -40 且发生金叉
            if not pd.isna(df.loc[i, 'wt1']) and not pd.isna(df.loc[i, 'wt2']):
                wt_golden_cross = (df.loc[i, 'wt1'] > df.loc[i, 'wt2']) and \
                                 (df.loc[i-1, 'wt1'] <= df.loc[i-1, 'wt2'])
                
                if wt_golden_cross and df.loc[i, 'wt1'] < -40:
                    df.loc[i, 'entry_signal'] = True
                    df.loc[i, 'entry_reason'] = f'WaveTrend金叉(wt1={df.loc[i, "wt1"]:.1f})'
        
        entry_count = df['entry_signal'].sum()
        print(f"✅ 信号生成完成：{entry_count}个入场信号（无止盈，只止损）")
        
        return df


class NoTakeProfitBacktest:
    """不止盈回测引擎"""
    
    def __init__(self, initial_capital=10000, position_size=0.95, max_loss_per_trade=0.10):
        self.initial_capital = initial_capital
        self.position_size = position_size  # 每次入场95%资金
        self.max_loss_per_trade = max_loss_per_trade  # 10%止损
    
    def run_backtest(self, df):
        """运行回测 - 无止盈，只止损"""
        print()
        print("=" * 100)
        print("🚀 不止盈策略回测（wt1<-40金叉入场 + 10%止损 + 无止盈）")
        print("=" * 100)
        print()
        
        cash = self.initial_capital
        btc_holdings = 0.0
        entry_price = 0.0
        entry_date = None
        
        portfolio_history = []
        trades = []
        
        for i in range(len(df)):
            row = df.iloc[i]
            date = row['date']
            price = row['close']
            
            position_value = btc_holdings * price
            total_value = cash + position_value
            
            # 检查止损（唯一的出场条件）
            if btc_holdings > 0 and entry_price > 0:
                loss_pct = (entry_price - price) / entry_price
                if loss_pct >= self.max_loss_per_trade:
                    # 止损
                    sell_value = btc_holdings * price
                    profit = sell_value - (btc_holdings * entry_price)
                    hold_days = (pd.to_datetime(date) - pd.to_datetime(entry_date)).days
                    
                    trades.append({
                        'entry_date': entry_date,
                        'exit_date': date,
                        'entry_price': entry_price,
                        'exit_price': price,
                        'btc_amount': btc_holdings,
                        'entry_value': btc_holdings * entry_price,
                        'exit_value': sell_value,
                        'profit': profit,
                        'profit_pct': profit / (btc_holdings * entry_price) * 100,
                        'hold_days': hold_days,
                        'exit_reason': f'止损：亏损{loss_pct*100:.1f}%'
                    })
                    
                    cash += sell_value
                    btc_holdings = 0.0
                    entry_price = 0.0
                    entry_date = None
            
            # 检查入场信号
            if row['entry_signal'] and btc_holdings == 0:
                buy_value = total_value * self.position_size
                if buy_value > 0 and cash >= buy_value:
                    btc_amount = buy_value / price
                    
                    cash -= buy_value
                    btc_holdings += btc_amount
                    entry_price = price
                    entry_date = date
                    
                    print(f"📥 {date}: 买入 @ ${price:,.2f}, 金额 ${buy_value:,.2f}")
            
            # 记录投资组合
            position_value = btc_holdings * price
            total_value = cash + position_value
            
            # 如果有持仓，计算浮动盈亏
            unrealized_profit = 0
            unrealized_profit_pct = 0
            if btc_holdings > 0 and entry_price > 0:
                unrealized_profit = position_value - (btc_holdings * entry_price)
                unrealized_profit_pct = unrealized_profit / (btc_holdings * entry_price) * 100
            
            portfolio_history.append({
                'date': date,
                'price': price,
                'cash': cash,
                'btc_holdings': btc_holdings,
                'position_value': position_value,
                'total_value': total_value,
                'return': (total_value - self.initial_capital) / self.initial_capital * 100,
                'unrealized_profit': unrealized_profit,
                'unrealized_profit_pct': unrealized_profit_pct
            })
        
        # 如果最后还有持仓，计算最终盈亏（未平仓）
        if btc_holdings > 0:
            final_price = df.iloc[-1]['close']
            final_value = btc_holdings * final_price
            final_profit = final_value - (btc_holdings * entry_price)
            hold_days = (pd.to_datetime(df.iloc[-1]['date']) - pd.to_datetime(entry_date)).days
            
            print()
            print("⚠️  最终仍持有仓位（未平仓）:")
            print(f"   入场日期: {entry_date}")
            print(f"   入场价格: ${entry_price:,.2f}")
            print(f"   当前价格: ${final_price:,.2f}")
            print(f"   持有BTC: {btc_holdings:.8f}")
            print(f"   持有天数: {hold_days}天")
            print(f"   浮动盈亏: ${final_profit:,.2f} ({final_profit/(btc_holdings*entry_price)*100:+.2f}%)")
        
        portfolio_df = pd.DataFrame(portfolio_history)
        trades_df = pd.DataFrame(trades) if len(trades) > 0 else pd.DataFrame()
        
        self.show_results(portfolio_df, trades_df, btc_holdings > 0)
        
        return portfolio_df, trades_df
    
    def show_results(self, portfolio_df, trades_df, has_open_position):
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
        
        has_position_days = (portfolio_df['btc_holdings'] > 0).sum()
        print(f"📊 持仓天数: {has_position_days}天 ({has_position_days/len(portfolio_df)*100:.1f}%)")
        
        if has_open_position:
            final_unrealized = portfolio_df.iloc[-1]['unrealized_profit']
            final_unrealized_pct = portfolio_df.iloc[-1]['unrealized_profit_pct']
            print(f"📊 当前未实现盈亏: ${final_unrealized:,.2f} ({final_unrealized_pct:+.2f}%)")
        
        print()
        
        if len(trades_df) > 0:
            print(f"📊 交易统计（已平仓）:")
            print(f"  总交易次数: {len(trades_df)}")
            
            if len(trades_df) > 0:
                profit_trades = trades_df[trades_df['profit'] > 0]
                loss_trades = trades_df[trades_df['profit'] < 0]
                
                realized_pnl = trades_df['profit'].sum()
                print(f"  已实现盈亏: ${realized_pnl:,.2f}")
                
                if len(profit_trades) > 0:
                    print(f"\n  💰 盈利交易: {len(profit_trades)}次")
                    print(f"     总盈利: ${profit_trades['profit'].sum():,.2f}")
                    print(f"     平均盈利: ${profit_trades['profit'].mean():,.2f} ({profit_trades['profit_pct'].mean():.2f}%)")
                    print(f"     最大盈利: ${profit_trades['profit'].max():,.2f} ({profit_trades['profit_pct'].max():.2f}%)")
                    print(f"     平均持有: {profit_trades['hold_days'].mean():.0f}天")
                
                if len(loss_trades) > 0:
                    print(f"\n  📉 亏损交易: {len(loss_trades)}次")
                    print(f"     总亏损: ${loss_trades['profit'].sum():,.2f}")
                    print(f"     平均亏损: ${loss_trades['profit'].mean():,.2f} ({loss_trades['profit_pct'].mean():.2f}%)")
                    print(f"     最大亏损: ${loss_trades['profit'].min():,.2f} ({loss_trades['profit_pct'].min():.2f}%)")
                    print(f"     平均持有: {loss_trades['hold_days'].mean():.0f}天")
                
                if len(profit_trades) > 0 and len(loss_trades) > 0:
                    win_rate = len(profit_trades) / len(trades_df) * 100
                    print(f"\n  🎯 胜率: {win_rate:.2f}%")
        
        print()
        print("=" * 100)


def main():
    print("=" * 100)
    print("🎯 不止盈策略测试（wt1<-40金叉入场，只止损不止盈）")
    print("=" * 100)
    print()
    
    # 1. 加载数据
    print("【步骤1】加载数据...")
    data_module = DataModule()
    price_data = data_module.get_price_data()
    print()
    
    # 2. 计算技术指标
    print("【步骤2】计算技术指标...")
    strategy = NoTakeProfitStrategy()
    df_with_indicators = strategy.calculate_indicators(price_data)
    print()
    
    # 3. 生成交易信号
    print("【步骤3】生成交易信号...")
    df_with_signals = strategy.generate_signals(df_with_indicators)
    print()
    
    # 4. 运行回测
    print("【步骤4】运行回测...")
    backtest = NoTakeProfitBacktest(initial_capital=10000, position_size=0.95, max_loss_per_trade=0.10)
    portfolio_df, trades_df = backtest.run_backtest(df_with_signals)
    
    # 5. 对比买入持有
    print("【步骤5】对比买入持有...")
    print("-" * 100)
    start_price = price_data.iloc[0]['close']
    end_price = price_data.iloc[-1]['close']
    hold_return = (end_price / start_price - 1) * 100
    strategy_return = (portfolio_df['total_value'].iloc[-1] / 10000 - 1) * 100
    
    print(f"\n📊 最终对比:")
    print(f"  买入持有: {hold_return:.2f}%")
    print(f"  不止盈策略: {strategy_return:.2f}%")
    print(f"  差距: {(strategy_return - hold_return):.2f}%")
    
    if strategy_return > hold_return:
        print(f"\n✅ 策略跑赢买入持有 {(strategy_return - hold_return):.2f}%！")
    else:
        gap = hold_return - strategy_return
        print(f"\n⚠️  策略跑输买入持有 {gap:.2f}%")
        if gap < 100:
            print(f"    但表现不错，差距可接受")
    
    print()
    
    # 6. 保存结果
    portfolio_df.to_csv('数字化数据/no_take_profit_portfolio.csv', index=False, encoding='utf-8-sig')
    if len(trades_df) > 0:
        trades_df.to_csv('数字化数据/no_take_profit_trades.csv', index=False, encoding='utf-8-sig')
    
    print("✅ 结果已保存:")
    print("  • 数字化数据/no_take_profit_portfolio.csv")
    print("  • 数字化数据/no_take_profit_trades.csv")
    print()
    
    # 显示已平仓交易
    if len(trades_df) > 0:
        print("\n📋 已平仓交易记录:")
        print(trades_df[['entry_date', 'exit_date', 'entry_price', 'exit_price', 'profit_pct', 'hold_days', 'exit_reason']].to_string(index=False))
    
    print()
    print("=" * 100)


if __name__ == "__main__":
    main()

