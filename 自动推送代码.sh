#!/bin/bash

echo "🚀 开始自动推送代码到GitHub..."

# 进入项目目录
cd "/Users/a11/Desktop/BTC策略（10-6）"

# 检查git状态
echo "📋 检查当前状态..."
git status

# 添加所有文件
echo "📁 添加所有文件..."
git add .

# 提交更改
echo "💾 提交更改..."
git commit -m "自动推送：BTC邮箱监控系统配置完成"

# 尝试推送
echo "📤 推送到GitHub..."
git push origin main

echo "✅ 推送完成！"
echo "🌐 请访问: https://github.com/Wuhuplayer/btc-indicator-monitor"
echo "📧 然后设置Secrets: https://github.com/Wuhuplayer/btc-indicator-monitor/settings/secrets/actions"
