#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试依赖包安装
"""

import sys
import os

def test_imports():
    """测试所有依赖包是否能正常导入"""
    print("🔍 开始测试依赖包导入...")
    
    try:
        import pandas as pd
        print("✅ pandas 导入成功")
    except ImportError as e:
        print(f"❌ pandas 导入失败: {e}")
        return False
    
    try:
        import numpy as np
        print("✅ numpy 导入成功")
    except ImportError as e:
        print(f"❌ numpy 导入失败: {e}")
        return False
    
    try:
        import yfinance as yf
        print("✅ yfinance 导入成功")
    except ImportError as e:
        print(f"❌ yfinance 导入失败: {e}")
        return False
    
    try:
        import requests
        print("✅ requests 导入成功")
    except ImportError as e:
        print(f"❌ requests 导入失败: {e}")
        return False
    
    try:
        import talib
        print("✅ talib 导入成功")
    except ImportError as e:
        print(f"❌ talib 导入失败: {e}")
        return False
    
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        print("✅ 邮件模块导入成功")
    except ImportError as e:
        print(f"❌ 邮件模块导入失败: {e}")
        return False
    
    return True

def test_basic_functionality():
    """测试基本功能"""
    print("\n🔍 开始测试基本功能...")
    
    try:
        import pandas as pd
        import numpy as np
        
        # 测试创建DataFrame
        df = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=10),
            'close': np.random.randn(10) * 1000 + 50000
        })
        print("✅ DataFrame创建成功")
        
        # 测试talib
        import talib
        close_prices = df['close'].values
        sma = talib.SMA(close_prices, timeperiod=5)
        print("✅ TA-Lib SMA计算成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 基本功能测试失败: {e}")
        return False

def test_email_config():
    """测试邮箱配置"""
    print("\n🔍 开始测试邮箱配置...")
    
    sender_email = os.getenv('SENDER_EMAIL', '350980368@qq.com')
    receiver_email = os.getenv('RECEIVER_EMAIL', '350980368@qq.com')
    password = os.getenv('EMAIL_PASSWORD', 'vortuxxxhkgubidh')
    
    print(f"📧 发送邮箱: {sender_email}")
    print(f"📧 接收邮箱: {receiver_email}")
    print(f"🔑 密码长度: {len(password)}")
    
    if not password or password == 'your_email_password':
        print("❌ 邮箱密码未正确配置")
        return False
    
    print("✅ 邮箱配置检查通过")
    return True

if __name__ == "__main__":
    print("🚀 开始依赖包测试...")
    print("="*50)
    
    # 测试导入
    if not test_imports():
        print("\n❌ 依赖包导入测试失败")
        sys.exit(1)
    
    # 测试基本功能
    if not test_basic_functionality():
        print("\n❌ 基本功能测试失败")
        sys.exit(1)
    
    # 测试邮箱配置
    if not test_email_config():
        print("\n❌ 邮箱配置测试失败")
        sys.exit(1)
    
    print("\n" + "="*50)
    print("🎉 所有测试通过！依赖包安装正常")
    print("✅ 可以运行完整版BTC监控脚本")
