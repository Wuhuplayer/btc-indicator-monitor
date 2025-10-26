#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BTC图表策略模块 - 专门处理策略分析逻辑
"""

import pandas as pd
import numpy as np

class StrategyModule:
    """策略模块 - 处理策略评分和信号生成"""

    def __init__(self):
        pass

    def calculate_strategy_scores(self, chart_data, price_data):
        """计算策略评分"""
        print("📊 计算策略评分...")

        # 如果chart_data和price_data是同一个数据，直接使用
        if chart_data is price_data:
            df = chart_data.copy()
        else:
            # 合并数据
            df = price_data.merge(chart_data, on='date', how='left')
        
        df = df.fillna(method='ffill').fillna(method='bfill')

        # 计算评分
        df['mvrv_score'] = df['sth_mvrv'].apply(self._calculate_mvrv_score)

        # 为缺失的列创建假数据（中性值）
        if 'whale_holdings_change' not in df.columns:
            df['whale_holdings_change'] = 0.0  # 中性值
        df['whale_score'] = df['whale_holdings_change'].apply(self._calculate_whale_score)

        if 'lth_net_change_30d' not in df.columns:
            df['lth_net_change_30d'] = 0  # 中性值
        df['lth_score'] = df['lth_net_change_30d'].apply(self._calculate_lth_score)

        # 计算总评分和信号
        df['total_score'] = df['mvrv_score'] + df['whale_score'] + df['lth_score']
        df['strategy_signal'] = df.apply(lambda row: self._get_strategy_signal(
            row['total_score'], row['mvrv_score'], row['whale_score'], row['lth_score']
        ), axis=1)

        print(f"✅ 策略评分完成: {len(df)} 条记录")
        return df

    def _calculate_mvrv_score(self, mvrv_value):
        """计算短期持有者MVRV评分 - 修复漏洞"""
        if pd.isna(mvrv_value):
            return 0
        if mvrv_value < 0.8:
            return 2  # 0.8以下超卖
        elif 0.8 <= mvrv_value < 1.0:
            return 1  # 0.8-1.0中性偏超卖
        elif 1.0 <= mvrv_value <= 1.2:
            return 1  # 1-1.2可买
        else:
            return 0  # 1.2以上超买

    def _calculate_whale_score(self, whale_change):
        """计算鲸鱼总持仓月度变化百分比评分 - 使用原始阈值"""
        if pd.isna(whale_change):
            return 0
        if whale_change < -0.01:
            return 0  # <-0.01大户逃离
        elif 0 <= whale_change <= 0.01:
            return 1  # 0-0.01入场
        else:
            return 2  # >0.01进场

    def _calculate_lth_score(self, lth_change):
        """计算长期持有者净持仓变化30天合计评分 - 使用原始阈值"""
        if pd.isna(lth_change):
            return 0
        if lth_change < -250000:
            return 0  # <-250k超卖出场
        elif 150000 <= lth_change <= 500000:
            return 1  # 150k-500k入场
        elif lth_change > 500000:
            return 2  # >500k加仓入场
        else:
            return 0  # 其他情况

    def _get_strategy_signal(self, total_score, mvrv_score, whale_score, lth_score):
        """获取策略信号 - 严格按照策略图规则"""
        if 5 <= total_score <= 6:
            return "BUY"  # 抄底时间段: 5-6分
        elif 3 <= total_score <= 4:
            return "DCA"  # 定投时间段: 3-4分
        else:
            # 停止时间段(1-2分)和其他情况: 检查卖出条件
            sell_conditions = 0
            if mvrv_score == 0:  # MVRV 1.2以上超买
                sell_conditions += 1
            if whale_score == 0:  # 鲸鱼 <-0.01大户逃离
                sell_conditions += 1
            if lth_score == 0:  # 长期持有者 <-250k超卖出场
                sell_conditions += 1
            
            if sell_conditions >= 2:
                return "SELL"  # 满足至少两个条件时卖出
            else:
                return "DCA"  # 其他情况定投

    def show_strategy_stats(self, df):
        """显示策略统计"""
        print("\n📈 策略分析结果:")

        signal_counts = df['strategy_signal'].value_counts()
        print("\n🎯 策略信号分布:")
        for signal, count in signal_counts.items():
            percentage = (count / len(df)) * 100
            print(f"  {signal}: {count} 天 ({percentage:.1f}%)")

        print(f"\n📊 评分统计:")
        print(f"  平均评分: {df['total_score'].mean():.2f}")
        print(f"  最高评分: {df['total_score'].max()}")
        print(f"  最低评分: {df['total_score'].min()}")

    def save_strategy_results(self, df, data_folder):
        """保存策略结果"""
        df.to_csv(f'{data_folder}/strategy_results.csv', index=False)
        print(f"💾 策略结果已保存: {data_folder}/strategy_results.csv")
