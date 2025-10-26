#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MVRV Z-Score策略 - 使用真实链上数据
数据来源: CoinMetrics Community API

真实MVRV Z-Score计算:
- Market Cap: 市值（价格 × 流通量）
- Realized Cap: 实现市值（每个币按最后移动时的价格计算）
- MVRV Z-Score: (Market Cap - Realized Cap) / std(Market Cap)
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

print("=" * 100)
print("🎯 MVRV Z-Score策略 - 使用真实链上数据")
print("=" * 100)
print()

# ============================================================================
# 加载真实MVRV数据
# ============================================================================
print("【步骤1】加载真实MVRV Z-Score数据...")
print()

try:
    mvrv_df = pd.read_csv('results/真实MVRV_Z_Score数据_CoinMetrics.csv')
    mvrv_df['date'] = pd.to_datetime(mvrv_df['date']).dt.tz_localize(None)
    
    print(f"✅ 成功加载真实MVRV数据")
    print(f"   数据条数: {len(mvrv_df)}")
    print(f"   时间范围: {mvrv_df['date'].min().strftime('%Y-%m-%d')} 至 {mvrv_df['date'].max().strftime('%Y-%m-%d')}")
    print(f"   MVRV范围: {mvrv_df['mvrv'].min():.2f} - {mvrv_df['mvrv'].max():.2f}")
    print(f"   MVRV Z-Score范围: {mvrv_df['mvrv_z_score'].min():.2f} - {mvrv_df['mvrv_z_score'].max():.2f}")
    print()
    
except Exception as e:
    print(f"❌ 加载失败: {e}")
    print("   请先运行 '爬取真实MVRV数据.py' 获取数据")
    exit(1)

# ============================================================================
# 加载BTC价格数据
# ============================================================================
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
    
    print(f"✅ 成功加载BTC价格数据")
    print(f"   数据条数: {len(price_df)}")
    print(f"   时间范围: {price_df['date'].min().strftime('%Y-%m-%d')} 至 {price_df['date'].max().strftime('%Y-%m-%d')}")
    print(f"   价格范围: ${price_df['close'].min():,.2f} - ${price_df['close'].max():,.2f}")
    print()
    
except Exception as e:
    print(f"❌ 加载失败: {e}")
    exit(1)

# ============================================================================
# 合并数据
# ============================================================================
print("【步骤3】合并价格和MVRV数据...")
print()

df = pd.merge(price_df, mvrv_df[['date', 'mvrv', 'mvrv_z_score']], on='date', how='inner')
df = df.sort_values('date').reset_index(drop=True)

print(f"✅ 合并完成")
print(f"   最终数据条数: {len(df)}")
print(f"   时间范围: {df['date'].min().strftime('%Y-%m-%d')} 至 {df['date'].max().strftime('%Y-%m-%d')}")
print()

# 显示真实MVRV Z-Score的分布
print("📊 真实MVRV Z-Score分布:")
print()
z_ranges = [
    (df['mvrv_z_score'] < -1, "Z < -1 (极度低估)", "🟢🟢🟢"),
    ((df['mvrv_z_score'] >= -1) & (df['mvrv_z_score'] < 0), "-1 < Z < 0 (低估)", "🟢🟢"),
    ((df['mvrv_z_score'] >= 0) & (df['mvrv_z_score'] < 2), "0 < Z < 2 (正常偏低)", "🟢"),
    ((df['mvrv_z_score'] >= 2) & (df['mvrv_z_score'] < 4), "2 < Z < 4 (正常)", "⚪"),
    ((df['mvrv_z_score'] >= 4) & (df['mvrv_z_score'] < 6), "4 < Z < 6 (偏高)", "🟡"),
    ((df['mvrv_z_score'] >= 6) & (df['mvrv_z_score'] < 8), "6 < Z < 8 (高估)", "🔴"),
    (df['mvrv_z_score'] >= 8, "Z > 8 (极度高估)", "🔴🔴")
]

for condition, label, indicator in z_ranges:
    count = condition.sum()
    pct = count / len(df) * 100
    bar = '█' * int(pct / 2)
    print(f"{indicator} {label:<25}: {count:>4}天 ({pct:>5.1f}%) {bar}")

print()
print()

# ============================================================================
# 策略类
# ============================================================================
class RealMVRVZStrategy:
    """基于真实MVRV Z-Score的策略"""
    
    def __init__(self, initial_capital=10000):
        self.initial_capital = initial_capital
        
        # 根据真实数据调整买入阈值
        self.buy_levels = [
            (-1.0, 0.20, "极度低估买入20%"),
            (0.0, 0.30, "低估买入30%"),
            (1.0, 0.30, "正常偏低买入30%"),
            (2.0, 0.20, "正常买入20%")
        ]
        
        # 根据真实数据调整卖出阈值
        self.sell_levels = [
            (6.0, 0.20, "高估卖出20%"),
            (7.0, 0.30, "深度高估卖出30%"),
            (8.0, 0.30, "极度高估卖出30%"),
            (9.0, 0.20, "泡沫区卖出20%")
        ]
    
    def run_backtest(self, df):
        """运行回测"""
        print("=" * 100)
        print("🚀 真实MVRV Z-Score策略回测")
        print("=" * 100)
        print()
        
        cash = self.initial_capital
        position = 0
        
        trades = []
        portfolio = []
        
        buy_triggered = {-1.0: False, 0.0: False, 1.0: False, 2.0: False}
        sell_triggered = {6.0: False, 7.0: False, 8.0: False, 9.0: False}
        
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
                            
                            print(f"  🟢 {reason}: {date.strftime('%Y-%m-%d')} @ ${price:,.0f}, "
                                  f"Z={z_score:.2f}, 仓位{position:.4f} BTC")
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
                        
                        print(f"  🔴 {reason}: {date.strftime('%Y-%m-%d')} @ ${price:,.0f}, "
                              f"Z={z_score:.2f}, 盈利{pnl_pct:+.1f}%, 剩余{position:.4f} BTC")
                        
                        if position < 0.01:
                            current_cycle_entry_price = None
                            current_cycle_entry_date = None
                        
                        break
            
            # 重置卖出标记
            if z_score < 5:
                sell_triggered = {6.0: False, 7.0: False, 8.0: False, 9.0: False}
            
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
        print(f"📊 真实MVRV Z-Score策略 - {period_name}回测结果")
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
            print()
            
            if len(sell_trades) > 0 and 'pnl_pct' in sell_trades.columns:
                sell_with_pnl = sell_trades[sell_trades['pnl_pct'].notna()]
                if len(sell_with_pnl) > 0:
                    win_sells = sell_with_pnl[sell_with_pnl['pnl_pct'] > 0]
                    print(f"  盈利卖出: {len(win_sells)}次")
                    if len(win_sells) > 0:
                        print(f"  💚 平均盈利: {win_sells['pnl_pct'].mean():+.1f}%")
                        print(f"  💚 最大盈利: {win_sells['pnl_pct'].max():+.1f}%")
        
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
print("【步骤4】运行真实MVRV Z策略（全周期）...")
print()

strategy = RealMVRVZStrategy(initial_capital=10000)
portfolio_df, trades_df = strategy.run_backtest(df)
result = strategy.show_results(portfolio_df, trades_df, "全周期")

# 对比买入持有
start_price = df.iloc[0]['close']
end_price = df.iloc[-1]['close']
hold_return = (end_price / start_price - 1) * 100
hold_value = 10000 * (end_price / start_price)

print()
print("📊 对比买入持有（全周期）:")
print(f"  买入持有:         {hold_return:+.2f}% (${hold_value:,.0f})")
print(f"  真实MVRV Z策略:   {result['return']:+.2f}% (${portfolio_df['total_value'].iloc[-1]:,.0f})")
print(f"  差距:             {result['return'] - hold_return:+.2f}%")
print()

if result['return'] > hold_return:
    print(f"🎉 真实MVRV Z策略超越买入持有 {result['return'] - hold_return:+.2f}%！")
else:
    print(f"⚠️  真实MVRV Z策略跑输买入持有 {hold_return - result['return']:.2f}%")

print()
print("=" * 100)

# ============================================================================
# 近5年回测
# ============================================================================
print()
print("【步骤5】运行真实MVRV Z策略（近5年）...")
print()

df_5y = df[df['date'].dt.year >= 2020].copy().reset_index(drop=True)
print(f"📊 近5年数据: {len(df_5y)}天 ({df_5y['date'].min().strftime('%Y-%m-%d')} 至 {df_5y['date'].max().strftime('%Y-%m-%d')})")
print()

strategy_5y = RealMVRVZStrategy(initial_capital=10000)
portfolio_5y, trades_5y = strategy_5y.run_backtest(df_5y)
result_5y = strategy_5y.show_results(portfolio_5y, trades_5y, "近5年")

# 对比买入持有（近5年）
start_price_5y = df_5y.iloc[0]['close']
end_price_5y = df_5y.iloc[-1]['close']
hold_return_5y = (end_price_5y / start_price_5y - 1) * 100
hold_value_5y = 10000 * (end_price_5y / start_price_5y)

print()
print("📊 对比买入持有（近5年）:")
print(f"  买入持有:         {hold_return_5y:+.2f}% (${hold_value_5y:,.0f})")
print(f"  真实MVRV Z策略:   {result_5y['return']:+.2f}% (${portfolio_5y['total_value'].iloc[-1]:,.0f})")
print(f"  差距:             {result_5y['return'] - hold_return_5y:+.2f}%")
print()

if result_5y['return'] > hold_return_5y:
    print(f"🎉 近5年真实MVRV Z策略超越买入持有 {result_5y['return'] - hold_return_5y:+.2f}%！")
else:
    print(f"⚠️  近5年真实MVRV Z策略跑输买入持有 {hold_return_5y - result_5y['return']:.2f}%")

print()
print("=" * 100)

# ============================================================================
# 对比表格
# ============================================================================
print()
print("📊 全周期 vs 近5年对比:")
print()
print(f"{'指标':<20} {'全周期':>20} {'近5年':>20}")
print("-" * 65)
print(f"{'收益率':<20} {result['return']:>19.2f}% {result_5y['return']:>19.2f}%")
print(f"{'最大回撤':<20} {result['max_dd']:>19.2f}% {result_5y['max_dd']:>19.2f}%")
print(f"{'交易次数':<20} {result['trades']:>19}次 {result_5y['trades']:>19}次")
print(f"{'vs买入持有':<20} {result['return']-hold_return:>19.2f}% {result_5y['return']-hold_return_5y:>19.2f}%")
print()
print("=" * 100)

# 保存结果
import os
os.makedirs('results', exist_ok=True)

portfolio_df.to_csv('results/真实mvrv_z_portfolio.csv', index=False, encoding='utf-8-sig')
if len(trades_df) > 0:
    trades_df.to_csv('results/真实mvrv_z_trades.csv', index=False, encoding='utf-8-sig')

portfolio_5y.to_csv('results/真实mvrv_z_portfolio_5y.csv', index=False, encoding='utf-8-sig')
if len(trades_5y) > 0:
    trades_5y.to_csv('results/真实mvrv_z_trades_5y.csv', index=False, encoding='utf-8-sig')

print()
print("✅ 结果已保存:")
print("  • results/真实mvrv_z_portfolio.csv (全周期)")
print("  • results/真实mvrv_z_trades.csv (全周期)")
print("  • results/真实mvrv_z_portfolio_5y.csv (近5年)")
print("  • results/真实mvrv_z_trades_5y.csv (近5年)")
print()
print("=" * 100)







