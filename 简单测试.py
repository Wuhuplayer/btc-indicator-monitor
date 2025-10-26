#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单测试，逐步排查问题
"""

import os
import sys
import traceback

def test_step_by_step():
    print("🔍 逐步测试...")
    
    try:
        # 步骤1：测试导入
        print("步骤1: 测试导入...")
        import pandas as pd
        import numpy as np
        import requests
        print("✅ 基础库导入成功")
        
        # 步骤2：测试TA-Lib
        print("步骤2: 测试TA-Lib...")
        try:
            import talib
            print("✅ TA-Lib导入成功")
        except Exception as e:
            print(f"❌ TA-Lib导入失败: {e}")
            return False
        
        # 步骤3：测试数据获取
        print("步骤3: 测试数据获取...")
        try:
            import requests
            url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                price = float(data['price'])
                print(f"✅ 获取BTC价格成功: ${price:,.0f}")
            else:
                print(f"❌ 获取价格失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 数据获取失败: {e}")
            return False
        
        # 步骤4：测试邮件发送
        print("步骤4: 测试邮件发送...")
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            email_config = {
                'smtp_server': 'smtp.qq.com',
                'smtp_port': 587,
                'sender_email': os.getenv('SENDER_EMAIL', '350980368@qq.com'),
                'sender_password': os.getenv('EMAIL_PASSWORD', 'vortuxxxhkgubidh'),
                'receiver_email': os.getenv('RECEIVER_EMAIL', '350980368@qq.com')
            }
            
            # 创建简单邮件
            msg = MIMEMultipart('alternative')
            msg['From'] = email_config['sender_email']
            msg['To'] = email_config['receiver_email']
            msg['Subject'] = "🧪 简单测试邮件"
            
            html_body = f"""
            <html>
            <body>
                <h2>✅ 简单测试成功！</h2>
                <p>当前BTC价格: ${price:,.0f}</p>
                <p>时间: 2025-10-26</p>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(html_body, 'html'))
            
            # 发送邮件
            with smtplib.SMTP_SSL('smtp.qq.com', 465) as server:
                server.login(email_config['sender_email'], email_config['sender_password'])
                server.send_message(msg)
            
            print("✅ 邮件发送成功")
            return True
            
        except Exception as e:
            print(f"❌ 邮件发送失败: {e}")
            return False
            
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_step_by_step()
    if success:
        print("\n🎉 所有测试通过！")
    else:
        print("\n💥 测试失败！")
        sys.exit(1)
