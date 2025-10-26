#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
组合因子策略测试
测试三种不同的多因子组合策略
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path

sys.path.append(str(Path(__file__).parent / '模块'))
from 数据模块 import DataModule


class MultiFactorStrategy:
    """多因子策略"""
    
    def __init__(self):
        pass
    
    def calculate_all_factors(self, df):
        """计算所有需要的因子"""
        print("📊 计算因子...")
        df = df.copy()
        
        # ========== 技术因子 ==========
        
        # 1. Momentum因子
        returns_20d = df['close'].pct_change(20)
        df['factor_momentum'] = (returns_20d - returns_20d.mean()) / returns_20d.std()
        
        # 2. WaveTrend深度超卖因子
        n1, n2 = 10, 21
        hlc3 = (df['high'] + df['low'] + df['close']) / 3
        esa = hlc3.ewm(span=n1, adjust=False).mean()
        d = (hlc3 - esa).abs().ewm(span=n1, adjust=False).mean()
        ci = (hlc3 - esa) / (0.015 * d)
        wt1 = ci.ewm(span=n2, adjust=False).mean()  # EMA - TradingView标准
        wt2 = wt1.rolling(window=4).mean()  # SMA
        df['wt1'] = wt1
        df['wt2'] = wt2
        df['factor_wt_oversold'] = ((-wt1 - 40) / 40).clip(lower=0, upper=2)
        
        # 3. 均值回归因子
        ma200 = df['close'].rolling(window=200).mean()
        deviation = (df['close'] - ma200) / ma200
        df['factor_mean_reversion'] = -deviation
        df['factor_mean_reversion'] = (df['factor_mean_reversion'] - df['factor_mean_reversion'].mean()) / df['factor_mean_reversion'].std()
        
        # 4. RSI反转因子
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        df['rsi'] = rsi
        df['factor_rsi_reversal'] = ((30 - rsi) / 30).clip(lower=-1, upper=1)
        
        # ========== 链上因子 ==========
        
        # 5. MVRV价值因子（反向）
        if 'sth_mvrv' in df.columns:
            mvrv = df['sth_mvrv']
            df['factor_mvrv'] = (1 - mvrv).clip(lower=-2, upper=2)
        else:
            df['factor_mvrv'] = 0
        
        # 6. 移动平均线位置（趋势过滤）
        ma50 = df['close'].rolling(window=50).mean()
        ma200 = df['close'].rolling(window=200).mean()
        df['price_above_ma200'] = (df['close'] > ma200).astype(int)
        df['ma50_above_ma200'] = (ma50 > ma200).astype(int)
        
        print("✅ 因子计算完成")
        return df
    
    # ========== 策略A: 多因子加权评分 ==========
    
    def strategy_a_weighted_score(self, df):
        """
        策略A: 多因子加权评分系统
        综合评分 = 0.4×Momentum + 0.3×(-MVRV) + 0.2×Mean_Reversion + 0.1×WT_Oversold
        """
        df = df.copy()
        
        # 计算综合评分
        df['composite_score'] = (
            0.4 * df['factor_momentum'] +
            0.3 * df['factor_mvrv'] +  # MVRV已经是反向的（1-mvrv）
            0.2 * df['factor_mean_reversion'] +
            0.1 * df['factor_wt_oversold']
        )
        
        # 生成信号
        df['signal'] = 0
        df.loc[df['composite_score'] > 0.5, 'signal'] = 1   # 买入
        df.loc[df['composite_score'] < -0.5, 'signal'] = -1  # 卖出
        
        return df
    
    # ========== 策略B: 动量+价值组合 ==========
    
    def strategy_b_momentum_value(self, df):
        """
        策略B: 动量+价值组合
        条件1: Momentum > 0.3 (有动量)
        条件2: MVRV < 1.2 (不太贵)
        条件3: WT_Oversold > 0 (超卖反弹)
        """
        df = df.copy()
        
        # 生成信号
        df['signal'] = 0
        
        # 买入条件：三个条件都满足
        buy_condition = (
            (df['factor_momentum'] > 0.3) &
            (df['sth_mvrv'] < 1.2) if 'sth_mvrv' in df.columns else (df['factor_momentum'] > 0.3) &
            (df['factor_wt_oversold'] > 0)
        )
        df.loc[buy_condition, 'signal'] = 1
        
        # 卖出条件：动量转负或MVRV过高
        sell_condition = (
            (df['factor_momentum'] < -0.3) |
            ((df['sth_mvrv'] > 1.8) if 'sth_mvrv' in df.columns else (df['factor_momentum'] < -0.3))
        )
        df.loc[sell_condition, 'signal'] = -1
        
        return df
    
    # ========== 策略C: 保守型组合 ==========
    
    def strategy_c_conservative(self, df):
        """
        策略C: 保守型组合
        只用RSI反转 + 均值回归，更注重风险控制
        """
        df = df.copy()
        
        # 计算保守评分
        df['conservative_score'] = (
            0.6 * df['factor_rsi_reversal'] +
            0.4 * df['factor_mean_reversion']
        )
        
        # 生成信号（阈值更高，更保守）
        df['signal'] = 0
        df.loc[df['conservative_score'] > 0.8, 'signal'] = 1   # 买入
        df.loc[df['conservative_score'] < -0.8, 'signal'] = -1  # 卖出
        
        return df


class MultiFactorBacktest:
    """多因子回测引擎"""
    
    def __init__(self, initial_capital=10000, position_size=0.95):
        self.initial_capital = initial_capital
        self.position_size = position_size
    
    def run_backtest(self, df, strategy_name):
        """运行回测"""
        print()
        print("=" * 100)
        print(f"🚀 {strategy_name} 回测")
        print("=" * 100)
        
        cash = self.initial_capital
        btc_holdings = 0
        entry_price = 0
        
        trades = []
        portfolio_history = []
        
        for i in range(len(df)):
            row = df.iloc[i]
            date = row['date']
            price = row['close']
            signal = row['signal']
            
            position_value = btc_holdings * price
            total_value = cash + position_value
            
            # 买入信号
            if signal == 1 and btc_holdings == 0 and cash > 0:
                buy_value = total_value * self.position_size
                btc_holdings = buy_value / price
                cash = total_value - buy_value
                entry_price = price
                
                trades.append({
                    'date': date,
                    'action': 'BUY',
                    'price': price,
                    'btc': btc_holdings
                })
            
            # 卖出信号
            elif signal == -1 and btc_holdings > 0:
                sell_value = btc_holdings * price
                profit = sell_value - (btc_holdings * entry_price)
                
                trades.append({
                    'date': date,
                    'action': 'SELL',
                    'price': price,
                    'btc': btc_holdings,
                    'profit': profit,
                    'profit_pct': (profit / (btc_holdings * entry_price)) * 100
                })
                
                cash += sell_value
                btc_holdings = 0
                entry_price = 0
            
            # 记录投资组合
            position_value = btc_holdings * price
            total_value = cash + position_value
            
            portfolio_history.append({
                'date': date,
                'price': price,
                'cash': cash,
                'btc_holdings': btc_holdings,
                'position_value': position_value,
                'total_value': total_value,
                'return': (total_value - self.initial_capital) / self.initial_capital * 100
            })
        
        # 如果最后还有持仓
        if btc_holdings > 0:
            final_price = df.iloc[-1]['close']
            final_value = btc_holdings * final_price
            profit = final_value - (btc_holdings * entry_price)
            print(f"\n⚠️  最终持仓未平仓: {btc_holdings:.8f} BTC @ ${final_price:,.2f}")
            print(f"   浮动盈亏: ${profit:,.2f} ({(profit/(btc_holdings*entry_price)*100):+.2f}%)")
        
        portfolio_df = pd.DataFrame(portfolio_history)
        trades_df = pd.DataFrame(trades) if len(trades) > 0 else pd.DataFrame()
        
        return portfolio_df, trades_df
    
    def show_summary(self, portfolio_df, trades_df, strategy_name):
        """显示回测摘要"""
        final_value = portfolio_df['total_value'].iloc[-1]
        total_return = (final_value - self.initial_capital) / self.initial_capital * 100
        
        # 最大回撤
        portfolio_df['peak'] = portfolio_df['total_value'].cummax()
        portfolio_df['drawdown'] = (portfolio_df['total_value'] - portfolio_df['peak']) / portfolio_df['peak'] * 100
        max_drawdown = portfolio_df['drawdown'].min()
        
        # 持仓天数
        has_position_days = (portfolio_df['btc_holdings'] > 0).sum()
        total_days = len(portfolio_df)
        
        # 交易统计
        if len(trades_df) > 0:
            completed_trades = trades_df[trades_df['action'] == 'SELL']
            num_trades = len(completed_trades)
            if num_trades > 0:
                profit_trades = completed_trades[completed_trades['profit'] > 0]
                win_rate = len(profit_trades) / num_trades * 100
            else:
                win_rate = 0
        else:
            num_trades = 0
            win_rate = 0
        
        print()
        print(f"📊 {strategy_name} - 结果摘要")
        print("-" * 100)
        print(f"  💰 最终价值: ${final_value:,.2f}")
        print(f"  📈 总收益率: {total_return:+.2f}%")
        print(f"  📉 最大回撤: {max_drawdown:.2f}%")
        print(f"  📊 持仓时间: {has_position_days}天 ({has_position_days/total_days*100:.1f}%)")
        print(f"  🔄 交易次数: {num_trades}次")
        if num_trades > 0:
            print(f"  🎯 胜率: {win_rate:.1f}%")
        
        return {
            'strategy': strategy_name,
            'final_value': final_value,
            'return': total_return,
            'max_drawdown': max_drawdown,
            'hold_days': has_position_days,
            'trades': num_trades,
            'win_rate': win_rate
        }


def main():
    print("=" * 100)
    print("🎯 组合因子策略对比测试")
    print("=" * 100)
    print()
    
    # 1. 加载数据
    print("【步骤1】加载数据...")
    data_module = DataModule()
    price_data = data_module.get_price_data()
    
    # 加载链上数据
    try:
        chart_data = data_module.digitize_chart_data()
        chart_data['date'] = pd.to_datetime(chart_data['date'])
        full_data = price_data.merge(chart_data, on='date', how='left')
        full_data = full_data.ffill().bfill()
        print(f"✅ 已加载价格数据和链上数据")
    except:
        full_data = price_data
        print(f"⚠️  仅加载价格数据")
    print()
    
    # 2. 计算因子
    print("【步骤2】计算因子...")
    strategy = MultiFactorStrategy()
    df_with_factors = strategy.calculate_all_factors(full_data)
    print()
    
    # 3. 测试三个策略
    print("【步骤3】测试三个组合策略...")
    backtest = MultiFactorBacktest(initial_capital=10000, position_size=0.95)
    
    results = []
    
    # 策略A: 多因子加权评分
    print("\n" + "="*100)
    print("📊 策略A: 多因子加权评分系统")
    print("   权重: 40% Momentum + 30% MVRV + 20% Mean Reversion + 10% WT Oversold")
    print("="*100)
    df_a = strategy.strategy_a_weighted_score(df_with_factors)
    portfolio_a, trades_a = backtest.run_backtest(df_a, "策略A: 多因子加权")
    result_a = backtest.show_summary(portfolio_a, trades_a, "策略A: 多因子加权")
    results.append(result_a)
    
    # 策略B: 动量+价值组合
    print("\n" + "="*100)
    print("📊 策略B: 动量+价值组合")
    print("   条件: Momentum>0.3 AND MVRV<1.2 AND WT_Oversold>0")
    print("="*100)
    df_b = strategy.strategy_b_momentum_value(df_with_factors)
    portfolio_b, trades_b = backtest.run_backtest(df_b, "策略B: 动量+价值")
    result_b = backtest.show_summary(portfolio_b, trades_b, "策略B: 动量+价值")
    results.append(result_b)
    
    # 策略C: 保守型组合
    print("\n" + "="*100)
    print("📊 策略C: 保守型组合")
    print("   权重: 60% RSI Reversal + 40% Mean Reversion (高阈值)")
    print("="*100)
    df_c = strategy.strategy_c_conservative(df_with_factors)
    portfolio_c, trades_c = backtest.run_backtest(df_c, "策略C: 保守型")
    result_c = backtest.show_summary(portfolio_c, trades_c, "策略C: 保守型")
    results.append(result_c)
    
    # 4. 综合对比
    print()
    print("=" * 100)
    print("📊 策略综合对比")
    print("=" * 100)
    print()
    
    # 对比买入持有
    start_price = full_data.iloc[0]['close']
    end_price = full_data.iloc[-1]['close']
    hold_return = (end_price / start_price - 1) * 100
    
    print(f"{'策略':<25} {'收益率':<15} {'最大回撤':<15} {'持仓天数':<15} {'交易次数':<12} {'胜率':<10}")
    print("-" * 100)
    print(f"{'买入持有':<25} {hold_return:+.2f}%         {'-81.00%':<15} {'1826 (100%)':<15} {'0':<12} {'N/A':<10}")
    
    for result in results:
        hold_pct = f"{result['hold_days']} ({result['hold_days']/1826*100:.1f}%)"
        win_rate_str = f"{result['win_rate']:.1f}%" if result['trades'] > 0 else "N/A"
        print(f"{result['strategy']:<25} {result['return']:+.2f}%         {result['max_drawdown']:.2f}%         {hold_pct:<15} {result['trades']:<12} {win_rate_str:<10}")
    
    print()
    print("=" * 100)
    
    # 5. 找出最佳策略
    best_strategy = max(results, key=lambda x: x['return'])
    print()
    print(f"🏆 最佳策略: {best_strategy['strategy']}")
    print(f"   收益率: {best_strategy['return']:+.2f}%")
    print(f"   最大回撤: {best_strategy['max_drawdown']:.2f}%")
    print(f"   风险调整后收益 (收益/回撤): {-best_strategy['return']/best_strategy['max_drawdown']:.2f}")
    
    # 最小回撤策略
    best_drawdown = max(results, key=lambda x: x['max_drawdown'])  # 最大的负数 = 最小回撤
    print()
    print(f"🛡️  最低回撤策略: {best_drawdown['strategy']}")
    print(f"   最大回撤: {best_drawdown['max_drawdown']:.2f}%")
    print(f"   收益率: {best_drawdown['return']:+.2f}%")
    
    print()
    print("=" * 100)
    
    # 保存结果
    results_df = pd.DataFrame(results)
    results_df.to_csv('数字化数据/multi_factor_comparison.csv', index=False, encoding='utf-8-sig')
    print()
    print("✅ 对比结果已保存: 数字化数据/multi_factor_comparison.csv")
    print()


if __name__ == "__main__":
    main()

