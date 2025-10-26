#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整版BTC技术指标监控系统 - 修复QUIT异常
直接调用完整版BTC监控.py
"""

import os
import sys

# 导入完整版监控系统
sys.path.insert(0, os.path.dirname(__file__))
from 完整版BTC监控 import BTCIndicatorMonitor

if __name__ == "__main__":
    # 配置邮箱 - 从环境变量获取
    email_config = {
        'smtp_server': 'smtp.qq.com',
        'smtp_port': 587,
        'sender_email': os.getenv('SENDER_EMAIL', '350980368@qq.com'),
        'sender_password': os.getenv('EMAIL_PASSWORD', 'ctohzxudhlxvbife'),
        'receiver_email': os.getenv('RECEIVER_EMAIL', '350980368@qq.com')
    }
    
    print(f"📧 邮箱配置: {email_config['sender_email']}")
    
    # 创建监控系统
    monitor = BTCIndicatorMonitor(email_config)
    
    # 运行监控并发送报告
    monitor.monitor_and_alert()
    
    print("\n✅ 完整版BTC监控系统运行完成")
