#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WaveTrend + 动量组合策略
测试不同wt阈值与动量过滤的组合效果
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
    
    # 1. WaveTrend（TradingView标准）
    n1, n2 = 10, 21
    hlc3 = (df['high'] + df['low'] + df['close']) / 3
    esa = hlc3.ewm(span=n1, adjust=False).mean()
    d = (hlc3 - esa).abs().ewm(span=n1, adjust=False).mean()
    ci = (hlc3 - esa) / (0.015 * d)
    
    df['wt1'] = ci.ewm(span=n2, adjust=False).mean()  # EMA
    df['wt2'] = df['wt1'].rolling(window=4).mean()  # SMA
    
    # 2. 动量指标（多个周期）
    df['momentum_5d'] = df['close'].pct_change(5)
    df['momentum_10d'] = df['close'].pct_change(10)
    df['momentum_20d'] = df['close'].pct_change(20)
    
    # 标准化动量
    df['momentum_20d_norm'] = (df['momentum_20d'] - df['momentum_20d'].mean()) / df['momentum_20d'].std()
    
    # 3. ADX（趋势强度）
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
    
    # 4. 移动平均线（趋势过滤）
    df['ma50'] = df['close'].rolling(window=50).mean()
    df['ma200'] = df['close'].rolling(window=200).mean()
    df['above_ma200'] = df['close'] > df['ma200']
    
    print("✅ 指标计算完成")
    return df


class CombinedStrategy:
    """WaveTrend + 动量组合策略"""
    
    def __init__(self, initial_capital=10000, position_size=0.95, stop_loss=0.10):
        self.initial_capital = initial_capital
        self.position_size = position_size
        self.stop_loss = stop_loss
    
    def generate_signals_v1(self, df, wt_threshold=-30):
        """
        策略V1: WT超卖 + 动量不太负
        买入: wt1<阈值 且 金叉 且 动量>-0.5
        卖出: ADX>20 且 wt1>0 且 死叉
        """
        df = df.copy()
        df['signal'] = 0
        
        for i in range(1, len(df)):
            # 金叉
            golden_cross = (df.loc[i, 'wt1'] > df.loc[i, 'wt2']) and \
                          (df.loc[i-1, 'wt1'] <= df.loc[i-1, 'wt2'])
            
            # 买入
            if (df.loc[i, 'wt1'] < wt_threshold and 
                golden_cross and 
                df.loc[i, 'momentum_20d_norm'] > -0.5):  # 动量不太负
                df.loc[i, 'signal'] = 1
            
            # 卖出
            death_cross = (df.loc[i, 'wt1'] < df.loc[i, 'wt2']) and \
                         (df.loc[i-1, 'wt1'] >= df.loc[i-1, 'wt2'])
            
            if (df.loc[i, 'adx'] > 20 and 
                df.loc[i, 'wt1'] > 0 and 
                death_cross):
                df.loc[i, 'signal'] = -1
        
        return df
    
    def generate_signals_v2(self, df, wt_threshold=-30):
        """
        策略V2: WT超卖 + 动量转正
        买入: wt1<阈值 且 金叉 且 动量>0
        卖出: 动量转负
        """
        df = df.copy()
        df['signal'] = 0
        
        for i in range(1, len(df)):
            golden_cross = (df.loc[i, 'wt1'] > df.loc[i, 'wt2']) and \
                          (df.loc[i-1, 'wt1'] <= df.loc[i-1, 'wt2'])
            
            # 买入：超卖金叉 + 动量转正
            if (df.loc[i, 'wt1'] < wt_threshold and 
                golden_cross and 
                df.loc[i, 'momentum_20d_norm'] > 0):  # 动量为正
                df.loc[i, 'signal'] = 1
            
            # 卖出：动量转负
            if df.loc[i, 'momentum_20d_norm'] < -0.3:
                df.loc[i, 'signal'] = -1
        
        return df
    
    def generate_signals_v3(self, df, wt_threshold=-30):
        """
        策略V3: WT超卖 + 趋势过滤
        买入: wt1<阈值 且 金叉 且 价格>200日均线
        卖出: 价格<200日均线
        """
        df = df.copy()
        df['signal'] = 0
        
        for i in range(1, len(df)):
            golden_cross = (df.loc[i, 'wt1'] > df.loc[i, 'wt2']) and \
                          (df.loc[i-1, 'wt1'] <= df.loc[i-1, 'wt2'])
            
            # 买入：超卖金叉 + 在上升趋势中
            if (df.loc[i, 'wt1'] < wt_threshold and 
                golden_cross and 
                df.loc[i, 'above_ma200']):  # 价格在200日均线上方
                df.loc[i, 'signal'] = 1
            
            # 卖出：跌破200日均线
            if not df.loc[i, 'above_ma200']:
                df.loc[i, 'signal'] = -1
        
        return df
    
    def generate_signals_v4(self, df, wt_threshold=-30):
        """
        策略V4: 综合过滤（最严格）
        买入: wt1<阈值 且 金叉 且 动量>-0.3 且 价格>ma200
        卖出: 动量<-0.5 或 跌破ma200
        """
        df = df.copy()
        df['signal'] = 0
        
        for i in range(1, len(df)):
            golden_cross = (df.loc[i, 'wt1'] > df.loc[i, 'wt2']) and \
                          (df.loc[i-1, 'wt1'] <= df.loc[i-1, 'wt2'])
            
            # 买入：多重过滤
            if (df.loc[i, 'wt1'] < wt_threshold and 
                golden_cross and 
                df.loc[i, 'momentum_20d_norm'] > -0.3 and  # 动量不太差
                df.loc[i, 'above_ma200']):  # 上升趋势
                df.loc[i, 'signal'] = 1
            
            # 卖出：任一条件满足
            if (df.loc[i, 'momentum_20d_norm'] < -0.5 or 
                not df.loc[i, 'above_ma200']):
                df.loc[i, 'signal'] = -1
        
        return df
    
    def run_backtest(self, df, strategy_name):
        """运行回测"""
        cash = self.initial_capital
        btc_holdings = 0
        entry_price = 0
        
        trades = []
        portfolio = []
        
        for i in range(len(df)):
            row = df.iloc[i]
            date = row['date']
            price = row['close']
            signal = row['signal']
            
            total_value = cash + btc_holdings * price
            
            # 止损
            if btc_holdings > 0 and entry_price > 0:
                loss_pct = (entry_price - price) / entry_price
                if loss_pct >= self.stop_loss:
                    sell_value = btc_holdings * price
                    profit = sell_value - (btc_holdings * entry_price)
                    
                    trades.append({
                        'date': date,
                        'action': 'STOP_LOSS',
                        'price': price,
                        'profit': profit,
                        'profit_pct': profit / (btc_holdings * entry_price) * 100
                    })
                    
                    cash += sell_value
                    btc_holdings = 0
                    entry_price = 0
            
            # 买入
            if signal == 1 and btc_holdings == 0:
                buy_value = total_value * self.position_size
                if buy_value > 0 and cash >= buy_value:
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
            
            # 卖出
            elif signal == -1 and btc_holdings > 0:
                sell_value = btc_holdings * price
                profit = sell_value - (btc_holdings * entry_price)
                
                trades.append({
                    'date': date,
                    'action': 'SELL',
                    'price': price,
                    'profit': profit,
                    'profit_pct': profit / (btc_holdings * entry_price) * 100
                })
                
                cash += sell_value
                btc_holdings = 0
                entry_price = 0
            
            portfolio.append({
                'date': date,
                'price': price,
                'total_value': cash + btc_holdings * price
            })
        
        # 如果最后还有持仓
        if btc_holdings > 0:
            final_price = df.iloc[-1]['close']
            final_value = btc_holdings * final_price
            profit = final_value - (btc_holdings * entry_price)
            print(f"\n⚠️  最终持仓: {btc_holdings:.6f} BTC @ ${final_price:,.0f}")
            print(f"   浮动盈亏: ${profit:,.0f} ({profit/(btc_holdings*entry_price)*100:+.1f}%)")
        
        portfolio_df = pd.DataFrame(portfolio)
        trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()
        
        # 统计
        final_value = portfolio_df['total_value'].iloc[-1]
        total_return = (final_value - self.initial_capital) / self.initial_capital * 100
        
        portfolio_df['peak'] = portfolio_df['total_value'].cummax()
        portfolio_df['drawdown'] = (portfolio_df['total_value'] - portfolio_df['peak']) / portfolio_df['peak'] * 100
        max_drawdown = portfolio_df['drawdown'].min()
        
        # 修复：检查trades_df是否为空
        if len(trades_df) > 0 and 'action' in trades_df.columns:
            completed = trades_df[trades_df['action'].isin(['SELL', 'STOP_LOSS'])]
            num_trades = len(completed)
            win_rate = (completed['profit'] > 0).sum() / num_trades * 100 if num_trades > 0 else 0
        else:
            num_trades = 0
            win_rate = 0
            completed = pd.DataFrame()
        
        print(f"\n📊 {strategy_name}")
        print("-" * 80)
        print(f"  💰 最终价值: ${final_value:,.0f}")
        print(f"  📈 总收益率: {total_return:+.2f}%")
        print(f"  📉 最大回撤: {max_drawdown:.2f}%")
        print(f"  🔄 交易次数: {num_trades}次")
        if num_trades > 0:
            print(f"  🎯 胜率: {win_rate:.1f}%")
            if len(completed) > 0:
                avg_profit = completed[completed['profit']>0]['profit_pct'].mean() if len(completed[completed['profit']>0])>0 else 0
                avg_loss = completed[completed['profit']<0]['profit_pct'].mean() if len(completed[completed['profit']<0])>0 else 0
                print(f"  📊 平均盈利: {avg_profit:.1f}%")
                print(f"  📊 平均亏损: {avg_loss:.1f}%")
        
        return {
            'strategy': strategy_name,
            'return': total_return,
            'max_drawdown': max_drawdown,
            'trades': num_trades,
            'win_rate': win_rate
        }


def main():
    print("=" * 100)
    print("🎯 WaveTrend + 动量组合策略测试")
    print("=" * 100)
    print()
    
    # 加载数据
    print("【步骤1】加载数据...")
    data_module = DataModule()
    price_data = data_module.get_price_data()
    print()
    
    # 计算指标
    print("【步骤2】计算所有指标...")
    df = calculate_all_indicators(price_data)
    print()
    
    # 测试不同策略
    print("【步骤3】测试组合策略...")
    strategy_engine = CombinedStrategy(initial_capital=10000, position_size=0.95, stop_loss=0.10)
    
    results = []
    
    # 测试不同wt阈值
    wt_thresholds = [-30, -40, -50, -60]
    
    for wt_thresh in wt_thresholds:
        print()
        print("=" * 100)
        print(f"📊 测试阈值: wt1 < {wt_thresh}")
        print("=" * 100)
        
        # V1: 动量不太负
        df1 = strategy_engine.generate_signals_v1(df, wt_thresh)
        r1 = strategy_engine.run_backtest(df1, f"wt1<{wt_thresh} + 动量>-0.5")
        results.append(r1)
        
        # V2: 动量为正
        df2 = strategy_engine.generate_signals_v2(df, wt_thresh)
        r2 = strategy_engine.run_backtest(df2, f"wt1<{wt_thresh} + 动量>0")
        results.append(r2)
        
        # V3: 趋势过滤
        df3 = strategy_engine.generate_signals_v3(df, wt_thresh)
        r3 = strategy_engine.run_backtest(df3, f"wt1<{wt_thresh} + 价格>MA200")
        results.append(r3)
        
        # V4: 综合过滤
        df4 = strategy_engine.generate_signals_v4(df, wt_thresh)
        r4 = strategy_engine.run_backtest(df4, f"wt1<{wt_thresh} + 综合过滤")
        results.append(r4)
    
    # 综合对比
    print()
    print("=" * 100)
    print("📊 所有策略综合对比")
    print("=" * 100)
    print()
    
    start_price = price_data.iloc[0]['close']
    end_price = price_data.iloc[-1]['close']
    hold_return = (end_price / start_price - 1) * 100
    
    print(f"{'策略':<35} {'收益率':<15} {'最大回撤':<15} {'交易次数':<12} {'胜率':<10}")
    print("-" * 100)
    print(f"{'买入持有':<35} {hold_return:+.2f}%         {'-81.00%':<15} {'0':<12} {'N/A':<10}")
    print()
    
    for r in results:
        win_rate_str = f"{r['win_rate']:.1f}%" if r['trades'] > 0 else "N/A"
        print(f"{r['strategy']:<35} {r['return']:+.2f}%         {r['max_drawdown']:.2f}%         {r['trades']:<12} {win_rate_str:<10}")
    
    print()
    print("=" * 100)
    
    # 找出最佳策略
    best_return = max(results, key=lambda x: x['return'])
    best_sharpe = max(results, key=lambda x: -x['return']/x['max_drawdown'] if x['max_drawdown'] < 0 else 0)
    
    print()
    print(f"🏆 最高收益策略: {best_return['strategy']}")
    print(f"   收益: {best_return['return']:+.2f}%")
    print(f"   回撤: {best_return['max_drawdown']:.2f}%")
    
    print()
    print(f"🛡️  最佳风险调整收益: {best_sharpe['strategy']}")
    print(f"   收益: {best_sharpe['return']:+.2f}%")
    print(f"   回撤: {best_sharpe['max_drawdown']:.2f}%")
    print(f"   收益/回撤比: {-best_sharpe['return']/best_sharpe['max_drawdown']:.2f}")
    
    print()
    print("=" * 100)
    
    # 保存结果
    results_df = pd.DataFrame(results)
    results_df.to_csv('数字化数据/wt_momentum_strategies.csv', index=False, encoding='utf-8-sig')
    print()
    print("✅ 结果已保存: 数字化数据/wt_momentum_strategies.csv")
    print()


if __name__ == "__main__":
    main()

