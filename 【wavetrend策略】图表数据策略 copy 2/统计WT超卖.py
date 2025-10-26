#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统计WaveTrend超卖情况
分析wt1在不同阈值下的出现次数和后续表现
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path

sys.path.append(str(Path(__file__).parent / '模块'))
from 数据模块 import DataModule


def calculate_wavetrend(df):
    """计算WaveTrend指标"""
    print("📊 计算WaveTrend...")
    df = df.copy()
    
    n1, n2 = 10, 21
    hlc3 = (df['high'] + df['low'] + df['close']) / 3
    esa = hlc3.ewm(span=n1, adjust=False).mean()
    d = (hlc3 - esa).abs().ewm(span=n1, adjust=False).mean()
    ci = (hlc3 - esa) / (0.015 * d)
    
    wt1 = ci.ewm(span=n2, adjust=False).mean()  # EMA - TradingView标准
    wt2 = wt1.rolling(window=4).mean()
    
    df['wt1'] = wt1
    df['wt2'] = wt2
    
    # 计算未来收益
    df['return_5d'] = df['close'].pct_change(5).shift(-5) * 100
    df['return_20d'] = df['close'].pct_change(20).shift(-20) * 100
    df['return_60d'] = df['close'].pct_change(60).shift(-60) * 100
    
    print("✅ WaveTrend计算完成")
    return df


def analyze_wt_levels(df):
    """分析不同wt1水平的统计"""
    print()
    print("=" * 100)
    print("📊 WaveTrend超卖统计分析")
    print("=" * 100)
    print()
    
    # 定义不同的超卖阈值
    thresholds = [-30, -40, -50, -60, -70]
    
    results = []
    
    for threshold in thresholds:
        # 找出wt1低于阈值的情况
        oversold = df[df['wt1'] < threshold].copy()
        count = len(oversold)
        
        if count == 0:
            continue
        
        # 统计这些时刻的价格和未来收益
        avg_price = oversold['close'].mean()
        min_price = oversold['close'].min()
        max_price = oversold['close'].max()
        
        # 未来收益统计
        avg_return_5d = oversold['return_5d'].mean()
        avg_return_20d = oversold['return_20d'].mean()
        avg_return_60d = oversold['return_60d'].mean()
        
        win_rate_5d = (oversold['return_5d'] > 0).sum() / oversold['return_5d'].notna().sum() * 100 if oversold['return_5d'].notna().sum() > 0 else 0
        win_rate_20d = (oversold['return_20d'] > 0).sum() / oversold['return_20d'].notna().sum() * 100 if oversold['return_20d'].notna().sum() > 0 else 0
        win_rate_60d = (oversold['return_60d'] > 0).sum() / oversold['return_60d'].notna().sum() * 100 if oversold['return_60d'].notna().sum() > 0 else 0
        
        results.append({
            'threshold': f'wt1 < {threshold}',
            'count': count,
            'percentage': count / len(df) * 100,
            'avg_price': avg_price,
            'min_price': min_price,
            'max_price': max_price,
            'avg_return_5d': avg_return_5d,
            'avg_return_20d': avg_return_20d,
            'avg_return_60d': avg_return_60d,
            'win_rate_5d': win_rate_5d,
            'win_rate_20d': win_rate_20d,
            'win_rate_60d': win_rate_60d
        })
    
    # 显示统计结果
    print(f"{'超卖阈值':<15} {'出现次数':<10} {'占比':<10} {'5日收益':<12} {'20日收益':<12} {'60日收益':<12}")
    print("-" * 100)
    
    for r in results:
        print(f"{r['threshold']:<15} {r['count']:<10} {r['percentage']:>6.2f}%   "
              f"{r['avg_return_5d']:>+8.2f}%    {r['avg_return_20d']:>+8.2f}%    {r['avg_return_60d']:>+8.2f}%")
    
    print()
    print("=" * 100)
    print("📊 详细分析")
    print("=" * 100)
    print()
    
    for r in results:
        print(f"\n{r['threshold']} 详细统计:")
        print(f"  出现次数: {r['count']}次 ({r['percentage']:.2f}%)")
        print(f"  价格范围: ${r['min_price']:,.0f} - ${r['max_price']:,.0f} (平均 ${r['avg_price']:,.0f})")
        print(f"  未来5日收益: {r['avg_return_5d']:+.2f}% (胜率 {r['win_rate_5d']:.1f}%)")
        print(f"  未来20日收益: {r['avg_return_20d']:+.2f}% (胜率 {r['win_rate_20d']:.1f}%)")
        print(f"  未来60日收益: {r['avg_return_60d']:+.2f}% (胜率 {r['win_rate_60d']:.1f}%)")
    
    return results


def find_wt_below_30(df):
    """详细列出wt1 < -30的所有情况"""
    print()
    print("=" * 100)
    print("📋 wt1 < -30 的所有出现记录")
    print("=" * 100)
    print()
    
    oversold = df[df['wt1'] < -30].copy()
    
    print(f"总共出现 {len(oversold)} 次\n")
    
    # 按时间顺序显示
    oversold = oversold.sort_values('date')
    
    print(f"{'日期':<12} {'价格':<12} {'wt1':<10} {'5日后收益':<12} {'20日后收益':<12} {'60日后收益':<12}")
    print("-" * 100)
    
    for idx, row in oversold.iterrows():
        date_str = str(row['date'])[:10]
        price_str = f"${row['close']:,.0f}"
        wt1_str = f"{row['wt1']:.1f}"
        ret5_str = f"{row['return_5d']:+.1f}%" if pd.notna(row['return_5d']) else "N/A"
        ret20_str = f"{row['return_20d']:+.1f}%" if pd.notna(row['return_20d']) else "N/A"
        ret60_str = f"{row['return_60d']:+.1f}%" if pd.notna(row['return_60d']) else "N/A"
        
        print(f"{date_str:<12} {price_str:<12} {wt1_str:<10} {ret5_str:<12} {ret20_str:<12} {ret60_str:<12}")
    
    # 分年统计
    print()
    print("=" * 100)
    print("📊 按年份统计")
    print("=" * 100)
    print()
    
    oversold['year'] = pd.to_datetime(oversold['date']).dt.year
    yearly_counts = oversold.groupby('year').size()
    
    print(f"{'年份':<10} {'出现次数':<10}")
    print("-" * 30)
    for year, count in yearly_counts.items():
        print(f"{year:<10} {count:<10}")
    
    return oversold


def analyze_golden_cross_after_oversold(df):
    """分析超卖后出现金叉的情况"""
    print()
    print("=" * 100)
    print("📊 超卖后金叉分析")
    print("=" * 100)
    print()
    
    df = df.copy()
    
    # 找出金叉点
    df['golden_cross'] = ((df['wt1'] > df['wt2']) & 
                          (df['wt1'].shift(1) <= df['wt2'].shift(1)))
    
    # 分析不同超卖程度下出现金叉的情况
    thresholds = [-30, -40, -50, -60]
    
    print(f"{'超卖阈值':<15} {'金叉次数':<12} {'平均20日收益':<15} {'胜率':<10}")
    print("-" * 70)
    
    for threshold in thresholds:
        # 找出在超卖区域且发生金叉的情况
        condition = (df['wt1'] < threshold) & df['golden_cross']
        signals = df[condition]
        
        if len(signals) == 0:
            continue
        
        avg_return = signals['return_20d'].mean()
        win_rate = (signals['return_20d'] > 0).sum() / signals['return_20d'].notna().sum() * 100 if signals['return_20d'].notna().sum() > 0 else 0
        
        print(f"wt1 < {threshold:<6} {len(signals):<12} {avg_return:>+10.2f}%       {win_rate:>6.1f}%")


def main():
    print("=" * 100)
    print("🎯 WaveTrend超卖统计分析")
    print("=" * 100)
    print()
    
    # 加载数据
    print("【步骤1】加载数据...")
    data_module = DataModule()
    price_data = data_module.get_price_data()
    print()
    
    # 计算WaveTrend
    print("【步骤2】计算WaveTrend...")
    df = calculate_wavetrend(price_data)
    print()
    
    # 统计分析
    print("【步骤3】统计分析...")
    results = analyze_wt_levels(df)
    
    # 详细列表
    print("\n【步骤4】详细记录...")
    oversold_records = find_wt_below_30(df)
    
    # 金叉分析
    print("\n【步骤5】金叉分析...")
    analyze_golden_cross_after_oversold(df)
    
    print()
    print("=" * 100)
    print("✅ 分析完成！")
    print("=" * 100)
    print()
    
    # 保存结果
    oversold_records.to_csv('数字化数据/wt_oversold_records.csv', index=False, encoding='utf-8-sig')
    print("✅ 详细记录已保存: 数字化数据/wt_oversold_records.csv")
    print()


if __name__ == "__main__":
    main()

