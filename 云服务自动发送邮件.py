#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
云服务自动发送BTC技术指标日报
适用于：Railway, Render, Heroku等云平台
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os
import requests
import pandas as pd
import numpy as np

def send_daily_report():
    """发送每日报告"""
    
    # 从环境变量读取配置（云服务推荐方式）
    sender_email = os.getenv('SENDER_EMAIL', '350980368@qq.com')
    receiver_email = os.getenv('RECEIVER_EMAIL', '350980368@qq.com')
    password = os.getenv('EMAIL_PASSWORD', 'orvnwyrgejhjcaaf')
    
    try:
        current_date = datetime.now().strftime('%Y年%m月%d日')
        
        html_body = f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>BTC技术指标日报</title>
</head>
<body>
    <h2>BTC技术指标日报 - {current_date}</h2>
    <p>这是一份自动发送的BTC技术指标日报</p>
    <p>发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    <p>✅ 邮件发送成功！</p>
</body>
</html>
'''
        
        # 创建邮件
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = f'BTC技术指标日报 - {current_date}'
        
        # 添加HTML内容
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))
        
        # 发送邮件 - 使用SSL连接
        server = smtplib.SMTP_SSL('smtp.qq.com', 465)
        server.login(sender_email, password)
        server.send_message(msg)
        server.quit()
        
        print(f'✅ 邮件发送成功！时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        return True
        
    except Exception as e:
        print(f'❌ 邮件发送失败: {str(e)}')
        return False

if __name__ == "__main__":
    send_daily_report()
