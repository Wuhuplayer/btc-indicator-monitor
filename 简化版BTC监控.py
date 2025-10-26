#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版BTC技术指标监控系统 - 不依赖TA-Lib
"""

import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
import warnings
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
warnings.filterwarnings('ignore')

class SimpleBTCIndicatorMonitor:
    def __init__(self, email_config=None):
        """简化版BTC技术指标监控系统"""
        self.email_config = email_config or {}
        
    def send_email(self, subject, body, is_alert=False):
        """发送邮件"""
        if not self.email_config or not self.email_config.get('sender_email'):
            print(f"⚠️ 邮箱未配置，跳过发送: {subject}")
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = self.email_config['sender_email']
            msg['To'] = self.email_config['receiver_email']
            
            if is_alert:
                msg['Subject'] = f"🚨 {subject}"
            else:
                msg['Subject'] = f"📊 {subject}"
            
            html_body = f"""
            <html>
            <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
                th {{ background-color: #4CAF50; color: white; padding: 10px; text-align: left; }}
                td {{ border: 1px solid #ddd; padding: 8px; }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
                .alert {{ background-color: #fff3cd; padding: 15px; margin: 10px 0; border-left: 5px solid #ff9800; }}
                .success {{ background-color: #e8f5e9; padding: 15px; margin: 10px 0; border-left: 5px solid #4CAF50; }}
            </style>
            </head>
            <body>
                {body}
            </body>
            </html>
            """
            
            msg.attach(MIMEText(html_body, 'html'))
            
            # 使用SSL连接发送邮件
            with smtplib.SMTP_SSL('smtp.qq.com', 465) as server:
                server.login(self.email_config['sender_email'], self.email_config['sender_password'])
                server.send_message(msg)
            
            print(f"✅ 邮件已发送: {subject}")
            return True
            
        except Exception as e:
            print(f"❌ 邮件发送失败: {e}")
            return False
    
    def get_btc_data(self):
        """获取BTC数据"""
        print("📥 开始获取BTC数据...")
        
        try:
            # 使用Binance API获取最近数据
            end_time = int(datetime.now().timestamp() * 1000)
            start_time = end_time - (90 * 24 * 60 * 60 * 1000)  # 最近90天，确保有足够数据计算指标
            
            url = "https://api.binance.com/api/v3/klines"
            params = {
                'symbol': 'BTCUSDT',
                'interval': '1d',
                'startTime': start_time,
                'endTime': end_time,
                'limit': 1000
            }
            
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if data and len(data) > 10:
                    df = pd.DataFrame(data, columns=[
                        'timestamp', 'open', 'high', 'low', 'close', 'volume',
                        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                        'taker_buy_quote', 'ignore'
                    ])
                    
                    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df['open'] = df['open'].astype(float)
                    df['high'] = df['high'].astype(float)
                    df['low'] = df['low'].astype(float)
                    df['close'] = df['close'].astype(float)
                    df['volume'] = df['volume'].astype(float)
                    
                    df = df[['date', 'open', 'high', 'low', 'close', 'volume']].reset_index(drop=True)
                    
                    print(f"✅ 成功获取 {len(df)} 天数据")
                    print(f"📅 数据区间: {df['date'].min().strftime('%Y-%m-%d')} 至 {df['date'].max().strftime('%Y-%m-%d')}")
                    print(f"💰 价格区间: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
                    print(f"📊 最新价格: ${df['close'].iloc[-1]:,.2f} (日期: {df['date'].iloc[-1].strftime('%Y-%m-%d')})")
                    
                    return df
                
        except Exception as e:
            print(f"⚠️ 获取数据失败: {e}")
        
        # 备用：生成模拟数据
        print("使用模拟数据...")
        # 生成从2024年1月到今天的日期范围
        from datetime import datetime
        today = datetime.now()
        dates = pd.date_range(start='2024-01-01', end=today.strftime('%Y-%m-%d'), freq='D')
        price = 50000
        prices = []
        
        for i in range(len(dates)):
            change = np.random.normal(0.001, 0.03)
            price *= (1 + change)
            if price < 20000:
                price = 20000
            elif price > 100000:
                price = 100000
            prices.append(price)
        
        df = pd.DataFrame({
            'date': dates,
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices], 
            'close': prices,
            'volume': [np.random.randint(20000000, 100000000) for _ in range(len(dates))]
        })
        
        print(f"✅ 生成模拟数据 {len(df)} 天")
        return df
    
    def calculate_simple_indicators(self, df):
        """计算简化版技术指标"""
        print("计算技术指标...")
        
        # 简单移动平均线
        df['ma14'] = df['close'].rolling(window=14).mean()
        df['ma50'] = df['close'].rolling(window=50).mean()
        
        # 简单RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 简单MACD
        ema12 = df['close'].ewm(span=12).mean()
        ema26 = df['close'].ewm(span=26).mean()
        df['macd'] = ema12 - ema26
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        
        # 布林带
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        
        # 填充NaN值
        df = df.fillna(method='bfill').fillna(method='ffill')
        
        print("✅ 技术指标计算完成")
        return df
    
    def check_signals(self, row):
        """检查交易信号"""
        signals = []
        
        # 买入信号
        if row['rsi'] < 30 and row['close'] > row['ma14']:
            signals.append({
                'type': '买入',
                'reason': f'RSI超卖({row["rsi"]:.1f})且价格在MA14上方',
                'price': row['close']
            })
        
        if row['macd'] > row['macd_signal'] and row['close'] > row['bb_middle']:
            signals.append({
                'type': '买入',
                'reason': 'MACD金叉且价格在布林带中轨上方',
                'price': row['close']
            })
        
        # 卖出信号
        if row['rsi'] > 70:
            signals.append({
                'type': '卖出',
                'reason': f'RSI超买({row["rsi"]:.1f})',
                'price': row['close']
            })
        
        if row['close'] < row['bb_lower']:
            signals.append({
                'type': '卖出',
                'reason': '价格跌破布林带下轨',
                'price': row['close']
            })
        
        return signals
    
    def generate_daily_report(self, df):
        """生成每日报告"""
        latest = df.iloc[-1]
        current_date = latest['date'].strftime('%Y-%m-%d')
        current_price = latest['close']
        
        # 检查信号
        signals = self.check_signals(latest)
        
        # 计算最近5天数据
        recent_5days = df.tail(5)
        
        html = f"""
        <h2>📊 BTC监控日报 - {current_date}</h2>
        <p style="font-size: 20px;"><strong>当前价格：</strong><span style="color: #2196F3; font-size: 24px;">${current_price:,.0f}</span></p>
        
        <h3>📈 技术指标现状</h3>
        <table>
          <tr>
            <th>指标</th>
            <th>当前值</th>
            <th>说明</th>
          </tr>
          <tr>
            <td><strong>RSI</strong></td>
            <td>{latest['rsi']:.1f}</td>
            <td>{'超卖' if latest['rsi'] < 30 else '超买' if latest['rsi'] > 70 else '中性'}</td>
          </tr>
          <tr>
            <td><strong>价格 vs MA14</strong></td>
            <td style="color: {'green' if latest['close'] > latest['ma14'] else 'red'}; font-weight: bold;">{'在上方' if latest['close'] > latest['ma14'] else '在下方'}</td>
            <td>${latest['close']:,.0f} / ${latest['ma14']:,.0f}</td>
          </tr>
          <tr>
            <td><strong>MACD</strong></td>
            <td>{latest['macd']:.2f}</td>
            <td>{'金叉' if latest['macd'] > latest['macd_signal'] else '死叉'}</td>
          </tr>
          <tr>
            <td><strong>布林带位置</strong></td>
            <td>{'上方' if latest['close'] > latest['bb_upper'] else '下方' if latest['close'] < latest['bb_lower'] else '中间'}</td>
            <td>${latest['close']:,.0f} (上轨:${latest['bb_upper']:,.0f}, 下轨:${latest['bb_lower']:,.0f})</td>
          </tr>
        </table>
        
        <h3>📊 最近5天走势</h3>
        <table>
          <tr>
            <th>日期</th>
            <th>价格</th>
            <th>RSI</th>
            <th>vs MA14</th>
          </tr>
        """
        
        for _, r in recent_5days.iterrows():
            ma_status = "上方" if r["close"] > r["ma14"] else "下方"
            ma_color = "green" if r["close"] > r["ma14"] else "red"
            html += f"""
          <tr>
            <td>{r['date'].strftime('%m-%d')}</td>
            <td>${r['close']:,.0f}</td>
            <td>{r['rsi']:.1f}</td>
            <td style="color: {ma_color};">{ma_status}</td>
          </tr>
        """
        
        html += """
        </table>
        """
        
        # 交易信号
        if signals:
            html += '<div class="alert"><h3>🚨 检测到交易信号！</h3>'
            for signal in signals:
                html += f"""
        <div style="background-color: white; padding: 15px; margin: 10px 0; border: 2px solid #ff9800;">
          <h4>{signal['type']}信号</h4>
          <p><strong>当前价格：</strong><span style="color: #2196F3; font-size: 18px;">${signal['price']:,.0f}</span></p>
          <p><strong>原因：</strong>{signal['reason']}</p>
        </div>
        """
            html += '</div>'
        else:
            html += '<div class="success"><p>✅ 暂无交易信号，继续观望</p></div>'
        
        html += """
        <hr>
        <h3>📋 策略说明</h3>
        <p><strong>买入条件：</strong></p>
        <ul>
          <li>RSI < 30 且价格在MA14上方</li>
          <li>MACD金叉且价格在布林带中轨上方</li>
        </ul>
        <p><strong>卖出条件：</strong></p>
        <ul>
          <li>RSI > 70 (超买)</li>
          <li>价格跌破布林带下轨</li>
        </ul>
        <p style="color: #666; font-size: 12px;">本邮件由简化版BTC技术指标监控系统自动发送</p>
        """
        
        return html
    
    def monitor_and_alert(self):
        """监控指标并发送邮件提醒"""
        print("🚀 启动简化版BTC技术指标监控系统...")
        print("="*80)
        
        # 获取数据
        df = self.get_btc_data()
        if df is None or len(df) == 0:
            print("❌ 获取数据失败")
            return
        
        # 计算指标
        df = self.calculate_simple_indicators(df)
        
        # 生成报告
        daily_report = self.generate_daily_report(df)
        
        # 发送邮件
        current_date = datetime.now().strftime('%Y-%m-%d')
        self.send_email(
            subject=f"BTC监控日报 {current_date}",
            body=daily_report,
            is_alert=False
        )
        
        print("\n✅ 监控完成")

if __name__ == "__main__":
    # 配置邮箱
    email_config = {
        'smtp_server': 'smtp.qq.com',
        'smtp_port': 465,
        'sender_email': os.getenv('SENDER_EMAIL', '350980368@qq.com'),
        'sender_password': os.getenv('EMAIL_PASSWORD', 'vortuxxxhkgubidh'),
        'receiver_email': os.getenv('RECEIVER_EMAIL', '350980368@qq.com')
    }
    
    # 创建监控系统
    monitor = SimpleBTCIndicatorMonitor(email_config)
    
    # 运行监控
    monitor.monitor_and_alert()
    
    print("\n" + "="*80)
    print("📧 简化版BTC监控系统运行完成")
    print("✅ 不依赖TA-Lib，使用基础技术指标")
    print("✅ 包含RSI、MACD、布林带、移动平均线等指标")
