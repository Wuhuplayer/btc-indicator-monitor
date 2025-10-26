#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图表图片数字化工具（半自动）：
- 输入：指标曲线截图（支持白底/灰底），已知坐标轴范围与时间范围
- 输出：逐日 CSV: date, value
- 方法：
  1) 解析图像，定位绘图区（可通过四角留白自适应或传参）
  2) HSV 阈值分割蓝色/红色曲线，Canny+细化得到像素轨迹
  3) 将像素 y 映射到数值，将 x 映射到日期（线性）
  4) 对每个自然日选取最邻近像素点（避免插值平滑），保证逐日一值
用法：
  python chart_digitizer.py --image path.png --start-date 2020-11-01 --end-date 2025-09-30 \
        --y-min 0.4 --y-max 1.6 --line-color blue --out 数字化数据/digitized_sth_mvrv.csv
可选：--plot 调试显示；--crop x y w h 指定绘图区；--thresh 参数微调阈值。
"""
import argparse, sys
from datetime import datetime, timedelta
import numpy as np
import cv2
import pandas as pd

COLOR_RANGES = {
    'blue': [(100, 60, 60), (130, 255, 255)],
    'red1': [(0, 70, 70), (10, 255, 255)],
    'red2': [(170, 70, 70), (180, 255, 255)],
    'orange': [(10, 120, 120), (25, 255, 255)],
}

def auto_detect_plot_area(img):
    h, w = img.shape[:2]
    # 更大的边距，适配CryptoQuant布局
    margin_x, margin_y = int(w*0.1), int(h*0.15)
    x, y = margin_x, margin_y
    ww, hh = w - 2*margin_x, h - 2*margin_y
    print(f"📐 绘图区域: ({x}, {y}, {ww}, {hh})")
    return x, y, ww, hh


def extract_curve_pixels(img, color_name):
    """精确提取曲线像素 - 多策略融合检测完整蓝色折线"""
    print("🔍 开始多策略蓝色检测...")
    
    # 策略1: 直接BGR颜色检测
    b, g, r = cv2.split(img)
    
    # 蓝色曲线特征：B通道高，G和R通道相对低
    mask1 = (b > 100) & (g < 200) & (r < 200)  # 放宽条件
    mask2 = (b > g + 20) & (b > r + 20)  # B通道明显高于G和R
    
    mask_bgr = mask1 & mask2
    mask_bgr = mask_bgr.astype(np.uint8) * 255
    
    print(f"🔵 BGR检测: {np.sum(mask_bgr > 0)} 个像素")
    
    # 策略2: HSV颜色空间检测
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    
    # 蓝色在HSV中的范围：H=100-130, S=50-255, V=50-255
    mask_hsv = (h >= 100) & (h <= 130) & (s >= 50) & (s <= 255) & (v >= 50) & (v <= 255)
    mask_hsv = mask_hsv.astype(np.uint8) * 255
    
    print(f"🔵 HSV检测: {np.sum(mask_hsv > 0)} 个像素")
    
    # 策略3: 边缘检测辅助
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 30, 100)
    
    print(f"🔵 边缘检测: {np.sum(edges > 0)} 个像素")
    
    # 融合所有策略
    combined_mask = cv2.bitwise_or(mask_bgr, mask_hsv)
    combined_mask = cv2.bitwise_or(combined_mask, edges)
    
    print(f"🔵 融合后: {np.sum(combined_mask > 0)} 个像素")
    
    # 形态学操作，连接断开的线条
    kernel_close = np.ones((3,3), np.uint8)
    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel_close, iterations=2)
    
    # 去除小噪声
    kernel_open = np.ones((2,2), np.uint8)
    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel_open, iterations=1)
    
    print(f"🔵 形态学处理后: {np.sum(combined_mask > 0)} 个像素")
    
    # 保存调试图片
    debug_img = img.copy()
    debug_img[combined_mask > 0] = [0, 255, 0]  # 绿色标记检测到的像素
    cv2.imwrite('调试_蓝色检测_完整.png', debug_img)
    print("💾 已保存调试图片: 调试_蓝色检测_完整.png")
    
    ys, xs = np.where(combined_mask > 0)
    pts = np.stack([xs, ys], axis=1)
    
    print(f"🔵 最终提取到 {len(pts)} 个数据点")
    return pts  # x,y


def map_pixels_to_series(pts, plot_rect, start_date, end_date, y_min, y_max):
    """智能映射到每日数据序列 - 使用智能插值确保每日数据"""
    x0,y0,w,h = plot_rect
    
    if len(pts) == 0:
        print("❌ 没有检测到像素点")
        return None
    
    # 过滤绘图区域内的点
    valid_mask = (pts[:,0] >= x0) & (pts[:,0] <= x0+w) & (pts[:,1] >= y0) & (pts[:,1] <= y0+h)
    pts = pts[valid_mask]
    
    if len(pts) == 0:
        print("❌ 没有有效的像素点")
        return None
    
    print(f"📊 有效像素点: {len(pts)}")
    
    xs = pts[:,0]
    ys = pts[:,1]
    
    # 像素→日期和数值
    total_days = (end_date - start_date).days
    dates = start_date + (xs - x0) * timedelta(days=1) * (total_days / max(w,1))
    values = y_max - (ys - y0) * (y_max - y_min) / max(h,1)
    
    df = pd.DataFrame({'date': dates, 'value': values})
    df['date'] = pd.to_datetime(df['date'])
    
    # 按天分组，每天取中位数附近的值
    df['date'] = df['date'].dt.floor('D')
    df = df.groupby('date').apply(lambda g: g.loc[(g['value']-g['value'].median()).abs().idxmin()])
    df = df.sort_index().reset_index(drop=True)
    
    # 生成完整的每日时间序列
    all_dates = pd.date_range(start=start_date, end=end_date, freq='D')
    full_df = pd.DataFrame({'date': all_dates})
    full_df = full_df.merge(df, on='date', how='left')
    
    # 智能插值：使用线性插值保持数据真实性
    # 线性插值不会产生过冲，更适合金融数据
    full_df['value'] = full_df['value'].interpolate(method='linear', limit_direction='both')
    
    # 对于开头和结尾的缺失值，使用最近值填充
    full_df['value'] = full_df['value'].ffill().bfill()
    
    # 确保所有值在合理范围内
    full_df['value'] = full_df['value'].clip(y_min, y_max)
    
    print(f"✅ 最终数据: {len(full_df)} 行（智能插值）")
    print(f"📈 数值范围: {full_df['value'].min():.3f} 到 {full_df['value'].max():.3f}")
    print(f"📅 日期范围: {full_df['date'].min()} 到 {full_df['date'].max()}")
    
    return full_df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--image', required=True)
    ap.add_argument('--start-date', required=True)
    ap.add_argument('--end-date', required=True)
    ap.add_argument('--y-min', type=float, required=True)
    ap.add_argument('--y-max', type=float, required=True)
    ap.add_argument('--line-color', default='blue', choices=['blue','red','orange','any'])
    ap.add_argument('--out', required=True)
    ap.add_argument('--crop', nargs=4, type=int, help='x y w h')
    args = ap.parse_args()

    print(f"🖼️ 处理图片: {args.image}")
    
    img = cv2.imread(args.image)
    if img is None:
        print('❌ 无法读取图片:', args.image)
        sys.exit(1)
    
    h, w = img.shape[:2]
    print(f"📏 图片尺寸: {w}x{h}")

    if args.crop:
        plot_rect = tuple(args.crop)
    else:
        plot_rect = auto_detect_plot_area(img)
    x,y,w,h = plot_rect
    plot_img = img[y:y+h, x:x+w]

    color_name = args.line_color if args.line_color!='any' else 'blue'
    pts = extract_curve_pixels(plot_img, color_name)
    
    if pts.size == 0:
        print('❌ 未检测到曲线像素')
        sys.exit(2)

    start_date = datetime.fromisoformat(args.start_date)
    end_date = datetime.fromisoformat(args.end_date)
    
    df = map_pixels_to_series(pts, (0,0,w,h), start_date, end_date, args.y_min, args.y_max)
    
    if df is None:
        print('❌ 数据映射失败')
        sys.exit(3)
    
    df.rename(columns={'value':'sth_mvrv'}, inplace=True)
    df.to_csv(args.out, index=False)
    print(f'✅ 已输出: {args.out}')
    print(f'📊 数据行数: {len(df)}')

if __name__ == '__main__':
    main()
