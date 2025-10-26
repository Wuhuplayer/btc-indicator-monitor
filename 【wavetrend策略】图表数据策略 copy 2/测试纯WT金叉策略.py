#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
纯WaveTrend金叉策略 - 只在wt1<-40时金叉入场
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path

sys.path.append(str(Path(__file__).parent / '模块'))

from 数据模块 import DataModule

class SimpleWaveTrendStrategy:
    """简单WaveTrend金叉策略"""
    
    def __init__(self):
        self.rsi_period = 14
        self.wavetrend_period = 10
        self.adx_period = 14
    
    def calculate_indicators(self, df):
        """计算技术指标"""
        print("📊 计算技术指标...")
        df = df.copy()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
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
        
        # ADX
        high_diff = df['high'].diff()
        low_diff = -df['low'].diff()
        
        plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
        minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)
        
        tr1 = df['high'] - df['low']
        tr2 = abs(df['high'] - df['close'].shift())
        tr3 = abs(df['low'] - df['close'].shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        atr = tr.rolling(window=self.adx_period).mean()
        plus_di = 100 * (plus_dm.rolling(window=self.adx_period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=self.adx_period).mean() / atr)
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        df['adx'] = dx.rolling(window=self.adx_period).mean()
        
        print("✅ 技术指标计算完成")
        return df
    
    def generate_signals(self, df):
        """生成交易信号 - 只在wt1<-40时金叉入场"""
        print("🎯 生成交易信号...")
        df = df.copy()
        df['entry_signal'] = False
        df['exit_signal'] = False
        df['entry_reason'] = ''
        df['exit_reason'] = ''
        
        for i in range(1, len(df)):
            # 入场信号：wt1 < -40 且发生金叉
            if not pd.isna(df.loc[i, 'wt1']) and not pd.isna(df.loc[i, 'wt2']):
                wt_golden_cross = (df.loc[i, 'wt1'] > df.loc[i, 'wt2']) and \
                                 (df.loc[i-1, 'wt1'] <= df.loc[i-1, 'wt2'])
                
                if wt_golden_cross and df.loc[i, 'wt1'] < -40:
                    df.loc[i, 'entry_signal'] = True
                    df.loc[i, 'entry_reason'] = f'WaveTrend金叉(wt1={df.loc[i, "wt1"]:.1f})'
            
            # 出场信号：ADX>20 且 wt1>0 且死叉
            if not pd.isna(df.loc[i, 'adx']) and not pd.isna(df.loc[i, 'wt1']):
                if df.loc[i, 'adx'] > 20 and df.loc[i, 'wt1'] > 0:
                    wt_death_cross = (df.loc[i, 'wt1'] < df.loc[i, 'wt2']) and \
                                    (df.loc[i-1, 'wt1'] >= df.loc[i-1, 'wt2'])
                    
                    if wt_death_cross:
                        df.loc[i, 'exit_signal'] = True
                        df.loc[i, 'exit_reason'] = 'ADX>20且WaveTrend死叉'
        
        entry_count = df['entry_signal'].sum()
        exit_count = df['exit_signal'].sum()
        print(f"✅ 信号生成完成：{entry_count}个入场信号，{exit_count}个出场信号")
        
        return df


class SimpleBacktest:
    """简单回测引擎"""
    
    def __init__(self, initial_capital=10000, position_size=0.95, max_loss_per_trade=0.10):
        self.initial_capital = initial_capital
        self.position_size = position_size  # 每次入场95%资金
        self.max_loss_per_trade = max_loss_per_trade  # 10%止损
    
    def run_backtest(self, df):
        """运行回测"""
        print()
        print("=" * 100)
        print("🚀 纯WaveTrend金叉策略回测（wt1<-40金叉入场）")
        print("=" * 100)
        print()
        
        cash = self.initial_capital
        btc_holdings = 0.0
        entry_price = 0.0
        
        portfolio_history = []
        trades = []
        
        for i in range(len(df)):
            row = df.iloc[i]
            date = row['date']
            price = row['close']
            
            position_value = btc_holdings * price
            total_value = cash + position_value
            
            # 检查止损
            if btc_holdings > 0 and entry_price > 0:
                loss_pct = (entry_price - price) / entry_price
                if loss_pct >= self.max_loss_per_trade:
                    # 止损
                    sell_value = btc_holdings * price
                    profit = sell_value - (btc_holdings * entry_price)
                    
                    trades.append({
                        'date': date,
                        'action': 'STOP_LOSS',
                        'price': price,
                        'btc_amount': btc_holdings,
                        'value': sell_value,
                        'profit': profit,
                        'profit_pct': profit / (btc_holdings * entry_price) * 100,
                        'reason': f'止损：亏损{loss_pct*100:.1f}%'
                    })
                    
                    cash += sell_value
                    btc_holdings = 0.0
                    entry_price = 0.0
            
            # 检查出场信号
            if row['exit_signal'] and btc_holdings > 0:
                sell_value = btc_holdings * price
                profit = sell_value - (btc_holdings * entry_price)
                
                trades.append({
                    'date': date,
                    'action': 'SELL',
                    'price': price,
                    'btc_amount': btc_holdings,
                    'value': sell_value,
                    'profit': profit,
                    'profit_pct': profit / (btc_holdings * entry_price) * 100,
                    'reason': row['exit_reason']
                })
                
                cash += sell_value
                btc_holdings = 0.0
                entry_price = 0.0
            
            # 检查入场信号
            if row['entry_signal'] and btc_holdings == 0:
                buy_value = total_value * self.position_size
                if buy_value > 0 and cash >= buy_value:
                    btc_amount = buy_value / price
                    
                    trades.append({
                        'date': date,
                        'action': 'BUY',
                        'price': price,
                        'btc_amount': btc_amount,
                        'value': buy_value,
                        'profit': 0,
                        'profit_pct': 0,
                        'reason': row['entry_reason']
                    })
                    
                    cash -= buy_value
                    btc_holdings += btc_amount
                    entry_price = price
            
            # 记录投资组合
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
        print()
        
        if len(trades_df) > 0:
            print(f"📊 交易统计:")
            print(f"  总交易次数: {len(trades_df)}")
            
            buy_trades = trades_df[trades_df['action'] == 'BUY']
            sell_trades = trades_df[trades_df['action'] == 'SELL']
            stop_loss_trades = trades_df[trades_df['action'] == 'STOP_LOSS']
            
            print(f"  买入次数: {len(buy_trades)}")
            print(f"  止盈次数: {len(sell_trades)}")
            print(f"  止损次数: {len(stop_loss_trades)}")
            
            completed_trades = trades_df[trades_df['action'].isin(['SELL', 'STOP_LOSS'])]
            if len(completed_trades) > 0:
                profit_trades = completed_trades[completed_trades['profit'] > 0]
                loss_trades = completed_trades[completed_trades['profit'] < 0]
                
                if len(profit_trades) > 0:
                    print(f"\n  💰 盈利交易: {len(profit_trades)}次")
                    print(f"     总盈利: ${profit_trades['profit'].sum():,.2f}")
                    print(f"     平均盈利: ${profit_trades['profit'].mean():,.2f} ({profit_trades['profit_pct'].mean():.2f}%)")
                    print(f"     最大盈利: ${profit_trades['profit'].max():,.2f} ({profit_trades['profit_pct'].max():.2f}%)")
                
                if len(loss_trades) > 0:
                    print(f"\n  📉 亏损交易: {len(loss_trades)}次")
                    print(f"     总亏损: ${loss_trades['profit'].sum():,.2f}")
                    print(f"     平均亏损: ${loss_trades['profit'].mean():,.2f} ({loss_trades['profit_pct'].mean():.2f}%)")
                    print(f"     最大亏损: ${loss_trades['profit'].min():,.2f} ({loss_trades['profit_pct'].min():.2f}%)")
                
                win_rate = len(profit_trades) / len(completed_trades) * 100
                print(f"\n  🎯 胜率: {win_rate:.2f}%")
                
                avg_profit = profit_trades['profit'].mean() if len(profit_trades) > 0 else 0
                avg_loss = abs(loss_trades['profit'].mean()) if len(loss_trades) > 0 else 1
                profit_factor = avg_profit / avg_loss if avg_loss > 0 else 0
                print(f"  📊 盈亏比: {profit_factor:.2f}")
        
        print()
        print("=" * 100)


def main():
    print("=" * 100)
    print("🎯 纯WaveTrend金叉策略测试（wt1<-40时金叉入场）")
    print("=" * 100)
    print()
    
    # 1. 加载数据
    print("【步骤1】加载数据...")
    data_module = DataModule()
    price_data = data_module.get_price_data()
    print()
    
    # 2. 计算技术指标
    print("【步骤2】计算技术指标...")
    strategy = SimpleWaveTrendStrategy()
    df_with_indicators = strategy.calculate_indicators(price_data)
    print()
    
    # 3. 生成交易信号
    print("【步骤3】生成交易信号...")
    df_with_signals = strategy.generate_signals(df_with_indicators)
    print()
    
    # 4. 运行回测
    print("【步骤4】运行回测...")
    backtest = SimpleBacktest(initial_capital=10000, position_size=0.95, max_loss_per_trade=0.10)
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
    print(f"  WaveTrend策略: {strategy_return:.2f}%")
    print(f"  差距: {(strategy_return - hold_return):.2f}%")
    
    if strategy_return > hold_return:
        print(f"\n✅ 策略跑赢买入持有 {(strategy_return - hold_return):.2f}%！")
    else:
        print(f"\n⚠️  策略跑输买入持有 {(hold_return - strategy_return):.2f}%")
    
    print()
    
    # 6. 保存结果
    portfolio_df.to_csv('数字化数据/wt_golden_cross_portfolio.csv', index=False, encoding='utf-8-sig')
    if len(trades_df) > 0:
        trades_df.to_csv('数字化数据/wt_golden_cross_trades.csv', index=False, encoding='utf-8-sig')
    
    print("✅ 结果已保存:")
    print("  • 数字化数据/wt_golden_cross_portfolio.csv")
    print("  • 数字化数据/wt_golden_cross_trades.csv")
    print()
    
    # 显示前几笔交易
    if len(trades_df) > 0:
        print("\n📋 前10笔交易:")
        print(trades_df.head(10).to_string(index=False))
    
    print()
    print("=" * 100)


if __name__ == "__main__":
    main()

