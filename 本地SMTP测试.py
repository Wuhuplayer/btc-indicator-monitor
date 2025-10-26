#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地直接测试QQ SMTP"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 使用你最新的授权码
sender = '350980368@qq.com'
password = 'ctohzxudhlxvbife'
receiver = '350980368@qq.com'

print(f"📧 测试发送: {sender} -> {receiver}")
print(f"🔐 授权码: {password[:4]}****{password[-4:]}")

msg = MIMEMultipart()
msg['From'] = sender
msg['To'] = receiver
msg['Subject'] = "本地SMTP测试"

body = "<html><body><h1>本地测试成功</h1><p>BTC价格: $112,460</p></body></html>"
msg.attach(MIMEText(body, 'html', 'utf-8'))

try:
    print("📤 尝试SSL 465...")
    with smtplib.SMTP_SSL('smtp.qq.com', 465, timeout=30) as server:
        server.set_debuglevel(1)  # 打开详细日志
        server.login(sender, password)
        server.sendmail(sender, [receiver], msg.as_string())
    print("✅ 本地测试成功！")
except Exception as e:
    print(f"❌ 本地测试失败: {e}")
    import traceback
    traceback.print_exc()

