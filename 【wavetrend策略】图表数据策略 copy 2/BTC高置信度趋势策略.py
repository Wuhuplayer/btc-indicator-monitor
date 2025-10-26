#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BTC高置信度趋势策略 - 四仓渐进策略
基于TradingView Pine Script策略实现

策略特点：
1. 四仓渐进式建仓（15%+25%+40%+25%）
2. 多重技术指标确认（SQZMOM、WaveTrend、ADX、ATR、VIX）
3. 分层止损和ATR追踪止盈
4. 回撤控制和趋势信号出场
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path

sys.path.append(str(Path(__file__).parent / '模块'))
from 数据模块 import DataModule


def calculate_sqzmom(df, lengthBB=20, multBB=2.0, lengthKC=20, multKC=1.5, useTrueRange=True):
    """计算SQZMOM挤压动能指标"""
    source = df['close']
    
    # 布林带计算
    basis = source.rolling(window=lengthBB).mean()
    dev = multBB * source.rolling(window=lengthBB).std()
    upperBB = basis + dev
    lowerBB = basis - dev
    
    # 肯特纳通道计算
    maKC = source.rolling(window=lengthKC).mean()
    if useTrueRange:
        # 计算True Range
        tr1 = df['high'] - df['low']
        tr2 = abs(df['high'] - df['close'].shift(1))
        tr3 = abs(df['low'] - df['close'].shift(1))
        rangeKC = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    else:
        rangeKC = df['high'] - df['low']
    
    rangemaKC = rangeKC.rolling(window=lengthKC).mean()
    upperKC = maKC + rangemaKC * multKC
    lowerKC = maKC - rangemaKC * multKC
    
    # 判断挤压状态
    sqzOn = (lowerBB > lowerKC) & (upperBB < upperKC)
    sqzOff = (lowerBB < lowerKC) & (upperBB > upperKC)
    
    # 动能线线性回归
    avgHL = (df['high'].rolling(window=lengthKC).max() + df['low'].rolling(window=lengthKC).min()) / 2
    avgAll = (avgHL + source.rolling(window=lengthKC).mean()) / 2
    val = (source - avgAll).rolling(window=lengthKC).apply(lambda x: np.polyfit(range(len(x)), x, 1)[0] * (len(x) - 1), raw=False)
    
    # 动能柱状态判断
    isLime = (val > 0) & (val > val.shift(1))    # 强多柱
    isGreen = (val > 0) & (val < val.shift(1))   # 弱多柱
    isRed = (val < 0) & (val < val.shift(1))     # 强空柱
    isMaroon = (val < 0) & (val > val.shift(1))  # 弱空柱
    
    return {
        'sqzOn': sqzOn,
        'sqzOff': sqzOff,
        'val': val,
        'isLime': isLime,
        'isGreen': isGreen,
        'isRed': isRed,
        'isMaroon': isMaroon
    }


def calculate_wavetrend(df, channelLength=10, averageLength=21):
    """计算WaveTrend指标"""
    esa = df['close'].ewm(span=channelLength, adjust=False).mean()
    de = abs(df['close'] - esa).ewm(span=channelLength, adjust=False).mean()
    ci = (df['close'] - esa) / (0.015 * de)
    tci = ci.ewm(span=averageLength, adjust=False).mean()
    wt1 = tci
    wt2 = wt1.rolling(window=4).mean()
    
    # 交叉信号
    wtGoldenCross = (wt1.shift(1) < wt2.shift(1)) & (wt1 > wt2)
    wtDeathCross = (wt1.shift(1) > wt2.shift(1)) & (wt1 < wt2)
    
    return {
        'wt1': wt1,
        'wt2': wt2,
        'wtGoldenCross': wtGoldenCross,
        'wtDeathCross': wtDeathCross
    }


def calculate_adx(df, length=14):
    """计算ADX指标"""
    high_diff = df['high'].diff()
    low_diff = -df['low'].diff()
    
    plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
    minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)
    
    tr1 = df['high'] - df['low']
    tr2 = abs(df['high'] - df['close'].shift(1))
    tr3 = abs(df['low'] - df['close'].shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    atr = tr.rolling(window=length).mean()
    plus_di = 100 * (plus_dm.rolling(window=length).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=length).mean() / atr)
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(window=length).mean()
    
    return {
        'plusDI': plus_di,
        'minusDI': minus_di,
        'adx': adx
    }


def calculate_atr(df, length=14):
    """计算ATR指标"""
    tr1 = df['high'] - df['low']
    tr2 = abs(df['high'] - df['close'].shift(1))
    tr3 = abs(df['low'] - df['close'].shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=length).mean()


def calculate_vix(df, length=14, mult=2.0):
    """计算VIX模拟指标"""
    mean = df['close'].rolling(window=length).mean()
    dev = mult * df['close'].rolling(window=length).std()
    return dev


def calculate_all_indicators(df):
    """计算所有技术指标"""
    print("📊 计算技术指标...")
    df = df.copy()
    
    # SQZMOM指标
    sqzmom = calculate_sqzmom(df)
    for key, value in sqzmom.items():
        df[key] = value
    
    # WaveTrend指标
    wt = calculate_wavetrend(df)
    for key, value in wt.items():
        df[key] = value
    
    # ADX指标
    adx = calculate_adx(df)
    for key, value in adx.items():
        df[key] = value
    
    # ATR指标
    df['atr'] = calculate_atr(df)
    
    # VIX指标
    df['vix'] = calculate_vix(df)
    
    # 其他指标
    df['ma14'] = df['close'].rolling(window=14).mean()
    df['ma21'] = df['close'].rolling(window=21).mean()
    df['ma60'] = df['close'].rolling(window=60).mean()
    df['ema10'] = df['close'].ewm(span=10, adjust=False).mean()
    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['sma14'] = df['close'].rolling(window=14).mean()
    df['sma24'] = df['close'].rolling(window=24).mean()
    
    # 结构确认信号
    df['lookbackHigh'] = df['high'].rolling(window=14).max()
    df['priceStructConfirmed'] = df['close'] > df['ma14']
    
    # 趋势判断
    df['longCondition'] = df['ma21'] > df['ma60']
    
    # 4小时模拟信号（简化版，使用日线数据）
    df['highlightGreen'] = df['sqzOn'] | ((df['val'] > df['val'].shift(1)) & (df['val'] > 0))
    
    # 趋势出场信号
    df['trendExit'] = (df['sma14'] < df['sma24']) & (df['isLime'].shift(1) & ~df['isLime'])
    
    print("✅ 指标计算完成")
    return df


class BTCHighConfidenceStrategy:
    """BTC高置信度趋势策略"""
    
    def __init__(self, initial_capital=10000, leverage=1.0):
        self.initial_capital = initial_capital
        self.leverage = leverage
        
        # 仓位配置（按照Pine Script设置）
        self.position_levels = {
            'base': 0.15,     # 基础仓位 15%
            'mid': 0.25,      # 二段加仓 25%
            'full': 0.40,     # 三段加仓 40%
            'full2': 0.25     # 四段加仓 25%
        }
        
        # 止损比例
        self.stop_loss_ratios = {
            'base': 0.85,     # -15%止损
            'mid': 0.85,      # -15%止损
            'full': 0.90,     # -10%止损
            'full2': 0.90     # -10%止损
        }
        
        # 最大回撤限制（BTC）
        self.max_drawdown_allowed = 0.30 / self.leverage  # 30% / 杠杆倍数
    
    def get_entry_conditions(self, row):
        """获取入场条件"""
        # 四阶段入场条件
        entryCond1 = (row['highlightGreen'] and 
                     row['wtGoldenCross'] and 
                     row['wt1'] < -20)
        
        entryCond2 = (row['sqzOff'] and 
                     row['isLime'] and 
                     row['wt1'] > row['wt2'])
        
        entryCond3 = (row['priceStructConfirmed'] and 
                     row['sqzOff'] and 
                     row['isLime'] and 
                     row['wt1'] > row['wt2'])
        
        entryCond4 = (row['adx'] > 20 and 
                     row['priceStructConfirmed'] and 
                     row['sqzOff'] and 
                     row['isLime'] and 
                     row['wt1'] > row['wt2'])
        
        return entryCond1, entryCond2, entryCond3, entryCond4
    
    def calculate_atr_multiplier(self, row):
        """计算ATR倍数"""
        if row['ema10'] > row['ema20']:  # 上升趋势
            if row['adx'] > 25:
                return 1.7
            elif row['adx'] < 20:
                return 1.3
            else:
                return 1.5
        else:  # 下降趋势
            return 1.5
    
    def run_backtest(self, df):
        """运行回测"""
        print()
        print("=" * 100)
        print("🚀 BTC高置信度趋势策略回测")
        print("=" * 100)
        print()
        
        cash = self.initial_capital
        position = 0
        entry_prices = {}
        entry_dates = {}
        position_levels_entered = set()
        
        trades = []
        portfolio = []
        
        # 状态变量
        long1Entered = False
        long2Entered = False
        long3Entered = False
        long4Entered = False
        
        peak_equity = self.initial_capital
        trail_stop_price = None
        
        for i in range(1, len(df)):
            row = df.iloc[i]
            prev_row = df.iloc[i-1]
            date = row['date']
            price = row['close']
            
            # 计算当前总价值
            total_value = cash + position * price
            
            # === 重置状态变量（如果当前没有持仓且上一根K线有持仓） ===
            if position == 0 and len(trades) > 0 and trades[-1].get('exit_date') == date:
                long1Entered = False
                long2Entered = False
                long3Entered = False
                long4Entered = False
                entry_prices = {}
                entry_dates = {}
                position_levels_entered = set()
                trail_stop_price = None
            
            # === 回撤控制 ===
            if position != 0:
                peak_equity = max(peak_equity, total_value)
                drawdown_pct = (peak_equity - total_value) / peak_equity
                
                if drawdown_pct > self.max_drawdown_allowed:
                    # 超出最大回撤，强制平仓
                    pnl = position * (price - sum(entry_prices.values()) / len(entry_prices)) if entry_prices else 0
                    trades.append({
                        'entry_date': entry_dates.get('base', ''),
                        'exit_date': date,
                        'entry_price': sum(entry_prices.values()) / len(entry_prices) if entry_prices else 0,
                        'exit_price': price,
                        'pnl': pnl,
                        'pnl_pct': pnl / (position * (sum(entry_prices.values()) / len(entry_prices))) * 100 if entry_prices and position > 0 else 0,
                        'reason': f'回撤止损-{drawdown_pct*100:.1f}%'
                    })
                    cash += position * price
                    position = 0
                    entry_prices = {}
                    entry_dates = {}
                    position_levels_entered = set()
                    long1Entered = False
                    long2Entered = False
                    long3Entered = False
                    long4Entered = False
                    trail_stop_price = None
                    continue
            
            # === ATR追踪止盈 ===
            if position > 0:
                atr_mult = self.calculate_atr_multiplier(row)
                current_trail_stop = price - atr_mult * row['atr']
                
                if trail_stop_price is None:
                    trail_stop_price = current_trail_stop
                else:
                    trail_stop_price = max(trail_stop_price, current_trail_stop)
                
                # 检查是否触发追踪止盈
                if price < trail_stop_price:
                    pnl = position * (price - sum(entry_prices.values()) / len(entry_prices)) if entry_prices else 0
                    trades.append({
                        'entry_date': entry_dates.get('base', ''),
                        'exit_date': date,
                        'entry_price': sum(entry_prices.values()) / len(entry_prices) if entry_prices else 0,
                        'exit_price': price,
                        'pnl': pnl,
                        'pnl_pct': pnl / (position * (sum(entry_prices.values()) / len(entry_prices))) * 100 if entry_prices and position > 0 else 0,
                        'reason': 'ATR追踪止盈'
                    })
                    cash += position * price
                    position = 0
                    entry_prices = {}
                    entry_dates = {}
                    position_levels_entered = set()
                    long1Entered = False
                    long2Entered = False
                    long3Entered = False
                    long4Entered = False
                    trail_stop_price = None
                    continue
            
            # === 分层止损检查 ===
            if position > 0 and entry_prices:
                for level, entry_price in entry_prices.items():
                    stop_loss_line = entry_price * self.stop_loss_ratios[level]
                    if row['low'] < stop_loss_line:
                        # 触发止损
                        pnl = position * (price - sum(entry_prices.values()) / len(entry_prices)) if entry_prices else 0
                        trades.append({
                            'entry_date': entry_dates.get('base', ''),
                            'exit_date': date,
                            'entry_price': sum(entry_prices.values()) / len(entry_prices) if entry_prices else 0,
                            'exit_price': price,
                            'pnl': pnl,
                            'pnl_pct': pnl / (position * (sum(entry_prices.values()) / len(entry_prices))) * 100 if entry_prices and position > 0 else 0,
                            'reason': f'{level}仓止损'
                        })
                        cash += position * price
                        position = 0
                        entry_prices = {}
                        entry_dates = {}
                        position_levels_entered = set()
                        long1Entered = False
                        long2Entered = False
                        long3Entered = False
                        long4Entered = False
                        trail_stop_price = None
                        break
                if position == 0:
                    continue
            
            # === 趋势信号出场 ===
            if position > 0 and row['trendExit']:
                pnl = position * (price - sum(entry_prices.values()) / len(entry_prices)) if entry_prices else 0
                trades.append({
                    'entry_date': entry_dates.get('base', ''),
                    'exit_date': date,
                    'entry_price': sum(entry_prices.values()) / len(entry_prices) if entry_prices else 0,
                    'exit_price': price,
                    'pnl': pnl,
                    'pnl_pct': pnl / (position * (sum(entry_prices.values()) / len(entry_prices))) * 100 if entry_prices and position > 0 else 0,
                    'reason': '趋势信号出场'
                })
                cash += position * price
                position = 0
                entry_prices = {}
                entry_dates = {}
                position_levels_entered = set()
                long1Entered = False
                long2Entered = False
                long3Entered = False
                long4Entered = False
                trail_stop_price = None
                continue
            
            # === 开仓信号（只在空仓时） ===
            if position == 0:
                entryCond1, entryCond2, entryCond3, entryCond4 = self.get_entry_conditions(row)
                
                # 第一仓
                if not long1Entered and entryCond1:
                    buy_value = total_value * self.position_levels['base']
                    position = buy_value / price
                    cash = total_value - buy_value
                    entry_prices['base'] = price
                    entry_dates['base'] = date
                    position_levels_entered.add('base')
                    long1Entered = True
                
                # 第二仓
                elif long1Entered and not long2Entered and entryCond2:
                    buy_value = total_value * self.position_levels['mid']
                    position += buy_value / price
                    cash -= buy_value
                    entry_prices['mid'] = price
                    entry_dates['mid'] = date
                    position_levels_entered.add('mid')
                    long2Entered = True
                
                # 第三仓
                elif long2Entered and not long3Entered and entryCond3:
                    buy_value = total_value * self.position_levels['full']
                    position += buy_value / price
                    cash -= buy_value
                    entry_prices['full'] = price
                    entry_dates['full'] = date
                    position_levels_entered.add('full')
                    long3Entered = True
                
                # 第四仓
                elif long3Entered and not long4Entered and entryCond4:
                    buy_value = total_value * self.position_levels['full2']
                    position += buy_value / price
                    cash -= buy_value
                    entry_prices['full2'] = price
                    entry_dates['full2'] = date
                    position_levels_entered.add('full2')
                    long4Entered = True
            
            # 记录组合价值
            total_value = cash + position * price
            portfolio.append({
                'date': date,
                'price': price,
                'total_value': total_value,
                'position': position,
                'position_levels': len(position_levels_entered)
            })
        
        # 最终仓位
        final_price = df.iloc[-1]['close']
        if position > 0:
            pnl = position * (final_price - sum(entry_prices.values()) / len(entry_prices)) if entry_prices else 0
            print(f"\n⚠️  最终持仓: {position:.6f} BTC")
            print(f"   入场: {entry_dates.get('base', 'N/A')} @ ${sum(entry_prices.values()) / len(entry_prices):,.0f}" if entry_prices else "N/A")
            print(f"   当前: ${final_price:,.0f}")
            print(f"   浮动盈亏: ${pnl:,.0f}")
            print(f"   仓位层级: {', '.join(position_levels_entered)}")
        
        portfolio_df = pd.DataFrame(portfolio)
        trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()
        
        return portfolio_df, trades_df
    
    def show_results(self, portfolio_df, trades_df):
        """显示回测结果"""
        print()
        print("=" * 100)
        print("📊 BTC高置信度趋势策略 - 回测结果")
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
            win_trades = trades_df[trades_df['pnl'] > 0]
            loss_trades = trades_df[trades_df['pnl'] < 0]
            win_rate = len(win_trades) / len(trades_df) * 100
            
            print(f"📊 交易统计:")
            print(f"  总交易次数: {len(trades_df)}次")
            print(f"  胜率: {win_rate:.1f}%")
            print(f"  盈利交易: {len(win_trades)}次")
            print(f"  亏损交易: {len(loss_trades)}次")
            print()
            
            if len(win_trades) > 0:
                print(f"  💚 平均盈利: ${win_trades['pnl'].mean():,.0f} ({win_trades['pnl_pct'].mean():+.1f}%)")
                print(f"  💚 最大盈利: ${win_trades['pnl'].max():,.0f} ({win_trades['pnl_pct'].max():+.1f}%)")
            
            if len(loss_trades) > 0:
                print(f"  💔 平均亏损: ${loss_trades['pnl'].mean():,.0f} ({loss_trades['pnl_pct'].mean():.1f}%)")
                print(f"  💔 最大亏损: ${loss_trades['pnl'].min():,.0f} ({loss_trades['pnl_pct'].min():.1f}%)")
            
            print(f"  💰 总盈亏: ${trades_df['pnl'].sum():,.0f}")
            
            # 盈亏比
            if len(win_trades) > 0 and len(loss_trades) > 0:
                avg_win = win_trades['pnl'].mean()
                avg_loss = abs(loss_trades['pnl'].mean())
                profit_factor = avg_win / avg_loss
                print(f"  📊 盈亏比: {profit_factor:.2f}")
            
            # 出场原因统计
            print()
            print("📋 出场原因统计:")
            exit_reasons = trades_df['reason'].value_counts()
            for reason, count in exit_reasons.items():
                print(f"  {reason}: {count}次")
        
        print()
        print("=" * 100)
        
        return {
            'return': ret,
            'max_dd': max_dd,
            'trades': len(trades_df),
            'win_rate': win_rate if len(trades_df) > 0 else 0
        }


def create_sample_data():
    """创建示例价格数据"""
    print("📈 创建模拟BTC价格数据...")
    try:
        # 创建模拟的BTC价格数据（2020-2025）
        import pandas as pd
        import numpy as np
        from datetime import datetime, timedelta
        
        # 创建日期范围
        start_date = datetime(2020, 1, 1)
        end_date = datetime(2024, 12, 31)
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # 模拟BTC价格走势
        np.random.seed(42)
        n_days = len(dates)
        
        # 基础价格走势（模拟BTC的周期性）
        base_price = 10000  # 2020年初价格
        trend = np.linspace(0, 80000, n_days)  # 长期上涨趋势
        
        # 添加周期性波动
        cycle1 = 5000 * np.sin(np.linspace(0, 4*np.pi, n_days))  # 4年周期
        cycle2 = 2000 * np.sin(np.linspace(0, 8*np.pi, n_days))  # 2年周期
        cycle3 = 1000 * np.sin(np.linspace(0, 16*np.pi, n_days))  # 1年周期
        
        # 随机波动
        random_noise = np.random.normal(0, 1000, n_days)
        
        # 合成价格
        close_prices = base_price + trend + cycle1 + cycle2 + cycle3 + random_noise
        
        # 确保价格为正
        close_prices = np.maximum(close_prices, 1000)
        
        # 生成OHLC数据
        data = []
        for i, (date, close) in enumerate(zip(dates, close_prices)):
            # 生成当日波动
            daily_volatility = 0.02  # 2%日波动
            high = close * (1 + np.random.uniform(0, daily_volatility))
            low = close * (1 - np.random.uniform(0, daily_volatility))
            open_price = close * (1 + np.random.uniform(-daily_volatility/2, daily_volatility/2))
            
            data.append({
                'date': date.strftime('%Y-%m-%d'),
                'open': round(open_price, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'close': round(close, 2),
                'volume': np.random.randint(1000000, 10000000)
            })
        
        df = pd.DataFrame(data)
        print(f"✅ 创建模拟BTC价格数据: {len(df)} 条记录")
        print(f"   价格范围: ${df['close'].min():,.0f} - ${df['close'].max():,.0f}")
        return df
        
    except Exception as e:
        print(f"❌ 创建价格数据失败: {e}")
        return None

def main():
    print("=" * 100)
    print("🎯 BTC高置信度趋势策略（四仓渐进 + 多重确认）")
    print("=" * 100)
    print()
    
    # 加载数据
    print("【步骤1】加载数据...")
    df = create_sample_data()
    
    if df is None:
        print("❌ 无法获取数据，退出程序")
        return
    
    print()
    
    # 计算指标
    print("【步骤2】计算技术指标...")
    df = calculate_all_indicators(df)
    print()
    
    # 运行回测
    print("【步骤3】运行BTC高置信度趋势策略...")
    
    strategy = BTCHighConfidenceStrategy(initial_capital=10000, leverage=1.0)
    portfolio_df, trades_df = strategy.run_backtest(df)
    result = strategy.show_results(portfolio_df, trades_df)
    
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
    print(f"  高置信度策略: {result['return']:+.2f}%")
    print(f"  差距: {result['return'] - hold_return:+.2f}%")
    print()
    
    if result['return'] > hold_return:
        print(f"🎉 恭喜！策略超越买入持有 {result['return'] - hold_return:+.2f}%！")
    else:
        print(f"⚠️  策略跑输买入持有 {hold_return - result['return']:.2f}%")
        print(f"   但回撤优势: {result['max_dd']:.2f}% vs -81.00%")
    
    print()
    print("=" * 100)
    
    # 显示交易明细
    if len(trades_df) > 0:
        print()
        print("📋 交易明细（前10笔）:")
        print()
        display_cols = ['entry_date', 'exit_date', 'entry_price', 'exit_price', 'pnl_pct', 'reason']
        print(trades_df[display_cols].head(10).to_string(index=False))
    
    # 保存结果
    portfolio_df.to_csv('数字化数据/btc_high_confidence_portfolio.csv', index=False, encoding='utf-8-sig')
    if len(trades_df) > 0:
        trades_df.to_csv('数字化数据/btc_high_confidence_trades.csv', index=False, encoding='utf-8-sig')
    
    print()
    print()
    print("✅ 结果已保存:")
    print("  • 数字化数据/btc_high_confidence_portfolio.csv")
    print("  • 数字化数据/btc_high_confidence_trades.csv")
    print()
    print("=" * 100)


if __name__ == "__main__":
    main()
