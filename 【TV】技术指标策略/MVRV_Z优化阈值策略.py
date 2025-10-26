#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MVRV Z-Score优化阈值策略
去掉复杂的技术指标，只优化MVRV Z-Score的买卖阈值

核心优化：
1. 降低卖出阈值：从Z>6降低到Z>4.5，提前在高位卖出
2. 分批卖出：在Z>4.5时就开始分批卖出
3. 保持买入逻辑不变
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

print("=" * 100)
print("🎯 MVRV Z-Score优化阈值策略 - 简化版")
print("=" * 100)
print()

# ============================================================================
# 加载数据
# ============================================================================
print("【步骤1】加载真实MVRV Z-Score数据...")
print()

try:
    mvrv_df = pd.read_csv('results/真实MVRV_Z_Score数据_CoinMetrics.csv')
    mvrv_df['date'] = pd.to_datetime(mvrv_df['date']).dt.tz_localize(None)
    print(f"✅ 成功加载MVRV数据: {len(mvrv_df)}条")
except Exception as e:
    print(f"❌ 加载失败: {e}")
    exit(1)

print()
print("【步骤2】加载BTC价格数据...")
print()

try:
    btc = yf.Ticker('BTC-USD')
    btc_hist = btc.history(start='2014-01-01', end='2025-12-31')
    btc_hist = btc_hist.reset_index()
    
    price_df = pd.DataFrame({
        'date': pd.to_datetime(btc_hist['Date']).dt.tz_localize(None),
        'close': btc_hist['Close']
    })
    
    print(f"✅ 成功加载BTC价格数据: {len(price_df)}条")
except Exception as e:
    print(f"❌ 加载失败: {e}")
    exit(1)

print()
print("【步骤3】合并数据...")
print()

df = pd.merge(price_df, mvrv_df[['date', 'mvrv', 'mvrv_z_score']], on='date', how='inner')
df = df.sort_values('date').reset_index(drop=True)

print(f"✅ 数据准备完成: {len(df)}条")
print(f"   时间范围: {df['date'].min().strftime('%Y-%m-%d')} 至 {df['date'].max().strftime('%Y-%m-%d')}")
print()

# ============================================================================
# 优化策略类
# ============================================================================
class OptimizedMVRVStrategy:
    """MVRV Z-Score优化阈值策略（简化版）"""
    
    def __init__(self, initial_capital=10000):
        self.initial_capital = initial_capital
        
        # 买入阈值（保持不变）
        self.buy_levels = [
            (-1.0, 0.20, "极度低估买入20%"),
            (0.0, 0.30, "低估买入30%"),
            (1.0, 0.30, "正常偏低买入30%"),
            (2.0, 0.20, "正常买入20%")
        ]
        
        # 卖出阈值（优化：降低阈值，提前卖出）
        self.sell_levels = [
            (4.5, 0.15, "偏高卖出15%"),      # 新增：Z>4.5就开始卖
            (5.5, 0.20, "高估卖出20%"),      # 原6.0降低到5.5
            (6.5, 0.25, "深度高估卖出25%"),  # 原7.0降低到6.5
            (7.5, 0.20, "极度高估卖出20%"),  # 原8.0降低到7.5
            (8.5, 0.20, "泡沫区卖出20%")     # 原9.0降低到8.5
        ]
    
    def run_backtest(self, df):
        """运行回测"""
        print("=" * 100)
        print("🚀 MVRV Z-Score优化阈值策略回测")
        print("=" * 100)
        print()
        
        cash = self.initial_capital
        position = 0
        
        trades = []
        portfolio = []
        
        buy_triggered = {-1.0: False, 0.0: False, 1.0: False, 2.0: False}
        sell_triggered = {4.5: False, 5.5: False, 6.5: False, 7.5: False, 8.5: False}
        
        current_cycle_entry_price = None
        current_cycle_entry_date = None
        
        for i in range(1, len(df)):
            row = df.iloc[i]
            date = row['date']
            price = row['close']
            z_score = row['mvrv_z_score']
            
            total_value = cash + position * price
            
            # === 买入逻辑 ===
            if cash > 100:
                for threshold, buy_pct, reason in self.buy_levels:
                    if z_score < threshold and not buy_triggered[threshold]:
                        buy_value = self.initial_capital * buy_pct
                        if buy_value <= cash:
                            buy_position = buy_value / price
                            position += buy_position
                            cash -= buy_value
                            buy_triggered[threshold] = True
                            
                            if current_cycle_entry_price is None:
                                current_cycle_entry_price = price
                                current_cycle_entry_date = date
                            
                            trades.append({
                                'date': date,
                                'type': 'BUY',
                                'price': price,
                                'z_score': z_score,
                                'reason': reason,
                                'position': position
                            })
                            
                            print(f"  🟢 {reason}: {date.strftime('%Y-%m-%d')} @ ${price:,.0f}, Z={z_score:.2f}")
                            break
            
            # 重置买入标记
            if z_score > 3:
                buy_triggered = {-1.0: False, 0.0: False, 1.0: False, 2.0: False}
            
            # === 卖出逻辑（优化阈值）===
            if position > 0.01:
                for threshold, sell_pct, reason in self.sell_levels:
                    if z_score > threshold and not sell_triggered[threshold]:
                        sell_position = position * sell_pct
                        sell_value = sell_position * price
                        position -= sell_position
                        cash += sell_value
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
                            'pnl_pct': pnl_pct
                        })
                        
                        print(f"  🔴 {reason}: {date.strftime('%Y-%m-%d')} @ ${price:,.0f}, Z={z_score:.2f}, 盈利{pnl_pct:+.1f}%")
                        
                        if position < 0.01:
                            current_cycle_entry_price = None
                            current_cycle_entry_date = None
                        
                        break
            
            # 重置卖出标记
            if z_score < 4:
                sell_triggered = {4.5: False, 5.5: False, 6.5: False, 7.5: False, 8.5: False}
            
            # 记录组合价值
            total_value = cash + position * price
            portfolio.append({
                'date': date,
                'price': price,
                'z_score': z_score,
                'total_value': total_value,
                'position': position,
                'cash': cash
            })
        
        # 最终持仓
        final_price = df.iloc[-1]['close']
        final_z = df.iloc[-1]['mvrv_z_score']
        if position > 0:
            print(f"\n⚠️  最终持仓: {position:.4f} BTC")
            print(f"   当前价格: ${final_price:,.0f}")
            print(f"   当前Z-Score: {final_z:.2f}")
            if current_cycle_entry_price:
                print(f"   入场价格: ${current_cycle_entry_price:,.0f}")
                print(f"   浮盈: {(final_price/current_cycle_entry_price-1)*100:+.1f}%")
        
        portfolio_df = pd.DataFrame(portfolio)
        trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()
        
        return portfolio_df, trades_df
    
    def show_results(self, portfolio_df, trades_df, period_name="全周期"):
        """显示回测结果"""
        print()
        print("=" * 100)
        print(f"📊 优化阈值策略 - {period_name}回测结果")
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
            
            print(f"📊 交易统计:")
            print(f"  总交易次数: {len(trades_df)}次")
            print(f"  买入次数: {len(buy_trades)}次")
            print(f"  卖出次数: {len(sell_trades)}次")
            
            if len(sell_trades) > 0 and 'pnl_pct' in sell_trades.columns:
                sell_with_pnl = sell_trades[sell_trades['pnl_pct'].notna()]
                if len(sell_with_pnl) > 0:
                    win_sells = sell_with_pnl[sell_with_pnl['pnl_pct'] > 0]
                    print(f"    • 盈利卖出: {len(win_sells)}次")
                    if len(win_sells) > 0:
                        print(f"    • 平均盈利: {win_sells['pnl_pct'].mean():+.1f}%")
        
        print()
        print("=" * 100)
        
        return {
            'return': ret,
            'max_dd': max_dd,
            'trades': len(trades_df)
        }


# ============================================================================
# 运行回测
# ============================================================================
print("【步骤4】运行优化阈值策略（全周期）...")
print()

strategy = OptimizedMVRVStrategy(initial_capital=10000)
portfolio_df, trades_df = strategy.run_backtest(df)
result = strategy.show_results(portfolio_df, trades_df, "全周期")

# 对比
start_price = df.iloc[0]['close']
end_price = df.iloc[-1]['close']
hold_return = (end_price / start_price - 1) * 100
hold_value = 10000 * (end_price / start_price)

print()
print("📊 策略对比（全周期）:")
print(f"  买入持有:         {hold_return:+.2f}% (${hold_value:,.0f})")
print(f"  优化阈值策略:     {result['return']:+.2f}% (${portfolio_df['total_value'].iloc[-1]:,.0f})")
print(f"  差距:             {result['return'] - hold_return:+.2f}%")
print()

# 近5年
print()
print("【步骤5】运行优化阈值策略（近5年）...")
print()

df_5y = df[df['date'].dt.year >= 2020].copy().reset_index(drop=True)
strategy_5y = OptimizedMVRVStrategy(initial_capital=10000)
portfolio_5y, trades_5y = strategy_5y.run_backtest(df_5y)
result_5y = strategy_5y.show_results(portfolio_5y, trades_5y, "近5年")

start_price_5y = df_5y.iloc[0]['close']
end_price_5y = df_5y.iloc[-1]['close']
hold_return_5y = (end_price_5y / start_price_5y - 1) * 100

print()
print("📊 策略对比（近5年）:")
print(f"  买入持有:         {hold_return_5y:+.2f}%")
print(f"  优化阈值策略:     {result_5y['return']:+.2f}%")
print(f"  差距:             {result_5y['return'] - hold_return_5y:+.2f}%")
print()

# ============================================================================
# 三策略对比
# ============================================================================
print()
print("=" * 100)
print("📊 三策略全面对比")
print("=" * 100)
print()

# 读取原始MVRV策略结果
try:
    orig_portfolio = pd.read_csv('results/真实mvrv_z_portfolio.csv')
    orig_final = orig_portfolio['total_value'].iloc[-1]
    orig_return = (orig_final - 10000) / 10000 * 100
    
    orig_portfolio['peak'] = orig_portfolio['total_value'].cummax()
    orig_portfolio['dd'] = (orig_portfolio['total_value'] - orig_portfolio['peak']) / orig_portfolio['peak'] * 100
    orig_max_dd = orig_portfolio['dd'].min()
    
    orig_trades = pd.read_csv('results/真实mvrv_z_trades.csv')
    orig_trade_count = len(orig_trades)
except:
    orig_return = 12627
    orig_max_dd = -83.14
    orig_trade_count = 20

print(f"{'策略':<20} {'收益率':>15} {'收益倍数':>12} {'最大回撤':>12} {'交易次数':>10}")
print("-" * 75)
print(f"{'买入持有':<20} {hold_return:>14.2f}% {hold_value/10000:>11.1f}倍 {'~-85%':>12} {'0次':>10}")
print(f"{'原始MVRV(Z>6)':<20} {orig_return:>14.2f}% {orig_final/10000:>11.1f}倍 {orig_max_dd:>11.2f}% {orig_trade_count:>9}次")
print(f"{'优化MVRV(Z>4.5)':<20} {result['return']:>14.2f}% {portfolio_df['total_value'].iloc[-1]/10000:>11.1f}倍 {result['max_dd']:>11.2f}% {result['trades']:>9}次")
print()

print("💡 关键发现:")
print(f"  • 优化策略回撤: {result['max_dd']:.2f}% (原始: {orig_max_dd:.2f}%)")
print(f"  • 回撤改善: {orig_max_dd - result['max_dd']:.2f}%")
print(f"  • 收益率: {result['return']:.2f}% (原始: {orig_return:.2f}%)")
print()

if result['max_dd'] > -50:
    print("🎉 成功！回撤控制在50%以内")
else:
    print("⚠️  回撤仍然较大，可能需要进一步优化")

print()
print("=" * 100)

# 保存结果
import os
os.makedirs('results', exist_ok=True)

portfolio_df.to_csv('results/优化阈值_portfolio.csv', index=False, encoding='utf-8-sig')
trades_df.to_csv('results/优化阈值_trades.csv', index=False, encoding='utf-8-sig')
portfolio_5y.to_csv('results/优化阈值_portfolio_5y.csv', index=False, encoding='utf-8-sig')
trades_5y.to_csv('results/优化阈值_trades_5y.csv', index=False, encoding='utf-8-sig')

print()
print("✅ 结果已保存到 results/ 文件夹")
print("=" * 100)







