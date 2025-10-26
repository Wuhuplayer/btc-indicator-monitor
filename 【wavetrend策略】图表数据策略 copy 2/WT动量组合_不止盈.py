#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WaveTrend + 动量组合策略（不止盈版）
只用动量过滤入场，不设止盈，让利润奔跑
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path

sys.path.append(str(Path(__file__).parent / '模块'))
from 数据模块 import DataModule


def calculate_all_indicators(df):
    """计算所有指标"""
    print("📊 计算指标...")
    df = df.copy()
    
    # WaveTrend（TradingView标准）
    n1, n2 = 10, 21
    hlc3 = (df['high'] + df['low'] + df['close']) / 3
    esa = hlc3.ewm(span=n1, adjust=False).mean()
    d = (hlc3 - esa).abs().ewm(span=n1, adjust=False).mean()
    ci = (hlc3 - esa) / (0.015 * d)
    
    df['wt1'] = ci.ewm(span=n2, adjust=False).mean()  # EMA
    df['wt2'] = df['wt1'].rolling(window=4).mean()  # SMA
    
    # 动量指标
    df['momentum_20d'] = df['close'].pct_change(20)
    df['momentum_20d_norm'] = (df['momentum_20d'] - df['momentum_20d'].mean()) / df['momentum_20d'].std()
    
    # 移动平均线
    df['ma200'] = df['close'].rolling(window=200).mean()
    df['above_ma200'] = df['close'] > df['ma200']
    
    print("✅ 指标计算完成")
    return df


def run_backtest_no_tp(df, strategy_name, initial_capital=10000, stop_loss=0.10):
    """运行回测（不止盈版）"""
    cash = initial_capital
    btc_holdings = 0
    entry_price = 0
    entry_date = None
    
    trades = []
    portfolio = []
    
    for i in range(len(df)):
        row = df.iloc[i]
        date = row['date']
        price = row['close']
        signal = row.get('signal', 0)
        
        total_value = cash + btc_holdings * price
        
        # 止损（唯一的出场方式）
        if btc_holdings > 0 and entry_price > 0:
            loss_pct = (entry_price - price) / entry_price
            if loss_pct >= stop_loss:
                sell_value = btc_holdings * price
                profit = sell_value - (btc_holdings * entry_price)
                hold_days = (pd.to_datetime(date) - pd.to_datetime(entry_date)).days
                
                trades.append({
                    'entry_date': entry_date,
                    'exit_date': date,
                    'entry_price': entry_price,
                    'exit_price': price,
                    'profit': profit,
                    'profit_pct': profit / (btc_holdings * entry_price) * 100,
                    'hold_days': hold_days,
                    'reason': 'STOP_LOSS'
                })
                
                cash += sell_value
                btc_holdings = 0
                entry_price = 0
                entry_date = None
        
        # 买入
        if signal == 1 and btc_holdings == 0:
            buy_value = total_value * 0.95
            if buy_value > 0:
                btc_holdings = buy_value / price
                cash = total_value - buy_value
                entry_price = price
                entry_date = date
        
        portfolio.append({
            'date': date,
            'price': price,
            'total_value': cash + btc_holdings * price
        })
    
    # 最终持仓
    if btc_holdings > 0:
        final_price = df.iloc[-1]['close']
        final_value = btc_holdings * final_price
        profit = final_value - (btc_holdings * entry_price)
        hold_days = (pd.to_datetime(df.iloc[-1]['date']) - pd.to_datetime(entry_date)).days
        
        print(f"\n⚠️  最终持仓: {btc_holdings:.6f} BTC @ ${final_price:,.0f}")
        print(f"   入场: {entry_date} @ ${entry_price:,.0f}")
        print(f"   持有: {hold_days}天")
        print(f"   浮动盈亏: ${profit:,.0f} ({profit/(btc_holdings*entry_price)*100:+.1f}%)")
    
    portfolio_df = pd.DataFrame(portfolio)
    trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()
    
    # 计算统计
    final_value = portfolio_df['total_value'].iloc[-1]
    total_return = (final_value - initial_capital) / initial_capital * 100
    
    portfolio_df['peak'] = portfolio_df['total_value'].cummax()
    portfolio_df['drawdown'] = (portfolio_df['total_value'] - portfolio_df['peak']) / portfolio_df['peak'] * 100
    max_drawdown = portfolio_df['drawdown'].min()
    
    num_stop_loss = len(trades_df)
    win_rate = 0  # 不止盈的策略，所有平仓都是止损
    
    print(f"\n📊 {strategy_name}")
    print("-" * 80)
    print(f"  💰 最终价值: ${final_value:,.0f}")
    print(f"  📈 总收益率: {total_return:+.2f}%")
    print(f"  📉 最大回撤: {max_drawdown:.2f}%")
    print(f"  🔄 止损次数: {num_stop_loss}次")
    
    return {
        'strategy': strategy_name,
        'return': total_return,
        'max_drawdown': max_drawdown,
        'stop_losses': num_stop_loss
    }


def main():
    print("=" * 100)
    print("🎯 WaveTrend + 动量组合策略（不止盈版）")
    print("=" * 100)
    print()
    
    # 加载数据
    print("【步骤1】加载数据...")
    data_module = DataModule()
    price_data = data_module.get_price_data()
    print()
    
    # 计算指标
    print("【步骤2】计算指标...")
    df = calculate_all_indicators(price_data)
    print()
    
    # 测试策略
    print("【步骤3】测试不同组合...")
    print()
    
    results = []
    
    # 策略组合矩阵
    wt_thresholds = [-30, -40, -50, -60]
    momentum_thresholds = [
        ('无过滤', None),
        ('动量>-0.8', -0.8),
        ('动量>-0.5', -0.5),
        ('动量>-0.3', -0.3),
        ('动量>0', 0)
    ]
    
    for wt_thresh in wt_thresholds:
        print()
        print("=" * 100)
        print(f"🔍 测试 wt1 < {wt_thresh}")
        print("=" * 100)
        
        for mom_name, mom_thresh in momentum_thresholds:
            # 生成信号
            df_test = df.copy()
            df_test['signal'] = 0
            
            for i in range(1, len(df_test)):
                # 金叉
                golden_cross = (df_test.loc[i, 'wt1'] > df_test.loc[i, 'wt2']) and \
                              (df_test.loc[i-1, 'wt1'] <= df_test.loc[i-1, 'wt2'])
                
                # 买入条件
                wt_condition = df_test.loc[i, 'wt1'] < wt_thresh
                
                if mom_thresh is None:
                    momentum_condition = True
                else:
                    momentum_condition = df_test.loc[i, 'momentum_20d_norm'] > mom_thresh
                
                if golden_cross and wt_condition and momentum_condition:
                    df_test.loc[i, 'signal'] = 1
            
            # 回测
            strategy_name = f"wt1<{wt_thresh} + {mom_name}"
            result = run_backtest_no_tp(df_test, strategy_name)
            results.append(result)
    
    # 综合对比
    print()
    print("=" * 100)
    print("📊 所有策略对比（按收益率排序）")
    print("=" * 100)
    print()
    
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('return', ascending=False)
    
    start_price = price_data.iloc[0]['close']
    end_price = price_data.iloc[-1]['close']
    hold_return = (end_price / start_price - 1) * 100
    
    print(f"{'策略':<40} {'收益率':<15} {'最大回撤':<15} {'止损次数':<10}")
    print("-" * 100)
    print(f"{'买入持有':<40} {hold_return:+.2f}%         {'-81.00%':<15} {'0':<10}")
    print()
    
    for _, r in results_df.iterrows():
        print(f"{r['strategy']:<40} {r['return']:+.2f}%         {r['max_drawdown']:.2f}%         {r['stop_losses']:<10}")
    
    # TOP 3
    print()
    print("=" * 100)
    print("🏆 TOP 3 策略")
    print("=" * 100)
    
    top3 = results_df.head(3)
    for i, (_, r) in enumerate(top3.iterrows(), 1):
        medal = ['🥇', '🥈', '🥉'][i-1]
        print(f"\n{medal} {r['strategy']}")
        print(f"   收益: {r['return']:+.2f}%")
        print(f"   回撤: {r['max_drawdown']:.2f}%")
        print(f"   止损: {r['stop_losses']}次")
        sharpe = -r['return']/r['max_drawdown'] if r['max_drawdown'] < 0 else 0
        print(f"   收益/回撤比: {sharpe:.2f}")
    
    print()
    print("=" * 100)
    
    # 保存
    results_df.to_csv('数字化数据/wt_momentum_no_tp.csv', index=False, encoding='utf-8-sig')
    print()
    print("✅ 结果已保存: 数字化数据/wt_momentum_no_tp.csv")
    print()


if __name__ == "__main__":
    main()

