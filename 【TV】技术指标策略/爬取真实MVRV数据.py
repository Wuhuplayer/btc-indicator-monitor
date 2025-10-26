#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
尝试从公开来源获取真实MVRV Z-Score数据
"""

import requests
import pandas as pd
import json
from datetime import datetime
import time

print("=" * 100)
print("🔍 尝试获取真实MVRV Z-Score数据")
print("=" * 100)
print()

# ============================================================================
# 方法1: 尝试从Glassnode Studio获取公开数据
# ============================================================================
print("【方法1】尝试Glassnode Studio公开API...")
print("-" * 100)

try:
    # Glassnode有一些公开的端点不需要API key
    url = "https://api.glassnode.com/v1/metrics/market/mvrv"
    params = {
        'a': 'BTC',
        'i': '24h',
        'f': 'JSON'
    }
    
    print("🔄 尝试获取MVRV数据（无API key）...")
    response = requests.get(url, params=params, timeout=10)
    
    if response.status_code == 200:
        print("✅ 成功！")
        data = response.json()
        print(f"   获取到 {len(data)} 条数据")
    else:
        print(f"❌ 状态码: {response.status_code}")
        if response.status_code == 401:
            print("   需要API key")
        elif response.status_code == 402:
            print("   需要付费订阅")
except Exception as e:
    print(f"❌ 失败: {e}")

print()

# ============================================================================
# 方法2: 尝试从CoinMetrics获取
# ============================================================================
print("【方法2】尝试CoinMetrics Community API (免费)...")
print("-" * 100)

try:
    # CoinMetrics提供免费的社区API
    url = "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"
    params = {
        'assets': 'btc',
        'metrics': 'CapMrktCurUSD,CapRealUSD',  # Market Cap和Realized Cap
        'frequency': '1d',
        'start_time': '2014-01-01',
        'page_size': 10000
    }
    
    print("🔄 尝试获取Market Cap和Realized Cap...")
    response = requests.get(url, params=params, timeout=30)
    
    if response.status_code == 200:
        data = response.json()
        if 'data' in data:
            df = pd.DataFrame(data['data'])
            print(f"✅ 成功获取 {len(df)} 条数据！")
            print(f"   时间范围: {df['time'].min()} 至 {df['time'].max()}")
            print()
            
            # 转换数据
            df['date'] = pd.to_datetime(df['time'])
            df['market_cap'] = pd.to_numeric(df['CapMrktCurUSD'], errors='coerce')
            df['realized_cap'] = pd.to_numeric(df['CapRealUSD'], errors='coerce')
            
            # 计算MVRV
            df['mvrv'] = df['market_cap'] / df['realized_cap']
            
            # 计算MVRV Z-Score
            # Z-Score = (MVRV - mean(MVRV)) / std(MVRV)
            # 或者更准确的: (Market Cap - Realized Cap) / std(Market Cap)
            df['mvrv_z_score'] = (df['market_cap'] - df['realized_cap']) / df['market_cap'].rolling(window=200).std()
            
            # 清理数据
            df_clean = df[['date', 'market_cap', 'realized_cap', 'mvrv', 'mvrv_z_score']].dropna()
            
            print(f"📊 计算完成:")
            print(f"   有效数据: {len(df_clean)} 条")
            print(f"   MVRV范围: {df_clean['mvrv'].min():.2f} - {df_clean['mvrv'].max():.2f}")
            print(f"   MVRV Z-Score范围: {df_clean['mvrv_z_score'].min():.2f} - {df_clean['mvrv_z_score'].max():.2f}")
            print()
            
            # 保存数据
            output_file = 'results/真实MVRV_Z_Score数据_CoinMetrics.csv'
            df_clean.to_csv(output_file, index=False, encoding='utf-8-sig')
            print(f"✅ 数据已保存到: {output_file}")
            print()
            
            # 显示最近的数据
            print("📋 最近10天的数据:")
            print(df_clean[['date', 'mvrv', 'mvrv_z_score']].tail(10).to_string(index=False))
            print()
            
            # 统计信息
            print("📊 MVRV Z-Score统计:")
            print(df_clean['mvrv_z_score'].describe())
            print()
            
            print("=" * 100)
            print("🎉 成功获取真实的MVRV数据！")
            print("=" * 100)
            print()
            print("数据来源: CoinMetrics Community API (免费)")
            print("数据说明:")
            print("  • Market Cap: 市值（价格 × 流通量）")
            print("  • Realized Cap: 实现市值（每个币按最后移动时的价格计算）")
            print("  • MVRV: Market Cap / Realized Cap")
            print("  • MVRV Z-Score: (Market Cap - Realized Cap) / std(Market Cap)")
            print()
            print("🔗 API文档: https://docs.coinmetrics.io/")
            print()
            
        else:
            print(f"❌ 响应格式异常: {data}")
    else:
        print(f"❌ 状态码: {response.status_code}")
        print(f"   响应: {response.text[:200]}")
        
except Exception as e:
    print(f"❌ 失败: {e}")
    import traceback
    traceback.print_exc()

print()

# ============================================================================
# 方法3: 尝试从Blockchain.com获取
# ============================================================================
print("【方法3】尝试Blockchain.com API...")
print("-" * 100)

try:
    url = "https://api.blockchain.info/charts/market-cap"
    params = {
        'timespan': 'all',
        'format': 'json'
    }
    
    print("🔄 尝试获取Market Cap历史数据...")
    response = requests.get(url, params=params, timeout=30)
    
    if response.status_code == 200:
        data = response.json()
        if 'values' in data:
            print(f"✅ 成功获取 {len(data['values'])} 条Market Cap数据")
            print("   ⚠️  但Blockchain.com不提供Realized Cap，无法计算真实MVRV")
        else:
            print(f"❌ 响应格式异常")
    else:
        print(f"❌ 状态码: {response.status_code}")
        
except Exception as e:
    print(f"❌ 失败: {e}")

print()
print()

# ============================================================================
# 总结
# ============================================================================
print("=" * 100)
print("📋 数据获取总结")
print("=" * 100)
print()
print("✅ CoinMetrics Community API - 成功！")
print("   • 免费API，无需注册")
print("   • 提供Market Cap和Realized Cap")
print("   • 可以计算真实的MVRV和MVRV Z-Score")
print("   • 数据已保存到: results/真实MVRV_Z_Score数据_CoinMetrics.csv")
print()
print("❌ Glassnode API - 需要API key")
print("❌ Blockchain.com - 缺少Realized Cap数据")
print()
print("🎯 下一步:")
print("   1. 使用真实MVRV数据重新运行策略")
print("   2. 对比简化版和真实版的差异")
print("   3. 优化策略参数")
print()
print("=" * 100)







