#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键推送代码到GitHub
"""

import subprocess
import os

def push_to_github():
    """推送代码到GitHub"""
    print("🚀 开始推送代码到GitHub...")
    
    # 进入项目目录
    os.chdir("/Users/a11/Desktop/BTC策略（10-6）")
    
    try:
        # 检查状态
        print("📋 检查Git状态...")
        result = subprocess.run(["git", "status"], capture_output=True, text=True)
        print(result.stdout)
        
        # 添加文件
        print("📁 添加所有文件...")
        subprocess.run(["git", "add", "."], check=True)
        
        # 提交
        print("💾 提交更改...")
        subprocess.run(["git", "commit", "-m", "自动推送：BTC邮箱监控系统"], check=True)
        
        # 推送
        print("📤 推送到GitHub...")
        subprocess.run(["git", "push", "origin", "main"], check=True)
        
        print("✅ 推送成功！")
        print("🌐 请访问: https://github.com/Wuhuplayer/btc-indicator-monitor")
        print("📧 设置Secrets: https://github.com/Wuhuplayer/btc-indicator-monitor/settings/secrets/actions")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 推送失败: {e}")
        print("💡 请手动使用GitHub Desktop推送")
    except Exception as e:
        print(f"❌ 错误: {e}")

if __name__ == "__main__":
    push_to_github()
