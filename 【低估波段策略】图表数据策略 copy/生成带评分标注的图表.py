#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成带评分标注的可视化图表
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent / '模块'))

from 可视化模块 import VisualizationModule

def main():
    print("=" * 100)
    print("🎨 生成带评分标注的BTC策略图表")
    print("=" * 100)
    print()
    
    # 创建可视化模块
    viz = VisualizationModule()
    
    # 生成图表数据
    print("📊 生成图表数据（包含评分标注）...")
    print("-" * 100)
    
    success = viz.generate_chart_data('数字化数据')
    
    if success:
        print()
        print("✅ 图表数据生成成功！")
        print()
        print("📂 生成的文件:")
        print("  • BTC策略可视化数据.js - 包含评分数据")
        print()
        print("📊 图表特色:")
        print("  ✅ 新增评分时间线图表")
        print("  ✅ 3分以上区域用黄色/绿色标注")
        print("  ✅ 5分以上区域用深绿色标注（抄底区）")
        print("  ✅ 鼠标悬浮显示详细评分信息")
        print()
        print("🌐 打开HTML文件查看:")
        print("  BTC策略可视化图表.html")
        print()
        print("=" * 100)
        print("✅ 完成！")
        print("=" * 100)
    else:
        print()
        print("❌ 图表生成失败")
        print()

if __name__ == "__main__":
    main()

