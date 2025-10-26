
# ============================================================================
# Glassnode MVRV Z-Score数据获取模板
# ============================================================================

import requests
import pandas as pd
from datetime import datetime

def get_glassnode_mvrv_z(api_key, start_date='2014-01-01'):
    """
    从Glassnode获取MVRV Z-Score数据
    
    参数:
        api_key: Glassnode API密钥
        start_date: 开始日期 (格式: 'YYYY-MM-DD')
    
    返回:
        DataFrame with columns: ['date', 'mvrv_z_score']
    """
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
        print("\n✅ 数据已保存到: glassnode_mvrv_z_score.csv")
        
        # 显示统计信息
        print("\n📊 数据统计:")
        print(df['mvrv_z_score'].describe())
