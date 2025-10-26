#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MVRV Z-Score定投定抛策略
- 底部（Z < 0）：每周定投 + 5倍杠杆
- 顶部（Z > 4）：每周定抛
- 中间区域：持有不动
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

print("=" * 100)
print("🎯 MVRV Z-Score定投定抛策略")
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
    btc_hist = btc.history(start='2020-01-01', end='2025-12-31')
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
# 定投定抛策略类
# ============================================================================
class DCAPlusStrategy:
    """定投定抛策略"""
    
    def __init__(self, initial_capital=10000):
        self.initial_capital = initial_capital
        
        # 定投参数
        self.dca_interval_days = 7  # 每周定投
        self.dca_amount = 200  # 每次定投$200
        self.dca_leverage = 5.0  # 5倍杠杆
        
        # 定抛参数
        self.sell_interval_days = 7  # 每周定抛
        self.sell_pct = 0.05  # 每次卖出5%持仓
        
        # Z-Score阈值
        self.dca_zone = 0.0  # Z < 0 定投
        self.sell_zone = 4.0  # Z > 4 定抛
        
        # 杠杆利息
        self.interest_rate = 0.08  # 8%年化
    
    def run_backtest(self, df):
        """运行回测"""
        print("=" * 100)
        print("🚀 定投定抛策略回测")
        print("=" * 100)
        print()
        
        cash = self.initial_capital
        position = 0
        borrowed = 0
        
        trades = []
        portfolio = []
        
        last_dca_date = None
        last_sell_date = None
        
        for i in range(1, len(df)):
            row = df.iloc[i]
            prev_row = df.iloc[i-1]
            date = row['date']
            price = row['close']
            z_score = row['mvrv_z_score']
            
            # 计算利息
            if borrowed > 0:
                days = (row['date'] - prev_row['date']).days
                interest = borrowed * (self.interest_rate / 365) * days
                cash -= interest
            
            # === 底部定投（Z < 0）===
            if z_score < self.dca_zone:
                # 检查是否到了定投时间
                if last_dca_date is None or (date - last_dca_date).days >= self.dca_interval_days:
                    if cash > self.dca_amount:
                        # 使用杠杆定投
                        actual_buy_value = self.dca_amount * self.dca_leverage
                        borrow_amount = self.dca_amount * (self.dca_leverage - 1)
                        
                        buy_position = actual_buy_value / price
                        position += buy_position
                        cash -= self.dca_amount
                        borrowed += borrow_amount
                        last_dca_date = date
                        
                        trades.append({
                            'date': date,
                            'type': 'DCA',
                            'price': price,
                            'z_score': z_score,
                            'amount': actual_buy_value,
                            'position': position,
                            'borrowed': borrowed
                        })
                        
                        print(f"  🟢 定投: {date.strftime('%Y-%m-%d')} @ ${price:,.0f}, Z={z_score:.2f}, 买入${actual_buy_value:,.0f}(5x杠杆)")
            
            # === 顶部定抛（Z > 4）===
            elif z_score > self.sell_zone and position > 0.01:
                # 检查是否到了定抛时间
                if last_sell_date is None or (date - last_sell_date).days >= self.sell_interval_days:
                    sell_position = position * self.sell_pct
                    sell_value = sell_position * price
                    position -= sell_position
                    cash += sell_value
                    
                    # 优先还款
                    if borrowed > 0:
                        repay = min(borrowed, sell_value * 0.5)
                        borrowed -= repay
                        cash -= repay
                    
                    last_sell_date = date
                    
                    trades.append({
                        'date': date,
                        'type': 'SELL',
                        'price': price,
                        'z_score': z_score,
                        'amount': sell_value,
                        'position': position,
                        'borrowed': borrowed
                    })
                    
                    print(f"  🔴 定抛: {date.strftime('%Y-%m-%d')} @ ${price:,.0f}, Z={z_score:.2f}, 卖出{self.sell_pct*100:.0f}%, 剩余{position:.4f} BTC, 借款${borrowed:,.0f}")
            
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
        
        # 最终状态
        final_price = df.iloc[-1]['close']
        final_z = df.iloc[-1]['mvrv_z_score']
        final_value = cash + position * final_price - borrowed
        
        print()
        print(f"📊 最终状态:")
        print(f"   持仓: {position:.4f} BTC (价值${position * final_price:,.0f})")
        print(f"   现金: ${cash:,.0f}")
        print(f"   借款: ${borrowed:,.0f}")
        print(f"   净值: ${final_value:,.0f}")
        print(f"   当前价格: ${final_price:,.0f}")
        print(f"   当前Z-Score: {final_z:.2f}")
        
        portfolio_df = pd.DataFrame(portfolio)
        trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()
        
        return portfolio_df, trades_df
    
    def show_results(self, portfolio_df, trades_df):
        """显示回测结果"""
        print()
        print("=" * 100)
        print("📊 定投定抛策略 - 近5年回测结果")
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
            dca_trades = trades_df[trades_df['type'] == 'DCA']
            sell_trades = trades_df[trades_df['type'] == 'SELL']
            
            print(f"📊 交易统计:")
            print(f"  总交易次数: {len(trades_df)}次")
            print(f"  定投次数: {len(dca_trades)}次")
            print(f"  定抛次数: {len(sell_trades)}次")
            
            if len(dca_trades) > 0:
                total_dca = dca_trades['amount'].sum()
                avg_dca_price = (dca_trades['amount'] / dca_trades['amount'].sum() * dca_trades['price']).sum()
                print(f"  总定投金额: ${total_dca:,.0f}")
                print(f"  平均买入价: ${avg_dca_price:,.0f}")
            
            if len(sell_trades) > 0:
                total_sell = sell_trades['amount'].sum()
                avg_sell_price = (sell_trades['amount'] / sell_trades['amount'].sum() * sell_trades['price']).sum()
                print(f"  总卖出金额: ${total_sell:,.0f}")
                print(f"  平均卖出价: ${avg_sell_price:,.0f}")
            
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
# 运行回测
# ============================================================================
print("【步骤2】运行定投定抛策略（近5年）...")
print()

strategy = DCAPlusStrategy(initial_capital=10000)
portfolio_df, trades_df = strategy.run_backtest(df)
result = strategy.show_results(portfolio_df, trades_df)

# 对比
start_price = df.iloc[0]['close']
end_price = df.iloc[-1]['close']
hold_return = (end_price / start_price - 1) * 100

print()
print("📊 策略对比（近5年）:")
print()
print(f"{'策略':<30} {'收益率':>15} {'收益倍数':>12} {'最大回撤':>12}")
print("-" * 75)
print(f"{'买入持有':<30} {hold_return:>14.2f}% {end_price/start_price:>11.1f}倍 {'~-77%':>12}")
print(f"{'5倍杠杆MVRV(分批)':<30} {'1569.23%':>14} {'16.7倍':>12} {'-53.15%':>12}")
print(f"{'定投定抛(5x杠杆)':<30} {result['return']:>14.2f}% {result['final_value']/10000:>11.1f}倍 {result['max_dd']:>11.2f}%")

print()
print("💡 关键发现:")
print(f"  • 定投定抛收益: {result['final_value']/10000:.1f}倍")
print(f"  • vs 买入持有: {result['return'] - hold_return:+.2f}%")
print(f"  • 最大回撤: {result['max_dd']:.2f}%")
print()

if result['final_value']/10000 > 15:
    print("🎉 太棒了！收益超过15倍")
elif result['final_value']/10000 > 10:
    print("✅ 不错！收益超过10倍")
else:
    print("⚠️  收益未达到10倍目标")

if result['max_dd'] > -40:
    print("🌟 优秀！回撤控制在40%以内")
elif result['max_dd'] > -50:
    print("✅ 良好！回撤控制在50%以内")
else:
    print("⚠️  回撤较大，超过50%")

print()
print("=" * 100)
print()
print("📋 策略说明:")
print()
print("【定投规则】")
print("  • 触发条件: MVRV Z-Score < 0（低估区间）")
print("  • 定投频率: 每周一次")
print("  • 定投金额: $200/次")
print("  • 使用杠杆: 5倍（实际买入$1,000）")
print()
print("【定抛规则】")
print("  • 触发条件: MVRV Z-Score > 4（高估区间）")
print("  • 定抛频率: 每周一次")
print("  • 定抛比例: 5%持仓")
print("  • 优先还款: 卖出金额的50%用于还款")
print()
print("【持有规则】")
print("  • 0 < Z < 4: 持有不动")
print()
print("=" * 100)

# 保存结果
import os
os.makedirs('results', exist_ok=True)

portfolio_df.to_csv('results/定投定抛_portfolio_5y.csv', index=False, encoding='utf-8-sig')
trades_df.to_csv('results/定投定抛_trades_5y.csv', index=False, encoding='utf-8-sig')

print()
print("✅ 结果已保存到 results/ 文件夹")
print("=" * 100)






