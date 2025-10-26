#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MVRV Z-Score + 低位杠杆策略
在低估区间（Z < 0）使用3倍杠杆买入，提升收益
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

print("=" * 100)
print("🎯 MVRV Z-Score + 低位杠杆策略")
print("=" * 100)
print()

# ============================================================================
# 加载数据
# ============================================================================
print("【步骤1】加载数据...")

try:
    mvrv_df = pd.read_csv('results/真实MVRV_Z_Score数据_CoinMetrics.csv')
    mvrv_df['date'] = pd.to_datetime(mvrv_df['date']).dt.tz_localize(None)
    
    btc = yf.Ticker('BTC-USD')
    btc_hist = btc.history(start='2014-01-01', end='2025-12-31')
    btc_hist = btc_hist.reset_index()
    
    price_df = pd.DataFrame({
        'date': pd.to_datetime(btc_hist['Date']).dt.tz_localize(None),
        'close': btc_hist['Close']
    })
    
    df = pd.merge(price_df, mvrv_df[['date', 'mvrv', 'mvrv_z_score']], on='date', how='inner')
    df = df.sort_values('date').reset_index(drop=True)
    
    print(f"✅ 数据加载完成: {len(df)}条")
    print(f"   时间范围: {df['date'].min().strftime('%Y-%m-%d')} 至 {df['date'].max().strftime('%Y-%m-%d')}")
    print()
except Exception as e:
    print(f"❌ 加载失败: {e}")
    exit(1)

# ============================================================================
# 杠杆策略类
# ============================================================================
class LeveragedMVRVStrategy:
    """MVRV Z-Score + 低位杠杆策略"""
    
    def __init__(self, initial_capital=10000):
        self.initial_capital = initial_capital
        
        # 买入阈值（带杠杆）
        self.buy_levels = [
            (-1.0, 0.20, 3.0, "极度低估买入20%(3x杠杆)"),  # Z < -1, 3倍杠杆
            (0.0, 0.30, 3.0, "低估买入30%(3x杠杆)"),      # Z < 0, 3倍杠杆
            (1.0, 0.30, 1.0, "正常偏低买入30%(无杠杆)"),   # Z < 1, 无杠杆
            (2.0, 0.20, 1.0, "正常买入20%(无杠杆)")        # Z < 2, 无杠杆
        ]
        
        # 卖出阈值（优化）
        self.sell_levels = [
            (4.5, 0.15, "偏高卖出15%"),
            (5.5, 0.20, "高估卖出20%"),
            (6.5, 0.25, "深度高估卖出25%"),
            (7.5, 0.20, "极度高估卖出20%"),
            (8.5, 0.20, "泡沫区卖出20%")
        ]
        
        # 杠杆利息（年化）
        self.leverage_interest_rate = 0.08  # 8%年化利息
    
    def run_backtest(self, df):
        """运行回测"""
        print("=" * 100)
        print("🚀 MVRV Z-Score + 低位杠杆策略回测")
        print("=" * 100)
        print()
        
        cash = self.initial_capital
        position = 0
        borrowed = 0  # 借入的资金
        
        trades = []
        portfolio = []
        
        buy_triggered = {-1.0: False, 0.0: False, 1.0: False, 2.0: False}
        sell_triggered = {4.5: False, 5.5: False, 6.5: False, 7.5: False, 8.5: False}
        
        current_cycle_entry_price = None
        
        for i in range(1, len(df)):
            row = df.iloc[i]
            prev_row = df.iloc[i-1]
            date = row['date']
            price = row['close']
            z_score = row['mvrv_z_score']
            
            # 计算杠杆利息（每日）
            if borrowed > 0:
                days = (row['date'] - prev_row['date']).days
                interest = borrowed * (self.leverage_interest_rate / 365) * days
                cash -= interest
            
            total_value = cash + position * price - borrowed
            
            # === 买入逻辑（带杠杆）===
            if cash > 100:
                for threshold, buy_pct, leverage, reason in self.buy_levels:
                    if z_score < threshold and not buy_triggered[threshold]:
                        buy_value = self.initial_capital * buy_pct
                        
                        # 应用杠杆
                        if leverage > 1.0:
                            actual_buy_value = buy_value * leverage
                            borrow_amount = buy_value * (leverage - 1)
                            
                            if buy_value <= cash:
                                buy_position = actual_buy_value / price
                                position += buy_position
                                cash -= buy_value
                                borrowed += borrow_amount
                                buy_triggered[threshold] = True
                                
                                if current_cycle_entry_price is None:
                                    current_cycle_entry_price = price
                                
                                trades.append({
                                    'date': date,
                                    'type': 'BUY',
                                    'price': price,
                                    'z_score': z_score,
                                    'reason': reason,
                                    'position': position,
                                    'leverage': leverage,
                                    'borrowed': borrowed
                                })
                                
                                print(f"  🟢 {reason}: {date.strftime('%Y-%m-%d')} @ ${price:,.0f}, Z={z_score:.2f}, 杠杆{leverage}x")
                                break
                        else:
                            # 无杠杆买入
                            if buy_value <= cash:
                                buy_position = buy_value / price
                                position += buy_position
                                cash -= buy_value
                                buy_triggered[threshold] = True
                                
                                if current_cycle_entry_price is None:
                                    current_cycle_entry_price = price
                                
                                trades.append({
                                    'date': date,
                                    'type': 'BUY',
                                    'price': price,
                                    'z_score': z_score,
                                    'reason': reason,
                                    'position': position,
                                    'leverage': 1.0,
                                    'borrowed': borrowed
                                })
                                
                                print(f"  🟢 {reason}: {date.strftime('%Y-%m-%d')} @ ${price:,.0f}, Z={z_score:.2f}")
                                break
            
            # 重置买入标记
            if z_score > 3:
                buy_triggered = {-1.0: False, 0.0: False, 1.0: False, 2.0: False}
            
            # === 卖出逻辑 ===
            if position > 0.01:
                for threshold, sell_pct, reason in self.sell_levels:
                    if z_score > threshold and not sell_triggered[threshold]:
                        sell_position = position * sell_pct
                        sell_value = sell_position * price
                        position -= sell_position
                        cash += sell_value
                        
                        # 优先偿还借款
                        if borrowed > 0:
                            repay = min(borrowed, sell_value * 0.5)  # 用50%的卖出资金还款
                            borrowed -= repay
                            cash -= repay
                        
                        sell_triggered[threshold] = True
                        
                        if current_cycle_entry_price:
                            pnl_pct = (price / current_cycle_entry_price - 1) * 100
                        else:
                            pnl_pct = 0
                        
                        trades.append({
                            'date': date,
                            'type': 'SELL',
                            'price': price,
                            'z_score': z_score,
                            'reason': reason,
                            'position': position,
                            'pnl_pct': pnl_pct,
                            'borrowed': borrowed
                        })
                        
                        print(f"  🔴 {reason}: {date.strftime('%Y-%m-%d')} @ ${price:,.0f}, Z={z_score:.2f}, 盈利{pnl_pct:+.1f}%, 剩余借款${borrowed:,.0f}")
                        
                        if position < 0.01:
                            current_cycle_entry_price = None
                        
                        break
            
            # 重置卖出标记
            if z_score < 4:
                sell_triggered = {4.5: False, 5.5: False, 6.5: False, 7.5: False, 8.5: False}
            
            # 记录组合价值
            total_value = cash + position * price - borrowed
            portfolio.append({
                'date': date,
                'price': price,
                'z_score': z_score,
                'total_value': total_value,
                'position': position,
                'cash': cash,
                'borrowed': borrowed
            })
        
        # 最终持仓
        final_price = df.iloc[-1]['close']
        final_z = df.iloc[-1]['mvrv_z_score']
        final_value = cash + position * price - borrowed
        
        print(f"\n📊 最终状态:")
        print(f"   持仓: {position:.4f} BTC (价值${position * final_price:,.0f})")
        print(f"   现金: ${cash:,.0f}")
        print(f"   借款: ${borrowed:,.0f}")
        print(f"   净值: ${final_value:,.0f}")
        print(f"   当前价格: ${final_price:,.0f}")
        print(f"   当前Z-Score: {final_z:.2f}")
        
        portfolio_df = pd.DataFrame(portfolio)
        trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()
        
        return portfolio_df, trades_df
    
    def show_results(self, portfolio_df, trades_df, period_name="近5年"):
        """显示回测结果"""
        print()
        print("=" * 100)
        print(f"📊 杠杆策略 - {period_name}回测结果")
        print("=" * 100)
        print()
        
        final = portfolio_df['total_value'].iloc[-1]
        ret = (final - self.initial_capital) / self.initial_capital * 100
        
        portfolio_df['peak'] = portfolio_df['total_value'].cummax()
        portfolio_df['dd'] = (portfolio_df['total_value'] - portfolio_df['peak']) / portfolio_df['peak'] * 100
        max_dd = portfolio_df['dd'].min()
        
        print(f"💰 初始资金: ${self.initial_capital:,.0f}")
        print(f"💰 最终价值: ${final:,.0f}")
        print(f"📈 总收益率: {ret:+.2f}%")
        print(f"📈 收益倍数: {final/self.initial_capital:.1f}倍")
        print(f"📉 最大回撤: {max_dd:.2f}%")
        print()
        
        if len(trades_df) > 0:
            buy_trades = trades_df[trades_df['type'] == 'BUY']
            sell_trades = trades_df[trades_df['type'] == 'SELL']
            
            leveraged_buys = buy_trades[buy_trades['leverage'] > 1.0]
            
            print(f"📊 交易统计:")
            print(f"  总交易次数: {len(trades_df)}次")
            print(f"  买入次数: {len(buy_trades)}次")
            print(f"    • 杠杆买入: {len(leveraged_buys)}次")
            print(f"    • 普通买入: {len(buy_trades) - len(leveraged_buys)}次")
            print(f"  卖出次数: {len(sell_trades)}次")
            
            # 最大借款
            if 'borrowed' in portfolio_df.columns:
                max_borrowed = portfolio_df['borrowed'].max()
                print(f"  最大借款: ${max_borrowed:,.0f}")
        
        print()
        print("=" * 100)
        
        return {
            'return': ret,
            'max_dd': max_dd,
            'trades': len(trades_df),
            'final_value': final
        }


# ============================================================================
# 运行回测（仅近5年）
# ============================================================================
print("【步骤2】运行杠杆策略（近5年）...")
print()

df_5y = df[df['date'].dt.year >= 2020].copy().reset_index(drop=True)

strategy = LeveragedMVRVStrategy(initial_capital=10000)
portfolio_df, trades_df = strategy.run_backtest(df_5y)
result = strategy.show_results(portfolio_df, trades_df, "近5年")

# 对比
start_price = df_5y.iloc[0]['close']
end_price = df_5y.iloc[-1]['close']
hold_return = (end_price / start_price - 1) * 100
hold_value = 10000 * (end_price / start_price)

print()
print("📊 策略对比（近5年）:")
print()
print(f"{'策略':<25} {'收益率':>15} {'收益倍数':>12} {'最大回撤':>12}")
print("-" * 70)
print(f"{'买入持有':<25} {hold_return:>14.2f}% {hold_value/10000:>11.1f}倍 {'~-77%':>12}")

# 读取其他策略结果
try:
    orig_portfolio = pd.read_csv('results/真实mvrv_z_portfolio_5y.csv')
    orig_final = orig_portfolio['total_value'].iloc[-1]
    orig_return = (orig_final - 10000) / 10000 * 100
    orig_portfolio['peak'] = orig_portfolio['total_value'].cummax()
    orig_portfolio['dd'] = (orig_portfolio['total_value'] - orig_portfolio['peak']) / orig_portfolio['peak'] * 100
    orig_max_dd = orig_portfolio['dd'].min()
    print(f"{'原始MVRV(Z>6)':<25} {orig_return:>14.2f}% {orig_final/10000:>11.1f}倍 {orig_max_dd:>11.2f}%")
except:
    pass

try:
    opt_portfolio = pd.read_csv('results/优化阈值_portfolio_5y.csv')
    opt_final = opt_portfolio['total_value'].iloc[-1]
    opt_return = (opt_final - 10000) / 10000 * 100
    opt_portfolio['peak'] = opt_portfolio['total_value'].cummax()
    opt_portfolio['dd'] = (opt_portfolio['total_value'] - opt_portfolio['peak']) / opt_portfolio['peak'] * 100
    opt_max_dd = opt_portfolio['dd'].min()
    print(f"{'优化MVRV(Z>4.5)':<25} {opt_return:>14.2f}% {opt_final/10000:>11.1f}倍 {opt_max_dd:>11.2f}%")
except:
    pass

print(f"{'杠杆MVRV(低位3x)':<25} {result['return']:>14.2f}% {result['final_value']/10000:>11.1f}倍 {result['max_dd']:>11.2f}%")

print()
print("💡 关键发现:")
print(f"  • 杠杆策略收益: {result['final_value']/10000:.1f}倍")
print(f"  • vs 买入持有: {result['return'] - hold_return:+.2f}%")
print(f"  • 最大回撤: {result['max_dd']:.2f}%")
print()

if result['final_value']/10000 > 10:
    print("🎉 成功！收益超过10倍")
else:
    print(f"⚠️  收益{result['final_value']/10000:.1f}倍，未达到10倍目标")

if result['max_dd'] > -50:
    print("✅ 回撤控制在50%以内")
else:
    print(f"⚠️  回撤{result['max_dd']:.2f}%，超过50%")

print()
print("=" * 100)

# 保存结果
import os
os.makedirs('results', exist_ok=True)

portfolio_df.to_csv('results/杠杆策略_portfolio_5y.csv', index=False, encoding='utf-8-sig')
trades_df.to_csv('results/杠杆策略_trades_5y.csv', index=False, encoding='utf-8-sig')

print()
print("✅ 结果已保存到 results/ 文件夹")
print("=" * 100)






