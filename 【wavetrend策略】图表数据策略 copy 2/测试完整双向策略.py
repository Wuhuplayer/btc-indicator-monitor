#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整双向交易策略
既做多又做空，充分利用市场的涨跌
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path

sys.path.append(str(Path(__file__).parent / '模块'))
from 数据模块 import DataModule


def calculate_indicators(df):
    """计算所有指标"""
    df = df.copy()
    
    # WaveTrend（TradingView标准）
    n1, n2 = 10, 21
    hlc3 = (df['high'] + df['low'] + df['close']) / 3
    esa = hlc3.ewm(span=n1, adjust=False).mean()
    d = (hlc3 - esa).abs().ewm(span=n1, adjust=False).mean()
    ci = (hlc3 - esa) / (0.015 * d)
    
    df['wt1'] = ci.ewm(span=n2, adjust=False).mean()  # EMA
    df['wt2'] = df['wt1'].rolling(window=4).mean()  # SMA
    
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


def backtest_long_short(df, long_wt, short_wt, long_mom, short_mom, stop_loss=0.10, strategy_name=""):
    """
    完整双向交易回测
    
    参数:
        long_wt: 做多的wt阈值（如-50）
        short_wt: 做空的wt阈值（如+50）
        long_mom: 做多的动量阈值（如-0.5）
        short_mom: 做空的动量阈值（如+0.5）
    """
    initial = 10000
    cash = initial
    position = 0  # 正数=做多BTC数量，负数=做空BTC数量
    entry_price = 0
    entry_date = None
    position_type = None  # 'LONG' or 'SHORT'
    
    trades = []
    portfolio = []
    
    for i in range(1, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]
        date = row['date']
        price = row['close']
        
        # 计算当前总价值
        if position > 0:  # 做多仓位
            unrealized_pnl = position * (price - entry_price)
            total_value = cash + position * price
        elif position < 0:  # 做空仓位
            unrealized_pnl = -position * (entry_price - price)
            total_value = cash + unrealized_pnl
        else:  # 空仓
            total_value = cash
            unrealized_pnl = 0
        
        # 检查止损
        if position != 0 and entry_price > 0:
            if position > 0:  # 做多止损
                loss_pct = (entry_price - price) / entry_price
                if loss_pct >= stop_loss:
                    pnl = position * (price - entry_price)
                    trades.append({
                        'entry_date': entry_date,
                        'exit_date': date,
                        'type': 'LONG',
                        'entry_price': entry_price,
                        'exit_price': price,
                        'pnl': pnl,
                        'pnl_pct': pnl / (position * entry_price) * 100,
                        'reason': 'STOP_LOSS'
                    })
                    cash += position * price
                    position = 0
                    entry_price = 0
                    position_type = None
            
            elif position < 0:  # 做空止损
                loss_pct = (price - entry_price) / entry_price
                if loss_pct >= stop_loss:
                    pnl = -position * (entry_price - price)
                    trades.append({
                        'entry_date': entry_date,
                        'exit_date': date,
                        'type': 'SHORT',
                        'entry_price': entry_price,
                        'exit_price': price,
                        'pnl': pnl,
                        'pnl_pct': pnl / (-position * entry_price) * 100,
                        'reason': 'STOP_LOSS'
                    })
                    cash += pnl
                    position = 0
                    entry_price = 0
                    position_type = None
        
        # 金叉和死叉
        golden_cross = (row['wt1'] > row['wt2']) and (prev['wt1'] <= prev['wt2'])
        death_cross = (row['wt1'] < row['wt2']) and (prev['wt1'] >= prev['wt2'])
        
        # === 做多信号 ===
        if (row['wt1'] < long_wt and 
            golden_cross and 
            row['momentum'] > long_mom and
            position == 0):
            
            # 开多仓
            buy_value = total_value * 0.95
            position = buy_value / price
            cash = total_value - buy_value
            entry_price = price
            entry_date = date
            position_type = 'LONG'
        
        # === 做空信号 ===
        elif (row['wt1'] > short_wt and 
              death_cross and 
              row['momentum'] < short_mom and
              position == 0):
            
            # 开空仓
            short_value = total_value * 0.95
            position = -short_value / price  # 负数表示做空
            entry_price = price
            entry_date = date
            position_type = 'SHORT'
        
        # === 平多仓信号（做多遇到死叉或wt1过高）===
        elif (position > 0 and 
              ((death_cross and row['adx'] > 20 and row['wt1'] > 0) or
               row['wt1'] > 60)):
            
            pnl = position * (price - entry_price)
            trades.append({
                'entry_date': entry_date,
                'exit_date': date,
                'type': 'LONG',
                'entry_price': entry_price,
                'exit_price': price,
                'pnl': pnl,
                'pnl_pct': pnl / (position * entry_price) * 100,
                'reason': 'TAKE_PROFIT'
            })
            cash += position * price
            position = 0
            entry_price = 0
            position_type = None
        
        # === 平空仓信号（做空遇到金叉或wt1过低）===
        elif (position < 0 and 
              ((golden_cross and row['wt1'] < -20) or
               row['wt1'] < -60)):
            
            pnl = -position * (entry_price - price)
            trades.append({
                'entry_date': entry_date,
                'exit_date': date,
                'type': 'SHORT',
                'entry_price': entry_price,
                'exit_price': price,
                'pnl': pnl,
                'pnl_pct': pnl / (-position * entry_price) * 100,
                'reason': 'TAKE_PROFIT'
            })
            cash += pnl
            position = 0
            entry_price = 0
            position_type = None
        
        # 记录组合价值
        if position > 0:
            total_value = cash + position * price
        elif position < 0:
            unrealized_pnl = -position * (entry_price - price)
            total_value = cash + unrealized_pnl
        else:
            total_value = cash
        
        portfolio.append({
            'date': date,
            'price': price,
            'total_value': total_value,
            'position': position,
            'position_type': position_type
        })
    
    # 最终持仓处理
    final_price = df.iloc[-1]['close']
    if position > 0:
        pnl = position * (final_price - entry_price)
        print(f"\n⚠️  最终做多仓位: {position:.6f} BTC @ ${final_price:,.0f}")
        print(f"   入场: {entry_date} @ ${entry_price:,.0f}")
        print(f"   浮动盈亏: ${pnl:,.0f} ({pnl/(position*entry_price)*100:+.1f}%)")
    elif position < 0:
        pnl = -position * (entry_price - final_price)
        print(f"\n⚠️  最终做空仓位: {-position:.6f} BTC @ ${final_price:,.0f}")
        print(f"   入场: {entry_date} @ ${entry_price:,.0f}")
        print(f"   浮动盈亏: ${pnl:,.0f} ({pnl/(-position*entry_price)*100:+.1f}%)")
    
    portfolio_df = pd.DataFrame(portfolio)
    trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()
    
    # 统计
    final = portfolio_df['total_value'].iloc[-1]
    ret = (final - initial) / initial * 100
    
    portfolio_df['peak'] = portfolio_df['total_value'].cummax()
    portfolio_df['dd'] = (portfolio_df['total_value'] - portfolio_df['peak']) / portfolio_df['peak'] * 100
    max_dd = portfolio_df['dd'].min()
    
    if len(trades_df) > 0:
        long_trades = trades_df[trades_df['type'] == 'LONG']
        short_trades = trades_df[trades_df['type'] == 'SHORT']
        
        completed_trades = trades_df
        win_trades = completed_trades[completed_trades['pnl'] > 0]
        win_rate = len(win_trades) / len(completed_trades) * 100 if len(completed_trades) > 0 else 0
        
        avg_pnl = completed_trades['pnl'].mean()
        total_pnl = completed_trades['pnl'].sum()
    else:
        long_trades = pd.DataFrame()
        short_trades = pd.DataFrame()
        win_rate = 0
        avg_pnl = 0
        total_pnl = 0
    
    print(f"\n📊 {strategy_name}")
    print("-" * 80)
    print(f"  💰 最终价值: ${final:,.0f}")
    print(f"  📈 总收益率: {ret:+.2f}%")
    print(f"  📉 最大回撤: {max_dd:.2f}%")
    print(f"  🔄 总交易次数: {len(trades_df)}次")
    if len(trades_df) > 0:
        print(f"     🟢 做多: {len(long_trades)}次")
        print(f"     🔴 做空: {len(short_trades)}次")
        print(f"  🎯 胜率: {win_rate:.1f}%")
        print(f"  💵 平均每笔: ${avg_pnl:,.0f}")
        print(f"  💰 已实现盈亏: ${total_pnl:,.0f}")
    
    return {
        'strategy': strategy_name,
        'return': ret,
        'max_dd': max_dd,
        'trades': len(trades_df),
        'win_rate': win_rate
    }


def main():
    print("=" * 100)
    print("🎯 双向交易策略测试（多空都做）")
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
    
    # 测试多种双向策略
    print("【步骤3】测试双向策略...")
    
    results = []
    
    # 策略1: 标准双向（wt±50）
    print("\n" + "="*100)
    print("📊 策略1: 标准双向交易")
    print("   做多: wt1<-50 且金叉 且 动量>-0.5")
    print("   做空: wt1>+50 且死叉 且 动量<+0.5")
    print("="*100)
    r1 = backtest_long_short(df, long_wt=-50, short_wt=50, 
                             long_mom=-0.5, short_mom=0.5,
                             strategy_name="双向: WT±50")
    results.append(r1)
    
    # 策略2: 宽松双向（wt±40）
    print("\n" + "="*100)
    print("📊 策略2: 宽松双向交易")
    print("   做多: wt1<-40 且金叉 且 动量>-0.5")
    print("   做空: wt1>+40 且死叉 且 动量<+0.5")
    print("="*100)
    r2 = backtest_long_short(df, long_wt=-40, short_wt=40, 
                             long_mom=-0.5, short_mom=0.5,
                             strategy_name="双向: WT±40")
    results.append(r2)
    
    # 策略3: 激进做空（wt+30）
    print("\n" + "="*100)
    print("📊 策略3: 激进做空双向")
    print("   做多: wt1<-50 且金叉 且 动量>-0.5")
    print("   做空: wt1>+30 且死叉 且 动量<+0.3")
    print("="*100)
    r3 = backtest_long_short(df, long_wt=-50, short_wt=30, 
                             long_mom=-0.5, short_mom=0.3,
                             strategy_name="双向: 做多保守做空激进")
    results.append(r3)
    
    # 策略4: 严格双向（wt±60）
    print("\n" + "="*100)
    print("📊 策略4: 严格双向交易")
    print("   做多: wt1<-60 且金叉 且 动量>-0.5")
    print("   做空: wt1>+60 且死叉 且 动量<+0.5")
    print("="*100)
    r4 = backtest_long_short(df, long_wt=-60, short_wt=60, 
                             long_mom=-0.5, short_mom=0.5,
                             strategy_name="双向: WT±60（严格）")
    results.append(r4)
    
    # 策略5: 动量主导
    print("\n" + "="*100)
    print("📊 策略5: 动量主导双向")
    print("   做多: wt1<-40 且金叉 且 动量>0（强动量）")
    print("   做空: wt1>+40 且死叉 且 动量<0（负动量）")
    print("="*100)
    r5 = backtest_long_short(df, long_wt=-40, short_wt=40, 
                             long_mom=0, short_mom=0,
                             strategy_name="双向: 动量主导")
    results.append(r5)
    
    # 综合对比
    print()
    print("=" * 100)
    print("📊 所有策略对比")
    print("=" * 100)
    print()
    
    start_price = price_data.iloc[0]['close']
    end_price = price_data.iloc[-1]['close']
    hold_return = (end_price / start_price - 1) * 100
    
    print(f"{'策略':<40} {'收益率':<15} {'最大回撤':<15} {'交易次数':<12} {'胜率':<10}")
    print("-" * 100)
    print(f"{'🏆 买入持有':<40} {hold_return:+.2f}%         {'-81.00%':<15} {'0':<12} {'N/A':<10}")
    print()
    
    results_sorted = sorted(results, key=lambda x: x['return'], reverse=True)
    for r in results_sorted:
        wr_str = f"{r['win_rate']:.1f}%" if r['trades'] > 0 else "N/A"
        print(f"{r['strategy']:<40} {r['return']:+.2f}%         {r['max_dd']:.2f}%         {r['trades']:<12} {wr_str:<10}")
    
    # 最佳策略分析
    print()
    print("=" * 100)
    best = max(results, key=lambda x: x['return'])
    
    print(f"\n🏆 最高收益策略: {best['strategy']}")
    print(f"   收益: {best['return']:+.2f}%")
    print(f"   回撤: {best['max_dd']:.2f}%")
    print(f"   vs 买入持有: {hold_return:+.2f}%")
    
    if best['return'] > hold_return:
        print(f"\n🎉🎉🎉 恭喜！双向策略超越买入持有！")
        print(f"   超额收益: {best['return'] - hold_return:+.2f}%")
    else:
        print(f"\n⚠️  双向策略跑输买入持有")
        print(f"   差距: {hold_return - best['return']:.2f}%")
        print(f"   但回撤优势: {best['max_dd']:.2f}% vs -81.00%")
    
    print()
    print("=" * 100)
    
    # 保存结果
    pd.DataFrame(results).to_csv('数字化数据/long_short_strategies.csv', 
                                 index=False, encoding='utf-8-sig')
    print()
    print("✅ 结果已保存: 数字化数据/long_short_strategies.csv")
    print()


if __name__ == "__main__":
    main()

