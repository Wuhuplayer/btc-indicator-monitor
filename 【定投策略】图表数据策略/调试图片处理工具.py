#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试版图片数字化工具 - 显示提取过程
"""
import argparse
import sys
from datetime import datetime, timedelta
import numpy as np
import cv2
import pandas as pd

def debug_extract_curve(image_path, start_date, end_date, y_min, y_max):
    """调试版曲线提取"""
    print(f"🖼️ 处理图片: {image_path}")
    
    # 读取图片
    img = cv2.imread(image_path)
    if img is None:
        print("❌ 无法读取图片")
        return None
    
    h, w = img.shape[:2]
    print(f"📏 图片尺寸: {w}x{h}")
    
    # 检测绘图区域
    margin_x, margin_y = int(w*0.1), int(h*0.15)
    plot_x, plot_y = margin_x, margin_y
    plot_w, plot_h = w - 2*margin_x, h - 2*margin_y
    print(f"📐 绘图区域: ({plot_x}, {plot_y}, {plot_w}, {plot_h})")
    
    # 裁剪绘图区域
    plot_img = img[plot_y:plot_y+plot_h, plot_x:plot_x+plot_w]
    
    # 转换为HSV
    hsv = cv2.cvtColor(plot_img, cv2.COLOR_BGR2HSV)
    
    # 更精确的蓝色范围 - 只检测深蓝色曲线
    blue_low = np.array([110, 100, 100])  # 更严格的蓝色范围
    blue_high = np.array([130, 255, 255])
    
    # 创建蓝色掩码
    mask = cv2.inRange(hsv, blue_low, blue_high)
    
    # 更严格的形态学操作
    kernel = np.ones((2,2), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
    
    # 只保留连续的曲线区域
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        # 找到最大的轮廓（应该是主曲线）
        largest_contour = max(contours, key=cv2.contourArea)
        mask = np.zeros_like(mask)
        cv2.drawContours(mask, [largest_contour], -1, 255, thickness=2)
    
    # 找到蓝色像素
    ys, xs = np.where(mask > 0)
    print(f"🔵 检测到 {len(xs)} 个蓝色像素")
    
    if len(xs) == 0:
        print("❌ 未检测到蓝色曲线，尝试其他颜色...")
        # 尝试检测其他颜色
        for color_name, (low, high) in [('red1', ([0, 70, 70], [10, 255, 255])), 
                                        ('red2', ([170, 70, 70], [180, 255, 255])),
                                        ('orange', ([10, 120, 120], [25, 255, 255]))]:
            mask1 = cv2.inRange(hsv, np.array(low), np.array(high))
            ys1, xs1 = np.where(mask1 > 0)
            print(f"🎨 {color_name}: {len(xs1)} 个像素")
            if len(xs1) > len(xs):
                xs, ys = xs1, ys1
                print(f"✅ 使用 {color_name} 颜色")
                break
    
    if len(xs) == 0:
        print("❌ 未检测到任何曲线")
        return None
    
    # 转换为数据
    pts = np.stack([xs, ys], axis=1)
    print(f"📊 提取到 {len(pts)} 个数据点")
    
    # 映射到数值
    total_days = (end_date - start_date).days
    dates = []
    values = []
    
    for x, y in pts:
        # X轴映射到日期
        progress = x / plot_w
        date = start_date + timedelta(days=int(progress * total_days))
        
        # Y轴映射到数值（注意Y轴向下）
        value = y_max - (y / plot_h) * (y_max - y_min)
        
        dates.append(date)
        values.append(value)
    
    # 创建DataFrame
    df = pd.DataFrame({'date': dates, 'value': values})
    df['date'] = pd.to_datetime(df['date'])
    
    # 按天去重
    df['date'] = df['date'].dt.floor('D')
    df = df.groupby('date').apply(lambda g: g.loc[(g['value']-g['value'].median()).abs().idxmin()])
    df = df.sort_index().reset_index(drop=True)
    
    print(f"✅ 最终数据: {len(df)} 行")
    print(f"📈 数值范围: {df['value'].min():.3f} 到 {df['value'].max():.3f}")
    print(f"📅 日期范围: {df['date'].min()} 到 {df['date'].max()}")
    
    return df

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--image', required=True)
    ap.add_argument('--start-date', required=True)
    ap.add_argument('--end-date', required=True)
    ap.add_argument('--y-min', type=float, required=True)
    ap.add_argument('--y-max', type=float, required=True)
    ap.add_argument('--out', required=True)
    
    args = ap.parse_args()
    
    start_date = datetime.fromisoformat(args.start_date)
    end_date = datetime.fromisoformat(args.end_date)
    
    df = debug_extract_curve(args.image, start_date, end_date, args.y_min, args.y_max)
    
    if df is not None:
        df.rename(columns={'value': 'sth_mvrv'}, inplace=True)
        df.to_csv(args.out, index=False)
        print(f"✅ 已保存: {args.out}")
    else:
        print("❌ 处理失败")
        sys.exit(1)

if __name__ == '__main__':
    main()
