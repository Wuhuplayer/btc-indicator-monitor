#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试主程序执行
"""

import os
import sys

def test_main_program():
    """测试主程序"""
    print("🧪 开始测试主程序...")
    
    try:
        # 导入主程序
        from 完整版BTC监控 import BTCIndicatorMonitor
        
        print("✅ 成功导入主程序")
        
        # 配置邮箱
        email_config = {
            'smtp_server': 'smtp.qq.com',
            'smtp_port': 587,
            'sender_email': os.getenv('SENDER_EMAIL', '350980368@qq.com'),
            'sender_password': os.getenv('EMAIL_PASSWORD', 'vortuxxxhkgubidh'),
            'receiver_email': os.getenv('RECEIVER_EMAIL', '350980368@qq.com')
        }
        
        print(f"📧 邮箱配置: {email_config['sender_email']}")
        
        # 创建监控系统
        monitor = BTCIndicatorMonitor(email_config)
        print("✅ 成功创建监控系统")
        
        # 运行监控
        print("🚀 开始运行监控...")
        monitor.monitor_and_alert()
        print("✅ 监控运行完成")
        
        return True
        
    except Exception as e:
        print(f"❌ 主程序执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_main_program()
    if success:
        print("\n🎉 主程序测试成功！")
    else:
        print("\n💥 主程序测试失败！")
        sys.exit(1)
