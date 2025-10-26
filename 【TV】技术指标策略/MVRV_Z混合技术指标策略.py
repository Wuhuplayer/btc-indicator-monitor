#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MVRV Z-Score + 技术指标混合策略
结合链上数据和技术分析，实现更灵活的分批卖出

卖出逻辑：
1. MVRV Z-Score作为主要信号（识别高估区间）
2. 技术指标作为辅助确认（RSI、MACD、均线死叉等）
3. 在Z > 4时就开始关注技术指标
4. 技术指标确认顶部时提前卖出
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

print("=" * 100)
print("🎯 MVRV Z-Score + 技术指标混合策略")
print("=" * 100)
print()

# ============================================================================
# 技术指标计算
# ============================================================================
def calculate_technical_indicators(df):
    """计算技术指标"""
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # MACD
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = exp1 - exp2
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    
    # 均线
    df['ma7'] = df['close'].rolling(window=7).mean()
    df['ma25'] = df['close'].rolling(window=25).mean()
    df['ma99'] = df['close'].rolling(window=99).mean()
    
    # 均线死叉
    df['ma_death_cross'] = (df['ma7'] < df['ma25']) & (df['ma7'].shift(1) >= df['ma25'].shift(1))
    
    # 价格相对于MA99的位置
    df['price_above_ma99_pct'] = (df['close'] - df['ma99']) / df['ma99'] * 100
    
    # 成交量变化
    df['volume_ma20'] = df['volume'].rolling(window=20).mean()
    df['volume_spike'] = df['volume'] > df['volume_ma20'] * 2
    
    return df


def check_technical_sell_signals(row, prev_row):
    """检查技术指标卖出信号"""
    signals = []
    
    # 1. RSI超买（>70）
    if row['rsi'] > 70:
        signals.append(f"RSI超买({row['rsi']:.1f})")
    
    # 2. RSI从超买区回落
    if prev_row['rsi'] > 75 and row['rsi'] < prev_row['rsi']:
        signals.append("RSI从超买回落")
    
    # 3. MACD死叉
    if row['macd'] < row['macd_signal'] and prev_row['macd'] >= prev_row['macd_signal']:
        signals.append("MACD死叉")
    
    # 4. MACD柱状图转负
    if row['macd_hist'] < 0 and prev_row['macd_hist'] >= 0:
        signals.append("MACD柱转负")
    
    # 5. 均线死叉
    if row['ma_death_cross']:
        signals.append("MA7/25死叉")
    
    # 6. 价格跌破MA99
    if row['close'] < row['ma99'] and prev_row['close'] >= prev_row['ma99']:
        signals.append("跌破MA99")
    
    # 7. 价格大幅高于MA99后回落
    if prev_row['price_above_ma99_pct'] > 100 and row['price_above_ma99_pct'] < prev_row['price_above_ma99_pct'] - 10:
        signals.append("高位回落")
    
    return signals


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
        'open': btc_hist['Open'],
        'high': btc_hist['High'],
        'low': btc_hist['Low'],
        'close': btc_hist['Close'],
        'volume': btc_hist['Volume']
    })
    
    print(f"✅ 成功加载BTC价格数据: {len(price_df)}条")
except Exception as e:
    print(f"❌ 加载失败: {e}")
    exit(1)

print()
print("【步骤3】合并数据并计算技术指标...")
print()

df = pd.merge(price_df, mvrv_df[['date', 'mvrv', 'mvrv_z_score']], on='date', how='inner')
df = df.sort_values('date').reset_index(drop=True)

# 计算技术指标
df = calculate_technical_indicators(df)
df = df.dropna().reset_index(drop=True)

print(f"✅ 数据准备完成: {len(df)}条")
print(f"   时间范围: {df['date'].min().strftime('%Y-%m-%d')} 至 {df['date'].max().strftime('%Y-%m-%d')}")
print()

# ============================================================================
# 混合策略类
# ============================================================================
class HybridMVRVStrategy:
    """MVRV Z-Score + 技术指标混合策略"""
    
    def __init__(self, initial_capital=10000):
        self.initial_capital = initial_capital
        
        # 买入阈值（保持不变）
        self.buy_levels = [
            (-1.0, 0.20, "极度低估买入20%"),
            (0.0, 0.30, "低估买入30%"),
            (1.0, 0.30, "正常偏低买入30%"),
            (2.0, 0.20, "正常买入20%")
        ]
        
        # 卖出策略（优化）
        # 1. 纯MVRV卖出（Z > 7，极度高估）
        self.mvrv_only_sell = [
            (7.0, 0.30, "MVRV极度高估卖出30%"),
            (8.0, 0.30, "MVRV泡沫卖出30%"),
            (9.0, 0.20, "MVRV极端泡沫卖出20%")
        ]
        
        # 2. MVRV + 技术指标混合卖出（4 < Z < 7）
        # 在这个区间，需要技术指标确认
        self.hybrid_sell_z_range = (4.0, 7.0)
        self.hybrid_sell_amounts = [0.15, 0.20, 0.25]  # 分3次卖出
    
    def run_backtest(self, df):
        """运行回测"""
        print("=" * 100)
        print("🚀 MVRV Z-Score + 技术指标混合策略回测")
        print("=" * 100)
        print()
        
        cash = self.initial_capital
        position = 0
        
        trades = []
        portfolio = []
        
        buy_triggered = {-1.0: False, 0.0: False, 1.0: False, 2.0: False}
        mvrv_sell_triggered = {7.0: False, 8.0: False, 9.0: False}
        hybrid_sell_count = 0  # 混合卖出次数
        
        current_cycle_entry_price = None
        in_hybrid_zone = False  # 是否在混合卖出区间
        
        for i in range(1, len(df)):
            row = df.iloc[i]
            prev_row = df.iloc[i-1]
            date = row['date']
            price = row['close']
            z_score = row['mvrv_z_score']
            
            total_value = cash + position * price
            
            # === 买入逻辑（保持不变）===
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
                            
                            trades.append({
                                'date': date,
                                'type': 'BUY',
                                'price': price,
                                'z_score': z_score,
                                'reason': reason,
                                'position': position,
                                'signals': ''
                            })
                            
                            print(f"  🟢 {reason}: {date.strftime('%Y-%m-%d')} @ ${price:,.0f}, Z={z_score:.2f}")
                            break
            
            # 重置买入标记
            if z_score > 3:
                buy_triggered = {-1.0: False, 0.0: False, 1.0: False, 2.0: False}
            
            # === 卖出逻辑（优化）===
            if position > 0.01:
                
                # 方案1: 纯MVRV卖出（Z > 7）
                if z_score >= 7.0:
                    for threshold, sell_pct, reason in self.mvrv_only_sell:
                        if z_score >= threshold and not mvrv_sell_triggered[threshold]:
                            sell_position = position * sell_pct
                            sell_value = sell_position * price
                            position -= sell_position
                            cash += sell_value
                            mvrv_sell_triggered[threshold] = True
                            
                            pnl_pct = (price / current_cycle_entry_price - 1) * 100 if current_cycle_entry_price else 0
                            
                            trades.append({
                                'date': date,
                                'type': 'SELL',
                                'price': price,
                                'z_score': z_score,
                                'reason': reason,
                                'position': position,
                                'pnl_pct': pnl_pct,
                                'signals': 'MVRV极度高估'
                            })
                            
                            print(f"  🔴 {reason}: {date.strftime('%Y-%m-%d')} @ ${price:,.0f}, Z={z_score:.2f}, 盈利{pnl_pct:+.1f}%")
                            
                            if position < 0.01:
                                current_cycle_entry_price = None
                                hybrid_sell_count = 0
                            
                            break
                
                # 方案2: MVRV + 技术指标混合卖出（4 < Z < 7）
                elif self.hybrid_sell_z_range[0] < z_score < self.hybrid_sell_z_range[1]:
                    if not in_hybrid_zone:
                        in_hybrid_zone = True
                        print(f"  ⚠️  进入混合卖出区间: {date.strftime('%Y-%m-%d')}, Z={z_score:.2f}")
                    
                    # 检查技术指标
                    tech_signals = check_technical_sell_signals(row, prev_row)
                    
                    # 如果有2个以上技术信号，且还没卖完3次
                    if len(tech_signals) >= 2 and hybrid_sell_count < len(self.hybrid_sell_amounts):
                        sell_pct = self.hybrid_sell_amounts[hybrid_sell_count]
                        sell_position = position * sell_pct
                        sell_value = sell_position * price
                        position -= sell_position
                        cash += sell_value
                        hybrid_sell_count += 1
                        
                        pnl_pct = (price / current_cycle_entry_price - 1) * 100 if current_cycle_entry_price else 0
                        
                        signals_str = '+'.join(tech_signals[:2])
                        reason = f"混合卖出{int(sell_pct*100)}%({signals_str})"
                        
                        trades.append({
                            'date': date,
                            'type': 'SELL',
                            'price': price,
                            'z_score': z_score,
                            'reason': reason,
                            'position': position,
                            'pnl_pct': pnl_pct,
                            'signals': signals_str
                        })
                        
                        print(f"  🟡 {reason}: {date.strftime('%Y-%m-%d')} @ ${price:,.0f}, Z={z_score:.2f}, 盈利{pnl_pct:+.1f}%")
                        
                        if position < 0.01:
                            current_cycle_entry_price = None
                            hybrid_sell_count = 0
                            in_hybrid_zone = False
                
                else:
                    # 离开混合区间
                    if in_hybrid_zone and z_score < self.hybrid_sell_z_range[0]:
                        in_hybrid_zone = False
                        hybrid_sell_count = 0
                        print(f"  ℹ️  离开混合卖出区间: {date.strftime('%Y-%m-%d')}, Z={z_score:.2f}")
            
            # 重置MVRV卖出标记
            if z_score < 6:
                mvrv_sell_triggered = {7.0: False, 8.0: False, 9.0: False}
            
            # 记录组合价值
            total_value = cash + position * price
            portfolio.append({
                'date': date,
                'price': price,
                'z_score': z_score,
                'rsi': row['rsi'],
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
                print(f"   浮盈: {(final_price/current_cycle_entry_price-1)*100:+.1f}%")
        
        portfolio_df = pd.DataFrame(portfolio)
        trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()
        
        return portfolio_df, trades_df
    
    def show_results(self, portfolio_df, trades_df, period_name="全周期"):
        """显示回测结果"""
        print()
        print("=" * 100)
        print(f"📊 混合策略 - {period_name}回测结果")
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
            
            if len(sell_trades) > 0:
                # 统计不同类型的卖出
                mvrv_sells = sell_trades[sell_trades['reason'].str.contains('MVRV')]
                hybrid_sells = sell_trades[sell_trades['reason'].str.contains('混合')]
                
                print(f"    • MVRV卖出: {len(mvrv_sells)}次")
                print(f"    • 混合卖出: {len(hybrid_sells)}次")
        
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
print("【步骤4】运行混合策略（全周期）...")
print()

strategy = HybridMVRVStrategy(initial_capital=10000)
portfolio_df, trades_df = strategy.run_backtest(df)
result = strategy.show_results(portfolio_df, trades_df, "全周期")

# 对比
start_price = df.iloc[0]['close']
end_price = df.iloc[-1]['close']
hold_return = (end_price / start_price - 1) * 100
hold_value = 10000 * (end_price / start_price)

print()
print("📊 策略对比（全周期）:")
print(f"  买入持有:     {hold_return:+.2f}% (${hold_value:,.0f})")
print(f"  混合策略:     {result['return']:+.2f}% (${portfolio_df['total_value'].iloc[-1]:,.0f})")
print(f"  差距:         {result['return'] - hold_return:+.2f}%")
print()

# 近5年
print()
print("【步骤5】运行混合策略（近5年）...")
print()

df_5y = df[df['date'].dt.year >= 2020].copy().reset_index(drop=True)
strategy_5y = HybridMVRVStrategy(initial_capital=10000)
portfolio_5y, trades_5y = strategy_5y.run_backtest(df_5y)
result_5y = strategy_5y.show_results(portfolio_5y, trades_5y, "近5年")

start_price_5y = df_5y.iloc[0]['close']
end_price_5y = df_5y.iloc[-1]['close']
hold_return_5y = (end_price_5y / start_price_5y - 1) * 100

print()
print("📊 策略对比（近5年）:")
print(f"  买入持有:     {hold_return_5y:+.2f}%")
print(f"  混合策略:     {result_5y['return']:+.2f}%")
print(f"  差距:         {result_5y['return'] - hold_return_5y:+.2f}%")
print()

# 保存结果
import os
os.makedirs('results', exist_ok=True)

portfolio_df.to_csv('results/混合策略_portfolio.csv', index=False, encoding='utf-8-sig')
trades_df.to_csv('results/混合策略_trades.csv', index=False, encoding='utf-8-sig')
portfolio_5y.to_csv('results/混合策略_portfolio_5y.csv', index=False, encoding='utf-8-sig')
trades_5y.to_csv('results/混合策略_trades_5y.csv', index=False, encoding='utf-8-sig')

print("=" * 100)
print("✅ 结果已保存到 results/ 文件夹")
print("=" * 100)






