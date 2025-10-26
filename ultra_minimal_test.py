#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""超级简化的SMTP测试，仅发一封最基础HTML邮件"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

sender = os.getenv('SENDER_EMAIL', '')
password = os.getenv('EMAIL_PASSWORD', '')
receiver = os.getenv('RECEIVER_EMAIL', '')

if not sender or not password or not receiver:
    print("❌ Secrets未注入")
    exit(1)

print(f"✅ Secrets检查: SENDER={len(sender)}, PASS={len(password)}, RECV={len(receiver)}")

msg = MIMEMultipart()
msg['From'] = sender
msg['To'] = receiver
msg['Subject'] = "Ultra Minimal Test"

body = "<html><body><h1>Test OK</h1><p>Price: $112,460</p></body></html>"
msg.attach(MIMEText(body, 'html', 'utf-8'))

try:
    with smtplib.SMTP_SSL('smtp.qq.com', 465, timeout=30) as server:
        server.login(sender, password)
        server.sendmail(sender, [receiver], msg.as_string())
    print("✅ 邮件发送成功")
except Exception as e:
    print(f"❌ 失败: {e}")
    exit(1)

