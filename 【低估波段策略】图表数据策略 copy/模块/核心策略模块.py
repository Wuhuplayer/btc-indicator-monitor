#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
核心策略模块 - 整合评分系统和趋势交易策略
包含：评分计算 + 技术指标 + 入场信号 + 渐进式仓位
"""

import pandas as pd
import numpy as np

# ==================== 评分模块 ====================
class ScoringModule:
    """链上指标评分模块（0-6分）"""
    
    def __init__(self):
        """初始化评分规则"""
        pass
    
    def calculate_period_scores(self, df):
        """计算每日的时期评分"""
        print("📊 计算时期评分...")
        
        df = df.copy()
        df['mvrv_score'] = 0
        df['whale_score'] = 0
        df['lth_score'] = 0
        df['total_score'] = 0
        df['period_label'] = ''
        
        # 计算各指标评分
        df['mvrv_score'] = df['sth_mvrv'].apply(self._score_mvrv)
        df['whale_score'] = df['whale_holdings_change'].apply(self._score_whale)
        df['lth_score'] = df['lth_net_change_30d'].apply(self._score_lth)
        
        # 计算总分
        df['total_score'] = df['mvrv_score'] + df['whale_score'] + df['lth_score']
        df['period_label'] = df['total_score'].apply(self._get_period_label)
        
        # 统计
        score_dist = df['total_score'].value_counts().sort_index()
        print(f"\n评分分布:")
        for score, count in score_dist.items():
            label = self._get_period_label(score)
            pct = count / len(df) * 100
            print(f"  {score}分 ({label}): {count}天 ({pct:.1f}%)")
        
        print(f"\n✅ 评分计算完成")
        return df
    
    def _score_mvrv(self, value):
        """STH MVRV评分 - 恢复原版"""
        if pd.isna(value):
            return 0
        if value < 0.8:
            return 2      # 0.8以下超卖
        elif 0.8 <= value < 1.0:
            return 1      # 0.8-1.0中性偏超卖
        elif 1.0 <= value <= 1.2:
            return 1      # 1-1.2可买
        else:
            return 0      # 1.2以上超买
    
    def _score_whale(self, value):
        """鲸鱼持仓变化评分"""
        if pd.isna(value):
            return 0
        if value < -0.01:
            return 0      # <-0.01大户逃离
        elif -0.01 <= value <= 0.01:
            return 1      # -0.01~0.01中性/入场
        else:
            return 2      # >0.01大量进场
    
    def _score_lth(self, value):
        """LTH净持仓变化评分"""
        if pd.isna(value):
            return 0
        if value < -250000:
            return 0
        elif 150000 <= value <= 500000:
            return 1
        elif value > 500000:
            return 2
        else:
            return 0
    
    def _get_period_label(self, total_score):
        """根据总分获取时期标签"""
        if total_score >= 5:
            return '抄底区'
        elif total_score >= 3:
            return '定投区'
        elif total_score >= 1:
            return '持有区'
        else:
            return '观望区'


# ==================== 趋势交易策略模块 ====================
class TrendTradingStrategy:
    """趋势交易策略 - 基于RSI、WaveTrend、挤压动能、ADX"""

    def __init__(self):
        """初始化策略参数"""
        # 仓位管理参数
        self.position_levels = {
            'level_1': 0.33,   # 第一仓: 33%
            'level_2': 0.33,   # 第二仓: 33%
            'level_3': 0.33    # 第三仓: 33%
        }
        
        # 技术指标参数
        self.rsi_period = 14
        self.rsi_oversold = 30
        self.wavetrend_period = 10
        self.adx_period = 14
        self.adx_threshold = 20

    def calculate_technical_indicators(self, df):
        """计算所有技术指标"""
        print("📊 计算技术指标...")
        df = df.copy()
        df = self._calculate_rsi(df)
        df = self._calculate_wavetrend(df)
        df = self._calculate_squeeze_momentum(df)
        df = self._calculate_adx(df)
        print(f"✅ 技术指标计算完成")
        return df

    def _calculate_rsi(self, df):
        """计算RSI指标"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        return df

    def _calculate_wavetrend(self, df):
        """计算WaveTrend指标 - 按照TradingView LazyBear标准实现"""
        # 参数设置 - 与TV保持一致
        n1 = 10  # Channel Length
        n2 = 21  # Average Length
        
        hlc3 = (df['high'] + df['low'] + df['close']) / 3
        esa = hlc3.ewm(span=n1, adjust=False).mean()
        d = (hlc3 - esa).abs().ewm(span=n1, adjust=False).mean()
        ci = (hlc3 - esa) / (0.015 * d)
        
        # 使用EMA（符合TradingView LazyBear原版：ta.ema(ci, n2)）
        tci = ci.ewm(span=n2, adjust=False).mean()
        df['wt1'] = tci
        df['wt2'] = df['wt1'].rolling(window=4).mean()  # wt2使用SMA
        return df

    def _calculate_squeeze_momentum(self, df):
        """计算挤压动能指标"""
        # 布林带
        bb_period = 20
        bb_std = 2
        bb_basis = df['close'].rolling(window=bb_period).mean()
        bb_dev = df['close'].rolling(window=bb_period).std() * bb_std
        bb_upper = bb_basis + bb_dev
        bb_lower = bb_basis - bb_dev
        
        # Keltner通道
        kc_period = 20
        kc_mult = 1.5
        tr1 = df['high'] - df['low']
        tr2 = abs(df['high'] - df['close'].shift())
        tr3 = abs(df['low'] - df['close'].shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=kc_period).mean()
        
        kc_basis = df['close'].rolling(window=kc_period).mean()
        kc_upper = kc_basis + atr * kc_mult
        kc_lower = kc_basis - atr * kc_mult
        
        df['squeeze_on'] = (bb_lower > kc_lower) & (bb_upper < kc_upper)
        
        highest = df['high'].rolling(window=kc_period).max()
        lowest = df['low'].rolling(window=kc_period).min()
        df['squeeze_momentum'] = df['close'] - ((highest + lowest) / 2 + kc_basis) / 2
        df['squeeze_green'] = df['squeeze_momentum'] > df['squeeze_momentum'].shift()
        
        return df

    def _calculate_adx(self, df):
        """计算ADX (Average Directional Index)"""
        high_diff = df['high'].diff()
        low_diff = -df['low'].diff()
        
        plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
        minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)
        
        tr1 = df['high'] - df['low']
        tr2 = abs(df['high'] - df['close'].shift())
        tr3 = abs(df['low'] - df['close'].shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        atr = tr.rolling(window=self.adx_period).mean()
        plus_di = 100 * (plus_dm.rolling(window=self.adx_period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=self.adx_period).mean() / atr)
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        df['adx'] = dx.rolling(window=self.adx_period).mean()
        
        return df

    def generate_entry_signals(self, df):
        """生成入场信号 - 渐进式三仓位（新策略）"""
        print("🎯 生成入场信号...")
        
        df = df.copy()
        df['entry_signal'] = None
        df['entry_reason'] = ''
        
        for i in range(len(df)):
            signals = []
            
            # ========== 渐进式三仓位逻辑 ==========
            signal_1_met = False
            signal_2_met = False
            signal_3_met = False
            
            # 第一仓: 低估区间(RSI<30) + (wt金叉 OR (挤压动能为绿 AND wt1>wt2))
            if not pd.isna(df.loc[i, 'rsi']) and df.loc[i, 'rsi'] < self.rsi_oversold:
                if not pd.isna(df.loc[i, 'wt1']) and not pd.isna(df.loc[i, 'wt2']):
                    wt_cross = (df.loc[i, 'wt1'] > df.loc[i, 'wt2']) and \
                              (i > 0 and df.loc[i-1, 'wt1'] <= df.loc[i-1, 'wt2'])
                    condition_b = df.loc[i, 'squeeze_green'] and (df.loc[i, 'wt1'] > df.loc[i, 'wt2'])
                    
                    if wt_cross or condition_b:
                        signal_1_met = True
                        signals.append('signal_1')
            
            # 第二仓: 必须第一仓满足 + (WaveTrend wt1<-20 and 金叉) or (挤压动能为绿 and wt1>wt2)
            # 注意：第二仓信号出现后一日进场
            if signal_1_met:
                # 检查当天是否有第二仓信号（信号出现，但第二天才进场）
                if not pd.isna(df.loc[i, 'wt1']) and not pd.isna(df.loc[i, 'wt2']):
                    wt_cross = (df.loc[i, 'wt1'] > df.loc[i, 'wt2']) and \
                              (i > 0 and df.loc[i-1, 'wt1'] <= df.loc[i-1, 'wt2'])
                    
                    condition_a = (df.loc[i, 'wt1'] < -20) and wt_cross
                    condition_b = df.loc[i, 'squeeze_green'] and (df.loc[i, 'wt1'] > df.loc[i, 'wt2'])
                    
                    if condition_a or condition_b:
                        signal_2_met = True
                        signals.append('signal_2_delayed')  # 标记为延迟信号
            
            # 第三仓: 必须第二仓满足 + ADX>20
            if signal_2_met:
                if not pd.isna(df.loc[i, 'adx']) and df.loc[i, 'adx'] > self.adx_threshold:
                    signal_3_met = True
                    signals.append('signal_3')
            
            if signals:
                df.loc[i, 'entry_signal'] = ','.join(signals)
                df.loc[i, 'entry_reason'] = self._get_entry_reason(signals)
        
        print(f"✅ 入场信号生成完成")
        return df

    def _get_entry_reason(self, signals):
        """获取入场原因描述"""
        reasons = []
        if 'signal_1' in signals:
            reasons.append('低估区间+WaveTrend金叉或挤压动能')
        if 'signal_2' in signals or 'signal_2_delayed' in signals:
            reasons.append('WaveTrend金叉或挤压动能')
        if 'signal_3' in signals:
            reasons.append('ADX>20(趋势)')
        return ' + '.join(reasons)

    def generate_exit_signals(self, df):
        """生成止盈信号"""
        print("🎯 生成止盈信号...")
        
        df = df.copy()
        df['exit_signal'] = False
        df['exit_reason'] = ''
        
        for i in range(len(df)):
            exit_conditions = []
            
            # 止盈条件: ADX>20 且 wt1>0 且死叉
            if not pd.isna(df.loc[i, 'adx']) and not pd.isna(df.loc[i, 'wt1']):
                if df.loc[i, 'adx'] > 20 and df.loc[i, 'wt1'] > 0:
                    if i > 0 and df.loc[i, 'wt1'] < df.loc[i, 'wt2'] and \
                       df.loc[i-1, 'wt1'] >= df.loc[i-1, 'wt2']:
                        exit_conditions.append('ADX>20且WaveTrend死叉')
            
            if exit_conditions:
                df.loc[i, 'exit_signal'] = True
                df.loc[i, 'exit_reason'] = ' 或 '.join(exit_conditions)
        
        print(f"✅ 止盈信号生成完成")
        return df

    def calculate_position_size(self, df):
        """计算仓位大小"""
        print("📊 计算仓位大小...")
        
        df = df.copy()
        df['position_size'] = 0.0
        
        for i in range(len(df)):
            if pd.notna(df.loc[i, 'entry_signal']):
                signals = df.loc[i, 'entry_signal'].split(',')
                total_position = 0.0
                
                if 'signal_1' in signals:
                    total_position += self.position_levels['level_1']
                if 'signal_2' in signals or 'signal_2_delayed' in signals:
                    total_position += self.position_levels['level_2']
                if 'signal_3' in signals:
                    total_position += self.position_levels['level_3']
                
                df.loc[i, 'position_size'] = total_position
        
        print(f"✅ 仓位计算完成")
        return df

    def run_strategy(self, price_data):
        """运行完整策略"""
        print("=" * 100)
        print("🚀 运行趋势交易策略")
        print("=" * 100)
        print()
        
        df = self.calculate_technical_indicators(price_data)
        df = self.generate_entry_signals(df)
        df = self.generate_exit_signals(df)
        df = self.calculate_position_size(df)
        self.show_strategy_stats(df)
        
        return df

    def show_strategy_stats(self, df):
        """显示策略统计"""
        print()
        print("=" * 100)
        print("📊 策略统计")
        print("=" * 100)
        print()
        
        entry_count = df['entry_signal'].notna().sum()
        print(f"🎯 入场信号总数: {entry_count}")
        
        signal_counts = {'signal_1': 0, 'signal_2': 0, 'signal_3': 0, 'signal_4': 0}
        
        for signals in df['entry_signal'].dropna():
            for signal in signals.split(','):
                if signal in signal_counts:
                    signal_counts[signal] += 1
        
        print("\n📈 各仓位信号触发次数:")
        print(f"  第一仓 (低估区间+技术指标): {signal_counts['signal_1']} 次")
        print(f"  第二仓 (WaveTrend/挤压): {signal_counts['signal_2']} 次")
        print(f"  第三仓 (ADX>20趋势): {signal_counts['signal_3']} 次")
        
        exit_count = df['exit_signal'].sum()
        print(f"\n💰 止盈信号总数: {exit_count}")
        
        avg_position = df[df['position_size'] > 0]['position_size'].mean()
        if not pd.isna(avg_position):
            print(f"\n📊 平均入场仓位: {avg_position*100:.1f}%")
        
        max_position = df['position_size'].max()
        print(f"📊 最大入场仓位: {max_position*100:.1f}%")

    def save_strategy_results(self, df, output_path):
        """保存策略结果"""
        columns_to_save = [
            'date', 'open', 'high', 'low', 'close', 'volume',
            'rsi', 'wt1', 'wt2', 'squeeze_green', 'squeeze_momentum', 'adx',
            'entry_signal', 'entry_reason', 'exit_signal', 'exit_reason', 'position_size'
        ]
        df_save = df[[col for col in columns_to_save if col in df.columns]].copy()
        df_save.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"\n💾 策略结果已保存: {output_path}")


if __name__ == "__main__":
    print("=" * 100)
    print("核心策略模块")
    print("=" * 100)
    print()
    print("包含功能:")
    print("  ✅ 评分系统（0-6分）")
    print("  ✅ 技术指标（RSI、WaveTrend、挤压动能、ADX）")
    print("  ✅ 渐进式入场信号")
    print("  ✅ 止盈信号")
    print()

