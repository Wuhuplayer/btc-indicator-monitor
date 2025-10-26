#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试主程序，找出具体问题
"""

import os
import sys
import traceback

def debug_main():
    print("🔍 开始调试主程序...")
    
    try:
        # 配置邮箱
        email_config = {
            'smtp_server': 'smtp.qq.com',
            'smtp_port': 587,
            'sender_email': os.getenv('SENDER_EMAIL', '350980368@qq.com'),
            'sender_password': os.getenv('EMAIL_PASSWORD', 'vortuxxxhkgubidh'),
            'receiver_email': os.getenv('RECEIVER_EMAIL', '350980368@qq.com')
        }
        
        print(f"📧 邮箱配置: {email_config['sender_email']}")
        
        # 导入主程序
        print("📦 导入主程序...")
        from 完整版BTC监控 import BTCIndicatorMonitor
        print("✅ 导入成功")
        
        # 创建监控系统
        print("🏗️ 创建监控系统...")
        monitor = BTCIndicatorMonitor(email_config)
        print("✅ 监控系统创建成功")
        
        # 测试数据获取
        print("📥 测试数据获取...")
        df = monitor.get_btc_data()
        if df is None or len(df) == 0:
            print("❌ 数据获取失败")
            return False
        print(f"✅ 数据获取成功，共 {len(df)} 条记录")
        
        # 测试指标计算
        print("📊 测试指标计算...")
        df = monitor.calculate_indicators(df)
        print("✅ 指标计算成功")
        
        # 获取最新数据
        latest = df.iloc[-1]
        current_date = latest['date'].strftime('%Y-%m-%d')
        current_price = latest['close']
        
        print(f"📅 最新日期: {current_date}")
        print(f"💰 最新价格: ${current_price:,.0f}")
        
        # 测试信号检查
        print("🎯 测试信号检查...")
        entry_signals = monitor.check_entry_signals_detailed(latest)
        exit_signal = monitor.check_exit_signals_detailed(latest)
        print(f"✅ 信号检查完成，入场信号: {len(entry_signals)}, 出场信号: {exit_signal.get('has_signal', False)}")
        
        # 测试报告生成
        print("📝 测试报告生成...")
        daily_report = monitor.generate_daily_report(latest, entry_signals, exit_signal)
        print("✅ 报告生成成功")
        
        # 测试邮件发送
        print("📧 测试邮件发送...")
        success = monitor.send_email(
            subject=f"BTC监控日报 {current_date}",
            body=daily_report,
            is_alert=False
        )
        
        if success:
            print("✅ 邮件发送成功")
            return True
        else:
            print("❌ 邮件发送失败")
            return False
            
    except Exception as e:
        print(f"❌ 调试过程中出错: {e}")
        print("📋 详细错误信息:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = debug_main()
    if success:
        print("\n🎉 调试完成，所有功能正常！")
    else:
        print("\n💥 调试发现问题！")
        sys.exit(1)
