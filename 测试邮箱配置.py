#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试QQ邮箱配置
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

def test_email_config():
    """测试邮箱配置"""
    
    # 从环境变量获取配置
    sender_email = os.getenv('SENDER_EMAIL', '350980368@qq.com')
    sender_password = os.getenv('EMAIL_PASSWORD', 'vortuxxxhkgubidh')
    receiver_email = os.getenv('RECEIVER_EMAIL', '350980368@qq.com')
    
    print(f"📧 测试邮箱配置:")
    print(f"   发送邮箱: {sender_email}")
    print(f"   接收邮箱: {receiver_email}")
    print(f"   授权码: {sender_password[:4]}****{sender_password[-4:]}")
    print()
    
    try:
        # 创建邮件
        msg = MIMEMultipart('alternative')
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = "🧪 邮箱配置测试"
        
        # 邮件内容
        html_body = """
        <html>
        <head>
        <style>
            body { font-family: Arial, sans-serif; }
            .success { background-color: #e8f5e9; padding: 15px; border-left: 5px solid #4CAF50; }
        </style>
        </head>
        <body>
            <div class="success">
                <h2>✅ 邮箱配置测试成功！</h2>
                <p>如果你收到这封邮件，说明邮箱配置正确。</p>
                <p>时间: 2025-10-26</p>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_body, 'html'))
        
        # 发送邮件（QQ邮箱使用SSL）
        print("📤 正在发送测试邮件...")
        with smtplib.SMTP_SSL('smtp.qq.com', 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
        
        print("✅ 测试邮件发送成功！")
        print("📧 请检查你的邮箱，应该会收到一封测试邮件。")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ 邮箱认证失败: {e}")
        print("💡 可能的原因:")
        print("   1. 授权码错误")
        print("   2. 没有开启IMAP/SMTP服务")
        print("   3. 授权码已过期")
        return False
        
    except Exception as e:
        print(f"❌ 发送失败: {e}")
        return False

if __name__ == "__main__":
    test_email_config()
