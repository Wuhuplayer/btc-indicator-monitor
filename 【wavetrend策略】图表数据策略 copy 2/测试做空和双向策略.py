#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试做空策略和双向交易策略
看能否超越买入持有的收益率
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path

sys.path.append(str(Path(__file__).parent / '模块'))
from 数据模块 import DataModule


def calculate_indicators(df):
    """计算指标"""
    df = df.copy()
    
    # WaveTrend
    n1, n2 = 10, 21
    hlc3 = (df['high'] + df['low'] + df['close']) / 3
    esa = hlc3.ewm(span=n1, adjust=False).mean()
    d = (hlc3 - esa).abs().ewm(span=n1, adjust=False).mean()
    ci = (hlc3 - esa) / (0.015 * d)
    
    df['wt1'] = ci.ewm(span=n2, adjust=False).mean()
    df['wt2'] = df['wt1'].rolling(window=4).mean()
    
    # 动量
    mom_20d = df['close'].pct_change(20)
    df['momentum'] = (mom_20d - mom_20d.mean()) / mom_20d.std()
    
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
    
    return df


def strategy_short_only(df):
    """
    策略1: 纯做空
    做空: wt1 > 50 且死叉 且 动量 < 0.5
    平空: wt1 < -30 且金叉
    """
    df = df.copy()
    df['signal'] = 0  # 0=空仓, 1=做多, -1=做空
    
    for i in range(1, len(df)):
        # 死叉
        death_cross = (df.loc[i, 'wt1'] < df.loc[i, 'wt2']) and \
                     (df.loc[i-1, 'wt1'] >= df.loc[i-1, 'wt2'])
        
        # 金叉
        golden_cross = (df.loc[i, 'wt1'] > df.loc[i, 'wt2']) and \
                      (df.loc[i-1, 'wt1'] <= df.loc[i-1, 'wt2'])
        
        # 做空信号
        if (df.loc[i, 'wt1'] > 50 and 
            death_cross and 
            df.loc[i, 'momentum'] < 0.5):
            df.loc[i, 'signal'] = -1
        
        # 平空信号
        elif (df.loc[i, 'wt1'] < -30 and 
              golden_cross):
            df.loc[i, 'signal'] = 1  # 平空（回到空仓）
    
    return df


def strategy_long_short(df):
    """
    策略2: 双向交易
    做多: wt1 < -50 且金叉 且 动量 > -0.5
    做空: wt1 > 50 且死叉 且 动量 < 0.5
    """
    df = df.copy()
    df['signal'] = 0  # 0=空仓, 1=做多, -1=做空
    
    for i in range(1, len(df)):
        death_cross = (df.loc[i, 'wt1'] < df.loc[i, 'wt2']) and \
                     (df.loc[i-1, 'wt1'] >= df.loc[i-1, 'wt2'])
        
        golden_cross = (df.loc[i, 'wt1'] > df.loc[i, 'wt2']) and \
                      (df.loc[i-1, 'wt1'] <= df.loc[i-1, 'wt2'])
        
        # 做多信号
        if (df.loc[i, 'wt1'] < -50 and 
            golden_cross and 
            df.loc[i, 'momentum'] > -0.5):
            df.loc[i, 'signal'] = 1
        
        # 做空信号
        elif (df.loc[i, 'wt1'] > 50 and 
              death_cross and 
              df.loc[i, 'momentum'] < 0.5):
            df.loc[i, 'signal'] = -1
        
        # 平仓信号（回到空仓）
        elif (df.loc[i, 'wt1'] > -30 and df.loc[i, 'wt1'] < 30):
            df.loc[i, 'signal'] = 0
    
    return df


def strategy_enhanced_long(df):
    """
    策略3: 增强做多（尝试超越买入持有）
    分批建仓 + 金字塔加仓
    """
    df = df.copy()
    df['signal'] = 0
    df['signal_strength'] = 0  # 0-3表示仓位等级
    
    for i in range(1, len(df)):
        golden_cross = (df.loc[i, 'wt1'] > df.loc[i, 'wt2']) and \
                      (df.loc[i-1, 'wt1'] <= df.loc[i-1, 'wt2'])
        
        # 三档买入信号
        if df.loc[i, 'wt1'] < -60 and golden_cross and df.loc[i, 'momentum'] > -0.5:
            df.loc[i, 'signal'] = 1
            df.loc[i, 'signal_strength'] = 3  # 强买入（50%仓位）
        elif df.loc[i, 'wt1'] < -50 and golden_cross and df.loc[i, 'momentum'] > -0.5:
            df.loc[i, 'signal'] = 1
            df.loc[i, 'signal_strength'] = 2  # 中等买入（30%仓位）
        elif df.loc[i, 'wt1'] < -40 and golden_cross and df.loc[i, 'momentum'] > -0.3:
            df.loc[i, 'signal'] = 1
            df.loc[i, 'signal_strength'] = 1  # 轻度买入（20%仓位）
    
    return df


def backtest_short(df, strategy_name):
    """做空回测"""
    print(f"\n{'='*80}")
    print(f"🔴 {strategy_name}")
    print('='*80)
    
    initial = 10000
    cash = initial
    short_btc = 0  # 做空的BTC数量
    short_entry_price = 0
    
    trades = []
    portfolio = []
    
    for i in range(len(df)):
        row = df.iloc[i]
        price = row['close']
        signal = row['signal']
        
        # 做空的市值计算
        if short_btc > 0:
            # 做空亏损 = (当前价 - 开仓价) × 数量
            unrealized_pnl = (short_entry_price - price) * short_btc
            total_value = cash + unrealized_pnl
        else:
            total_value = cash
        
        # 平空信号
        if signal == 1 and short_btc > 0:
            # 平空
            pnl = (short_entry_price - price) * short_btc
            trades.append({
                'date': row['date'],
                'action': 'COVER',
                'price': price,
                'pnl': pnl
            })
            cash += pnl
            short_btc = 0
            short_entry_price = 0
        
        # 做空信号
        elif signal == -1 and short_btc == 0:
            # 做空（借入BTC卖出）
            short_value = total_value * 0.95
            short_btc = short_value / price
            short_entry_price = price
            
            trades.append({
                'date': row['date'],
                'action': 'SHORT',
                'price': price,
                'pnl': 0
            })
        
        # 止损（做空亏损超过10%）
        if short_btc > 0 and price > short_entry_price * 1.10:
            pnl = (short_entry_price - price) * short_btc
            trades.append({
                'date': row['date'],
                'action': 'STOP_LOSS',
                'price': price,
                'pnl': pnl
            })
            cash += pnl
            short_btc = 0
            short_entry_price = 0
        
        # 记录
        if short_btc > 0:
            unrealized_pnl = (short_entry_price - price) * short_btc
            total_value = cash + unrealized_pnl
        else:
            total_value = cash
        
        portfolio.append({'date': row['date'], 'total_value': total_value})
    
    portfolio_df = pd.DataFrame(portfolio)
    trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()
    
    final = portfolio_df['total_value'].iloc[-1]
    ret = (final - initial) / initial * 100
    
    portfolio_df['peak'] = portfolio_df['total_value'].cummax()
    portfolio_df['dd'] = (portfolio_df['total_value'] - portfolio_df['peak']) / portfolio_df['peak'] * 100
    max_dd = portfolio_df['dd'].min()
    
    print(f"  💰 最终价值: ${final:,.0f}")
    print(f"  📈 总收益率: {ret:+.2f}%")
    print(f"  📉 最大回撤: {max_dd:.2f}%")
    print(f"  🔄 交易次数: {len(trades_df)}次")
    
    return {'strategy': strategy_name, 'return': ret, 'max_dd': max_dd, 'trades': len(trades_df)}


def backtest_long_no_tp(df, strategy_name):
    """做多回测（不止盈）"""
    print(f"\n{'='*80}")
    print(f"🟢 {strategy_name}")
    print('='*80)
    
    initial = 10000
    cash = initial
    btc = 0
    entry_price = 0
    entry_date = None
    
    trades = []
    portfolio = []
    
    for i in range(len(df)):
        row = df.iloc[i]
        price = row['close']
        signal = row.get('signal', 0)
        
        total_value = cash + btc * price
        
        # 止损
        if btc > 0 and price < entry_price * 0.9:
            pnl = btc * (price - entry_price)
            trades.append({
                'entry_date': entry_date,
                'exit_date': row['date'],
                'pnl': pnl,
                'action': 'STOP_LOSS'
            })
            cash += btc * price
            btc = 0
            entry_price = 0
        
        # 买入
        if signal == 1 and btc == 0:
            buy_value = total_value * 0.95
            btc = buy_value / price
            cash = total_value - buy_value
            entry_price = price
            entry_date = row['date']
        
        portfolio.append({'date': row['date'], 'total_value': cash + btc * price})
    
    # 最终持仓
    if btc > 0:
        final_price = df.iloc[-1]['close']
        profit = btc * (final_price - entry_price)
        print(f"\n⚠️  最终持仓: {btc:.6f} BTC @ ${final_price:,.0f}")
        print(f"   浮动盈亏: ${profit:,.0f} ({profit/(btc*entry_price)*100:+.1f}%)")
    
    portfolio_df = pd.DataFrame(portfolio)
    trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()
    
    final = portfolio_df['total_value'].iloc[-1]
    ret = (final - initial) / initial * 100
    
    portfolio_df['peak'] = portfolio_df['total_value'].cummax()
    portfolio_df['dd'] = (portfolio_df['total_value'] - portfolio_df['peak']) / portfolio_df['peak'] * 100
    max_dd = portfolio_df['dd'].min()
    
    print(f"  💰 最终价值: ${final:,.0f}")
    print(f"  📈 总收益率: {ret:+.2f}%")
    print(f"  📉 最大回撤: {max_dd:.2f}%")
    print(f"  🔄 止损次数: {len(trades_df)}次")
    
    return {'strategy': strategy_name, 'return': ret, 'max_dd': max_dd, 'trades': len(trades_df)}


def main():
    print("=" * 100)
    print("🎯 做空和双向交易策略测试")
    print("=" * 100)
    print()
    
    # 加载数据
    print("【步骤1】加载数据...")
    data_module = DataModule()
    df = data_module.get_price_data()
    print()
    
    # 计算指标
    print("【步骤2】计算指标...")
    df = calculate_indicators(df)
    print()
    
    print("【步骤3】测试策略...")
    
    results = []
    
    # === 做多策略（对比基准）===
    
    # 1. 冠军策略（做多）
    df_long = df.copy()
    df_long['signal'] = 0
    for i in range(1, len(df_long)):
        gc = (df_long.loc[i, 'wt1'] > df_long.loc[i, 'wt2']) and \
             (df_long.loc[i-1, 'wt1'] <= df_long.loc[i-1, 'wt2'])
        if df_long.loc[i, 'wt1'] < -50 and gc and df_long.loc[i, 'momentum'] > -0.5:
            df_long.loc[i, 'signal'] = 1
    
    r1 = backtest_long_no_tp(df_long, "做多: wt1<-50 + 动量>-0.5（冠军策略）")
    results.append(r1)
    
    # === 做空策略 ===
    
    # 2. 对称做空
    df_short = strategy_short_only(df)
    r2 = backtest_short(df_short, "做空: wt1>50 + 死叉 + 动量<0.5")
    results.append(r2)
    
    # 3. 激进做空（wt1>40）
    df_short2 = df.copy()
    df_short2['signal'] = 0
    for i in range(1, len(df_short2)):
        dc = (df_short2.loc[i, 'wt1'] < df_short2.loc[i, 'wt2']) and \
             (df_short2.loc[i-1, 'wt1'] >= df_short2.loc[i-1, 'wt2'])
        gc = (df_short2.loc[i, 'wt1'] > df_short2.loc[i, 'wt2']) and \
             (df_short2.loc[i-1, 'wt1'] <= df_short2.loc[i-1, 'wt2'])
        
        if df_short2.loc[i, 'wt1'] > 40 and dc and df_short2.loc[i, 'momentum'] < 0.3:
            df_short2.loc[i, 'signal'] = -1
        elif df_short2.loc[i, 'wt1'] < -30 and gc:
            df_short2.loc[i, 'signal'] = 1
    
    r3 = backtest_short(df_short2, "做空: wt1>40 + 死叉（激进）")
    results.append(r3)
    
    # === 优化做多策略 ===
    
    # 4. 更激进的做多（wt1<-40）
    df_long2 = df.copy()
    df_long2['signal'] = 0
    for i in range(1, len(df_long2)):
        gc = (df_long2.loc[i, 'wt1'] > df_long2.loc[i, 'wt2']) and \
             (df_long2.loc[i-1, 'wt1'] <= df_long2.loc[i-1, 'wt2'])
        if df_long2.loc[i, 'wt1'] < -40 and gc and df_long2.loc[i, 'momentum'] > -0.5:
            df_long2.loc[i, 'signal'] = 1
    
    r4 = backtest_long_no_tp(df_long2, "做多: wt1<-40 + 动量>-0.5")
    results.append(r4)
    
    # 5. 保守做多（wt1<-60）
    df_long3 = df.copy()
    df_long3['signal'] = 0
    for i in range(1, len(df_long3)):
        gc = (df_long3.loc[i, 'wt1'] > df_long3.loc[i, 'wt2']) and \
             (df_long3.loc[i-1, 'wt1'] <= df_long3.loc[i-1, 'wt2'])
        if df_long3.loc[i, 'wt1'] < -60 and gc and df_long3.loc[i, 'momentum'] > -0.5:
            df_long3.loc[i, 'signal'] = 1
    
    r5 = backtest_long_no_tp(df_long3, "做多: wt1<-60 + 动量>-0.5（保守）")
    results.append(r5)
    
    # 综合对比
    print()
    print("=" * 100)
    print("📊 策略综合对比")
    print("=" * 100)
    print()
    
    start_price = df.iloc[0]['close']
    end_price = df.iloc[-1]['close']
    hold_return = (end_price / start_price - 1) * 100
    
    print(f"{'策略':<50} {'收益率':<15} {'最大回撤':<15} {'交易次数':<10}")
    print("-" * 100)
    print(f"{'🏆 买入持有':<50} {hold_return:+.2f}%         {'-81.00%':<15} {'0':<10}")
    print()
    
    results_sorted = sorted(results, key=lambda x: x['return'], reverse=True)
    for r in results_sorted:
        emoji = '🟢' if '做多' in r['strategy'] else '🔴'
        print(f"{emoji + ' ' + r['strategy']:<50} {r['return']:+.2f}%         {r['max_dd']:.2f}%         {r['trades']:<10}")
    
    # 最佳策略
    print()
    print("=" * 100)
    best = max(results, key=lambda x: x['return'])
    print(f"\n🏆 最高收益策略: {best['strategy']}")
    print(f"   收益: {best['return']:+.2f}%")
    print(f"   vs 买入持有: {hold_return:+.2f}%")
    print(f"   差距: {best['return'] - hold_return:+.2f}%")
    
    if best['return'] > hold_return:
        print(f"\n🎉 恭喜！该策略超越了买入持有！")
    else:
        print(f"\n⚠️  该策略跑输买入持有 {hold_return - best['return']:.2f}%")
        print(f"   但最大回撤更小: {best['max_dd']:.2f}% vs -81.00%")
    
    print()
    print("=" * 100)


if __name__ == "__main__":
    main()

