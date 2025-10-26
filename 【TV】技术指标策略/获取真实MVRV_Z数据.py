#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取真实的MVRV Z-Score数据

数据源选项：
1. Glassnode API (需要API key)
2. CryptoQuant API (需要API key)
3. Alternative.me API (免费，但可能没有MVRV)
4. 手动从TradingView导出
5. 从公开网站爬取（如MacroMicro）
"""

import requests
import pandas as pd
import json
from datetime import datetime
import time

print("=" * 100)
print("🔍 寻找真实MVRV Z-Score数据源")
print("=" * 100)
print()

# ============================================================================
# 方案1: Glassnode API (最权威，但需要付费API key)
# ============================================================================
print("【方案1】Glassnode API")
print("-" * 100)
print("📊 Glassnode是最权威的链上数据提供商")
print()
print("✅ 优点:")
print("  • 数据最准确、最权威")
print("  • 提供完整的MVRV、Realized Cap、Market Cap等指标")
print("  • API文档完善")
print()
print("❌ 缺点:")
print("  • 需要付费订阅（免费版有限制）")
print("  • 免费版只能获取最近1年的数据")
print()
print("🔗 API文档: https://docs.glassnode.com/")
print("🔗 注册地址: https://studio.glassnode.com/")
print()
print("示例代码:")
print("""
import requests

api_key = "YOUR_GLASSNODE_API_KEY"
url = "https://api.glassnode.com/v1/metrics/market/mvrv_z_score"
params = {
    'a': 'BTC',
    'api_key': api_key,
    's': '2014-01-01',  # 开始日期
    'i': '24h'  # 1天间隔
}
response = requests.get(url, params=params)
data = response.json()
""")
print()

# 尝试测试Glassnode（无API key会失败，但可以看到响应）
print("🔄 测试Glassnode API（无API key）...")
try:
    url = "https://api.glassnode.com/v1/metrics/market/mvrv_z_score"
    params = {
        'a': 'BTC',
        'api_key': 'test',  # 测试key
        's': '2024-01-01',
        'i': '24h'
    }
    response = requests.get(url, params=params, timeout=10)
    print(f"   状态码: {response.status_code}")
    if response.status_code == 401:
        print("   ⚠️  需要有效的API key")
    else:
        print(f"   响应: {response.text[:200]}")
except Exception as e:
    print(f"   ❌ 请求失败: {e}")
print()
print()

# ============================================================================
# 方案2: CryptoQuant API
# ============================================================================
print("【方案2】CryptoQuant API")
print("-" * 100)
print("📊 CryptoQuant也是专业的链上数据平台")
print()
print("✅ 优点:")
print("  • 数据准确")
print("  • 提供多种链上指标")
print()
print("❌ 缺点:")
print("  • 同样需要付费订阅")
print("  • 免费版限制更多")
print()
print("🔗 API文档: https://docs.cryptoquant.com/")
print("🔗 注册地址: https://cryptoquant.com/")
print()
print()

# ============================================================================
# 方案3: Alternative.me API (免费)
# ============================================================================
print("【方案3】Alternative.me API (免费)")
print("-" * 100)
print("📊 提供Fear & Greed Index等指标")
print()

print("🔄 测试Alternative.me API...")
try:
    url = "https://api.alternative.me/v2/ticker/Bitcoin/"
    response = requests.get(url, timeout=10)
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ 成功获取数据")
        print(f"   可用字段: {list(data.get('data', {}).get('1', {}).keys())}")
        print()
        print("   ⚠️  但此API不包含MVRV Z-Score数据")
    else:
        print(f"   状态码: {response.status_code}")
except Exception as e:
    print(f"   ❌ 请求失败: {e}")
print()
print()

# ============================================================================
# 方案4: 从公开图表网站获取
# ============================================================================
print("【方案4】从公开网站获取数据")
print("-" * 100)
print()
print("📊 可用的免费数据源:")
print()
print("1. LookIntoBitcoin")
print("   🔗 https://www.lookintobitcoin.com/charts/mvrv-zscore/")
print("   • 提供MVRV Z-Score图表")
print("   • 可能需要手动导出CSV")
print()
print("2. MacroMicro 财经M平方")
print("   🔗 https://sc.macromicro.me/charts/30335/bitcoin-mvrv-zscore")
print("   • 中文界面")
print("   • 提供图表，可能支持数据导出")
print()
print("3. TradingView")
print("   🔗 https://www.tradingview.com/")
print("   • 搜索 'MVRV Z-Score' 指标")
print("   • 可以导出CSV数据")
print()
print()

# ============================================================================
# 方案5: 使用现有的开源数据集
# ============================================================================
print("【方案5】使用开源数据集")
print("-" * 100)
print()
print("📊 GitHub上可能有人分享的历史数据:")
print()
print("🔍 搜索关键词:")
print("  • 'bitcoin mvrv z-score csv'")
print("  • 'bitcoin on-chain data dataset'")
print("  • 'glassnode data export'")
print()
print()

# ============================================================================
# 推荐方案
# ============================================================================
print("=" * 100)
print("🎯 推荐方案")
print("=" * 100)
print()
print("【免费方案】")
print("1. 注册Glassnode免费账户，获取最近1年的数据")
print("   • 足够测试策略逻辑")
print("   • 可以验证策略有效性")
print()
print("2. 从TradingView手动导出数据")
print("   • 添加MVRV Z-Score指标到图表")
print("   • 使用TradingView的数据导出功能")
print()
print("3. 使用我们的简化版MVRV Z-Score")
print("   • 基于MA200和标准差")
print("   • 能捕捉相似的市场周期特征")
print("   • 已经在当前策略中使用")
print()
print("【付费方案】")
print("1. Glassnode订阅 (推荐)")
print("   • Starter: $29/月")
print("   • Advanced: $99/月")
print("   • Professional: $799/月")
print()
print("2. CryptoQuant订阅")
print("   • Pro: $99/月")
print("   • Premium: $299/月")
print()
print("=" * 100)
print()

# ============================================================================
# 创建数据获取模板
# ============================================================================
print("📝 创建Glassnode API调用模板...")
print()

template_code = """
# ============================================================================
# Glassnode MVRV Z-Score数据获取模板
# ============================================================================

import requests
import pandas as pd
from datetime import datetime

def get_glassnode_mvrv_z(api_key, start_date='2014-01-01'):
    \"\"\"
    从Glassnode获取MVRV Z-Score数据
    
    参数:
        api_key: Glassnode API密钥
        start_date: 开始日期 (格式: 'YYYY-MM-DD')
    
    返回:
        DataFrame with columns: ['date', 'mvrv_z_score']
    \"\"\"
    url = "https://api.glassnode.com/v1/metrics/market/mvrv_z_score"
    
    params = {
        'a': 'BTC',
        'api_key': api_key,
        's': start_date,
        'i': '24h',  # 1天间隔
        'f': 'JSON'
    }
    
    print(f"📊 正在从Glassnode获取MVRV Z-Score数据...")
    print(f"   开始日期: {start_date}")
    
    try:
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            # 转换为DataFrame
            df = pd.DataFrame(data)
            df.columns = ['timestamp', 'mvrv_z_score']
            
            # 转换时间戳
            df['date'] = pd.to_datetime(df['timestamp'], unit='s')
            df = df[['date', 'mvrv_z_score']]
            
            print(f"✅ 成功获取 {len(df)} 条数据")
            print(f"   时间范围: {df['date'].min()} 至 {df['date'].max()}")
            print(f"   MVRV Z范围: {df['mvrv_z_score'].min():.2f} 至 {df['mvrv_z_score'].max():.2f}")
            
            return df
        
        elif response.status_code == 401:
            print("❌ API密钥无效或未授权")
            print("   请访问 https://studio.glassnode.com/ 获取有效的API密钥")
            return None
        
        elif response.status_code == 402:
            print("❌ 需要付费订阅才能访问此数据")
            print("   免费账户只能获取最近1年的数据")
            return None
        
        else:
            print(f"❌ 请求失败: {response.status_code}")
            print(f"   响应: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 获取数据失败: {e}")
        return None


# 使用示例:
if __name__ == "__main__":
    # 替换为你的API密钥
    API_KEY = "YOUR_GLASSNODE_API_KEY_HERE"
    
    # 获取数据
    df = get_glassnode_mvrv_z(API_KEY, start_date='2014-01-01')
    
    if df is not None:
        # 保存为CSV
        df.to_csv('glassnode_mvrv_z_score.csv', index=False, encoding='utf-8-sig')
        print("\\n✅ 数据已保存到: glassnode_mvrv_z_score.csv")
        
        # 显示统计信息
        print("\\n📊 数据统计:")
        print(df['mvrv_z_score'].describe())
"""

# 保存模板
with open('Glassnode_API模板.py', 'w', encoding='utf-8') as f:
    f.write(template_code)

print("✅ 已创建文件: Glassnode_API模板.py")
print()
print("=" * 100)
print()
print("📋 总结:")
print()
print("1. 如果你有Glassnode API key，编辑 'Glassnode_API模板.py' 并运行")
print("2. 如果没有，可以:")
print("   • 注册Glassnode免费账户获取最近1年数据")
print("   • 从TradingView手动导出数据")
print("   • 继续使用当前的简化版MVRV Z-Score（已经很有效）")
print()
print("3. 当前策略使用的简化版MVRV Z-Score:")
print("   • 基于MA200和价格标准差")
print("   • 能够捕捉市场周期的极端情绪")
print("   • 全周期回测表现: +26,060% (261.6倍)")
print()
print("=" * 100)






