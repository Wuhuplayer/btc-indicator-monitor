#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分批止盈策略全对比 - 根据市场技术信号分批出场

核心理念：不是"走出来才知道怎么分段"，而是实时根据技术信号决定何时分批卖出

分批止盈方法对比：
1. 固定比例分批（传统方法）- 30%/50%/100% 各出1/3
2. ATR回撤分批 - 回撤1.5/2.5/3.5倍ATR时分批
3. 技术指标分批 - RSI超买/MACD死叉/MA死叉
4. 支撑位分批 - 跌破斐波那契回调位
5. 动态回撤分批 - 盈利后回撤5%/10%/15%
6. 混合信号分批 - 固定比例+技术确认+支撑位
7. 时间+技术分批 - 持仓时间+技术信号
8. 波动率分批 - ATR突增+技术确认

所有方法均无未来函数！
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

sys.path.append(str(Path(__file__).parent))

from 真实BTC高置信度策略 import (
    get_real_btc_data, calculate_sqzmom, calculate_wavetrend, 
    calculate_adx, calculate_atr
)


def calculate_all_indicators(df):
    """计算所有技术指标"""
    df = df.copy()
    
    # 基础指标
    sqzmom = calculate_sqzmom(df)
    for key, value in sqzmom.items():
        df[key] = value
    
    wt = calculate_wavetrend(df)
    for key, value in wt.items():
        df[key] = value
    
    adx = calculate_adx(df)
    for key, value in adx.items():
        df[key] = value
    
    df['atr'] = calculate_atr(df)
    
    # 均线系统
    df['ma7'] = df['close'].rolling(window=7).mean()
    df['ma14'] = df['close'].rolling(window=14).mean()
    df['ma21'] = df['close'].rolling(window=21).mean()
    df['ma30'] = df['close'].rolling(window=30).mean()
    df['ma60'] = df['close'].rolling(window=60).mean()
    df['ema10'] = df['close'].ewm(span=10, adjust=False).mean()
    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
    
    # 布林带
    df['bb_middle'] = df['close'].rolling(window=20).mean()
    df['bb_std'] = df['close'].rolling(window=20).std()
    df['bb_upper'] = df['bb_middle'] + 2 * df['bb_std']
    df['bb_lower'] = df['bb_middle'] - 2 * df['bb_std']
    
    # MACD
    df['ema12'] = df['close'].ewm(span=12, adjust=False).mean()
    df['ema26'] = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = df['ema12'] - df['ema26']
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # 支撑位/斐波那契
    df['support_7'] = df['low'].rolling(window=7).min()
    df['support_14'] = df['low'].rolling(window=14).min()
    df['resistance_14'] = df['high'].rolling(window=14).max()
    
    # ATR相关
    df['atr_ma'] = df['atr'].rolling(window=14).mean()
    
    # 入场信号
    df['priceStructConfirmed'] = df['close'] > df['ma14']
    df['longCondition'] = df['ma21'] > df['ma60']
    
    return df


def get_entry_conditions(row):
    """统一的入场条件"""
    entryCond1 = (row['wtGoldenCross'] and row['wt1'] < 40)
    entryCond2 = (row['sqzOff'] and row['isLime'] and row['wt1'] > row['wt2'])
    entryCond3 = (row['priceStructConfirmed'] and row['sqzOff'] and 
                 row['isLime'] and row['wt1'] > row['wt2'])
    entryCond4 = (row['adx'] > 20 and row['priceStructConfirmed'] and 
                 row['sqzOff'] and row['isLime'] and row['wt1'] > row['wt2'])
    
    return entryCond1, entryCond2, entryCond3, entryCond4


class PartialExitStrategy:
    """分批止盈策略基类"""
    
    def __init__(self, name, exit_portions=[0.33, 0.33, 0.34], initial_capital=10000):
        """
        exit_portions: 每次止盈的仓位比例（加起来应该=1.0）
        例如：[0.33, 0.33, 0.34] = 第一次出33%，第二次出33%，第三次出34%
        """
        self.name = name
        self.initial_capital = initial_capital
        self.exit_portions = exit_portions
        self.num_exits = len(exit_portions)
        
        # 仓位配置
        self.position_levels = {
            'base': 0.15,
            'mid': 0.25,
            'full': 0.40,
            'full2': 0.25
        }
        
        # 固定止损
        self.stop_loss_ratio = 0.80
        self.max_drawdown_allowed = 0.30
    
    def check_partial_exit_signals(self, df, i, position_info, exit_count):
        """
        检查分批止盈信号（子类实现）
        
        参数:
        - df: 完整数据
        - i: 当前索引
        - position_info: 持仓信息
        - exit_count: 已经止盈的次数（0, 1, 2...）
        
        返回: (是否止盈, 止盈原因, 止盈比例)
        """
        raise NotImplementedError
    
    def run_backtest(self, df):
        """运行回测"""
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
        
        entry_date = None
        avg_entry_price = None
        highest_price = 0
        peak_equity = self.initial_capital
        exit_count = 0  # 已止盈次数
        
        for i in range(1, len(df)):
            row = df.iloc[i]
            date = row['date']
            price = row['close']
            
            total_value = cash + position * price
            
            # 更新最高价
            if position > 0:
                highest_price = max(highest_price, price)
            
            # 回撤控制
            if position != 0:
                peak_equity = max(peak_equity, total_value)
                drawdown_pct = (peak_equity - total_value) / peak_equity
                
                if drawdown_pct > self.max_drawdown_allowed:
                    pnl = position * (price - avg_entry_price)
                    
                    trades.append({
                        'entry_date': entry_date,
                        'exit_date': date,
                        'entry_price': avg_entry_price,
                        'exit_price': price,
                        'position_sold': position,
                        'pnl': pnl,
                        'pnl_pct': (price / avg_entry_price - 1) * 100,
                        'exit_num': exit_count + 1,
                        'reason': f'超出最大回撤{drawdown_pct*100:.1f}%'
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
                    entry_date = None
                    avg_entry_price = None
                    highest_price = 0
                    peak_equity = self.initial_capital
                    exit_count = 0
                    continue
            
            # 固定止损
            if position > 0 and avg_entry_price and price < avg_entry_price * self.stop_loss_ratio:
                pnl = position * (price - avg_entry_price)
                
                trades.append({
                    'entry_date': entry_date,
                    'exit_date': date,
                    'entry_price': avg_entry_price,
                    'exit_price': price,
                    'position_sold': position,
                    'pnl': pnl,
                    'pnl_pct': (price / avg_entry_price - 1) * 100,
                    'exit_num': exit_count + 1,
                    'reason': '固定止损-20%'
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
                entry_date = None
                avg_entry_price = None
                highest_price = 0
                exit_count = 0
                continue
            
            # 检查分批止盈信号
            if position > 0 and avg_entry_price and exit_count < self.num_exits:
                position_info = {
                    'entry_date': entry_date,
                    'entry_price': avg_entry_price,
                    'highest_price': highest_price,
                    'position': position,
                    'days_held': (date - entry_date).days
                }
                
                should_exit, exit_reason, exit_ratio = self.check_partial_exit_signals(
                    df, i, position_info, exit_count
                )
                
                if should_exit:
                    # 如果返回的exit_ratio为None，使用预设的比例
                    if exit_ratio is None:
                        if exit_count < len(self.exit_portions):
                            # 计算剩余仓位的比例
                            remaining_ratio = sum(self.exit_portions[exit_count:])
                            exit_ratio = self.exit_portions[exit_count] / remaining_ratio
                        else:
                            exit_ratio = 1.0  # 全部卖出
                    
                    exit_position = position * exit_ratio
                    pnl = exit_position * (price - avg_entry_price)
                    
                    trades.append({
                        'entry_date': entry_date,
                        'exit_date': date,
                        'entry_price': avg_entry_price,
                        'exit_price': price,
                        'position_sold': exit_position,
                        'pnl': pnl,
                        'pnl_pct': (price / avg_entry_price - 1) * 100,
                        'exit_num': exit_count + 1,
                        'reason': f"第{exit_count+1}次止盈-{exit_reason}"
                    })
                    
                    cash += exit_position * price
                    position -= exit_position
                    exit_count += 1
                    
                    # 如果仓位太小或者已经全部止盈，重置
                    if position < 0.001 or exit_count >= self.num_exits:
                        position = 0
                        entry_prices = {}
                        entry_dates = {}
                        position_levels_entered = set()
                        long1Entered = False
                        long2Entered = False
                        long3Entered = False
                        long4Entered = False
                        entry_date = None
                        avg_entry_price = None
                        highest_price = 0
                        exit_count = 0
                        continue
            
            # 开仓信号
            if position == 0:
                entryCond1, entryCond2, entryCond3, entryCond4 = get_entry_conditions(row)
                
                # 第一仓
                if not long1Entered and entryCond1:
                    buy_value = total_value * self.position_levels['base']
                    position = buy_value / price
                    cash = total_value - buy_value
                    entry_prices['base'] = price
                    entry_dates['base'] = date
                    position_levels_entered.add('base')
                    long1Entered = True
                    entry_date = date
                    avg_entry_price = price
                    highest_price = price
                    exit_count = 0
            else:
                entryCond1, entryCond2, entryCond3, entryCond4 = get_entry_conditions(row)
                
                # 第二仓
                if long1Entered and not long2Entered and entryCond2:
                    buy_value = total_value * self.position_levels['mid']
                    new_position = buy_value / price
                    avg_entry_price = (position * avg_entry_price + new_position * price) / (position + new_position)
                    position += new_position
                    cash -= buy_value
                    entry_prices['mid'] = price
                    entry_dates['mid'] = date
                    position_levels_entered.add('mid')
                    long2Entered = True
                
                # 第三仓
                if long2Entered and not long3Entered and entryCond3:
                    buy_value = total_value * self.position_levels['full']
                    new_position = buy_value / price
                    avg_entry_price = (position * avg_entry_price + new_position * price) / (position + new_position)
                    position += new_position
                    cash -= buy_value
                    entry_prices['full'] = price
                    entry_dates['full'] = date
                    position_levels_entered.add('full')
                    long3Entered = True
                
                # 第四仓
                if long3Entered and not long4Entered and entryCond4:
                    buy_value = total_value * self.position_levels['full2']
                    new_position = buy_value / price
                    avg_entry_price = (position * avg_entry_price + new_position * price) / (position + new_position)
                    position += new_position
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
                'position': position
            })
        
        portfolio_df = pd.DataFrame(portfolio)
        trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()
        
        return portfolio_df, trades_df


# ============ 1. 固定比例分批 ============
class FixedRatioPartialExit(PartialExitStrategy):
    """固定比例分批止盈（传统方法）"""
    
    def __init__(self, targets=[0.30, 0.50, 1.00], **kwargs):
        super().__init__(f"固定比例分批({int(targets[0]*100)}%/{int(targets[1]*100)}%/{int(targets[2]*100)}%)", **kwargs)
        self.targets = targets
    
    def check_partial_exit_signals(self, df, i, position_info, exit_count):
        row = df.iloc[i]
        price = row['close']
        profit_pct = (price / position_info['entry_price'] - 1)
        
        if exit_count < len(self.targets) and profit_pct >= self.targets[exit_count]:
            return True, f"盈利{int(self.targets[exit_count]*100)}%", None
        
        return False, None, None


# ============ 2. ATR回撤分批 ============
class ATRDrawdownPartialExit(PartialExitStrategy):
    """ATR回撤分批止盈"""
    
    def __init__(self, atr_multipliers=[1.5, 2.0, 2.5], **kwargs):
        super().__init__(f"ATR回撤分批({atr_multipliers[0]}/{atr_multipliers[1]}/{atr_multipliers[2]}倍)", **kwargs)
        self.atr_multipliers = atr_multipliers
        self.trail_stops = [None] * len(atr_multipliers)
    
    def check_partial_exit_signals(self, df, i, position_info, exit_count):
        row = df.iloc[i]
        price = row['close']
        atr = row['atr']
        
        if exit_count >= len(self.atr_multipliers):
            return False, None, None
        
        mult = self.atr_multipliers[exit_count]
        current_stop = price - mult * atr
        
        if self.trail_stops[exit_count] is None:
            self.trail_stops[exit_count] = current_stop
        else:
            self.trail_stops[exit_count] = max(self.trail_stops[exit_count], current_stop)
        
        if price < self.trail_stops[exit_count]:
            self.trail_stops[exit_count] = None
            return True, f"ATR{mult}倍回撤", None
        
        return False, None, None


# ============ 3. 技术指标分批 ============
class TechnicalSignalPartialExit(PartialExitStrategy):
    """技术指标分批止盈：RSI超买 → MACD死叉 → MA死叉"""
    
    def __init__(self, **kwargs):
        super().__init__("技术指标分批(RSI/MACD/MA死叉)", **kwargs)
        self.signals_triggered = [False, False, False]
    
    def check_partial_exit_signals(self, df, i, position_info, exit_count):
        row = df.iloc[i]
        prev_row = df.iloc[i-1]
        profit_pct = (row['close'] / position_info['entry_price'] - 1)
        
        # 第一批：RSI超买（需要有一定盈利）
        if exit_count == 0 and not self.signals_triggered[0]:
            if row['rsi'] > 70 and profit_pct > 0.20:
                self.signals_triggered[0] = True
                return True, "RSI超买(>70)", None
        
        # 第二批：MACD死叉
        if exit_count == 1 and not self.signals_triggered[1]:
            if prev_row['macd'] >= prev_row['macd_signal'] and row['macd'] < row['macd_signal']:
                self.signals_triggered[1] = True
                return True, "MACD死叉", None
        
        # 第三批：MA死叉
        if exit_count == 2 and not self.signals_triggered[2]:
            if prev_row['ma14'] >= prev_row['ma30'] and row['ma14'] < row['ma30']:
                self.signals_triggered[2] = True
                return True, "MA14/30死叉", None
        
        return False, None, None


# ============ 4. 支撑位分批（斐波那契）============
class FibonacciPartialExit(PartialExitStrategy):
    """斐波那契回调位分批止盈"""
    
    def __init__(self, **kwargs):
        super().__init__("斐波那契分批(0.786/0.618/0.382回调)", **kwargs)
        self.fib_levels = [0.786, 0.618, 0.382]  # 从高位回调的比例
    
    def check_partial_exit_signals(self, df, i, position_info, exit_count):
        row = df.iloc[i]
        price = row['close']
        
        if exit_count >= len(self.fib_levels):
            return False, None, None
        
        # 计算斐波那契回调位
        high_price = position_info['highest_price']
        entry_price = position_info['entry_price']
        fib_level = self.fib_levels[exit_count]
        
        # 回调位 = 最高价 - (最高价 - 入场价) * fib_level
        support_level = high_price - (high_price - entry_price) * fib_level
        
        # 需要先有盈利，然后跌破回调位
        profit_pct = (price / entry_price - 1)
        if profit_pct > 0.20 and price < support_level:
            return True, f"跌破{fib_level}回调位", None
        
        return False, None, None


# ============ 5. 动态回撤分批 ============
class DynamicDrawdownPartialExit(PartialExitStrategy):
    """动态回撤分批：盈利后回撤触发"""
    
    def __init__(self, profit_thresholds=[0.30, 0.50, 1.00], 
                 drawdown_thresholds=[0.05, 0.10, 0.15], **kwargs):
        super().__init__(f"动态回撤分批(30%+5%/50%+10%/100%+15%)", **kwargs)
        self.profit_thresholds = profit_thresholds
        self.drawdown_thresholds = drawdown_thresholds
    
    def check_partial_exit_signals(self, df, i, position_info, exit_count):
        row = df.iloc[i]
        price = row['close']
        
        if exit_count >= len(self.profit_thresholds):
            return False, None, None
        
        profit_pct = (price / position_info['entry_price'] - 1)
        drawdown = (position_info['highest_price'] - price) / position_info['highest_price']
        
        # 需要达到盈利阈值，且回撤超过设定值
        if (profit_pct >= self.profit_thresholds[exit_count] and 
            drawdown >= self.drawdown_thresholds[exit_count]):
            return True, f"盈利{int(self.profit_thresholds[exit_count]*100)}%后回撤{int(self.drawdown_thresholds[exit_count]*100)}%", None
        
        return False, None, None


# ============ 6. 混合信号分批 ============
class HybridPartialExit(PartialExitStrategy):
    """混合信号分批：固定比例 + 技术确认 + 支撑位"""
    
    def __init__(self, **kwargs):
        super().__init__("混合信号分批(固定+技术+支撑)", **kwargs)
    
    def check_partial_exit_signals(self, df, i, position_info, exit_count):
        row = df.iloc[i]
        prev_row = df.iloc[i-1]
        price = row['close']
        profit_pct = (price / position_info['entry_price'] - 1)
        
        # 第一批：30%盈利 + RSI超买
        if exit_count == 0:
            if profit_pct >= 0.30 and row['rsi'] > 65:
                return True, "30%盈利+RSI超买", None
        
        # 第二批：50%盈利 + MACD死叉
        if exit_count == 1:
            if profit_pct >= 0.50:
                if prev_row['macd'] >= prev_row['macd_signal'] and row['macd'] < row['macd_signal']:
                    return True, "50%盈利+MACD死叉", None
        
        # 第三批：跌破7日支撑
        if exit_count == 2:
            if profit_pct > 0.30 and price < row['support_7']:
                return True, "跌破7日支撑", None
        
        return False, None, None


# ============ 7. 时间+技术分批 ============
class TimeAndTechnicalPartialExit(PartialExitStrategy):
    """时间+技术分批"""
    
    def __init__(self, **kwargs):
        super().__init__("时间+技术分批(20天/MACD/MA死叉)", **kwargs)
    
    def check_partial_exit_signals(self, df, i, position_info, exit_count):
        row = df.iloc[i]
        prev_row = df.iloc[i-1]
        days_held = position_info['days_held']
        profit_pct = (row['close'] / position_info['entry_price'] - 1)
        
        # 第一批：持仓20天且有盈利
        if exit_count == 0:
            if days_held >= 20 and profit_pct > 0.15:
                return True, "持仓20天+盈利15%", None
        
        # 第二批：MACD死叉
        if exit_count == 1:
            if prev_row['macd'] >= prev_row['macd_signal'] and row['macd'] < row['macd_signal']:
                return True, "MACD死叉", None
        
        # 第三批：MA死叉
        if exit_count == 2:
            if prev_row['ma14'] >= prev_row['ma30'] and row['ma14'] < row['ma30']:
                return True, "MA14/30死叉", None
        
        return False, None, None


# ============ 8. 波动率分批 ============
class VolatilityPartialExit(PartialExitStrategy):
    """波动率分批：ATR突增+技术确认"""
    
    def __init__(self, **kwargs):
        super().__init__("波动率分批(ATR突增+技术确认)", **kwargs)
    
    def check_partial_exit_signals(self, df, i, position_info, exit_count):
        row = df.iloc[i]
        prev_row = df.iloc[i-1]
        profit_pct = (row['close'] / position_info['entry_price'] - 1)
        
        # 第一批：ATR突增1.5倍
        if exit_count == 0:
            if row['atr'] > row['atr_ma'] * 1.5 and profit_pct > 0.20:
                return True, "ATR突增1.5倍", None
        
        # 第二批：ATR持续高位 + MACD死叉
        if exit_count == 1:
            if row['atr'] > row['atr_ma'] * 1.3:
                if prev_row['macd'] >= prev_row['macd_signal'] and row['macd'] < row['macd_signal']:
                    return True, "高波动+MACD死叉", None
        
        # 第三批：波动率回落 + MA死叉
        if exit_count == 2:
            if prev_row['ma14'] >= prev_row['ma30'] and row['ma14'] < row['ma30']:
                return True, "MA死叉", None
        
        return False, None, None


def compare_partial_exit_strategies(df):
    """对比所有分批止盈策略"""
    print()
    print("=" * 120)
    print("🎯 分批止盈策略全对比 - 根据市场技术信号分批出场")
    print("=" * 120)
    print()
    
    # 定义所有策略
    strategies = [
        # 1. 固定比例分批（不同目标）
        FixedRatioPartialExit(targets=[0.30, 0.50, 1.00]),
        FixedRatioPartialExit(targets=[0.50, 1.00, 2.00]),
        FixedRatioPartialExit(targets=[0.20, 0.40, 0.80]),
        FixedRatioPartialExit(targets=[0.30, 0.80, 1.50]),
        
        # 2. ATR回撤分批
        ATRDrawdownPartialExit(atr_multipliers=[1.5, 2.0, 2.5]),
        ATRDrawdownPartialExit(atr_multipliers=[1.0, 1.5, 2.0]),
        ATRDrawdownPartialExit(atr_multipliers=[2.0, 2.5, 3.0]),
        
        # 3. 技术指标分批
        TechnicalSignalPartialExit(),
        
        # 4. 斐波那契分批
        FibonacciPartialExit(),
        
        # 5. 动态回撤分批
        DynamicDrawdownPartialExit(profit_thresholds=[0.30, 0.50, 1.00], 
                                   drawdown_thresholds=[0.05, 0.10, 0.15]),
        DynamicDrawdownPartialExit(profit_thresholds=[0.50, 1.00, 2.00], 
                                   drawdown_thresholds=[0.08, 0.12, 0.20]),
        DynamicDrawdownPartialExit(profit_thresholds=[0.20, 0.40, 0.80], 
                                   drawdown_thresholds=[0.10, 0.15, 0.20]),
        
        # 6. 混合信号分批
        HybridPartialExit(),
        
        # 7. 时间+技术分批
        TimeAndTechnicalPartialExit(),
        
        # 8. 波动率分批
        VolatilityPartialExit(),
    ]
    
    results = []
    
    for idx, strategy in enumerate(strategies, 1):
        print(f"[{idx}/{len(strategies)}] 回测: {strategy.name}...")
        
        try:
            portfolio_df, trades_df = strategy.run_backtest(df)
            
            if len(portfolio_df) > 0:
                final_value = portfolio_df['total_value'].iloc[-1]
                total_return = (final_value - strategy.initial_capital) / strategy.initial_capital * 100
                
                # 计算最大回撤
                portfolio_df['peak'] = portfolio_df['total_value'].cummax()
                portfolio_df['dd'] = (portfolio_df['total_value'] - portfolio_df['peak']) / portfolio_df['peak'] * 100
                max_dd = portfolio_df['dd'].min()
                
                # 交易统计
                if len(trades_df) > 0:
                    # 按入场日期分组统计完整交易
                    trades_df['entry_date_str'] = trades_df['entry_date'].astype(str)
                    complete_trades = trades_df.groupby('entry_date_str').agg({
                        'pnl': 'sum',
                        'exit_num': 'count'
                    }).reset_index()
                    
                    win_trades = complete_trades[complete_trades['pnl'] > 0]
                    loss_trades = complete_trades[complete_trades['pnl'] < 0]
                    win_rate = len(win_trades) / len(complete_trades) * 100 if len(complete_trades) > 0 else 0
                    
                    avg_exits_per_trade = trades_df.groupby('entry_date_str').size().mean()
                    
                    # 盈亏比
                    if len(win_trades) > 0 and len(loss_trades) > 0:
                        profit_factor = abs(win_trades['pnl'].mean() / loss_trades['pnl'].mean())
                    else:
                        profit_factor = 0
                else:
                    win_rate = 0
                    avg_exits_per_trade = 0
                    profit_factor = 0
                
                results.append({
                    '策略名称': strategy.name,
                    '总收益率': f"{total_return:+.2f}%",
                    '最大回撤': f"{max_dd:.2f}%",
                    '完整交易次数': len(complete_trades) if len(trades_df) > 0 else 0,
                    '总出场次数': len(trades_df) if len(trades_df) > 0 else 0,
                    '平均分批次数': f"{avg_exits_per_trade:.1f}" if len(trades_df) > 0 else "0",
                    '胜率': f"{win_rate:.1f}%" if len(trades_df) > 0 else "N/A",
                    '盈亏比': f"{profit_factor:.2f}" if profit_factor > 0 else "N/A",
                    '最终价值': f"${final_value:,.0f}"
                })
        except Exception as e:
            print(f"   ⚠️ 策略执行出错: {e}")
            continue
    
    # 显示结果
    print()
    print("=" * 120)
    print("📊 分批止盈策略对比结果（按收益率排序）")
    print("=" * 120)
    print()
    
    results_df = pd.DataFrame(results)
    
    # 提取收益率数值用于排序
    results_df['收益率数值'] = results_df['总收益率'].str.replace('%', '').str.replace('+', '').astype(float)
    results_df = results_df.sort_values('收益率数值', ascending=False).drop('收益率数值', axis=1)
    
    print(results_df.to_string(index=False))
    
    print()
    print("=" * 120)
    
    # 保存结果
    import os
    os.makedirs('results', exist_ok=True)
    results_df.to_csv('results/分批止盈策略对比结果_近5年.csv', index=False, encoding='utf-8-sig')
    
    print()
    print("✅ 结果已保存到: results/分批止盈策略对比结果_近5年.csv")
    print()
    
    # 对比买入持有
    start_price = df.iloc[0]['close']
    end_price = df.iloc[-1]['close']
    hold_return = (end_price / start_price - 1) * 100
    
    print(f"📊 买入持有基准: {hold_return:+.2f}%")
    print()
    
    # 找出最佳策略
    if len(results_df) > 0:
        best_strategy = results_df.iloc[0]
        print(f"🏆 最佳分批止盈策略: {best_strategy['策略名称']}")
        print(f"   总收益率: {best_strategy['总收益率']}")
        print(f"   最大回撤: {best_strategy['最大回撤']}")
        print(f"   胜率: {best_strategy['胜率']}")
        print(f"   完整交易: {best_strategy['完整交易次数']}次")
        print(f"   平均分批: {best_strategy['平均分批次数']}次")
    print()
    print("=" * 120)


def main():
    print("=" * 120)
    print("🎯 分批止盈策略全对比系统（近5年：2020-2024）")
    print("=" * 120)
    print()
    
    # 获取数据
    print("【步骤1】加载BTC历史数据...")
    df = get_real_btc_data()
    
    if df is None:
        print("❌ 无法获取数据")
        return
    
    # 只保留最近5年的数据（2020-2024）
    print("【步骤2】筛选最近5年数据（2020-01-01至今）...")
    df['date'] = pd.to_datetime(df['date'])
    df = df[df['date'] >= '2020-01-01'].reset_index(drop=True)
    print(f"✅ 筛选后数据: {len(df)} 条记录")
    print(f"   时间范围: {df['date'].min().strftime('%Y-%m-%d')} 到 {df['date'].max().strftime('%Y-%m-%d')}")
    print(f"   价格范围: ${df['close'].min():,.2f} - ${df['close'].max():,.2f}")
    print()
    
    # 计算指标
    print("【步骤3】计算技术指标...")
    df = calculate_all_indicators(df)
    print("✅ 指标计算完成")
    print()
    
    # 对比所有策略
    print("【步骤4】对比所有分批止盈策略...")
    compare_partial_exit_strategies(df)


if __name__ == "__main__":
    main()

