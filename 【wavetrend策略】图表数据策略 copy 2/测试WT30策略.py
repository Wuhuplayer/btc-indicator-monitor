#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于 wt1 < -30 的交易策略
测试不同的组合条件
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path

sys.path.append(str(Path(__file__).parent / '模块'))
from 数据模块 import DataModule


def calculate_indicators(df):
    """计算所有指标"""
    print("📊 计算指标...")
    df = df.copy()
    
    # WaveTrend
    n1, n2 = 10, 21
    hlc3 = (df['high'] + df['low'] + df['close']) / 3
    esa = hlc3.ewm(span=n1, adjust=False).mean()
    d = (hlc3 - esa).abs().ewm(span=n1, adjust=False).mean()
    ci = (hlc3 - esa) / (0.015 * d)
    
    wt1 = ci.ewm(span=n2, adjust=False).mean()  # EMA - TradingView标准
    wt2 = wt1.rolling(window=4).mean()  # SMA
    
    df['wt1'] = wt1
    df['wt2'] = wt2
    
    # 动量
    returns_20d = df['close'].pct_change(20)
    df['momentum'] = (returns_20d - returns_20d.mean()) / returns_20d.std()
    
    # ADX
    period = 14
    high_diff = df['high'].diff()
    low_diff = -df['low'].diff()
    
    plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
    minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)
    
    tr1 = df['high'] - df['low']
    tr2 = abs(df['high'] - df['close'].shift())
    tr3 = abs(df['low'] - df['close'].shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    atr = tr.rolling(window=period).mean()
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    df['adx'] = dx.rolling(window=period).mean()
    
    print("✅ 指标计算完成")
    return df


class WT30Strategy:
    """wt1 < -30 策略"""
    
    def __init__(self, initial_capital=10000, position_size=0.95, stop_loss=0.10):
        self.initial_capital = initial_capital
        self.position_size = position_size
        self.stop_loss = stop_loss
    
    def strategy_simple(self, df):
        """策略1: 简单 wt1<-30 金叉"""
        df = df.copy()
        df['signal'] = 0
        
        for i in range(1, len(df)):
            # 买入: wt1 < -30 且金叉
            if df.loc[i, 'wt1'] < -30:
                golden_cross = (df.loc[i, 'wt1'] > df.loc[i, 'wt2']) and \
                              (df.loc[i-1, 'wt1'] <= df.loc[i-1, 'wt2'])
                if golden_cross:
                    df.loc[i, 'signal'] = 1
            
            # 卖出: ADX>20 且 wt1>0 且死叉
            if df.loc[i, 'adx'] > 20 and df.loc[i, 'wt1'] > 0:
                death_cross = (df.loc[i, 'wt1'] < df.loc[i, 'wt2']) and \
                             (df.loc[i-1, 'wt1'] >= df.loc[i-1, 'wt2'])
                if death_cross:
                    df.loc[i, 'signal'] = -1
        
        return df
    
    def strategy_momentum_filter(self, df):
        """策略2: wt1<-30 金叉 + 动量过滤"""
        df = df.copy()
        df['signal'] = 0
        
        for i in range(1, len(df)):
            # 买入: wt1 < -30 且金叉 且动量不太负
            if df.loc[i, 'wt1'] < -30:
                golden_cross = (df.loc[i, 'wt1'] > df.loc[i, 'wt2']) and \
                              (df.loc[i-1, 'wt1'] <= df.loc[i-1, 'wt2'])
                momentum_ok = df.loc[i, 'momentum'] > -0.5  # 不要在强烈下跌中买入
                
                if golden_cross and momentum_ok:
                    df.loc[i, 'signal'] = 1
            
            # 卖出: ADX>20 且 wt1>0 且死叉，或动量转负
            if df.loc[i, 'adx'] > 20 and df.loc[i, 'wt1'] > 0:
                death_cross = (df.loc[i, 'wt1'] < df.loc[i, 'wt2']) and \
                             (df.loc[i-1, 'wt1'] >= df.loc[i-1, 'wt2'])
                if death_cross:
                    df.loc[i, 'signal'] = -1
            
            # 动量转负也卖出
            if df.loc[i, 'momentum'] < -0.5:
                df.loc[i, 'signal'] = -1
        
        return df
    
    def strategy_no_take_profit(self, df):
        """策略3: wt1<-30 金叉，只止损不止盈"""
        df = df.copy()
        df['signal'] = 0
        
        for i in range(1, len(df)):
            # 买入: wt1 < -30 且金叉
            if df.loc[i, 'wt1'] < -30:
                golden_cross = (df.loc[i, 'wt1'] > df.loc[i, 'wt2']) and \
                              (df.loc[i-1, 'wt1'] <= df.loc[i-1, 'wt2'])
                if golden_cross:
                    df.loc[i, 'signal'] = 1
        
        # 不设止盈，只在回测中用止损
        return df
    
    def run_backtest(self, df, strategy_name):
        """运行回测"""
        cash = self.initial_capital
        btc_holdings = 0
        entry_price = 0
        
        trades = []
        portfolio_history = []
        
        for i in range(len(df)):
            row = df.iloc[i]
            date = row['date']
            price = row['close']
            signal = row['signal']
            
            position_value = btc_holdings * price
            total_value = cash + position_value
            
            # 止损检查
            if btc_holdings > 0 and entry_price > 0:
                loss_pct = (entry_price - price) / entry_price
                if loss_pct >= self.stop_loss:
                    # 止损
                    sell_value = btc_holdings * price
                    profit = sell_value - (btc_holdings * entry_price)
                    
                    trades.append({
                        'date': date,
                        'action': 'STOP_LOSS',
                        'price': price,
                        'profit': profit,
                        'profit_pct': (profit / (btc_holdings * entry_price)) * 100
                    })
                    
                    cash += sell_value
                    btc_holdings = 0
                    entry_price = 0
            
            # 买入信号
            if signal == 1 and btc_holdings == 0 and cash > 0:
                buy_value = total_value * self.position_size
                btc_holdings = buy_value / price
                cash = total_value - buy_value
                entry_price = price
                
                trades.append({
                    'date': date,
                    'action': 'BUY',
                    'price': price,
                    'profit': 0,
                    'profit_pct': 0
                })
            
            # 卖出信号
            elif signal == -1 and btc_holdings > 0:
                sell_value = btc_holdings * price
                profit = sell_value - (btc_holdings * entry_price)
                
                trades.append({
                    'date': date,
                    'action': 'SELL',
                    'price': price,
                    'profit': profit,
                    'profit_pct': (profit / (btc_holdings * entry_price)) * 100
                })
                
                cash += sell_value
                btc_holdings = 0
                entry_price = 0
            
            # 记录组合
            position_value = btc_holdings * price
            total_value = cash + position_value
            
            portfolio_history.append({
                'date': date,
                'price': price,
                'total_value': total_value,
                'btc_holdings': btc_holdings
            })
        
        # 如果最后还有持仓
        if btc_holdings > 0:
            final_price = df.iloc[-1]['close']
            final_value = btc_holdings * final_price
            profit = final_value - (btc_holdings * entry_price)
            print(f"\n⚠️  最终持仓: {btc_holdings:.8f} BTC @ ${final_price:,.2f}")
            print(f"   浮动盈亏: ${profit:,.2f} ({(profit/(btc_holdings*entry_price)*100):+.2f}%)")
        
        portfolio_df = pd.DataFrame(portfolio_history)
        trades_df = pd.DataFrame(trades) if len(trades) > 0 else pd.DataFrame()
        
        # 计算指标
        final_value = portfolio_df['total_value'].iloc[-1]
        total_return = (final_value - self.initial_capital) / self.initial_capital * 100
        
        portfolio_df['peak'] = portfolio_df['total_value'].cummax()
        portfolio_df['drawdown'] = (portfolio_df['total_value'] - portfolio_df['peak']) / portfolio_df['peak'] * 100
        max_drawdown = portfolio_df['drawdown'].min()
        
        has_position_days = (portfolio_df['btc_holdings'] > 0).sum()
        
        # 交易统计
        if len(trades_df) > 0:
            completed = trades_df[trades_df['action'].isin(['SELL', 'STOP_LOSS'])]
            num_trades = len(completed)
            if num_trades > 0:
                profit_trades = completed[completed['profit'] > 0]
                win_rate = len(profit_trades) / num_trades * 100
            else:
                win_rate = 0
        else:
            num_trades = 0
            win_rate = 0
        
        print()
        print(f"📊 {strategy_name} - 结果")
        print("-" * 80)
        print(f"  💰 最终价值: ${final_value:,.2f}")
        print(f"  📈 总收益率: {total_return:+.2f}%")
        print(f"  📉 最大回撤: {max_drawdown:.2f}%")
        print(f"  📊 持仓天数: {has_position_days}天 ({has_position_days/len(portfolio_df)*100:.1f}%)")
        print(f"  🔄 交易次数: {num_trades}次")
        if num_trades > 0:
            print(f"  🎯 胜率: {win_rate:.1f}%")
        
        return {
            'strategy': strategy_name,
            'return': total_return,
            'max_drawdown': max_drawdown,
            'trades': num_trades,
            'win_rate': win_rate,
            'hold_days': has_position_days
        }


def main():
    print("=" * 100)
    print("🎯 wt1 < -30 策略对比测试")
    print("=" * 100)
    print()
    
    # 加载数据
    print("【步骤1】加载数据...")
    data_module = DataModule()
    price_data = data_module.get_price_data()
    print()
    
    # 计算指标
    print("【步骤2】计算指标...")
    df = calculate_indicators(price_data)
    print()
    
    # 测试三个策略
    print("【步骤3】测试策略...")
    strategy = WT30Strategy(initial_capital=10000, position_size=0.95, stop_loss=0.10)
    
    results = []
    
    # 策略1: 简单金叉
    print("\n" + "="*100)
    print("📊 策略1: 简单 wt1<-30 金叉 + 止盈止损")
    print("="*100)
    df1 = strategy.strategy_simple(df)
    result1 = strategy.run_backtest(df1, "策略1: 简单金叉")
    results.append(result1)
    
    # 策略2: 动量过滤
    print("\n" + "="*100)
    print("📊 策略2: wt1<-30 金叉 + 动量过滤 (避免强下跌)")
    print("="*100)
    df2 = strategy.strategy_momentum_filter(df)
    result2 = strategy.run_backtest(df2, "策略2: 动量过滤")
    results.append(result2)
    
    # 策略3: 不止盈
    print("\n" + "="*100)
    print("📊 策略3: wt1<-30 金叉，只止损不止盈")
    print("="*100)
    df3 = strategy.strategy_no_take_profit(df)
    result3 = strategy.run_backtest(df3, "策略3: 不止盈")
    results.append(result3)
    
    # 对比
    print()
    print("=" * 100)
    print("📊 策略对比")
    print("=" * 100)
    print()
    
    start_price = price_data.iloc[0]['close']
    end_price = price_data.iloc[-1]['close']
    hold_return = (end_price / start_price - 1) * 100
    
    print(f"{'策略':<30} {'收益率':<15} {'最大回撤':<15} {'交易次数':<12} {'胜率':<10}")
    print("-" * 100)
    print(f"{'买入持有':<30} {hold_return:+.2f}%         {'-81.00%':<15} {'0':<12} {'N/A':<10}")
    
    for r in results:
        win_rate_str = f"{r['win_rate']:.1f}%" if r['trades'] > 0 else "N/A"
        print(f"{r['strategy']:<30} {r['return']:+.2f}%         {r['max_drawdown']:.2f}%         {r['trades']:<12} {win_rate_str:<10}")
    
    # 找出最佳
    best = max(results, key=lambda x: x['return'])
    print()
    print(f"🏆 最佳策略: {best['strategy']}")
    print(f"   收益: {best['return']:+.2f}%")
    print(f"   回撤: {best['max_drawdown']:.2f}%")
    
    print()
    print("=" * 100)


if __name__ == "__main__":
    main()

