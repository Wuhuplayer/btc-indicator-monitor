#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
专业双向交易系统
结合 WaveTrend + 动量 + ADX + 仓位管理
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path

sys.path.append(str(Path(__file__).parent / '模块'))
from 数据模块 import DataModule


def calculate_all_indicators(df):
    """计算所有技术指标"""
    print("📊 计算技术指标...")
    df = df.copy()
    
    # 1. WaveTrend（TradingView标准）
    n1, n2 = 10, 21
    hlc3 = (df['high'] + df['low'] + df['close']) / 3
    esa = hlc3.ewm(span=n1, adjust=False).mean()
    d = (hlc3 - esa).abs().ewm(span=n1, adjust=False).mean()
    ci = (hlc3 - esa) / (0.015 * d)
    
    df['wt1'] = ci.ewm(span=n2, adjust=False).mean()
    df['wt2'] = df['wt1'].rolling(window=4).mean()
    
    # 2. 动量指标
    mom_20d = df['close'].pct_change(20)
    df['momentum'] = (mom_20d - mom_20d.mean()) / mom_20d.std()
    df['momentum_raw'] = mom_20d * 100  # 原始百分比
    
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
    df['plus_di'] = 100 * (plus_dm.rolling(window=period).mean() / atr)
    df['minus_di'] = 100 * (minus_dm.rolling(window=period).mean() / atr)
    
    dx = 100 * abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])
    df['adx'] = dx.rolling(window=period).mean()
    
    # 4. 移动平均线（趋势方向）
    df['ma50'] = df['close'].rolling(window=50).mean()
    df['ma200'] = df['close'].rolling(window=200).mean()
    
    print("✅ 指标计算完成")
    return df


class ProfessionalTradingSystem:
    """专业双向交易系统"""
    
    def __init__(self, initial_capital=10000, stop_loss=0.10):
        self.initial_capital = initial_capital
        self.stop_loss = stop_loss
        
        # 仓位配置
        self.position_levels = {
            'light': 0.33,    # 轻仓
            'medium': 0.66,   # 中仓
            'heavy': 0.95     # 重仓
        }
    
    def determine_position_size(self, wt1, momentum, adx, direction='LONG'):
        """
        根据信号强度确定仓位大小
        
        信号强度分级：
        - 强信号：重仓（95%）
        - 中等信号：中仓（66%）
        - 弱信号：轻仓（33%）
        """
        if direction == 'LONG':
            # 做多仓位判断
            if wt1 < -60 and momentum > -0.3 and adx > 25:
                return self.position_levels['heavy'], '强买入'
            elif wt1 < -50 and momentum > -0.5 and adx > 20:
                return self.position_levels['heavy'], '强买入'
            elif wt1 < -50 and momentum > -0.5:
                return self.position_levels['medium'], '中等买入'
            elif wt1 < -40 and momentum > -0.3:
                return self.position_levels['light'], '轻度买入'
            else:
                return 0, '不买入'
        
        else:  # direction == 'SHORT'
            # 做空仓位判断
            if wt1 > 60 and momentum < 0.3 and adx > 25:
                return self.position_levels['heavy'], '强做空'
            elif wt1 > 50 and momentum < 0.5 and adx > 20:
                return self.position_levels['medium'], '中等做空'
            elif wt1 > 40 and momentum < 0.3:
                return self.position_levels['light'], '轻度做空'
            else:
                return 0, '不做空'
    
    def should_close_long(self, wt1, wt2, prev_wt1, prev_wt2, momentum, adx):
        """判断是否平多仓"""
        death_cross = (wt1 < wt2) and (prev_wt1 >= prev_wt2)
        
        # 平多条件
        if death_cross and wt1 > 0 and adx > 20:
            return True, 'ADX>20且WT死叉'
        elif wt1 > 70:
            return True, 'WT极度超买'
        elif momentum < -0.8:
            return True, '动量严重转负'
        
        return False, ''
    
    def should_close_short(self, wt1, wt2, prev_wt1, prev_wt2, momentum, adx):
        """判断是否平空仓"""
        golden_cross = (wt1 > wt2) and (prev_wt1 <= prev_wt2)
        
        # 平空条件
        if golden_cross and wt1 < -20:
            return True, 'WT金叉'
        elif wt1 < -70:
            return True, 'WT极度超卖'
        elif momentum > 0.8:
            return True, '动量强势转正'
        
        return False, ''
    
    def run_backtest(self, df):
        """运行完整回测"""
        print()
        print("=" * 100)
        print("🚀 专业双向交易系统回测")
        print("=" * 100)
        print()
        
        cash = self.initial_capital
        position = 0  # 正=做多，负=做空
        entry_price = 0
        entry_date = None
        position_type = None
        position_size_name = ''
        
        trades = []
        portfolio = []
        
        for i in range(1, len(df)):
            row = df.iloc[i]
            prev = df.iloc[i-1]
            date = row['date']
            price = row['close']
            
            # 计算当前总价值
            if position > 0:  # 做多
                total_value = cash + position * price
            elif position < 0:  # 做空
                unrealized_pnl = -position * (entry_price - price)
                total_value = cash + unrealized_pnl
            else:
                total_value = cash
            
            # === 止损检查 ===
            if position != 0:
                if position > 0:  # 做多止损
                    loss_pct = (entry_price - price) / entry_price
                    if loss_pct >= self.stop_loss:
                        pnl = position * (price - entry_price)
                        trades.append({
                            'entry_date': entry_date,
                            'exit_date': date,
                            'type': 'LONG',
                            'position_size': position_size_name,
                            'entry_price': entry_price,
                            'exit_price': price,
                            'pnl': pnl,
                            'pnl_pct': pnl / (position * entry_price) * 100,
                            'reason': f'止损-{loss_pct*100:.1f}%'
                        })
                        cash += position * price
                        position = 0
                        entry_price = 0
                        position_type = None
                
                elif position < 0:  # 做空止损
                    loss_pct = (price - entry_price) / entry_price
                    if loss_pct >= self.stop_loss:
                        pnl = -position * (entry_price - price)
                        trades.append({
                            'entry_date': entry_date,
                            'exit_date': date,
                            'type': 'SHORT',
                            'position_size': position_size_name,
                            'entry_price': entry_price,
                            'exit_price': price,
                            'pnl': pnl,
                            'pnl_pct': pnl / (-position * entry_price) * 100,
                            'reason': f'止损-{loss_pct*100:.1f}%'
                        })
                        cash += pnl
                        position = 0
                        entry_price = 0
                        position_type = None
            
            # === 平仓信号 ===
            if position > 0:  # 检查是否平多
                should_close, reason = self.should_close_long(
                    row['wt1'], row['wt2'], prev['wt1'], prev['wt2'],
                    row['momentum'], row['adx']
                )
                if should_close:
                    pnl = position * (price - entry_price)
                    trades.append({
                        'entry_date': entry_date,
                        'exit_date': date,
                        'type': 'LONG',
                        'position_size': position_size_name,
                        'entry_price': entry_price,
                        'exit_price': price,
                        'pnl': pnl,
                        'pnl_pct': pnl / (position * entry_price) * 100,
                        'reason': reason
                    })
                    cash += position * price
                    position = 0
                    entry_price = 0
                    position_type = None
            
            elif position < 0:  # 检查是否平空
                should_close, reason = self.should_close_short(
                    row['wt1'], row['wt2'], prev['wt1'], prev['wt2'],
                    row['momentum'], row['adx']
                )
                if should_close:
                    pnl = -position * (entry_price - price)
                    trades.append({
                        'entry_date': entry_date,
                        'exit_date': date,
                        'type': 'SHORT',
                        'position_size': position_size_name,
                        'entry_price': entry_price,
                        'exit_price': price,
                        'pnl': pnl,
                        'pnl_pct': pnl / (-position * entry_price) * 100,
                        'reason': reason
                    })
                    cash += pnl
                    position = 0
                    entry_price = 0
                    position_type = None
            
            # === 开仓信号（只在空仓时） ===
            if position == 0:
                golden_cross = (row['wt1'] > row['wt2']) and (prev['wt1'] <= prev['wt2'])
                death_cross = (row['wt1'] < row['wt2']) and (prev['wt1'] >= prev['wt2'])
                
                # 做多信号
                if golden_cross:
                    pos_size, size_name = self.determine_position_size(
                        row['wt1'], row['momentum'], row['adx'], 'LONG'
                    )
                    
                    if pos_size > 0:
                        buy_value = total_value * pos_size
                        position = buy_value / price
                        cash = total_value - buy_value
                        entry_price = price
                        entry_date = date
                        position_type = 'LONG'
                        position_size_name = size_name
                
                # 做空信号
                elif death_cross:
                    pos_size, size_name = self.determine_position_size(
                        row['wt1'], row['momentum'], row['adx'], 'SHORT'
                    )
                    
                    if pos_size > 0:
                        short_value = total_value * pos_size
                        position = -short_value / price  # 负数表示做空
                        entry_price = price
                        entry_date = date
                        position_type = 'SHORT'
                        position_size_name = size_name
            
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
        
        # 最终仓位
        final_price = df.iloc[-1]['close']
        if position > 0:
            pnl = position * (final_price - entry_price)
            print(f"\n⚠️  最终做多仓位: {position:.6f} BTC")
            print(f"   入场: {entry_date} @ ${entry_price:,.0f} ({position_size_name})")
            print(f"   当前: ${final_price:,.0f}")
            print(f"   浮动盈亏: ${pnl:,.0f} ({pnl/(position*entry_price)*100:+.1f}%)")
        elif position < 0:
            pnl = -position * (entry_price - final_price)
            print(f"\n⚠️  最终做空仓位: {-position:.6f} BTC")
            print(f"   入场: {entry_date} @ ${entry_price:,.0f} ({position_size_name})")
            print(f"   当前: ${final_price:,.0f}")
            print(f"   浮动盈亏: ${pnl:,.0f} ({pnl/(-position*entry_price)*100:+.1f}%)")
        
        portfolio_df = pd.DataFrame(portfolio)
        trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()
        
        return portfolio_df, trades_df
    
    def show_results(self, portfolio_df, trades_df, strategy_name):
        """显示回测结果"""
        print()
        print("=" * 100)
        print(f"📊 {strategy_name} - 回测结果")
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
        print(f"📉 最大回撤: {max_dd:.2f}%")
        print()
        
        if len(trades_df) > 0:
            long_trades = trades_df[trades_df['type'] == 'LONG']
            short_trades = trades_df[trades_df['type'] == 'SHORT']
            
            print(f"📊 交易统计:")
            print(f"  总交易次数: {len(trades_df)}次")
            print(f"    🟢 做多: {len(long_trades)}次")
            print(f"    🔴 做空: {len(short_trades)}次")
            print()
            
            # 做多统计
            if len(long_trades) > 0:
                long_win = long_trades[long_trades['pnl'] > 0]
                long_loss = long_trades[long_trades['pnl'] < 0]
                long_win_rate = len(long_win) / len(long_trades) * 100
                
                print(f"  🟢 做多详情:")
                print(f"    胜率: {long_win_rate:.1f}%")
                print(f"    总盈亏: ${long_trades['pnl'].sum():,.0f}")
                if len(long_win) > 0:
                    print(f"    平均盈利: ${long_win['pnl'].mean():,.0f} ({long_win['pnl_pct'].mean():+.1f}%)")
                if len(long_loss) > 0:
                    print(f"    平均亏损: ${long_loss['pnl'].mean():,.0f} ({long_loss['pnl_pct'].mean():.1f}%)")
                print()
            
            # 做空统计
            if len(short_trades) > 0:
                short_win = short_trades[short_trades['pnl'] > 0]
                short_loss = short_trades[short_trades['pnl'] < 0]
                short_win_rate = len(short_win) / len(short_trades) * 100
                
                print(f"  🔴 做空详情:")
                print(f"    胜率: {short_win_rate:.1f}%")
                print(f"    总盈亏: ${short_trades['pnl'].sum():,.0f}")
                if len(short_win) > 0:
                    print(f"    平均盈利: ${short_win['pnl'].mean():,.0f} ({short_win['pnl_pct'].mean():+.1f}%)")
                if len(short_loss) > 0:
                    print(f"    平均亏损: ${short_loss['pnl'].mean():,.0f} ({short_loss['pnl_pct'].mean():.1f}%)")
                print()
            
            # 整体胜率
            win_trades = trades_df[trades_df['pnl'] > 0]
            overall_win_rate = len(win_trades) / len(trades_df) * 100
            
            print(f"  🎯 整体胜率: {overall_win_rate:.1f}%")
            print(f"  💰 已实现盈亏: ${trades_df['pnl'].sum():,.0f}")
            
            # 盈亏比
            if len(win_trades) > 0 and len(trades_df[trades_df['pnl'] < 0]) > 0:
                avg_win = win_trades['pnl'].mean()
                avg_loss = abs(trades_df[trades_df['pnl'] < 0]['pnl'].mean())
                profit_factor = avg_win / avg_loss
                print(f"  📊 盈亏比: {profit_factor:.2f}")
        
        print()
        print("=" * 100)
        
        return {
            'strategy': strategy_name,
            'return': ret,
            'max_dd': max_dd,
            'trades': len(trades_df),
            'win_rate': overall_win_rate if len(trades_df) > 0 else 0
        }


def main():
    print("=" * 100)
    print("🎯 专业双向交易系统（WT + 动量 + ADX + 仓位管理）")
    print("=" * 100)
    print()
    
    # 加载数据
    print("【步骤1】加载数据...")
    data_module = DataModule()
    df = data_module.get_price_data()
    print()
    
    # 计算指标
    print("【步骤2】计算技术指标...")
    df = calculate_all_indicators(df)
    print()
    
    # 运行回测
    print("【步骤3】运行专业双向交易系统...")
    
    system = ProfessionalTradingSystem(initial_capital=10000, stop_loss=0.10)
    portfolio_df, trades_df = system.run_backtest(df)
    result = system.show_results(portfolio_df, trades_df, "专业双向交易系统")
    
    # 对比买入持有
    print()
    print("【步骤4】对比买入持有...")
    print("=" * 100)
    
    start_price = df.iloc[0]['close']
    end_price = df.iloc[-1]['close']
    hold_return = (end_price / start_price - 1) * 100
    
    print()
    print(f"📊 最终对比:")
    print(f"  买入持有: {hold_return:+.2f}%")
    print(f"  双向交易: {result['return']:+.2f}%")
    print(f"  差距: {result['return'] - hold_return:+.2f}%")
    print()
    
    if result['return'] > hold_return:
        print(f"🎉 恭喜！双向交易超越买入持有 {result['return'] - hold_return:+.2f}%！")
    else:
        print(f"⚠️  双向交易跑输买入持有 {hold_return - result['return']:.2f}%")
        print(f"   但回撤优势: {result['max_dd']:.2f}% vs -81.00%")
    
    print()
    print("=" * 100)
    
    # 显示交易明细
    if len(trades_df) > 0:
        print()
        print("📋 交易明细（前20笔）:")
        print()
        print(trades_df[['entry_date', 'exit_date', 'type', 'position_size', 
                         'entry_price', 'exit_price', 'pnl_pct', 'reason']].head(20).to_string(index=False))
    
    # 保存结果
    portfolio_df.to_csv('数字化数据/professional_portfolio.csv', index=False, encoding='utf-8-sig')
    if len(trades_df) > 0:
        trades_df.to_csv('数字化数据/professional_trades.csv', index=False, encoding='utf-8-sig')
    
    print()
    print()
    print("✅ 结果已保存:")
    print("  • 数字化数据/professional_portfolio.csv")
    print("  • 数字化数据/professional_trades.csv")
    print()
    print("=" * 100)


if __name__ == "__main__":
    main()

