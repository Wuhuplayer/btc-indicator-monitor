#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据模块 - 获取真实BTC价格数据
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import os

class DataModule:
    """数据模块 - 处理所有数据相关操作"""

    def __init__(self):
        self.data_folder = "数字化数据"
        os.makedirs(self.data_folder, exist_ok=True)

    def get_price_data(self):
        """获取BTC价格数据"""
        print("💰 获取BTC价格数据...")

        try:
            url = "https://min-api.cryptocompare.com/data/v2/histoday"
            params = {
                'fsym': 'BTC',
                'tsym': 'USD',
                'limit': 1825,
                'toTs': int(datetime.now().timestamp())
            }

            response = requests.get(url, params=params, timeout=30)

            if response.status_code == 200:
                data = response.json()
                if 'Data' in data and 'Data' in data['Data']:
                    price_data = []
                    for item in data['Data']['Data']:
                        price_data.append({
                            'date': datetime.fromtimestamp(item['time']).date(),
                            'open': item['open'],
                            'high': item['high'],
                            'low': item['low'],
                            'close': item['close'],
                            'price': item['close'],  # 保留兼容性
                            'volume': item['volumeto']
                        })

                    df = pd.DataFrame(price_data)
                    df['date'] = pd.to_datetime(df['date'])
                    print(f"✅ 获取价格数据: {len(df)} 条记录")
                    return df

            print("❌ 价格数据获取失败")
            return None

        except:
            print("❌ 价格数据获取失败")
            return None

    def load_chart_data(self):
        """加载完整图表数据"""
        try:
            df = pd.read_csv(f'{self.data_folder}/complete_chart_data.csv')
            df['date'] = pd.to_datetime(df['date'])
            print(f"✅ 加载图表数据: {len(df)} 条记录")
            return df
        except:
            print("❌ 请先运行数字化功能生成数据")
            return None
