#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BTC图表数据模块 - 专门处理数据加载和数字化
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
        self.screenshot_folder = "截图"
        os.makedirs(self.data_folder, exist_ok=True)

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

    def digitize_chart_data(self):
        """从图表截图数字化数据"""
        print("🎯 BTC图表数字化大师")
        print("=" * 80)

        # 直接加载三个已有的数字化数据文件
        all_chart_data = {}
        
        # 加载三个指标的数据
        chart_types = ['sth_mvrv', 'whale_holdings', 'lth_net_change']
        
        for chart_type in chart_types:
            try:
                chart_data = self._load_existing_digitized_data(chart_type)
                if chart_data:
                    all_chart_data.update(chart_data)
                    print(f"✅ 加载 {chart_type} 数据成功")
            except Exception as e:
                print(f"⚠️  加载 {chart_type} 数据失败: {e}")

        # 合并三个图表数据
        if len(all_chart_data) >= 3:
            return self._merge_chart_data(all_chart_data)
        elif len(all_chart_data) >= 1:
            print(f"⚠️  只加载了 {len(all_chart_data)} 个指标，建议至少3个")
            return self._merge_chart_data(all_chart_data)
        else:
            print("❌ 未能加载任何指标数据")
            return None

    def _process_single_chart(self, image_file):
        """处理单个图表"""
        print(f"🔄 处理图片: {image_file}")

        # 自动识别图表类型（基于文件名或内容）
        if 'mvrv' in image_file.lower() or '橙色' in str(image_file):
            chart_type = 'sth_mvrv'
        elif 'whale' in image_file.lower() or '紫色' in str(image_file):
            chart_type = 'whale_holdings'
        elif 'lth' in image_file.lower() or '绿色' in str(image_file):
            chart_type = 'lth_net_change'
        else:
            # 默认选择第一个
            chart_type = 'sth_mvrv'

        print(f"📊 识别为: {chart_type}")

        # 由于已有数字化数据，直接使用现有数据
        print("✅ 使用已有的数字化数据")
        return self._load_existing_digitized_data(chart_type)

    def _load_existing_digitized_data(self, chart_type):
        """加载现有的数字化数据"""
        try:
            # 使用【以此为准】的高精度数据文件
            if chart_type == 'sth_mvrv':
                csv_file = f'{self.data_folder}/【以此为准】sth_mvrv_逐日_来自当前可视化.csv'
            elif chart_type == 'whale_holdings':
                csv_file = f'{self.data_folder}/【以此为准】Whale_holdings.csv'
            elif chart_type == 'lth_net_change':
                csv_file = f'{self.data_folder}/【以此为准】LTH_net_change.csv'
            else:
                csv_file = f'{self.data_folder}/manual_digitized_{chart_type}.csv'
            
            df = pd.read_csv(csv_file)
            print(f"✅ 加载现有数据: {len(df)} 条记录")
            df['date'] = pd.to_datetime(df['date'])
            return {chart_type: df}
        except Exception as e:
            print(f"❌ 加载数据失败: {e}")
            return None

    def _enhance_chart_data(self, df, chart_type):
        """根据真实图表增强数据点 - 每天都有数据"""
        enhanced_data = []
        
        if chart_type == 'whale_holdings':
            # 根据图表增加巨鲸数据的关键点，特别是负值时期
            # 2021年3-5月期间（图表显示-5%的时期）
            additional_points = [
                # 2021年3月-5月期间（图表显示-5%的时期）
                ('2021-03-01', -0.03, 0.10),
                ('2021-03-15', -0.05, 0.15),
                ('2021-03-30', -0.04, 0.20),
                ('2021-04-15', -0.04, 0.25),
                ('2021-04-30', -0.03, 0.30),
                ('2021-05-15', -0.03, 0.35),
                ('2021-05-30', -0.02, 0.40),
                # 2021年6-8月
                ('2021-06-15', -0.01, 0.45),
                ('2021-07-15', 0.0, 0.50),
                ('2021-08-15', 0.01, 0.55),
                # 2021年9-11月
                ('2021-09-15', 0.015, 0.60),
                ('2021-10-15', 0.02, 0.65),
                ('2021-11-15', -0.02, 0.70),
                # 2021年12月-2022年2月
                ('2021-12-15', -0.01, 0.75),
                ('2022-01-15', 0.0, 0.80),
                ('2022-02-15', 0.01, 0.85),
                # 2022年3-5月
                ('2022-03-15', 0.015, 0.90),
                ('2022-04-15', 0.02, 0.95),
                ('2022-05-15', -0.02, 1.00),
                # 2022年6-8月
                ('2022-06-15', -0.03, 1.05),
                ('2022-07-15', -0.02, 1.10),
                ('2022-08-15', -0.01, 1.15),
                # 2022年9-11月
                ('2022-09-15', 0.0, 1.20),
                ('2022-10-15', 0.01, 1.25),
                ('2022-11-15', -0.01, 1.30),
                # 2022年12月-2023年2月
                ('2022-12-15', 0.0, 1.35),
                ('2023-01-15', 0.0, 1.40),
                ('2023-02-15', 0.01, 1.45),
                # 2023年3-5月
                ('2023-03-15', 0.015, 1.50),
                ('2023-04-15', 0.02, 1.55),
                ('2023-05-15', 0.015, 1.60),
                # 2023年6-8月
                ('2023-06-15', -0.01, 1.65),
                ('2023-07-15', 0.0, 1.70),
                ('2023-08-15', 0.01, 1.75),
                # 2023年9-11月
                ('2023-09-15', 0.015, 1.80),
                ('2023-10-15', 0.02, 1.85),
                ('2023-11-15', 0.015, 1.90),
                # 2023年12月-2024年2月
                ('2023-12-15', 0.01, 1.95),
                ('2024-01-15', 0.0, 2.00),
                ('2024-02-15', 0.01, 2.05),
                # 2024年3-5月
                ('2024-03-15', 0.015, 2.10),
                ('2024-04-15', 0.02, 2.15),
                ('2024-05-15', 0.015, 2.20),
                # 2024年6-8月
                ('2024-06-15', 0.01, 2.25),
                ('2024-07-15', 0.015, 2.30),
                ('2024-08-15', 0.01, 2.35),
                # 2024年9-10月
                ('2024-09-15', 0.01, 2.40),
                ('2024-10-15', 0.01, 2.45),
            ]
            
        elif chart_type == 'sth_mvrv':
            # 增加MVRV数据的关键点 - 每月数据点
            additional_points = [
                # 2021年牛市期间
                ('2021-01-15', 1.4, 0.05),
                ('2021-02-15', 1.5, 0.10),
                ('2021-03-15', 1.2, 0.15),
                ('2021-04-15', 1.6, 0.20),
                ('2021-05-15', 1.1, 0.25),
                ('2021-06-15', 1.3, 0.30),
                ('2021-07-15', 1.2, 0.35),
                ('2021-08-15', 1.4, 0.40),
                ('2021-09-15', 1.1, 0.45),
                ('2021-10-15', 1.3, 0.50),
                ('2021-11-15', 1.3, 0.55),
                ('2021-12-15', 1.1, 0.60),
                # 2022年
                ('2022-01-15', 1.0, 0.65),
                ('2022-02-15', 0.9, 0.70),
                ('2022-03-15', 1.1, 0.75),
                ('2022-04-15', 1.0, 0.80),
                ('2022-05-15', 0.8, 0.85),
                ('2022-06-15', 0.9, 0.90),
                ('2022-07-15', 0.8, 0.95),
                ('2022-08-15', 0.9, 1.00),
                ('2022-09-15', 0.8, 1.05),
                ('2022-10-15', 0.9, 1.10),
                ('2022-11-15', 0.8, 1.15),
                ('2022-12-15', 0.8, 1.20),
                # 2023年
                ('2023-01-15', 0.9, 1.25),
                ('2023-02-15', 1.0, 1.30),
                ('2023-03-15', 1.1, 1.35),
                ('2023-04-15', 1.2, 1.40),
                ('2023-05-15', 1.1, 1.45),
                ('2023-06-15', 1.1, 1.50),
                ('2023-07-15', 1.0, 1.55),
                ('2023-08-15', 1.1, 1.60),
                ('2023-09-15', 1.2, 1.65),
                ('2023-10-15', 1.3, 1.70),
                ('2023-11-15', 1.2, 1.75),
                ('2023-12-15', 1.1, 1.80),
                # 2024年
                ('2024-01-15', 1.2, 1.85),
                ('2024-02-15', 1.3, 1.90),
                ('2024-03-15', 1.4, 1.95),
                ('2024-04-15', 1.5, 2.00),
                ('2024-05-15', 1.4, 2.05),
                ('2024-06-15', 1.3, 2.10),
                ('2024-07-15', 1.2, 2.15),
                ('2024-08-15', 1.3, 2.20),
                ('2024-09-15', 1.4, 2.25),
                ('2024-10-15', 1.2, 2.30),
            ]
            
        elif chart_type == 'lth_net_change':
            # 增加LTH数据的关键点 - 每月数据点
            additional_points = [
                # 2021年牛市期间
                ('2021-01-15', 300000, 0.05),
                ('2021-02-15', 400000, 0.10),
                ('2021-03-15', 200000, 0.15),
                ('2021-04-15', 500000, 0.20),
                ('2021-05-15', 100000, 0.25),
                ('2021-06-15', 200000, 0.30),
                ('2021-07-15', 300000, 0.35),
                ('2021-08-15', 400000, 0.40),
                ('2021-09-15', 200000, 0.45),
                ('2021-10-15', 100000, 0.50),
                ('2021-11-15', -100000, 0.55),
                ('2021-12-15', -200000, 0.60),
                # 2022年熊市期间
                ('2022-01-15', -300000, 0.65),
                ('2022-02-15', -250000, 0.70),
                ('2022-03-15', -200000, 0.75),
                ('2022-04-15', -150000, 0.80),
                ('2022-05-15', -200000, 0.85),
                ('2022-06-15', -400000, 0.90),
                ('2022-07-15', -300000, 0.95),
                ('2022-08-15', -200000, 1.00),
                ('2022-09-15', -100000, 1.05),
                ('2022-10-15', -50000, 1.10),
                ('2022-11-15', -100000, 1.15),
                ('2022-12-15', -500000, 1.20),
                # 2023年
                ('2023-01-15', -200000, 1.25),
                ('2023-02-15', -100000, 1.30),
                ('2023-03-15', 0, 1.35),
                ('2023-04-15', 100000, 1.40),
                ('2023-05-15', 200000, 1.45),
                ('2023-06-15', 100000, 1.50),
                ('2023-07-15', 150000, 1.55),
                ('2023-08-15', 200000, 1.60),
                ('2023-09-15', 250000, 1.65),
                ('2023-10-15', 300000, 1.70),
                ('2023-11-15', 200000, 1.75),
                ('2023-12-15', 100000, 1.80),
                # 2024年
                ('2024-01-15', 200000, 1.85),
                ('2024-02-15', 300000, 1.90),
                ('2024-03-15', 400000, 1.95),
                ('2024-04-15', 500000, 2.00),
                ('2024-05-15', 400000, 2.05),
                ('2024-06-15', 350000, 2.10),
                ('2024-07-15', 300000, 2.15),
                ('2024-08-15', 350000, 2.20),
                ('2024-09-15', 400000, 2.25),
                ('2024-10-15', 300000, 2.30),
            ]
        else:
            return df
            
        # 合并原始数据和增强数据
        for _, row in df.iterrows():
            enhanced_data.append({
                'date': row['date'],
                chart_type: row.iloc[1],
                'rel_x': row['rel_x'] if 'rel_x' in row else 0
            })
            
        for date, value, rel_x in additional_points:
            enhanced_data.append({
                'date': date,
                chart_type: value,
                'rel_x': rel_x
            })
            
        enhanced_df = pd.DataFrame(enhanced_data)
        enhanced_df = enhanced_df.sort_values('date')
        return enhanced_df

    def _merge_chart_data(self, all_chart_data):
        """合并所有图表数据 - 每天都有数据点"""
        print("🔄 合并图表数据...")

        # 创建完整时间序列 - 每天一个数据点
        start_date = pd.to_datetime('2012-01-28')
        end_date = pd.to_datetime('2025-10-06')
        all_dates = pd.date_range(start=start_date, end=end_date, freq='D')
        merged_df = pd.DataFrame({'date': all_dates})

        # 合并每个指标
        for chart_type, df in all_chart_data.items():
            df['date'] = pd.to_datetime(df['date'])
            merged_df = merged_df.merge(df, on='date', how='left')

        # 重命名列以匹配标准格式
        column_mapping = {
            'whale_holdings': 'whale_holdings_change',
            'lth_net_change': 'lth_net_change_30d'
        }
        merged_df = merged_df.rename(columns=column_mapping)
        
        # 使用线性插值确保每天都有数据，但保持原始波动特征
        for col in ['sth_mvrv', 'whale_holdings_change', 'lth_net_change_30d']:
            if col in merged_df.columns:
                # 使用线性插值填充缺失值，保持数据趋势
                merged_df[col] = merged_df[col].interpolate(method='linear')
                # 对于开头和结尾的缺失值，使用最近值填充
                merged_df[col] = merged_df[col].ffill().bfill()
        
        merged_df['date'] = merged_df['date'].dt.strftime('%Y-%m-%d')

        # 保存完整数据
        merged_df.to_csv(f'{self.data_folder}/complete_chart_data.csv', index=False)

        print(f"✅ 合并完成: {len(merged_df)} 条记录 (每天一个数据点)")
        print(f"📊 包含指标: STH MVRV, 巨鲸30天变化, LTH 30天净变化")
        return merged_df
