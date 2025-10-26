#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据修复脚本 - 修复图像数字化过程中的异常值
生成时间: 2025-10-09
"""

import pandas as pd
import numpy as np
from datetime import datetime

print('=' * 100)
print('数据修复程序启动')
print('=' * 100)
print()

# ==================== 读取原始数据 ====================
print('【步骤1】读取原始数据...')
sth = pd.read_csv('【以此为准】sth_mvrv_逐日_来自当前可视化.csv')
lth = pd.read_csv('【以此为准】LTH_net_change.csv')
whale = pd.read_csv('【以此为准】Whale_holdings.csv')

sth['date'] = pd.to_datetime(sth['date'])
lth['date'] = pd.to_datetime(lth['date'])
whale['date'] = pd.to_datetime(whale['date'])

print(f'  ✓ STH MVRV: {len(sth)} 行')
print(f'  ✓ LTH Net Change: {len(lth)} 行')
print(f'  ✓ 鲸鱼持仓: {len(whale)} 行')
print()

# ==================== 修复 STH MVRV ====================
print('【步骤2】修复STH MVRV数据...')
print('-' * 100)

sth_fixed = sth.copy()
sth_fixed = sth_fixed.sort_values('date').reset_index(drop=True)

fix_count = 0

# 2.1 识别和修复魔法数字
print('  [2.1] 修复魔法数字...')
magic_numbers = [1.0410, 1.0414, 1.0422, 1.0930]

for i in range(1, len(sth_fixed) - 1):
    current_value = sth_fixed.loc[i, 'sth_mvrv']
    
    # 检查是否是魔法数字
    is_magic = False
    for magic in magic_numbers:
        if abs(current_value - magic) < 0.0001:
            is_magic = True
            break
    
    if is_magic:
        # 用前后值的平均值替换
        prev_value = sth_fixed.loc[i-1, 'sth_mvrv']
        next_value = sth_fixed.loc[i+1, 'sth_mvrv']
        
        # 如果前后值都是魔法数字，向前追溯找正常值
        if abs(prev_value - magic) < 0.0001 or abs(next_value - magic) < 0.0001:
            # 向前找最近的非魔法数字
            j = i - 1
            while j >= 0 and any(abs(sth_fixed.loc[j, 'sth_mvrv'] - m) < 0.0001 for m in magic_numbers):
                j -= 1
            if j >= 0:
                prev_value = sth_fixed.loc[j, 'sth_mvrv']
            
            # 向后找最近的非魔法数字
            k = i + 1
            while k < len(sth_fixed) and any(abs(sth_fixed.loc[k, 'sth_mvrv'] - m) < 0.0001 for m in magic_numbers):
                k += 1
            if k < len(sth_fixed):
                next_value = sth_fixed.loc[k, 'sth_mvrv']
            
            # 线性插值
            if j >= 0 and k < len(sth_fixed):
                weight = (i - j) / (k - j)
                new_value = prev_value + (next_value - prev_value) * weight
            else:
                new_value = (prev_value + next_value) / 2
        else:
            new_value = (prev_value + next_value) / 2
        
        old_value = sth_fixed.loc[i, 'sth_mvrv']
        sth_fixed.loc[i, 'sth_mvrv'] = new_value
        fix_count += 1
        
        if fix_count <= 5:  # 显示前5个修复
            date_str = sth_fixed.loc[i, 'date'].strftime('%Y-%m-%d')
            print(f'      {date_str}: {old_value:.4f} → {new_value:.4f}')

print(f'  ✓ 修复了 {fix_count} 个魔法数字')
print()

# 2.2 修复异常跳跃（尖刺检测）
print('  [2.2] 修复异常跳跃（尖刺）...')
spike_count = 0

for i in range(2, len(sth_fixed) - 2):
    current = sth_fixed.loc[i, 'sth_mvrv']
    prev = sth_fixed.loc[i-1, 'sth_mvrv']
    next_val = sth_fixed.loc[i+1, 'sth_mvrv']
    prev2 = sth_fixed.loc[i-2, 'sth_mvrv']
    next2 = sth_fixed.loc[i+2, 'sth_mvrv']
    
    # 检测尖刺：当前值与前后值差异大，但前后值趋势连续
    jump_up = abs(current - prev) > 0.08
    jump_down = abs(current - next_val) > 0.08
    prev_next_close = abs(prev - next_val) < 0.05
    
    if jump_up and jump_down and prev_next_close:
        # 检查是否是真实的峰值（前后都在上升/下降）
        if not ((prev > prev2 and next_val > next2) or (prev < prev2 and next_val < next2)):
            # 这是一个尖刺，用平滑值替换
            new_value = (prev + next_val) / 2
            old_value = sth_fixed.loc[i, 'sth_mvrv']
            sth_fixed.loc[i, 'sth_mvrv'] = new_value
            spike_count += 1
            
            if spike_count <= 5:
                date_str = sth_fixed.loc[i, 'date'].strftime('%Y-%m-%d')
                print(f'      {date_str}: {old_value:.4f} → {new_value:.4f} (尖刺)')

print(f'  ✓ 修复了 {spike_count} 个尖刺')
print()

# 2.3 保守修复：只修复明显的魔法数字，保留真实波动
print('  [2.3] 保守修复：只修复魔法数字...')
anomaly_2022_count = 0

# 只修复明显的魔法数字，不修复其他波动
for i in range(len(sth_fixed)):
    current = sth_fixed.loc[i, 'sth_mvrv']
    
    # 只修复明显的魔法数字
    if abs(current - 1.0410) < 0.0001 or abs(current - 1.0414) < 0.0001:
        if i > 0 and i < len(sth_fixed) - 1:
            prev = sth_fixed.loc[i-1, 'sth_mvrv']
            next_val = sth_fixed.loc[i+1, 'sth_mvrv']
            
            # 如果前后值都不是魔法数字，用插值替换
            if not (abs(prev - 1.0410) < 0.0001 or abs(prev - 1.0414) < 0.0001) and \
               not (abs(next_val - 1.0410) < 0.0001 or abs(next_val - 1.0414) < 0.0001):
                new_value = (prev + next_val) / 2
                old_value = sth_fixed.loc[i, 'sth_mvrv']
                sth_fixed.loc[i, 'sth_mvrv'] = new_value
                anomaly_2022_count += 1
                
                if anomaly_2022_count <= 5:
                    date_str = sth_fixed.loc[i, 'date'].strftime('%Y-%m-%d')
                    print(f'      {date_str}: {old_value:.4f} → {new_value:.4f} (魔法数字)')

print(f'  ✓ 保守修复了 {anomaly_2022_count} 个魔法数字')
print()

# 2.4 最后的平滑处理（移动平均）
print('  [2.4] 应用轻度平滑...')
# 对修复后的数据应用3日移动平均（权重: 0.25, 0.5, 0.25）
sth_smoothed = sth_fixed.copy()
for i in range(1, len(sth_smoothed) - 1):
    prev = sth_fixed.loc[i-1, 'sth_mvrv']
    current = sth_fixed.loc[i, 'sth_mvrv']
    next_val = sth_fixed.loc[i+1, 'sth_mvrv']
    
    # 计算变化率
    change_prev = abs(current - prev) / prev if prev > 0 else 0
    change_next = abs(next_val - current) / current if current > 0 else 0
    
    # 只在变化率>5%时应用平滑
    if change_prev > 0.05 or change_next > 0.05:
        smoothed = 0.25 * prev + 0.5 * current + 0.25 * next_val
        sth_smoothed.loc[i, 'sth_mvrv'] = smoothed

print(f'  ✓ 平滑处理完成')
print()

total_sth_changes = fix_count + spike_count + anomaly_2022_count
print(f'【STH MVRV 修复总结】共修复 {total_sth_changes} 个异常点')
print()

# ==================== 修复 LTH Net Change ====================
print('【步骤3】修复LTH Net Change数据...')
print('-' * 100)

lth_fixed = lth.copy()
lth_fixed = lth_fixed.sort_values('date').reset_index(drop=True)

# 计算每日变化
lth_fixed['daily_change'] = lth_fixed['lth_net_change_30d'].diff().abs()

# 保守修复：只修复明显的异常值，保留真实市场波动
print('  [3.1] 保守修复：只修复明显异常...')

# 读取原始数据对比
lth_original = pd.read_csv('【以此为准】LTH_net_change.csv')
lth_original['date'] = pd.to_datetime(lth_original['date'])

lth_fix_count = 0

# 只修复那些明显是数字化错误的点
for i in range(1, len(lth_fixed) - 1):
    current_value = lth_fixed.loc[i, 'lth_net_change_30d']
    prev_value = lth_fixed.loc[i-1, 'lth_net_change_30d']
    next_value = lth_fixed.loc[i+1, 'lth_net_change_30d']
    
    # 检查是否是明显的异常跳跃（前后值差异巨大）
    prev_diff = abs(current_value - prev_value)
    next_diff = abs(next_value - current_value)
    
    # 只修复那些前后值差异都很大的孤立点
    if prev_diff > 150000 and next_diff > 150000:
        # 检查原始数据是否也有这个跳跃
        date = lth_fixed.loc[i, 'date']
        original_row = lth_original[lth_original['date'] == date]
        
        if len(original_row) > 0:
            original_value = original_row.iloc[0]['lth_net_change_30d']
            # 如果原始数据也有类似的大跳跃，说明可能是真实的市场事件，不修复
            if abs(original_value - current_value) < 50000:  # 差异不大，保留
                continue
        
        # 用前后值的平均值替换
        new_value = (prev_value + next_value) / 2
        old_value = lth_fixed.loc[i, 'lth_net_change_30d']
        lth_fixed.loc[i, 'lth_net_change_30d'] = new_value
        lth_fix_count += 1
        
        if lth_fix_count <= 5:
            date_str = lth_fixed.loc[i, 'date'].strftime('%Y-%m-%d')
            print(f'      {date_str}: {old_value:.0f} → {new_value:.0f} (孤立异常)')

print(f'  ✓ 保守修复了 {lth_fix_count} 个明显异常点')
print()

# 保守处理：不应用过度平滑，保留市场波动
print('  [3.2] 保守处理：保留市场波动...')
print(f'  ✓ 保留原始市场波动特征')
print()

print(f'【LTH Net Change 修复总结】共修复 {lth_fix_count} 个异常点')
print()

# ==================== 修复鲸鱼持仓 ====================
print('【步骤4】修复鲸鱼持仓数据...')
print('-' * 100)

whale_fixed = whale.copy()
whale_fixed = whale_fixed.sort_values('date').reset_index(drop=True)

# 鲸鱼数据质量较好，只做轻度平滑
print('  [4.1] 应用轻度平滑...')
whale_fixed['whale_holdings_change'] = whale_fixed['whale_holdings_change'].rolling(
    window=3, center=True, min_periods=1
).mean()
print(f'  ✓ 平滑完成')
print()

print(f'【鲸鱼持仓 修复总结】应用了轻度平滑')
print()

# ==================== 保存修复后的数据 ====================
print('【步骤5】保存修复后的数据...')
print('-' * 100)

# 清理辅助列
lth_fixed = lth_fixed[['date', 'lth_net_change_30d']]
sth_smoothed = sth_smoothed[['date', 'sth_mvrv']]
whale_fixed = whale_fixed[['date', 'whale_holdings_change']]

# 保存
sth_smoothed.to_csv('【已修复】sth_mvrv.csv', index=False, encoding='utf-8-sig')
lth_fixed.to_csv('【已修复】LTH_net_change.csv', index=False, encoding='utf-8-sig')
whale_fixed.to_csv('【已修复】Whale_holdings.csv', index=False, encoding='utf-8-sig')

print('  ✓ 已保存: 【已修复】sth_mvrv.csv')
print('  ✓ 已保存: 【已修复】LTH_net_change.csv')
print('  ✓ 已保存: 【已修复】Whale_holdings.csv')
print()

# ==================== 生成对比报告 ====================
print('【步骤6】生成修复前后对比报告...')
print('-' * 100)

# 计算修复前后的差异
sth_diff = abs(sth_smoothed['sth_mvrv'] - sth['sth_mvrv'])
lth_diff = abs(lth_fixed['lth_net_change_30d'] - lth['lth_net_change_30d'])

print()
print('=' * 100)
print('修复完成总结')
print('=' * 100)
print()
print('【STH MVRV】')
print(f'  修复数据点: {total_sth_changes} 个')
print(f'  平均修正幅度: {sth_diff.mean():.6f}')
print(f'  最大修正幅度: {sth_diff.max():.6f}')
print(f'  修正>0.05的点: {len(sth_diff[sth_diff > 0.05])} 个')
print()
print('【LTH Net Change】')
print(f'  修复数据点: {lth_fix_count} 个')
print(f'  平均修正幅度: {lth_diff.mean():.2f} BTC')
print(f'  最大修正幅度: {lth_diff.max():.2f} BTC')
print()
print('【鲸鱼持仓】')
print(f'  应用了轻度平滑处理')
print()
print('=' * 100)
print('✅ 所有数据修复完成！')
print('=' * 100)
print()
print('修复后的文件：')
print('  • 【已修复】sth_mvrv.csv')
print('  • 【已修复】LTH_net_change.csv')
print('  • 【已修复】Whale_holdings.csv')
print()
print('原始文件已保留作为备份。')
print()

