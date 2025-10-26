#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细统计 wt1 < -30 的出现次数和后续涨幅
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path

sys.path.append(str(Path(__file__).parent / '模块'))
from 数据模块 import DataModule


def calculate_wavetrend(df):
    """计算WaveTrend"""
    df = df.copy()
    
    n1, n2 = 10, 21
    hlc3 = (df['high'] + df['low'] + df['close']) / 3
    esa = hlc3.ewm(span=n1, adjust=False).mean()
    d = (hlc3 - esa).abs().ewm(span=n1, adjust=False).mean()
    ci = (hlc3 - esa) / (0.015 * d)
    
    wt1 = ci.ewm(span=n2, adjust=False).mean()  # EMA - TradingView标准
    wt2 = wt1.rolling(window=4).mean()  # SMA
    
    df['wt1'] = wt1
    df['wt2'] = wt2
    
    return df


def find_continuous_periods(df):
    """将连续的超卖天数合并为一个周期"""
    df = df.copy()
    df['oversold'] = df['wt1'] < -30
    
    periods = []
    in_period = False
    period_start = None
    period_data = []
    
    for i in range(len(df)):
        row = df.iloc[i]
        
        if row['oversold'] and not in_period:
            # 开始新的超卖周期
            in_period = True
            period_start = i
            period_data = [row]
        elif row['oversold'] and in_period:
            # 继续超卖周期
            period_data.append(row)
        elif not row['oversold'] and in_period:
            # 超卖周期结束
            in_period = False
            
            # 记录这个周期
            start_date = period_data[0]['date']
            end_date = period_data[-1]['date']
            duration = len(period_data)
            
            # 找出最低wt1
            min_wt1 = min([p['wt1'] for p in period_data])
            min_wt1_date = [p['date'] for p in period_data if p['wt1'] == min_wt1][0]
            min_wt1_price = [p['close'] for p in period_data if p['wt1'] == min_wt1][0]
            
            # 计算周期结束后的涨幅
            end_price = period_data[-1]['close']
            
            # 计算未来涨幅
            if i + 5 < len(df):
                price_5d = df.iloc[i + 5]['close']
                return_5d = (price_5d / end_price - 1) * 100
            else:
                return_5d = np.nan
            
            if i + 20 < len(df):
                price_20d = df.iloc[i + 20]['close']
                return_20d = (price_20d / end_price - 1) * 100
            else:
                return_20d = np.nan
            
            if i + 60 < len(df):
                price_60d = df.iloc[i + 60]['close']
                return_60d = (price_60d / end_price - 1) * 100
            else:
                return_60d = np.nan
            
            periods.append({
                'period_num': len(periods) + 1,
                'start_date': start_date,
                'end_date': end_date,
                'duration': duration,
                'min_wt1': min_wt1,
                'min_wt1_date': min_wt1_date,
                'min_wt1_price': min_wt1_price,
                'exit_price': end_price,
                'return_5d': return_5d,
                'return_20d': return_20d,
                'return_60d': return_60d
            })
    
    return pd.DataFrame(periods)


def main():
    print("=" * 120)
    print("🎯 wt1 < -30 详细统计分析")
    print("=" * 120)
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
    
    # 统计超卖情况
    print("【步骤3】统计超卖周期...")
    
    # 方法1：所有超卖天数
    oversold_days = df[df['wt1'] < -30].copy()
    total_oversold_days = len(oversold_days)
    
    print(f"✅ wt1 < -30 总共出现: {total_oversold_days} 天")
    print(f"   占比: {total_oversold_days/len(df)*100:.2f}%")
    print()
    
    # 方法2：合并连续的超卖天数为周期
    periods_df = find_continuous_periods(df)
    total_periods = len(periods_df)
    
    print(f"✅ 合并连续天数后，共 {total_periods} 个独立的超卖周期")
    print()
    
    # 统计摘要
    print("=" * 120)
    print("📊 超卖周期统计摘要")
    print("=" * 120)
    print()
    
    avg_duration = periods_df['duration'].mean()
    max_duration = periods_df['duration'].max()
    min_wt1_overall = periods_df['min_wt1'].min()
    
    avg_return_5d = periods_df['return_5d'].mean()
    avg_return_20d = periods_df['return_20d'].mean()
    avg_return_60d = periods_df['return_60d'].mean()
    
    win_rate_5d = (periods_df['return_5d'] > 0).sum() / periods_df['return_5d'].notna().sum() * 100
    win_rate_20d = (periods_df['return_20d'] > 0).sum() / periods_df['return_20d'].notna().sum() * 100
    win_rate_60d = (periods_df['return_60d'] > 0).sum() / periods_df['return_60d'].notna().sum() * 100
    
    print(f"平均持续天数: {avg_duration:.1f} 天")
    print(f"最长持续天数: {max_duration} 天")
    print(f"最低wt1值: {min_wt1_overall:.1f}")
    print()
    print(f"周期结束后的平均涨幅:")
    print(f"  5日后:  {avg_return_5d:+.2f}% (胜率 {win_rate_5d:.1f}%)")
    print(f"  20日后: {avg_return_20d:+.2f}% (胜率 {win_rate_20d:.1f}%)")
    print(f"  60日后: {avg_return_60d:+.2f}% (胜率 {win_rate_60d:.1f}%)")
    print()
    
    # 详细列表
    print("=" * 120)
    print("📋 所有超卖周期详细记录")
    print("=" * 120)
    print()
    
    print(f"{'#':<4} {'开始日期':<12} {'结束日期':<12} {'天数':<6} {'最低wt1':<10} {'最低点日期':<12} {'最低点价格':<12} {'5日涨幅':<10} {'20日涨幅':<10} {'60日涨幅':<10}")
    print("-" * 120)
    
    for _, row in periods_df.iterrows():
        num_str = f"{row['period_num']}"
        start_str = str(row['start_date'])[:10]
        end_str = str(row['end_date'])[:10]
        dur_str = f"{row['duration']}"
        wt1_str = f"{row['min_wt1']:.1f}"
        min_date_str = str(row['min_wt1_date'])[:10]
        min_price_str = f"${row['min_wt1_price']:,.0f}"
        
        ret5_str = f"{row['return_5d']:+.1f}%" if pd.notna(row['return_5d']) else "N/A"
        ret20_str = f"{row['return_20d']:+.1f}%" if pd.notna(row['return_20d']) else "N/A"
        ret60_str = f"{row['return_60d']:+.1f}%" if pd.notna(row['return_60d']) else "N/A"
        
        print(f"{num_str:<4} {start_str:<12} {end_str:<12} {dur_str:<6} {wt1_str:<10} {min_date_str:<12} {min_price_str:<12} {ret5_str:<10} {ret20_str:<10} {ret60_str:<10}")
    
    print()
    
    # 按涨幅排序显示TOP和BOTTOM
    print("=" * 120)
    print("🏆 TOP 10 最佳周期（按20日涨幅排序）")
    print("=" * 120)
    print()
    
    top10 = periods_df.nlargest(10, 'return_20d')
    
    print(f"{'#':<4} {'日期':<12} {'最低wt1':<10} {'价格':<12} {'20日涨幅':<12} {'60日涨幅':<12}")
    print("-" * 80)
    
    for _, row in top10.iterrows():
        date_str = str(row['min_wt1_date'])[:10]
        wt1_str = f"{row['min_wt1']:.1f}"
        price_str = f"${row['min_wt1_price']:,.0f}"
        ret20_str = f"{row['return_20d']:+.1f}%" if pd.notna(row['return_20d']) else "N/A"
        ret60_str = f"{row['return_60d']:+.1f}%" if pd.notna(row['return_60d']) else "N/A"
        
        print(f"{row['period_num']:<4} {date_str:<12} {wt1_str:<10} {price_str:<12} {ret20_str:<12} {ret60_str:<12}")
    
    print()
    
    print("=" * 120)
    print("💔 BOTTOM 10 最差周期（按20日涨幅排序）")
    print("=" * 120)
    print()
    
    bottom10 = periods_df.nsmallest(10, 'return_20d')
    
    print(f"{'#':<4} {'日期':<12} {'最低wt1':<10} {'价格':<12} {'20日涨幅':<12} {'60日涨幅':<12}")
    print("-" * 80)
    
    for _, row in bottom10.iterrows():
        date_str = str(row['min_wt1_date'])[:10]
        wt1_str = f"{row['min_wt1']:.1f}"
        price_str = f"${row['min_wt1_price']:,.0f}"
        ret20_str = f"{row['return_20d']:+.1f}%" if pd.notna(row['return_20d']) else "N/A"
        ret60_str = f"{row['return_60d']:+.1f}%" if pd.notna(row['return_60d']) else "N/A"
        
        print(f"{row['period_num']:<4} {date_str:<12} {wt1_str:<10} {price_str:<12} {ret20_str:<12} {ret60_str:<12}")
    
    print()
    print("=" * 120)
    
    # 保存结果
    periods_df.to_csv('数字化数据/wt30_periods_detail.csv', index=False, encoding='utf-8-sig')
    oversold_days.to_csv('数字化数据/wt30_all_days.csv', index=False, encoding='utf-8-sig')
    
    print()
    print("✅ 详细数据已保存:")
    print("  • 数字化数据/wt30_periods_detail.csv (周期汇总)")
    print("  • 数字化数据/wt30_all_days.csv (所有天数)")
    print()


if __name__ == "__main__":
    main()

