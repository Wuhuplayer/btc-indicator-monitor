#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MVRV Z-Score策略 - 低估买入，高估卖出
基于链上数据的价值投资策略

MVRV Z-Score说明：
- MVRV = Market Value / Realized Value（市值/实现市值）
- Z-Score = (Market Cap - Realized Cap) / Std(Market Cap)
- 衡量BTC相对于其"公允价值"的偏离程度

策略逻辑：
1. 低估区间（Z < 0）：分批买入
   - Z < -0.5: 买入20%
   - Z < -1.0: 再买入30%
   - Z < -1.5: 再买入30%
   - Z < -2.0: 再买入20%

2. 高估区间（Z > 5）：分批卖出
   - Z > 5.0: 卖出20%
   - Z > 6.0: 卖出30%
   - Z > 7.0: 卖出30%
   - Z > 8.0: 卖出20%

3. 中性区间（0 < Z < 5）：持有不动
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
import yfinance as yf
from datetime import datetime

sys.path.append(str(Path(__file__).parent))


def get_btc_data():
    """获取BTC价格数据"""
    print("📈 获取BTC历史数据...")
    
    try:
        btc = yf.Ticker('BTC-USD')
        btc_hist = btc.history(start='2014-09-17', end='2024-12-31')
        
        if len(btc_hist) > 100:
            btc_hist = btc_hist.reset_index()
            df = pd.DataFrame({
                'date': btc_hist['Date'],
                'open': btc_hist['Open'],
                'high': btc_hist['High'],
                'low': btc_hist['Low'],
                'close': btc_hist['Close'],
                'volume': btc_hist['Volume']
            })
            df['date'] = pd.to_datetime(df['date'])
            
            print(f"✅ 获取BTC数据: {len(df)}条")
            print(f"   时间范围: {df['date'].min().strftime('%Y-%m-%d')} 至 {df['date'].max().strftime('%Y-%m-%d')}")
            print(f"   价格范围: ${df['close'].min():,.2f} - ${df['close'].max():,.2f}")
            return df
    except Exception as e:
        print(f"❌ 获取数据失败: {e}")
        return None


def calculate_mvrv_z_score(df):
    """
    计算MVRV Z-Score
    
    由于无法获取真实的链上数据（Realized Cap），我们使用简化模型：
    1. 使用200日移动平均作为"实现价格"的代理
    2. Z-Score = (Price - MA200) / Std(Price, 200)
    
    这个简化模型能捕捉价格相对于长期均值的偏离程度
    """
    print("📊 计算MVRV Z-Score...")
    
    # 方法1：使用MA200作为实现价格
    df['ma200'] = df['close'].rolling(window=200).mean()
    df['price_std_200'] = df['close'].rolling(window=200).std()
    
    # 计算Z-Score
    df['mvrv_z'] = (df['close'] - df['ma200']) / df['price_std_200']
    
    # 填充NaN
    df['mvrv_z'] = df['mvrv_z'].fillna(0)
    
    print("✅ MVRV Z-Score计算完成")
    print(f"   Z-Score范围: {df['mvrv_z'].min():.2f} 至 {df['mvrv_z'].max():.2f}")
    print(f"   平均值: {df['mvrv_z'].mean():.2f}")
    
    # 统计分布
    print(f"\n   分布统计:")
    print(f"   Z < -1 (极度低估): {(df['mvrv_z'] < -1).sum()}天 ({(df['mvrv_z'] < -1).sum()/len(df)*100:.1f}%)")
    print(f"   -1 < Z < 0 (低估): {((df['mvrv_z'] >= -1) & (df['mvrv_z'] < 0)).sum()}天 ({((df['mvrv_z'] >= -1) & (df['mvrv_z'] < 0)).sum()/len(df)*100:.1f}%)")
    print(f"   0 < Z < 3 (正常): {((df['mvrv_z'] >= 0) & (df['mvrv_z'] < 3)).sum()}天 ({((df['mvrv_z'] >= 0) & (df['mvrv_z'] < 3)).sum()/len(df)*100:.1f}%)")
    print(f"   3 < Z < 5 (偏高): {((df['mvrv_z'] >= 3) & (df['mvrv_z'] < 5)).sum()}天 ({((df['mvrv_z'] >= 3) & (df['mvrv_z'] < 5)).sum()/len(df)*100:.1f}%)")
    print(f"   Z > 5 (高估): {(df['mvrv_z'] >= 5).sum()}天 ({(df['mvrv_z'] >= 5).sum()/len(df)*100:.1f}%)")
    print(f"   Z > 7 (极度高估): {(df['mvrv_z'] >= 7).sum()}天 ({(df['mvrv_z'] >= 7).sum()/len(df)*100:.1f}%)")
    
    return df


class MVRVZStrategy:
    """MVRV Z-Score策略"""
    
    def __init__(self, initial_capital=10000):
        self.initial_capital = initial_capital
        
        # 买入阈值和比例
        self.buy_levels = [
            (-2.0, 0.20, "极度低估买入20%"),
            (-1.5, 0.30, "深度低估买入30%"),
            (-1.0, 0.30, "低估买入30%"),
            (-0.5, 0.20, "轻度低估买入20%")
        ]
        
        # 卖出阈值和比例
        self.sell_levels = [
            (5.0, 0.20, "高估卖出20%"),
            (6.0, 0.30, "深度高估卖出30%"),
            (7.0, 0.30, "极度高估卖出30%"),
            (8.0, 0.20, "泡沫区卖出20%")
        ]
    
    def run_backtest(self, df):
        """运行回测"""
        print()
        print("=" * 100)
        print("🚀 MVRV Z-Score策略回测")
        print("=" * 100)
        print()
        
        cash = self.initial_capital
        position = 0
        
        trades = []
        portfolio = []
        
        # 记录已触发的买入/卖出级别
        buy_triggered = {-2.0: False, -1.5: False, -1.0: False, -0.5: False}
        sell_triggered = {5.0: False, 6.0: False, 7.0: False, 8.0: False}
        
        # 记录当前周期的入场价（用于计算盈亏）
        current_cycle_entry_price = None
        current_cycle_entry_date = None
        
        for i in range(1, len(df)):
            row = df.iloc[i]
            prev_row = df.iloc[i-1]
            date = row['date']
            price = row['close']
            z_score = row['mvrv_z']
            
            total_value = cash + position * price
            
            # === 买入逻辑（分批买入）===
            if cash > 100:  # 还有现金
                for threshold, buy_pct, reason in self.buy_levels:
                    # 检查是否触发该级别
                    if z_score < threshold and not buy_triggered[threshold]:
                        # 买入
                        buy_value = self.initial_capital * buy_pct
                        if buy_value <= cash:
                            buy_position = buy_value / price
                            position += buy_position
                            cash -= buy_value
                            buy_triggered[threshold] = True
                            
                            # 如果是第一次买入，记录为新周期
                            if current_cycle_entry_price is None:
                                current_cycle_entry_price = price
                                current_cycle_entry_date = date
                            
                            trades.append({
                                'date': date,
                                'type': 'BUY',
                                'price': price,
                                'position_change': buy_position,
                                'cash_change': -buy_value,
                                'z_score': z_score,
                                'reason': reason,
                                'total_position': position,
                                'total_value': total_value
                            })
                            
                            print(f"  🟢 {reason}: {date.strftime('%Y-%m-%d')} @ ${price:,.0f}, "
                                  f"Z={z_score:.2f}, 仓位{position:.4f} BTC")
                            break
            
            # 重置买入标记（当Z-Score回到正常区间）
            if z_score > 0:
                buy_triggered = {-2.0: False, -1.5: False, -1.0: False, -0.5: False}
            
            # === 卖出逻辑（分批卖出）===
            if position > 0.01:  # 有持仓
                for threshold, sell_pct, reason in self.sell_levels:
                    # 检查是否触发该级别
                    if z_score > threshold and not sell_triggered[threshold]:
                        # 卖出
                        sell_position = position * sell_pct
                        sell_value = sell_position * price
                        position -= sell_position
                        cash += sell_value
                        sell_triggered[threshold] = True
                        
                        # 计算盈亏
                        if current_cycle_entry_price:
                            pnl = sell_position * (price - current_cycle_entry_price)
                            pnl_pct = (price / current_cycle_entry_price - 1) * 100
                        else:
                            pnl = 0
                            pnl_pct = 0
                        
                        trades.append({
                            'date': date,
                            'type': 'SELL',
                            'price': price,
                            'position_change': -sell_position,
                            'cash_change': sell_value,
                            'z_score': z_score,
                            'reason': reason,
                            'total_position': position,
                            'total_value': total_value,
                            'pnl': pnl,
                            'pnl_pct': pnl_pct
                        })
                        
                        print(f"  🔴 {reason}: {date.strftime('%Y-%m-%d')} @ ${price:,.0f}, "
                              f"Z={z_score:.2f}, 盈利{pnl_pct:+.1f}%, 剩余{position:.4f} BTC")
                        
                        # 如果全部卖出，结束当前周期
                        if position < 0.01:
                            current_cycle_entry_price = None
                            current_cycle_entry_date = None
                        
                        break
            
            # 重置卖出标记（当Z-Score回到正常区间）
            if z_score < 3:
                sell_triggered = {5.0: False, 6.0: False, 7.0: False, 8.0: False}
            
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
        final_z = df.iloc[-1]['mvrv_z']
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
    
    def show_results(self, portfolio_df, trades_df):
        """显示回测结果"""
        print()
        print("=" * 100)
        print("📊 MVRV Z-Score策略 - 回测结果")
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
            
            if len(sell_trades) > 0:
                sell_with_pnl = sell_trades[sell_trades['pnl'].notna()]
                if len(sell_with_pnl) > 0:
                    win_sells = sell_with_pnl[sell_with_pnl['pnl'] > 0]
                    loss_sells = sell_with_pnl[sell_with_pnl['pnl'] < 0]
                    
                    print(f"  盈利卖出: {len(win_sells)}次")
                    print(f"  亏损卖出: {len(loss_sells)}次")
                    
                    if len(win_sells) > 0:
                        print(f"  💚 平均盈利: {win_sells['pnl_pct'].mean():+.1f}%")
                        print(f"  💚 最大盈利: {win_sells['pnl_pct'].max():+.1f}%")
                    
                    if len(loss_sells) > 0:
                        print(f"  💔 平均亏损: {loss_sells['pnl_pct'].mean():.1f}%")
                        print(f"  💔 最大亏损: {loss_sells['pnl_pct'].min():.1f}%")
            
            print()
            print("📋 买入信号统计:")
            buy_reasons = buy_trades['reason'].value_counts()
            for reason, count in buy_reasons.items():
                avg_z = buy_trades[buy_trades['reason'] == reason]['z_score'].mean()
                print(f"  {reason}: {count}次 (平均Z={avg_z:.2f})")
            
            print()
            print("📋 卖出信号统计:")
            sell_reasons = sell_trades['reason'].value_counts()
            for reason, count in sell_reasons.items():
                avg_z = sell_trades[sell_trades['reason'] == reason]['z_score'].mean()
                avg_pnl = sell_trades[sell_trades['reason'] == reason]['pnl_pct'].mean()
                print(f"  {reason}: {count}次 (平均Z={avg_z:.2f}, 平均盈利{avg_pnl:+.1f}%)")
        
        print()
        print("=" * 100)
        
        return {
            'return': ret,
            'max_dd': max_dd,
            'trades': len(trades_df)
        }


def main():
    print("=" * 100)
    print("🎯 MVRV Z-Score策略 - 低估买入，高估卖出")
    print("=" * 100)
    print()
    
    # 获取数据
    print("【步骤1】加载BTC数据...")
    df = get_btc_data()
    
    if df is None:
        print("❌ 无法获取数据")
        return
    
    print()
    
    # 计算MVRV Z-Score
    print("【步骤2】计算MVRV Z-Score...")
    df = calculate_mvrv_z_score(df)
    print()
    
    # === 全周期回测 ===
    print("【步骤3】运行MVRV Z策略（全周期）...")
    strategy = MVRVZStrategy(initial_capital=10000)
    portfolio_df, trades_df = strategy.run_backtest(df)
    result = strategy.show_results(portfolio_df, trades_df)
    
    # 对比买入持有
    print()
    print("【步骤4】对比买入持有（全周期）...")
    print("=" * 100)
    
    start_price = df.iloc[0]['close']
    end_price = df.iloc[-1]['close']
    hold_return = (end_price / start_price - 1) * 100
    hold_value = 10000 * (end_price / start_price)
    
    print()
    print(f"📊 最终对比（全周期）:")
    print(f"  买入持有:     {hold_return:+.2f}% (${hold_value:,.0f})")
    print(f"  MVRV Z策略:   {result['return']:+.2f}% (${portfolio_df['total_value'].iloc[-1]:,.0f})")
    print(f"  差距:         {result['return'] - hold_return:+.2f}%")
    print()
    
    if result['return'] > hold_return:
        print(f"🎉 MVRV Z策略超越买入持有 {result['return'] - hold_return:+.2f}%！")
    else:
        print(f"⚠️  MVRV Z策略跑输买入持有 {hold_return - result['return']:.2f}%")
        print(f"   但回撤优势: {result['max_dd']:.2f}%")
    
    print()
    
    # 对比ATR策略
    print("vs ATR追踪策略（339倍）:")
    print(f"  ATR策略:      +33,924% ($3,402,432)")
    print(f"  MVRV Z策略:   {result['return']:+.2f}% (${portfolio_df['total_value'].iloc[-1]:,.0f})")
    print(f"  差距:         {result['return'] - 33924.32:+.2f}%")
    print()
    
    print("=" * 100)
    
    # === 近5年回测 ===
    print()
    print()
    print("=" * 100)
    print("🎯 MVRV Z-Score策略 - 近5年回测（2020-2024）")
    print("=" * 100)
    print()
    
    df_5y = df[df['date'].dt.year >= 2020].copy().reset_index(drop=True)
    
    print(f"📊 近5年数据范围: {df_5y['date'].min().strftime('%Y-%m-%d')} 至 {df_5y['date'].max().strftime('%Y-%m-%d')}")
    print(f"   数据条数: {len(df_5y)}天")
    print(f"   价格范围: ${df_5y['close'].min():,.0f} - ${df_5y['close'].max():,.0f}")
    print()
    
    strategy_5y = MVRVZStrategy(initial_capital=10000)
    portfolio_5y, trades_5y = strategy_5y.run_backtest(df_5y)
    result_5y = strategy_5y.show_results(portfolio_5y, trades_5y)
    
    # 对比买入持有（近5年）
    print()
    print("【对比】近5年买入持有...")
    print("=" * 100)
    
    start_price_5y = df_5y.iloc[0]['close']
    end_price_5y = df_5y.iloc[-1]['close']
    hold_return_5y = (end_price_5y / start_price_5y - 1) * 100
    hold_value_5y = 10000 * (end_price_5y / start_price_5y)
    
    print()
    print(f"📊 近5年对比:")
    print(f"  买入持有:     {hold_return_5y:+.2f}% (${hold_value_5y:,.0f})")
    print(f"  MVRV Z策略:   {result_5y['return']:+.2f}% (${portfolio_5y['total_value'].iloc[-1]:,.0f})")
    print(f"  差距:         {result_5y['return'] - hold_return_5y:+.2f}%")
    print()
    
    if result_5y['return'] > hold_return_5y:
        print(f"🎉 近5年MVRV Z策略超越买入持有 {result_5y['return'] - hold_return_5y:+.2f}%！")
    else:
        print(f"⚠️  近5年MVRV Z策略跑输买入持有 {hold_return_5y - result_5y['return']:.2f}%")
        print(f"   但回撤优势: {result_5y['max_dd']:.2f}%")
    
    print()
    print("=" * 100)
    
    # 对比全周期和近5年
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
    
    # 显示关键交易
    if len(trades_df) > 0:
        print()
        print("📋 关键交易记录（前20笔）:")
        print()
        display_cols = ['date', 'type', 'price', 'z_score', 'reason', 'total_position']
        trades_display = trades_df[display_cols].head(20)
        
        for _, trade in trades_display.iterrows():
            trade_type = "🟢买入" if trade['type'] == 'BUY' else "🔴卖出"
            print(f"{trade_type} {trade['date'].strftime('%Y-%m-%d')} @ ${trade['price']:>8,.0f} | "
                  f"Z={trade['z_score']:>6.2f} | {trade['reason']:<20} | 持仓{trade['total_position']:.4f} BTC")
    
    # 保存结果
    import os
    os.makedirs('results', exist_ok=True)
    
    portfolio_df.to_csv('results/mvrv_z_portfolio.csv', index=False, encoding='utf-8-sig')
    if len(trades_df) > 0:
        trades_df.to_csv('results/mvrv_z_trades.csv', index=False, encoding='utf-8-sig')
    
    portfolio_5y.to_csv('results/mvrv_z_portfolio_5y.csv', index=False, encoding='utf-8-sig')
    if len(trades_5y) > 0:
        trades_5y.to_csv('results/mvrv_z_trades_5y.csv', index=False, encoding='utf-8-sig')
    
    print()
    print()
    print("✅ 结果已保存:")
    print("  • results/mvrv_z_portfolio.csv (全周期)")
    print("  • results/mvrv_z_trades.csv (全周期)")
    print("  • results/mvrv_z_portfolio_5y.csv (近5年)")
    print("  • results/mvrv_z_trades_5y.csv (近5年)")
    print()
    print("=" * 100)
    
    # 生成Z-Score分布图
    print()
    print("📊 MVRV Z-Score历史分布:")
    print()
    
    z_ranges = [
        (df['mvrv_z'] < -2, "Z < -2 (极度低估)", "🟢🟢🟢"),
        ((df['mvrv_z'] >= -2) & (df['mvrv_z'] < -1), "-2 < Z < -1 (深度低估)", "🟢🟢"),
        ((df['mvrv_z'] >= -1) & (df['mvrv_z'] < 0), "-1 < Z < 0 (低估)", "🟢"),
        ((df['mvrv_z'] >= 0) & (df['mvrv_z'] < 3), "0 < Z < 3 (正常)", "⚪"),
        ((df['mvrv_z'] >= 3) & (df['mvrv_z'] < 5), "3 < Z < 5 (偏高)", "🟡"),
        ((df['mvrv_z'] >= 5) & (df['mvrv_z'] < 7), "5 < Z < 7 (高估)", "🔴"),
        (df['mvrv_z'] >= 7, "Z > 7 (极度高估)", "🔴🔴")
    ]
    
    for condition, label, indicator in z_ranges:
        count = condition.sum()
        pct = count / len(df) * 100
        bar = '█' * int(pct / 2)
        print(f"{indicator} {label:<25}: {count:>4}天 ({pct:>5.1f}%) {bar}")
    
    print()
    print("=" * 100)


if __name__ == "__main__":
    main()

