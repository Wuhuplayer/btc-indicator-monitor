#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接测试主程序，查看详细输出
"""

import os
import sys

def main():
    print("🚀 直接测试主程序...")
    
    # 配置邮箱
    email_config = {
        'smtp_server': 'smtp.qq.com',
        'smtp_port': 587,
        'sender_email': os.getenv('SENDER_EMAIL', '350980368@qq.com'),
        'sender_password': os.getenv('EMAIL_PASSWORD', 'vortuxxxhkgubidh'),
        'receiver_email': os.getenv('RECEIVER_EMAIL', '350980368@qq.com')
    }
    
    print(f"📧 邮箱配置: {email_config['sender_email']}")
    
    try:
        # 导入并运行主程序
        from 完整版BTC监控 import BTCIndicatorMonitor
        
        monitor = BTCIndicatorMonitor(email_config)
        print("✅ 监控系统创建成功")
        
        # 运行监控
        print("🚀 开始运行监控...")
        monitor.monitor_and_alert()
        print("✅ 监控运行完成")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
