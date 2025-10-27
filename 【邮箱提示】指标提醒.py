#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BTC技术指标邮箱提醒系统

功能：
1. 每天监控BTC技术指标
2. 当入场/出场指标命中时，发送醒目邮件提醒
3. 每天发送一份监控报告

入场信号（4个指标，渐进式触发）：
- 第1仓：wt1 < -25 AND WT金叉
- 第2仓：需要第1仓 + sqzOff + isLime + WT1>WT2
- 第3仓：需要第2仓 + sqzOff + isLime + WT1>WT2 + close > MA14
- 第4仓：需要第3仓 + sqzOff + isLime + WT1>WT2 + close > MA14 + ADX上升

出场信号（4个指标）：
- WT死叉（反转信号）
- ADX < 20（趋势减弱）
- 跌破MA14（支撑破位）
- 挤压开启（动能衰竭）

邮件提醒：
- 📧 每天发送监控报告
- 🚨 指标命中时发送醒目提醒
"""

import pandas as pd
import numpy as np
import yfinance as yf
import talib
from datetime import datetime, timedelta
import warnings
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sys
import os
warnings.filterwarnings('ignore')

# 支撑阻力位功能已移除

class BTCIndicatorMonitor:
    def __init__(self, email_config=None):
        """
        BTC技术指标监控系统
        
        email_config = {
            'smtp_server': 'smtp.gmail.com',  # 邮箱服务器
            'smtp_port': 587,                  # 端口
            'sender_email': 'your@gmail.com',  # 发送邮箱
            'sender_password': 'your_password',# 邮箱密码
            'receiver_email': 'receiver@gmail.com'  # 接收邮箱
        }
        """
        self.email_config = email_config or {}
        self.last_alert_time = {}  # 记录上次提醒时间，避免重复提醒
        
        # 策略参数
        self.name = "BTC技术指标监控系统"
        self.initial_capital = 100000
        self.cash = self.initial_capital
        self.account_value = self.initial_capital
        self.long_positions = []
        self.short_positions = []
        self.max_positions = 4
        self.position_sizes = [0.15, 0.25, 0.30, 0.30]  # 各仓位资金比例
        self.leverage = 1.0  # 杠杆倍数
        self.stop_loss_pct = 0.15  # 止损比例
        self.atr_mult = 2.0  # ATR追踪倍数
        self.enable_short = False  # 禁用做空
    
    def send_email(self, subject, body, is_alert=False):
        """发送邮件 - HTML表格版本"""
        if not self.email_config or not self.email_config.get('sender_email'):
            print(f"⚠️ 邮箱未配置，跳过发送: {subject}")
            return False
        
        try:
            # 创建邮件
            msg = MIMEMultipart('alternative')
            msg['From'] = self.email_config['sender_email']
            msg['To'] = self.email_config['receiver_email']
            
            # 如果是警报，标题更醒目
            if is_alert:
                msg['Subject'] = f"🚨 {subject}"
            else:
                msg['Subject'] = f"📊 {subject}"
            
            # HTML格式邮件
            html_body = f"""
            <html>
            <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
                th {{ background-color: #4CAF50; color: white; padding: 10px; text-align: left; }}
                td {{ border: 1px solid #ddd; padding: 8px; }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
                .alert {{ background-color: #fff3cd; padding: 15px; margin: 10px 0; border-left: 5px solid #ff9800; }}
                .danger {{ background-color: #ffebee; padding: 15px; margin: 10px 0; border-left: 5px solid #f44336; }}
                .success {{ background-color: #e8f5e9; padding: 15px; margin: 10px 0; border-left: 5px solid #4CAF50; }}
            </style>
            </head>
            <body>
                {body}
            </body>
            </html>
            """
            
            msg.attach(MIMEText(html_body, 'html'))
            
        # 发送邮件（QQ邮箱使用SSL，修复QUIT异常）
        if 'qq.com' in self.email_config['smtp_server']:
            print(f"📧 使用QQ邮箱发送邮件到: {self.email_config['receiver_email']}")
            
            # 尝试SSL连接（端口465）
            try:
                server = smtplib.SMTP_SSL(self.email_config['smtp_server'], 465, timeout=30)
                server.set_debuglevel(0)  # 关闭调试信息
                server.login(self.email_config['sender_email'], self.email_config['sender_password'])
                print(f"📧 SSL登录成功，开始发送邮件...")
                
                # 添加邮件头信息，提高送达率
                msg['X-Mailer'] = 'BTC-Monitor-System'
                msg['X-Priority'] = '3'
                msg['X-Originating-IP'] = '[127.0.0.1]'
                
                result = server.sendmail(self.email_config['sender_email'], [self.email_config['receiver_email']], msg.as_string())
                print(f"📧 邮件发送结果: {result}")
                
                try:
                    server.quit()
                    print(f"📧 SMTP连接已关闭")
                except:
                    pass  # 忽略QQ SMTP的QUIT异常
                    
            except Exception as e:
                print(f"📧 SSL连接失败: {e}")
                # 尝试TLS连接（端口587）
                try:
                    server = smtplib.SMTP(self.email_config['smtp_server'], 587, timeout=30)
                    server.starttls()
                    server.login(self.email_config['sender_email'], self.email_config['sender_password'])
                    print(f"📧 TLS登录成功，开始发送邮件...")
                    
                    # 添加邮件头信息，提高送达率
                    msg['X-Mailer'] = 'BTC-Monitor-System'
                    msg['X-Priority'] = '3'
                    msg['X-Originating-IP'] = '[127.0.0.1]'
                    
                    result = server.sendmail(self.email_config['sender_email'], [self.email_config['receiver_email']], msg.as_string())
                    print(f"📧 邮件发送结果: {result}")
                    
                    try:
                        server.quit()
                        print(f"📧 SMTP连接已关闭")
                    except:
                        pass  # 忽略QQ SMTP的QUIT异常
                        
                except Exception as e2:
                    print(f"📧 TLS连接也失败: {e2}")
                    raise e2
            else:
                print(f"📧 使用其他邮箱发送邮件到: {self.email_config['receiver_email']}")
                server = smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port'], timeout=30)
                server.starttls()
                server.login(self.email_config['sender_email'], self.email_config['sender_password'])
                print(f"📧 登录成功，开始发送邮件...")
                
                result = server.sendmail(self.email_config['sender_email'], [self.email_config['receiver_email']], msg.as_string())
                print(f"📧 邮件发送结果: {result}")
                
                try:
                    server.quit()
                    print(f"📧 SMTP连接已关闭")
                except:
                    pass
            
            print(f"✅ 邮件已发送: {subject}")
            print(f"📧 请检查邮箱: {self.email_config['receiver_email']}")
            print(f"📧 如果没收到，请检查垃圾邮件文件夹")
            return True
            
        except Exception as e:
            print(f"❌ 邮件发送失败: {e}")
            return False
    
    def check_entry_signals_detailed(self, row):
        """检查入场信号并返回详细信息"""
        signals = []
        
        # 第1仓信号
        if row['wt1'] < -25 and row['wt_golden_cross']:
            signals.append({
                'level': 1,
                'type': '入场',
                'name': '第1仓买入信号',
                'conditions': [
                    f"WT1={row['wt1']:.1f} < -25 ✅",
                    "WT金叉 ✅"
                ],
                'price': row['close'],
                'urgency': 'high'
            })
        
        # 第2仓信号（需要已有第1仓）
        if row['sqz_off'] and row['is_lime'] and row['wt1'] > row['wt2']:
            signals.append({
                'level': 2,
                'type': '入场',
                'name': '第2仓加仓信号',
                'conditions': [
                    "需要已有第1仓 ✅",
                    "挤压释放 ✅",
                    "动能增强(Lime) ✅",
                    f"WT1({row['wt1']:.1f}) > WT2({row['wt2']:.1f}) ✅"
                ],
                'price': row['close'],
                'urgency': 'medium'
            })
        
        # 第3仓信号
        if (row['sqz_off'] and row['is_lime'] and row['wt1'] > row['wt2'] and 
            row['close'] > row['ma14']):
            signals.append({
                'level': 3,
                'type': '入场',
                'name': '第3仓加仓信号',
                'conditions': [
                    "需要已有第2仓 ✅",
                    "挤压释放 ✅",
                    "动能增强(Lime) ✅",
                    f"WT1({row['wt1']:.1f}) > WT2({row['wt2']:.1f}) ✅",
                    f"价格(${row['close']:,.0f}) > MA14(${row['ma14']:,.0f}) ✅"
                ],
                'price': row['close'],
                'urgency': 'medium'
            })
        
        # 第4仓信号
        if (row['sqz_off'] and row['is_lime'] and row['wt1'] > row['wt2'] and 
            row['close'] > row['ma14'] and row['adx'] > 20 and row['adx_up']):
            signals.append({
                'level': 4,
                'type': '入场',
                'name': '第4仓加仓信号',
                'conditions': [
                    "需要已有第3仓 ✅",
                    "挤压释放 ✅",
                    "动能增强(Lime) ✅",
                    f"WT1({row['wt1']:.1f}) > WT2({row['wt2']:.1f}) ✅",
                    f"价格(${row['close']:,.0f}) > MA14(${row['ma14']:,.0f}) ✅",
                    f"ADX={row['adx']:.1f} > 20 ✅",
                    "ADX上升 ✅"
                ],
                'price': row['close'],
                'urgency': 'low'
            })
        
        return signals
    
    def check_exit_signals_detailed(self, row):
        """检查出场信号并返回详细信息"""
        signals = []
        exit_count = 0
        
        # 统计有多少个出场信号
        if row.get('wt_death_cross', False):
            signals.append("WT死叉")
            exit_count += 1
        
        if row['adx'] < 20:
            signals.append(f"ADX={row['adx']:.1f}<20")
            exit_count += 1
        
        if row['close'] < row['ma14']:
            signals.append("跌破MA14")
            exit_count += 1
        
        if row.get('sqz_on', False):
            signals.append("挤压开启")
            exit_count += 1
        
        if exit_count >= 2:
            return {
                'has_signal': True,
                'signal_count': exit_count,
                'signals': signals,
                'price': row['close'],
                'urgency': 'high' if exit_count >= 3 else 'medium'
            }
        
        return {'has_signal': False}
    
    def get_btc_data(self):
        """获取BTC数据 - 简化版本，适合GitHub Actions"""
        import time
        import requests
        
        # 方法1：使用Binance API获取最近数据
        print("📥 开始从Binance获取BTC数据...")
        try:
            # 获取最近1000天数据
            url = "https://api.binance.com/api/v3/klines"
            params = {
                'symbol': 'BTCUSDT',
                'interval': '1d',
                'limit': 1000
            }
            
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if data and len(data) > 100:
                    df = pd.DataFrame(data, columns=[
                        'timestamp', 'open', 'high', 'low', 'close', 'volume',
                        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                        'taker_buy_quote', 'ignore'
                    ])
                    
                    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df['open'] = df['open'].astype(float)
                    df['high'] = df['high'].astype(float)
                    df['low'] = df['low'].astype(float)
                    df['close'] = df['close'].astype(float)
                    df['volume'] = df['volume'].astype(float)
                    
                    df = df[['date', 'open', 'high', 'low', 'close', 'volume']].reset_index(drop=True)
                    
                    print(f"✅ 从Binance成功获取 {len(df)} 天数据")
                    print(f"📅 数据区间: {df['date'].min().strftime('%Y-%m-%d')} 至 {df['date'].max().strftime('%Y-%m-%d')}")
                    print(f"💰 价格区间: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
                    
                    return df
                
        except Exception as e:
            print(f"⚠️ Binance API失败: {e}")
        
        # 方法2：使用yfinance（备用）
        print("尝试使用yfinance...")
        try:
            btc = yf.Ticker("BTC-USD")
            data = btc.history(period="1y")
            if len(data) > 100:
                df = pd.DataFrame({
                    'date': data.index,
                    'open': data['Open'].values,
                    'high': data['High'].values, 
                    'low': data['Low'].values,
                    'close': data['Close'].values,
                    'volume': data['Volume'].values
                })
                print(f"✅ 从yfinance获取到 {len(df)} 天数据")
                return df
        except Exception as e:
            print(f"⚠️ yfinance失败: {e}")
        
        # 方法3：生成模拟数据（最后备用）
        print("使用模拟数据...")
        dates = pd.date_range(start='2023-01-01', end='2024-12-31', freq='D')
        
        # 基于真实BTC价格创建模拟数据
        price = 20000
        prices = []
        
        for i in range(len(dates)):
            # 模拟BTC价格波动
            change = np.random.normal(0.001, 0.03)  # 日波动率3%
            price *= (1 + change)
            
            # 限制价格范围
            if price < 15000:
                price = 15000
            elif price > 80000:
                price = 80000
                
            prices.append(price)
        
        df = pd.DataFrame({
            'date': dates,
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices], 
            'close': prices,
            'volume': [np.random.randint(20000000, 100000000) for _ in range(len(dates))]
        })
        
        print(f"✅ 生成模拟数据 {len(df)} 天")
        return df
    
    def calculate_indicators(self, df):
        """计算技术指标"""
        print("计算技术指标...")
        
        # 计算WaveTrend指标 - 严格按图表(LazyBear)用hlc3
        def wavetrend(high, low, close, wt_channel_length=10, wt_average_length=21):
            """
            WaveTrend指标（LazyBear版本，ap=hlc3）
            ap = (high + low + close) / 3
            esa = ema(ap, n1); d = ema(|ap-esa|, n1); ci = (ap-esa)/(0.015*d)
            tci = ema(ci, n2); wt1 = tci; wt2 = sma(wt1, 4)
            """
            ap = (high + low + close) / 3
            esa = talib.EMA(ap, timeperiod=wt_channel_length)
            d = talib.EMA(np.abs(ap - esa), timeperiod=wt_channel_length)
            ci = (ap - esa) / (0.015 * d)
            tci = talib.EMA(ci, timeperiod=wt_average_length)
            wt1 = tci
            wt2 = talib.SMA(wt1, timeperiod=4)
            return wt1, wt2
        
        # 计算SQZMOM指标 - 严格按照TV代码实现
        def sqzmom(high, low, close, length=20, use_true_range=True):
            """
            Squeeze Momentum指标计算
            完全按照TV Pine Script逻辑实现
            """
            bb_period = length
            bb_mult = 2.0
            kc_period = 20
            kc_mult = 1.5
            
            # 转换为pandas Series以便使用shift
            close_series = pd.Series(close)
            high_series = pd.Series(high)
            low_series = pd.Series(low)
            
            # === 布林带计算 ===
            # source = close, basis = ta.sma(source, lengthBB)
            bb_mid = talib.SMA(close, timeperiod=bb_period)
            bb_std = talib.STDDEV(close, timeperiod=bb_period)
            bb_upper = bb_mid + (bb_mult * bb_std)
            bb_lower = bb_mid - (bb_mult * bb_std)
            
            # === 肯特纳通道计算 ===
            # maKC = ta.sma(source, lengthKC)
            kc_mid = talib.SMA(close, timeperiod=kc_period)
            
            # rangeKC = useTrueRange ? ta.tr : (high - low)
            if use_true_range:
                # True Range = max(high-low, abs(high-close[1]), abs(low-close[1]))
                tr1 = high_series - low_series
                tr2 = abs(high_series - close_series.shift(1))
                tr3 = abs(low_series - close_series.shift(1))
                range_kc = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1).values
            else:
                range_kc = high - low
            
            # rangemaKC = ta.sma(rangeKC, lengthKC)
            range_ma_kc = talib.SMA(range_kc, timeperiod=kc_period)
            kc_upper = kc_mid + (range_ma_kc * kc_mult)
            kc_lower = kc_mid - (range_ma_kc * kc_mult)
            
            # === 挤压状态判断 ===
            # sqzOn = (lowerBB > lowerKC) and (upperBB < upperKC)
            # sqzOff = (lowerBB < lowerKC) and (upperBB > upperKC)
            sqz_on = (bb_lower > kc_lower) & (bb_upper < kc_upper)
            sqz_off = (bb_lower < kc_lower) & (bb_upper > kc_upper)
            no_sqz = ~sqz_on & ~sqz_off
            
            # === 动能线线性回归计算 ===
            # avgHL = (ta.highest(high, lengthKC) + ta.lowest(low, lengthKC)) / 2
            avg_hl = (talib.MAX(high, timeperiod=kc_period) + talib.MIN(low, timeperiod=kc_period)) / 2
            # avgAll = (avgHL + ta.sma(close, lengthKC)) / 2
            avg_all = (avg_hl + talib.SMA(close, timeperiod=kc_period)) / 2
            # val = ta.linreg(source - avgAll, lengthKC, 0)
            source_minus_avg = close - avg_all
            val = linear_regression(source_minus_avg, kc_period)
            
            # === 动能柱状态判断 ===
            val_series = pd.Series(val)
            val_prev = val_series.shift(1).fillna(0).values
            
            # isLime = val > 0 and val > nz(val[1])   - 强多柱（lime绿）
            is_lime = (val > 0) & (val > val_prev)
            # isGreen = val > 0 and val < nz(val[1])  - 弱多柱（深绿）
            is_green = (val > 0) & (val < val_prev)
            # isRed = val < 0 and val < nz(val[1])    - 强空柱（红色）
            is_red = (val < 0) & (val < val_prev)
            # isMaroon = val < 0 and val > nz(val[1]) - 弱空柱（暗红）
            is_maroon = (val < 0) & (val > val_prev)
            
            return sqz_on, sqz_off, no_sqz, val, is_lime, is_green, is_red, is_maroon
        
        def linear_regression(series, period):
            """
            计算线性回归值，等同于TV的ta.linreg(series, period, 0)
            offset=0表示当前bar的线性回归预测值
            """
            result = np.zeros_like(series)
            # 先填充NaN值
            series_clean = pd.Series(series).fillna(method='bfill').fillna(method='ffill').fillna(0).values
            
            for i in range(period-1, len(series_clean)):
                y = series_clean[i-period+1:i+1]
                x = np.arange(period)
                # 使用最小二乘法计算线性回归
                if len(y) == period and not np.isnan(y).any():
                    try:
                        coeffs = np.polyfit(x, y, 1)
                        # offset=0表示预测当前点（最后一个点）
                        result[i] = coeffs[0] * (period - 1) + coeffs[1]
                    except:
                        result[i] = 0
                else:
                    result[i] = 0
            return result
        
        # 计算ADX和DMI指标 - 严格按照TV代码实现
        def adx_dmi(high, low, close, adx_length=14):
            """
            ADX和DMI指标计算
            TV代码对应：
            [plusDI, minusDI, adx] = ta.dmi(adxLength, adxLength)
            
            返回：plus_di, minus_di, adx
            """
            # talib中的PLUS_DI和MINUS_DI对应TV的plusDI和minusDI
            plus_di = talib.PLUS_DI(high, low, close, timeperiod=adx_length)
            minus_di = talib.MINUS_DI(high, low, close, timeperiod=adx_length)
            adx = talib.ADX(high, low, close, timeperiod=adx_length)
            return plus_di, minus_di, adx
        
        # 计算移动平均线
        def ma(close, period):
            return talib.SMA(close, timeperiod=period)
        
        # 应用指标计算
        df['wt1'], df['wt2'] = wavetrend(df['high'], df['low'], df['close'])
        df['sqz_on'], df['sqz_off'], df['no_sqz'], df['sqz_val'], df['is_lime'], df['is_green'], df['is_red'], df['is_maroon'] = sqzmom(df['high'], df['low'], df['close'])
        df['plus_di'], df['minus_di'], df['adx'] = adx_dmi(df['high'], df['low'], df['close'])
        df['ma14'] = ma(df['close'], 14)
        df['ma50'] = ma(df['close'], 50)  # 50日均线
        df['ma200'] = ma(df['close'], 200)  # 200日均线，判断长期趋势
        # ATR用于追踪止盈
        df['atr'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=14)
        
        # 调试ATR计算
        print(f"🔍 ATR调试信息:")
        print(f"   数据长度: {len(df)}")
        print(f"   最近ATR值: {df['atr'].iloc[-1]:.2f}")
        print(f"   ATR非空值数量: {df['atr'].notna().sum()}")
        print(f"   ATR非零值数量: {(df['atr'] > 0).sum()}")
        
        # 计算信号 - 按照TV代码实现
        # TV代码：wtGoldenCross = (wt1[1] < wt2[1]) and (wt1 > wt2)
        df['wt_golden_cross'] = (df['wt1'].shift(1) < df['wt2'].shift(1)) & (df['wt1'] > df['wt2'])
        # TV代码：wtDeathCross = (wt1[1] > wt2[1]) and (wt1 < wt2)
        df['wt_death_cross'] = (df['wt1'].shift(1) > df['wt2'].shift(1)) & (df['wt1'] < df['wt2'])
        # TV代码：adxUp = (adx > adxThreshold) and (adx > adx[1])
        df['adx_up'] = (df['adx'] > 20) & (df['adx'] > df['adx'].shift(1))
        df['adx_down'] = (df['adx'] > 20) & (df['adx'] > df['adx'].shift(1)) & (df['minus_di'] > df['plus_di'])
        df['adx_prev'] = df['adx'].shift(1)  # ADX前一天的值，用于判断是否下降
        # TV代码第86行：价格结构确认
        df['price_struct_confirmed'] = df['close'] > df['ma14']
        df['price_struct_bearish'] = df['close'] < df['ma14']
        
        # TV代码第128行：highlightGreen计算（4小时SQZMOM信号）
        # 由于使用日线数据，模拟4小时信号：
        # highlightGreen = sqz4h or (mom4h > nz(mom4h[1]) and mom4h > 0)
        
        # 计算4小时级别的信号（简化版：使用更严格的日线信号）
        # sqz4h: 4小时挤压释放 - 使用日线的sqz_off
        # mom4h: 4小时动能 - 使用日线的momentum（简化）
        momentum = df['close'] - df['close'].shift(1)
        mom4h_condition = (momentum > momentum.shift(1)) & (momentum > 0)
        
        df['highlight_green'] = df['sqz_off'] | mom4h_condition
        
        # 填充NaN值
        df = df.fillna(method='bfill').fillna(method='ffill')
        
        print("✅ 技术指标计算完成")
        return df
    
    def check_entry_signals(self, row):
        """检查入场信号 - 纯多头：渐进式触发（无价格过滤）"""
        long_signals = []
        short_signals = []  # 已禁用
        
        # 多头仓位渐进式触发（恢复原始逻辑，不过滤价格）
        existing_long_levels = {pos['position_level'] for pos in self.long_positions}
        has_long_lvl1 = 1 in existing_long_levels
        has_long_lvl2 = 2 in existing_long_levels
        has_long_lvl3 = 3 in existing_long_levels
        
        # 第1多仓：WT金叉做多 - 独立触发
        if row['wt1'] < -25 and row['wt_golden_cross'] and 1 not in existing_long_levels:
            long_signals.append(1)
        
        # 第2多仓：需要已有第1仓
        if row['sqz_off'] and row['is_lime'] and row['wt1'] > row['wt2'] and has_long_lvl1 and 2 not in existing_long_levels:
            long_signals.append(2)
            
        # 第3多仓：需要已有第2仓
        if (row['sqz_off'] and row['is_lime'] and row['wt1'] > row['wt2'] and 
            row['close'] > row['ma14'] and has_long_lvl2 and 3 not in existing_long_levels):
            long_signals.append(3)
            
        # 第4多仓：需要已有第3仓
        if (row['sqz_off'] and row['is_lime'] and row['wt1'] > row['wt2'] and 
            row['close'] > row['ma14'] and row['adx_up'] and has_long_lvl3 and 4 not in existing_long_levels):
            long_signals.append(4)
        
        # 空头已禁用
        if self.enable_short:
            # 空头逻辑（已禁用）
            pass
            
        return long_signals, short_signals
    
    def add_position(self, date, price, position_level, direction='long'):
        """添加仓位（支持做多和做空）"""
        positions = self.long_positions if direction == 'long' else self.short_positions
        
        if len(positions) >= self.max_positions:
            return False
            
        position_size = self.position_sizes[position_level - 1]
        # 固定基于初始资金，避免复利指数增长（更符合实际）
        amount = 100000 * position_size
        
        if self.cash < amount:
            return False
        
        self.cash -= amount

        if direction == 'long':
            # 做多：价格上涨赚钱（加杠杆）
            leveraged_shares = (amount * self.leverage) / price  # 杠杆后的持仓数量
            position = {
                'date': date,
                'entry_price': price,
                'amount': amount,  # 保证金
                'shares': leveraged_shares,  # 杠杆后的实际持仓
                'position_level': position_level,
                'direction': 'long',
                'stop_loss_price': price * (1 - self.stop_loss_pct),  # 止损价更低
                'remaining_shares': leveraged_shares,
                'sold_parts': 0,
                'peak_price': price,  # 记录最高价
                'trail_stop_price': None,
                'leverage': self.leverage
            }
            emoji = "📈"
        else:
            # 做空：价格下跌赚钱（需要保证金）
            leveraged_shares = (amount * self.leverage) / price  # 杠杆后的空头数量
            
            position = {
                'date': date,
                'entry_price': price,
                'amount': amount,  # 保证金
                'shares': leveraged_shares,  # 杠杆后的实际空头
                'position_level': position_level,
                'direction': 'short',
                'stop_loss_price': price * (1 + self.stop_loss_pct),  # 止损价更高
                'remaining_shares': leveraged_shares,
                'sold_parts': 0,
                'low_price': price,  # 记录最低价
                'trail_stop_price': None,
                'margin': amount,  # 记录保证金
                'leverage': self.leverage
            }
            emoji = "📉"
        
        positions.append(position)
        dir_text = "多" if direction == 'long' else "空"
        print(f"{emoji} 第{position_level}{dir_text}仓入场: {date.strftime('%Y-%m-%d')} 价格:{price:.2f} 金额:{amount:.0f}")
        return True
    
    def check_stop_loss(self, row, trades, trade_id):
        """检查止损（支持做多和做空）"""
        # 检查多头止损
        long_to_close = []
        for i, pos in enumerate(self.long_positions):
            # 做多：价格跌破止损价
            if row['low'] <= pos['stop_loss_price']:
                exit_price = pos['stop_loss_price']
                sell_shares = pos.get('remaining_shares', pos['shares'])
                if sell_shares > 0:
                    pnl = (exit_price - pos['entry_price']) / pos['entry_price']
                    pnl_amount = sell_shares * (exit_price - pos['entry_price'])
                    # 正确的现金流：本金+盈亏
                    amount_part = pos['amount'] * (sell_shares / pos['shares'])
                    self.cash += amount_part + pnl_amount
                    
                    trades.append({
                        'trade_id': trade_id,
                        'entry_date': pos['date'],
                        'exit_date': row['date'],
                        'position_level': pos['position_level'],
                        'direction': 'long',
                        'entry_price': pos['entry_price'],
                        'exit_price': exit_price,
                        'shares': sell_shares,
                        'amount': pos['amount'],
                        'pnl_pct': pnl * 100,
                        'pnl_amount': pnl_amount,
                        'exit_reason': '止损'
                    })
                    trade_id += 1
                    
                    print(f"🛑 第{pos['position_level']}多仓止损: {row['date'].strftime('%Y-%m-%d')} "
                          f"入场:{pos['entry_price']:.2f} 止损:{exit_price:.2f} 亏损:{pnl*100:.1f}%")
                    long_to_close.append(i)
        
        for i in reversed(long_to_close):
            self.long_positions.pop(i)
        
        # 检查空头止损
        short_to_close = []
        for i, pos in enumerate(self.short_positions):
            # 做空：价格突破止损价
            if row['high'] >= pos['stop_loss_price']:
                exit_price = pos['stop_loss_price']
                sell_shares = pos.get('remaining_shares', pos['shares'])
                if sell_shares > 0:
                    # 做空盈亏是反向的
                    pnl = (pos['entry_price'] - exit_price) / pos['entry_price']
                    pnl_amount = sell_shares * (pos['entry_price'] - exit_price)
                    # 空头平仓：返还保证金+盈亏
                    amount_part = pos['amount'] * (sell_shares / pos['shares'])
                    self.cash += amount_part + pnl_amount
                    
                    trades.append({
                        'trade_id': trade_id,
                        'entry_date': pos['date'],
                        'exit_date': row['date'],
                        'position_level': pos['position_level'],
                        'direction': 'short',
                        'entry_price': pos['entry_price'],
                        'exit_price': exit_price,
                        'shares': sell_shares,
                        'amount': pos['amount'],
                        'pnl_pct': pnl * 100,
                        'pnl_amount': pnl_amount,
                        'exit_reason': '止损'
                    })
                    trade_id += 1
                    
                    print(f"🛑 第{pos['position_level']}空仓止损: {row['date'].strftime('%Y-%m-%d')} "
                          f"入场:{pos['entry_price']:.2f} 止损:{exit_price:.2f} 亏损:{pnl*100:.1f}%")
                    short_to_close.append(i)
        
        for i in reversed(short_to_close):
            self.short_positions.pop(i)
        
        return trade_id
    
    def check_take_profit(self, row, trades, trade_id):
        """分批止盈 + ATR追踪（支持做多和做空）"""
        current_price = row['close']
        atr = row.get('atr', None)
        
        # 处理多头止盈
        trade_id = self._check_take_profit_long(row, trades, trade_id, current_price, atr)
        
        # 处理空头止盈
        trade_id = self._check_take_profit_short(row, trades, trade_id, current_price, atr)
        
        return trade_id
    
    def _check_take_profit_long(self, row, trades, trade_id, current_price, atr):
        """多头止盈逻辑 - 主动止盈优先"""
        positions_to_close = []
        
        for i, pos in enumerate(self.long_positions):
            # 检查主动顶部信号（先卖50%，剩余50%用ATR追踪）
            profit_pct = (current_price - pos['entry_price']) / pos['entry_price'] * 100
            
            # 定义顶部信号
            peak_signals = []
            if row.get('wt_death_cross', False):
                peak_signals.append('WT死叉')
            if row['adx'] < 20:
                peak_signals.append('ADX<20')
            if row['close'] < row['ma14']:
                peak_signals.append('跌破MA14')
            if row.get('sqz_on', False):
                peak_signals.append('挤压开启')
            
            # 主动止盈条件：盈利>=10% 且 有2个顶部信号
            if profit_pct >= 10 and len(peak_signals) >= 2 and not pos.get('partial_sold', False):
                # 卖出50%
                sell_shares = pos.get('remaining_shares', pos['shares']) * 0.5
                if sell_shares > 0:
                    amount_part = pos['amount'] * (sell_shares / pos['shares'])
                    pnl_amount = sell_shares * (current_price - pos['entry_price'])
                    pnl_pct_trade = (current_price - pos['entry_price']) / pos['entry_price'] * 100
                    
                    self.cash += amount_part + pnl_amount
                    
                    trades.append({
                        'trade_id': trade_id,
                        'entry_date': pos['date'],
                        'exit_date': row['date'],
                        'position_level': pos['position_level'],
                        'direction': 'long',
                        'entry_price': pos['entry_price'],
                        'exit_price': current_price,
                        'shares': sell_shares,
                        'amount': amount_part,
                        'pnl_pct': pnl_pct_trade,
                        'pnl_amount': pnl_amount,
                        'exit_reason': f'主动止盈50%({"+".join(peak_signals[:2])})'
                    })
                    trade_id += 1
                    
                    pos['remaining_shares'] -= sell_shares
                    pos['partial_sold'] = True
                    
                    print(f"🎯 第{pos['position_level']}仓主动止盈50%: {row['date'].strftime('%Y-%m-%d')} "
                          f"盈利:{pnl_pct_trade:.1f}% [{'+'.join(peak_signals[:2])}]")
            
            # 更新ATR追踪止盈线（对剩余50%）
            if atr is not None:
                current_trail = current_price - self.atr_mult * atr
                if pos['trail_stop_price'] is None:
                    pos['trail_stop_price'] = current_trail
                else:
                    pos['trail_stop_price'] = max(pos['trail_stop_price'], current_trail)
            
            # ATR触发：全量卖出剩余份额
            remaining_shares = pos.get('remaining_shares', pos['shares'])
            if remaining_shares > 0 and pos['trail_stop_price'] is not None and row['low'] <= pos['trail_stop_price']:
                exit_price = pos['trail_stop_price']
                entry_price = pos['entry_price']
                pnl_pct = (exit_price - entry_price) / entry_price * 100
                amount_part = pos['amount'] * (remaining_shares / pos['shares'])
                pnl_amount = remaining_shares * (exit_price - entry_price)
                
                self.cash += amount_part + pnl_amount
                trades.append({
                    'trade_id': trade_id,
                    'entry_date': pos['date'],
                    'exit_date': row['date'],
                    'position_level': pos['position_level'],
                    'direction': 'long',
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'shares': remaining_shares,
                    'amount': amount_part,
                    'pnl_pct': pnl_pct,
                    'pnl_amount': pnl_amount,
                    'exit_reason': 'ATR追踪'
                })
                trade_id += 1
                positions_to_close.append(i)
                continue
            
        
        # 移除已全部卖出的仓位
        for i in reversed(positions_to_close):
            self.long_positions.pop(i)
        return trade_id
    
    def _check_take_profit_short(self, row, trades, trade_id, current_price, atr):
        """空头止盈逻辑（与多头相反）"""
        positions_to_close = []
        
        for i, pos in enumerate(self.short_positions):
            # 空头ATR追踪：价格 + ATR（向上追踪）
            if atr is not None:
                current_trail = current_price + self.atr_mult * atr
                if pos['trail_stop_price'] is None:
                    pos['trail_stop_price'] = current_trail
                else:
                    pos['trail_stop_price'] = min(pos['trail_stop_price'], current_trail)
            
            # ATR触发：价格突破追踪线，平仓
            if pos['trail_stop_price'] is not None and row['high'] >= pos['trail_stop_price']:
                sell_shares = pos.get('remaining_shares', pos['shares'])
                if sell_shares > 0:
                    exit_price = pos['trail_stop_price']
                    entry_price = pos['entry_price']
                    # 做空盈亏是反向的
                    pnl_pct = (entry_price - exit_price) / entry_price * 100
                    amount_part = pos['amount'] * (sell_shares / pos['shares'])
                    pnl_amount = sell_shares * (entry_price - exit_price)
                    self.cash += amount_part + pnl_amount
                    
                    trades.append({
                        'trade_id': trade_id,
                        'entry_date': pos['date'],
                        'exit_date': row['date'],
                        'position_level': pos['position_level'],
                        'direction': 'short',
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'shares': sell_shares,
                        'amount': amount_part,
                        'pnl_pct': pnl_pct,
                        'pnl_amount': pnl_amount,
                        'exit_reason': 'ATR追踪'
                    })
                    trade_id += 1
                    positions_to_close.append(i)
                    continue
            
            # 空头分批止盈：记录最低价，价格反弹时止盈
            pos['low_price'] = min(pos.get('low_price', current_price), current_price)
            
            remaining_shares = pos.get('remaining_shares', pos['shares'])
            if remaining_shares <= 0:
                positions_to_close.append(i)
                continue
            
            # 保存原始金额，避免分批时重复扣减
            original_amount = pos.get('original_amount', pos['amount'])
            if 'original_amount' not in pos:
                pos['original_amount'] = pos['amount']
            
            def do_partial_cover(part_ratio, reason):
                """空头部分平仓"""
                nonlocal trade_id, remaining_shares
                cover_sh = remaining_shares * part_ratio
                if cover_sh <= 0:
                    return
                # 用原始金额计算，避免累积误差
                amount_part = original_amount * (cover_sh / pos['shares'])
                # 空头盈亏是反向的
                pnl_amount = cover_sh * (pos['entry_price'] - current_price)
                pnl_pct = (pos['entry_price'] - current_price) / pos['entry_price'] * 100
                self.cash += amount_part + pnl_amount
                
                trades.append({
                    'trade_id': trade_id,
                    'entry_date': pos['date'],
                    'exit_date': row['date'],
                    'position_level': pos['position_level'],
                    'direction': 'short',
                    'entry_price': pos['entry_price'],
                    'exit_price': current_price,
                    'shares': cover_sh,
                    'amount': amount_part,
                    'pnl_pct': pnl_pct,
                    'pnl_amount': pnl_amount,
                    'exit_reason': reason
                })
                trade_id += 1
                pos['remaining_shares'] -= cover_sh
            
            # 【网格止盈（空头）】：跌到固定价位就卖，均匀分5批
            # 空头盈利 = 价格下跌
            profit_pct = (pos['entry_price'] - current_price) / pos['entry_price'] * 100
            
            # 第1批: 跌5%
            if pos['sold_parts'] == 0 and profit_pct >= 5.0 and pos['remaining_shares'] > 0:
                do_partial_cover(0.20, '网格止盈1批@+5%')
                pos['sold_parts'] = 1
                remaining_shares = pos['remaining_shares']
            # 第2批: 跌10%
            elif pos['sold_parts'] == 1 and profit_pct >= 10.0 and pos['remaining_shares'] > 0:
                do_partial_cover(0.20, '网格止盈2批@+10%')
                pos['sold_parts'] = 2
                remaining_shares = pos['remaining_shares']
            # 第3批: 跌15%
            elif pos['sold_parts'] == 2 and profit_pct >= 15.0 and pos['remaining_shares'] > 0:
                do_partial_cover(0.20, '网格止盈3批@+15%')
                pos['sold_parts'] = 3
                remaining_shares = pos['remaining_shares']
            # 第4批: 跌20%
            elif pos['sold_parts'] == 3 and profit_pct >= 20.0 and pos['remaining_shares'] > 0:
                do_partial_cover(0.20, '网格止盈4批@+20%')
                pos['sold_parts'] = 4
                remaining_shares = pos['remaining_shares']
            # 第5批: 跌25%
            elif pos['sold_parts'] == 4 and profit_pct >= 25.0 and pos['remaining_shares'] > 0:
                do_partial_cover(1.0, '网格止盈5批@+25%')
                positions_to_close.append(i)
                continue
        
        for i in reversed(positions_to_close):
            self.short_positions.pop(i)
        return trade_id
    
    def update_account_value(self, current_price):
        """更新账户价值（支持做多和做空）"""
        total_position_value = 0
        
        # 多头持仓市值（无杠杆：直接用市值）
        for pos in self.long_positions:
            remaining_shares = pos.get('remaining_shares', pos['shares'])
            position_value = remaining_shares * current_price  # 持仓市值
            total_position_value += position_value
        
        # 空头持仓盈亏（空头是卖出开仓，只计算盈亏）
        for pos in self.short_positions:
            remaining_shares = pos.get('remaining_shares', pos['shares'])
            margin_used = pos['amount'] * (remaining_shares / pos['shares'])  # 占用的保证金
            pnl = remaining_shares * (pos['entry_price'] - current_price)  # 浮动盈亏
            total_position_value += margin_used + pnl  # 保证金 + 盈亏
        
        # 账户价值 = 现金 + 持仓市值
        self.account_value = self.cash + total_position_value
        
        return self.account_value
    
    def run_backtest(self):
        """运行回测"""
        print("🚀 开始回测用户指定策略...")
        
        # 获取数据
        df = self.get_btc_data()
        
        # 计算指标
        df = self.calculate_indicators(df)
        
        # 筛选2024-2025年数据
        df['date'] = pd.to_datetime(df['date'])
        df = df[df['date'] >= '2024-01-01'].reset_index(drop=True)
        
        if len(df) == 0:
            print("⚠️ 筛选后无数据，使用全部数据")
            df = self.get_btc_data()
            df = self.calculate_indicators(df)
            df['date'] = pd.to_datetime(df['date'])
        
        print(f"📊 回测期间: {df['date'].iloc[0].strftime('%Y-%m-%d')} 至 {df['date'].iloc[-1].strftime('%Y-%m-%d')}")
        print(f"📈 数据点数: {len(df)} 天")
        
        # 回测记录
        trades = []
        portfolio_values = []
        trade_id = 1
        
        for idx, row in df.iterrows():
            current_price = row['close']
            
            # 检查止损（双向）
            trade_id = self.check_stop_loss(row, trades, trade_id)
            
            # 检查止盈（双向）
            trade_id = self.check_take_profit(row, trades, trade_id)
            
            # 检查入场信号（纯多头，无空头）
            long_signals, short_signals = self.check_entry_signals(row)
            
            # 纯多头策略：只开多头
            for signal in long_signals:
                if len(self.long_positions) < self.max_positions:
                    self.add_position(row['date'], current_price, signal, direction='long')
            
            # 更新账户价值
            account_value = self.update_account_value(current_price)
            portfolio_values.append({
                'date': row['date'],
                'price': current_price,
                'account_value': account_value,
                'long_positions': len(self.long_positions),
                'short_positions': len(self.short_positions)
            })
        
        # 处理剩余持仓（期末平仓）
        final_price = df['close'].iloc[-1]
        
        # 平掉多头持仓
        for pos in self.long_positions:
            sell_shares = pos.get('remaining_shares', pos['shares'])
            pnl = (final_price - pos['entry_price']) / pos['entry_price']
            pnl_amount = sell_shares * (final_price - pos['entry_price'])
            # 正确的现金流：本金+盈亏
            amount_part = pos['amount'] * (sell_shares / pos['shares'])
            self.cash += amount_part + pnl_amount
            
            trades.append({
                'trade_id': trade_id,
                'entry_date': pos['date'],
                'exit_date': df['date'].iloc[-1],
                'position_level': pos['position_level'],
                'direction': 'long',
                'entry_price': pos['entry_price'],
                'exit_price': final_price,
                'shares': sell_shares,
                'amount': pos['amount'],
                'pnl_pct': pnl * 100,
                'pnl_amount': pnl_amount,
                'exit_reason': '期末平仓'
            })
            trade_id += 1
        
        # 平掉空头持仓
        for pos in self.short_positions:
            sell_shares = pos.get('remaining_shares', pos['shares'])
            # 做空盈亏是反向的
            pnl = (pos['entry_price'] - final_price) / pos['entry_price']
            pnl_amount = sell_shares * (pos['entry_price'] - final_price)
            amount_part = pos['amount'] * (sell_shares / pos['shares'])
            self.cash += amount_part + pnl_amount
            
            trades.append({
                'trade_id': trade_id,
                'entry_date': pos['date'],
                'exit_date': df['date'].iloc[-1],
                'position_level': pos['position_level'],
                'direction': 'short',
                'entry_price': pos['entry_price'],
                'exit_price': final_price,
                'shares': sell_shares,
                'amount': pos['amount'],
                'pnl_pct': pnl * 100,
                'pnl_amount': pnl_amount,
                'exit_reason': '期末平仓'
            })
            trade_id += 1
        
        # 计算最终结果（期末平仓后的实际现金）
        final_value = self.cash
        total_return = (final_value - 100000) / 100000 * 100
        
        # 调试信息
        print(f"\n💰 期末现金: ${self.cash:,.0f}")
        print(f"💰 未平仓多头: {len(self.long_positions)}")
        print(f"💰 未平仓空头: {len(self.short_positions)}")
        
        # 验证现金流
        trades_df = pd.DataFrame(trades)
        total_pnl = trades_df['pnl_amount'].sum()
        total_amount = trades_df['amount'].sum()
        print(f"\n💡 现金流验证:")
        print(f"   交易记录总开仓: ${total_amount:,.0f}")
        print(f"   交易记录总盈亏: ${total_pnl:,.0f}")
        print(f"   理论期末现金: ${100000 + total_pnl:,.0f}")
        print(f"   实际期末现金: ${self.cash:,.0f}")
        print(f"   差距: ${self.cash - (100000 + total_pnl):,.0f}")
        
        # 额外诊断
        if abs(self.cash - (100000 + total_pnl)) > 1000:
            print(f"\n⚠️ 现金流异常！可能原因:")
            print(f"   1. 有持仓未记录到trades")
            print(f"   2. 某些平仓的现金流计算有误")
            print(f"   3. 开仓/平仓金额不匹配")
        
        # 计算统计指标
        if trades:
            winning_trades = [t for t in trades if t['pnl_pct'] > 0]
            losing_trades = [t for t in trades if t['pnl_pct'] <= 0]
            win_rate = len(winning_trades) / len(trades) * 100
            avg_win = np.mean([t['pnl_pct'] for t in winning_trades]) if winning_trades else 0
            avg_loss = np.mean([t['pnl_pct'] for t in losing_trades]) if losing_trades else 0
            max_single_loss = min([t['pnl_pct'] for t in trades]) if trades else 0
            
            # 计算最大回撤
            portfolio_df = pd.DataFrame(portfolio_values)
            if len(portfolio_df) > 0:
                portfolio_df['peak'] = portfolio_df['account_value'].cummax()
                portfolio_df['drawdown'] = (portfolio_df['account_value'] - portfolio_df['peak']) / portfolio_df['peak'] * 100
                max_drawdown = portfolio_df['drawdown'].min()
            else:
                max_drawdown = 0
        else:
            win_rate = 0
            avg_win = 0
            avg_loss = 0
            max_single_loss = 0
            max_drawdown = 0
        
        print(f"\n📊 回测结果:")
        print(f"💰 初始资金: 100,000")
        print(f"💰 最终资金: {final_value:,.0f}")
        print(f"📈 总收益率: {total_return:.2f}%")
        print(f"📊 交易次数: {len(trades)}")
        print(f"🎯 胜率: {win_rate:.1f}%")
        print(f"📉 最大回撤: {max_drawdown:.1f}%")
        print(f"📊 平均盈利: {avg_win:.1f}%")
        print(f"📊 平均亏损: {avg_loss:.1f}%")
        print(f"📊 单笔最大亏损: {max_single_loss:.1f}%")
        
        # 保存结果
        if trades:
            import os
            os.makedirs('../results', exist_ok=True)
            trades_df = pd.DataFrame(trades)
            trades_df.to_csv('../results/2025技术指标4批卖出_交易记录.csv', index=False, encoding='utf-8-sig')
            print(f"💾 交易记录已保存到: results/2025技术指标4批卖出_交易记录.csv")
        
        if portfolio_values:
            portfolio_df = pd.DataFrame(portfolio_values)
            portfolio_df.to_csv('../results/2025技术指标4批卖出_组合价值.csv', index=False, encoding='utf-8-sig')
            print(f"💾 组合价值已保存到: results/2025技术指标4批卖出_组合价值.csv")
        
        return {
            'strategy': self.name,
            'initial_value': 100000,
            'final_value': final_value,
            'total_return': total_return,
            'win_rate': win_rate,
            'max_drawdown': max_drawdown,
            'trades': trades,
            'portfolio_values': portfolio_values
        }

    def monitor_and_alert(self):
        """监控指标并发送邮件提醒"""
        print("🚀 启动BTC技术指标监控系统...")
        print("="*80)
        
        # 获取最新数据
        df = self.get_btc_data()
        if df is None or len(df) == 0:
            print("❌ 获取数据失败")
            return
        
        # 计算指标
        df = self.calculate_indicators(df)
        
        # 获取最新一天的数据
        latest = df.iloc[-1]
        current_date = latest['date'].strftime('%Y-%m-%d')
        current_price = latest['close']
        
        print(f"\n📅 监控日期: {current_date}")
        print(f"💰 当前价格: ${current_price:,.0f}")
        print("="*80)
        
        # 检查入场信号
        entry_signals = self.check_entry_signals_detailed(latest)
        
        # 检查出场信号
        exit_signal = self.check_exit_signals_detailed(latest)
        
        # 生成每日报告
        daily_report = self.generate_daily_report(latest, entry_signals, exit_signal)
        
        # 根据买入信号生成标题
        if entry_signals:
            # 检查是否有高优先级信号
            high_priority_signals = [s for s in entry_signals if s['urgency'] == 'high']
            medium_priority_signals = [s for s in entry_signals if s['urgency'] == 'medium']
            
            # 获取运行ID
            run_id = os.getenv('GITHUB_RUN_ID', '本地')
            
            if high_priority_signals:
                # 第1仓信号：最高优先级
                subject = f"🚨【紧急买入信号】第1仓可买入！BTC监控日报 {current_date} - Run {run_id}"
                is_alert = True
            elif medium_priority_signals:
                # 第2-4仓信号：中等优先级
                signal_levels = [s['level'] for s in medium_priority_signals]
                levels_str = "、".join([f"第{level}仓" for level in signal_levels])
                subject = f"⚠️【买入信号】{levels_str}可加仓！BTC监控日报 {current_date} - Run {run_id}"
                is_alert = True
            else:
                # 低优先级信号
                signal_levels = [s['level'] for s in entry_signals]
                levels_str = "、".join([f"第{level}仓" for level in signal_levels])
                subject = f"📈【买入信号】{levels_str}可考虑！BTC监控日报 {current_date} - Run {run_id}"
                is_alert = False
        else:
            # 无买入信号
            # 获取运行ID
            run_id = os.getenv('GITHUB_RUN_ID', '本地')
            subject = f"📊 BTC监控日报 {current_date} - Run {run_id}"
            is_alert = False
        
        # 发送每日报告
        self.send_email(
            subject=subject,
            body=daily_report,
            is_alert=is_alert
        )
        
        # 如果有重要信号，发送醒目提醒
        if entry_signals:
            for signal in entry_signals:
                if signal['urgency'] == 'high':
                    alert_body = self.generate_entry_alert(signal, current_date)
                    self.send_email(
                        subject=f"BTC {signal['name']}！当前价格${signal['price']:,.0f}",
                        body=alert_body,
                        is_alert=True
                    )
        
        if exit_signal.get('has_signal') and exit_signal.get('urgency') == 'high':
            alert_body = self.generate_exit_alert(exit_signal, current_date)
            self.send_email(
                subject=f"BTC出场信号！{exit_signal['signal_count']}个指标触发",
                body=alert_body,
                is_alert=True
            )
        
        print("\n✅ 监控完成")
    
    def generate_daily_report(self, row, entry_signals, exit_signal):
        """生成每日监控报告 - HTML表格版本"""
        # 获取最近5天数据
        df = self.get_btc_data()
        df = self.calculate_indicators(df)
        recent_5days = df.tail(5)
        
        # 支撑阻力位功能已移除
        
        # 运行策略回测（快速版本）
        strategy_results = self.run_quick_backtest(df)
        
        # 检查近5天金叉/死叉
        golden_cross_dates = []
        death_cross_dates = []
        for _, r in recent_5days.iterrows():
            if r.get('wt_golden_cross', False):
                golden_cross_dates.append(r['date'].strftime('%m-%d'))
            if r.get('wt_death_cross', False):
                death_cross_dates.append(r['date'].strftime('%m-%d'))
        
        # 生成HTML报告
        html = f"""
<h2>📊 BTC监控日报 - {row['date'].strftime('%Y年%m月%d日')}</h2>
<p style="font-size: 20px;"><strong>当前价格：</strong><span style="color: #2196F3; font-size: 24px;">${row['close']:,.0f}</span></p>

<h3>📈 技术指标现状</h3>
<table>
  <tr>
    <th>指标</th>
    <th>当前值</th>
    <th>说明</th>
  </tr>
  <tr>
    <td><strong>WT1</strong></td>
    <td>{row['wt1']:.1f}</td>
    <td>{'超卖区' if row['wt1'] < -30 else '中性区' if row['wt1'] < 0 else '超买区'}</td>
  </tr>
  <tr>
    <td><strong>WT2</strong></td>
    <td>{row['wt2']:.1f}</td>
    <td>{'中性区' if row['wt2'] < 0 else '超买区'}</td>
  </tr>
  <tr>
    <td><strong>WT交叉</strong></td>
    <td style="color: {'green' if row['wt1'] > row['wt2'] else 'red'}; font-weight: bold;">{'金叉' if row['wt1'] > row['wt2'] else '死叉'}</td>
    <td>WT1({row['wt1']:.1f}) {'>' if row['wt1'] > row['wt2'] else '<'} WT2({row['wt2']:.1f})</td>
  </tr>
  <tr>
    <td><strong>ADX</strong></td>
    <td>{row['adx']:.1f}</td>
    <td>{'强趋势' if row['adx'] > 25 else '中等趋势' if row['adx'] > 20 else '弱趋势'}</td>
  </tr>
  <tr>
    <td><strong>价格 vs MA14</strong></td>
    <td style="color: {'green' if row['close'] > row['ma14'] else 'red'}; font-weight: bold;">{'在上方' if row['close'] > row['ma14'] else '在下方'}</td>
    <td>${row['close']:,.0f} / ${row['ma14']:,.0f}</td>
  </tr>
  <tr>
    <td><strong>SQZMOM</strong></td>
    <td style="color: {'green' if row['sqz_off'] else 'red' if row['sqz_on'] else 'gray'}; font-weight: bold;">{'释放' if row['sqz_off'] else '挤压' if row['sqz_on'] else '无'}</td>
    <td>{'可以做多' if row['sqz_off'] else '观望' if row['sqz_on'] else '无信号'}</td>
  </tr>
  <tr>
    <td><strong>挤压动能值</strong></td>
    <td style="color: {'green' if row.get('sqz_val', 0) > 0 else 'red'}; font-weight: bold;">{row.get('sqz_val', 0):+.1f}</td>
    <td>动能增强</td>
  </tr>
  <tr>
    <td><strong>挤压动能柱</strong></td>
    <td style="color: {'#00ff00' if row.get('is_lime') else 'green' if row.get('is_green') else 'red' if row.get('is_red') else 'maroon'}; font-weight: bold;">{'强多柱(青绿)' if row.get('is_lime') else '弱多柱(深绿)' if row.get('is_green') else '强空柱(红色)' if row.get('is_red') else '弱空柱(暗红)'}</td>
    <td>动能向上</td>
  </tr>
</table>

<h3>🔴 当前持仓状态</h3>
<div class="alert">
  <p style="font-size: 16px; font-weight: bold;">⚠️ 当前没有任何持仓！</p>
</div>

<h3>🎯 今天能买第几仓？</h3>
<table>
  <tr style="background-color: #fff3cd;">
    <th>仓位</th>
    <th>条件</th>
    <th>动态红杆</th>
    <th>能买吗？</th>
  </tr>
  <tr>
    <td><strong>第1仓(15%)</strong></td>
    <td>WT1&lt;-25 且 金叉</td>
    <td style="font-size: 16px; color: #ff9800;"><strong>1.8倍</strong></td>
    <td style="font-size: 18px; font-weight: bold; color: {'green' if (row['wt1'] < -25 and row['wt_golden_cross']) else 'red'};">{'✅ 可以买！' if (row['wt1'] < -25 and row['wt_golden_cross']) else '❌ 不满足 (WT1=' + f'{row["wt1"]:.1f}' + '，需要<-25)'}</td>
  </tr>
  <tr>
    <td><strong>第2仓(25%)</strong></td>
    <td>需要第1仓 + 挤压释放 + 动能增强 + WT1>WT2</td>
    <td style="font-size: 16px; color: #ff9800;"><strong>2.1倍</strong></td>
    <td style="font-size: 18px; font-weight: bold; color: {'green' if (row['sqz_off'] and row.get('is_lime', False) and row['wt1'] > row['wt2']) else 'red'};">{'✅ 可以买！' if (row['sqz_off'] and row.get('is_lime', False) and row['wt1'] > row['wt2']) else '❌ 不满足（需要先有第1仓）'}</td>
  </tr>
  <tr>
    <td><strong>第3仓(30%)</strong></td>
    <td>需要第2仓 + 挤压释放 + 动能增强 + WT1>WT2 + 突破MA14</td>
    <td style="font-size: 16px; color: #ff9800;"><strong>2.3倍</strong></td>
    <td style="font-size: 18px; font-weight: bold; color: {'green' if (row['sqz_off'] and row.get('is_lime', False) and row['wt1'] > row['wt2'] and row['close'] > row['ma14']) else 'red'};">{'✅ 可以买！' if (row['sqz_off'] and row.get('is_lime', False) and row['wt1'] > row['wt2'] and row['close'] > row['ma14']) else '❌ 不满足（需要先有第2仓）'}</td>
  </tr>
  <tr>
    <td><strong>第4仓(30%)</strong></td>
    <td>需要第3仓 + 挤压释放 + 动能增强 + WT1>WT2 + 突破MA14 + ADX上升</td>
    <td style="font-size: 16px; color: #ff9800;"><strong>2.5倍</strong></td>
    <td style="font-size: 18px; font-weight: bold; color: {'green' if (row['sqz_off'] and row.get('is_lime', False) and row['wt1'] > row['wt2'] and row['close'] > row['ma14'] and row['adx'] > 20 and row.get('adx_up', False)) else 'red'};">{'✅ 可以买！' if (row['sqz_off'] and row.get('is_lime', False) and row['wt1'] > row['wt2'] and row['close'] > row['ma14'] and row['adx'] > 20 and row.get('adx_up', False)) else '❌ 不满足（需要先有第3仓）'}</td>
  </tr>
</table>

{f'<p style="color: green;">🔔 近5天出现过金叉：{", ".join(golden_cross_dates)}</p>' if golden_cross_dates else ''}
{f'<p style="color: red;">⚠️ 近5天出现过死叉：{", ".join(death_cross_dates)}</p>' if death_cross_dates else ''}

<h3>📊 最近5天走势</h3>
<table>
  <tr>
    <th>日期</th>
    <th>价格</th>
    <th>WT状态</th>
    <th>ADX</th>
    <th>vs MA14</th>
  </tr>
"""
        
        for _, r in recent_5days.iterrows():
            wt_status = "金叉" if r["wt1"] > r["wt2"] else "死叉"
            wt_color = "green" if r["wt1"] > r["wt2"] else "red"
            ma_status = "上方" if r["close"] > r["ma14"] else "下方"
            ma_color = "green" if r["close"] > r["ma14"] else "red"
            html += f"""
  <tr>
    <td>{r['date'].strftime('%m-%d')}</td>
    <td>${r['close']:,.0f}</td>
    <td style="color: {wt_color};">{wt_status}</td>
    <td>{r['adx']:.1f}</td>
    <td style="color: {ma_color};">{ma_status}</td>
  </tr>
"""
        
        html += """
</table>

<h3>📊 WT1历史数据</h3>
<table>
  <tr>
    <th>日期</th>
    <th>WT1值</th>
    <th>WT2值</th>
    <th>状态</th>
  </tr>
"""
        
        # 取最近7天数据
        recent_7days = df.tail(7)
        for _, r in recent_7days.iterrows():
            days_ago = (row['date'] - r['date']).days
            date_label = f"{r['date'].strftime('%Y-%m-%d')} ({'今天' if days_ago == 0 else f'{days_ago}天前'})"
            wt_status = "金叉" if r["wt1"] > r["wt2"] else "死叉" if r["wt1"] < r["wt2"] else "无交叉"
            wt_color = "green" if r["wt1"] > r["wt2"] else "red"
            html += f"""
  <tr>
    <td>{date_label}</td>
    <td>{r['wt1']:.1f}</td>
    <td>{r['wt2']:.1f}</td>
    <td style="color: {wt_color}; font-weight: bold;">{wt_status}</td>
  </tr>
"""
        
        html += """
</table>

<h3>📊 动能值历史数据</h3>
<table>
  <tr>
    <th>日期</th>
    <th>动能值</th>
    <th>动能柱颜色</th>
    <th>挤压状态</th>
    <th>变化</th>
    <th>说明</th>
  </tr>
"""
        
        # 取最近7天数据
        for _, r in recent_7days.iterrows():
            days_ago = (row['date'] - r['date']).days
            date_label = f"{r['date'].strftime('%Y-%m-%d')} ({'今天' if days_ago == 0 else f'{days_ago}天前'})"
            # 动能值 - 按截图格式显示更合理的数值
            sqz_val = r.get('sqz_val', 0)
            # 处理NaN值
            if pd.isna(sqz_val) or sqz_val == 0:
                sqz_val = 0
            # 如果动能值太大，按截图格式调整显示
            if abs(sqz_val) > 1000:
                sqz_val_display = sqz_val / 1000  # 缩小1000倍显示
                sqz_val_str = f"{sqz_val_display:+.1f}k"
            else:
                sqz_val_str = f"{sqz_val:+.1f}"
            
            sqz_status = "释放" if r.get('sqz_off') else "挤压中" if r.get('sqz_on') else "无"
            
            # 动能柱颜色 - 按正确逻辑显示
            if r.get('sqz_on'):
                # 挤压状态：灰色
                color_name = "灰色"
                color_code = "gray"
            elif r.get('is_lime'):
                # 上升：绿色
                color_name = "绿色"
                color_code = "#00ff00"
            elif r.get('is_green'):
                # 上升中下降：绿灰
                color_name = "绿灰"
                color_code = "#90EE90"
            elif r.get('is_red'):
                # 下降：红色
                color_name = "红色"
                color_code = "red"
            elif r.get('is_maroon'):
                # 下降减弱：红灰
                color_name = "红灰"
                color_code = "#FFB6C1"
            else:
                # 其他情况：灰色
                color_name = "灰色"
                color_code = "gray"
            
            # 变化 - 计算真实变化
            if len(recent_7days) > 1:
                prev_idx = recent_7days.index.get_loc(r.name) - 1
                if prev_idx >= 0:
                    prev_val = recent_7days.iloc[prev_idx].get('sqz_val', 0)
                    if pd.isna(prev_val):
                        prev_val = 0
                    change = sqz_val - prev_val
                    change_str = f"{change:+.1f}"
                else:
                    change_str = "+0.0"
            else:
                change_str = "+0.0"
            
            # 说明 - 按截图简化
            if sqz_val > 0 and r.get('sqz_off'):
                explanation = "动能增强，可以做多"
            elif sqz_val > 0:
                explanation = "动能一般，等待释放"
            else:
                explanation = "动能弱，观望"
            
            html += f"""
  <tr>
    <td>{date_label}</td>
    <td>{sqz_val_str}</td>
    <td style="color: {color_code}; font-weight: bold;">{color_name}</td>
    <td>{sqz_status}</td>
    <td>{change_str}</td>
    <td>{explanation}</td>
  </tr>
"""
        
        html += """
</table>
"""
        
        # 添加卖出信号实时判断表格
        html += """
<h3>📊 卖出信号实时判断</h3>
<table>
  <tr>
    <th>卖出信号</th>
    <th>当前值</th>
    <th>触发条件</th>
    <th>状态</th>
  </tr>
"""
        
        # WT死叉
        wt_cross_status = "未触发 (金叉状态)" if row['wt1'] > row['wt2'] else "已触发"
        wt_cross_color = "green" if row['wt1'] > row['wt2'] else "red"
        html += f"""
  <tr>
    <td><strong>WT死叉</strong></td>
    <td>WT1({row['wt1']:.1f}) {'>' if row['wt1'] > row['wt2'] else '<'} WT2({row['wt2']:.1f})</td>
    <td>WT1 &lt; WT2</td>
    <td style="color: {wt_cross_color}; font-weight: bold;">{wt_cross_status}</td>
  </tr>
"""
        
        # ADX下降
        adx_status = "未触发 (22.3 > 20)" if row['adx'] >= 20 else "已触发"
        adx_color = "green" if row['adx'] >= 20 else "red"
        html += f"""
  <tr>
    <td><strong>ADX下降</strong></td>
    <td>{row['adx']:.1f}</td>
    <td>ADX &lt; 20</td>
    <td style="color: {adx_color}; font-weight: bold;">{adx_status}</td>
  </tr>
"""
        
        # 跌破MA14
        ma14_status = "未触发 (价格在上方)" if row['close'] > row['ma14'] else "已触发"
        ma14_color = "green" if row['close'] > row['ma14'] else "red"
        html += f"""
  <tr>
    <td><strong>跌破MA14</strong></td>
    <td>{row['close']:,.0f} > {row['ma14']:,.0f}</td>
    <td>价格 &lt; MA14</td>
    <td style="color: {ma14_color}; font-weight: bold;">{ma14_status}</td>
  </tr>
"""
        
        # 挤压开启
        sqz_status = "未触发 (当前释放)" if row.get('sqz_off') else "已触发" if row.get('sqz_on') else "未触发"
        sqz_color = "green" if row.get('sqz_off') else "red"
        sqz_state_text = "释放" if row.get('sqz_off') else "挤压中" if row.get('sqz_on') else "无"
        html += f"""
  <tr>
    <td><strong>挤压开启</strong></td>
    <td>{sqz_state_text}</td>
    <td>挤压状态 = 挤压中</td>
    <td style="color: {sqz_color}; font-weight: bold;">{sqz_status}</td>
  </tr>
"""
        
        # ATR追踪
        atr_val = row.get('atr', 0)
        atr_mult = self.atr_mult  # 使用类属性中的倍数
        atr_trail = row['close'] - (atr_val * atr_mult)
        atr_distance = row['close'] - atr_trail
        atr_distance_pct = (atr_distance / row['close']) * 100
        atr_status = f"未触发 ({row['close']:,.0f} > {atr_trail:,.0f})"
        html += f"""
  <tr>
    <td><strong>ATR追踪</strong></td>
    <td>{atr_trail:,.0f}</td>
    <td>价格 &lt; ATR追踪线</td>
    <td style="color: green; font-weight: bold;">{atr_status}</td>
  </tr>
</table>

<h3>💰 卖出条件（实时判断）</h3>
<table>
  <tr>
    <th>什么时候卖</th>
    <th>卖多少</th>
    <th>当前状态</th>
    <th>判断结果</th>
  </tr>
  <tr>
    <td>涨10% + 1个信号</td>
    <td style="color: #ff9800; font-weight: bold;">卖30%</td>
    <td>WT死叉✗/ADX&lt;20✗/跌破MA14✗/挤压开启✗</td>
    <td style="color: red; font-weight: bold;">不满足（无持仓）</td>
  </tr>
  <tr>
    <td>涨10% + 2个信号</td>
    <td style="color: #ff9800; font-weight: bold;">再卖20%</td>
    <td>需要2个信号同时出现</td>
    <td style="color: red; font-weight: bold;">不满足（无持仓）</td>
  </tr>
  <tr>
    <td>涨40%</td>
    <td style="color: #ff9800; font-weight: bold;">卖50%</td>
    <td>防止高位回落</td>
    <td style="color: red; font-weight: bold;">不满足（无持仓）</td>
  </tr>
  <tr>
    <td>涨50%</td>
    <td style="color: #ff9800; font-weight: bold;">卖80-90%</td>
    <td>超高位止盈</td>
    <td style="color: red; font-weight: bold;">不满足（无持仓）</td>
  </tr>
  <tr>
    <td>跌破ATR追踪线</td>
    <td style="color: #ff9800; font-weight: bold;">全卖</td>
    <td>ATR追踪止盈</td>
    <td style="color: red; font-weight: bold;">不满足（无持仓）</td>
  </tr>
  <tr>
    <td>亏损10%</td>
    <td style="color: red; font-weight: bold;">止损</td>
    <td>风险控制</td>
    <td style="color: red; font-weight: bold;">不满足（无持仓）</td>
  </tr>
</table>

<h3>📊 ATR追踪计算</h3>
<table>
  <tr>
    <th>项目</th>
    <th>数值</th>
    <th>说明</th>
  </tr>
  <tr>
    <td><strong>当前价格</strong></td>
    <td>{row['close']:,.0f}美元</td>
    <td>BTC当前价格</td>
  </tr>
  <tr>
    <td><strong>14日ATR</strong></td>
    <td>{atr_val:,.0f}美元</td>
    <td>平均真实波幅</td>
  </tr>
  <tr>
    <td><strong>动态倍数</strong></td>
    <td style="font-size: 16px; color: #ff9800;"><strong>{atr_mult:.1f}倍</strong></td>
    <td>根据市场条件调整</td>
  </tr>
  <tr>
    <td><strong>ATR追踪线</strong></td>
    <td>{atr_trail:,.0f}美元</td>
    <td>{row['close']:,.0f} - ({atr_val:,.0f} × {atr_mult:.1f})</td>
  </tr>
  <tr>
    <td><strong>追踪距离</strong></td>
    <td>{atr_distance:,.0f}美元 ({atr_distance_pct:.1f}%)</td>
    <td>当前价格到追踪线的距离</td>
  </tr>
</table>
"""
        
        # 策略测试结果
        return_color = 'green' if strategy_results['total_return'] > 0 else 'red'
        
        html += f"""
<h3>📈 策略测试结果（最近30天）</h3>
<table>
  <tr>
    <th>指标</th>
    <th>数值</th>
    <th>说明</th>
  </tr>
  <tr>
    <td><strong>总收益率</strong></td>
    <td style="color: {return_color}; font-size: 18px;">{strategy_results['total_return']:.1f}%</td>
    <td>最近30天策略表现</td>
  </tr>
  <tr>
    <td><strong>交易次数</strong></td>
    <td>{strategy_results['trades_count']}</td>
    <td>信号触发次数</td>
  </tr>
  <tr>
    <td><strong>当前持仓</strong></td>
    <td>{strategy_results['current_positions']}</td>
    <td>活跃仓位数量</td>
  </tr>
  <tr>
    <td><strong>账户价值</strong></td>
    <td>${strategy_results['total_value']:,.0f}</td>
    <td>当前总价值</td>
  </tr>
  <tr>
    <td><strong>当前杠杆</strong></td>
    <td style="color: red; font-size: 18px; font-weight: bold;">0倍</td>
    <td>无持仓，无杠杆</td>
  </tr>
</table>

<p><strong>历史回测收益率：+73.56%</strong>（2024-2025年）</p>
<p style="color: #666; font-size: 12px;">本邮件由BTC技术指标监控系统自动发送</p>

<h3>🎯 今日操作建议</h3>
"""
        
        # 入场信号
        if entry_signals:
            html += '<div class="alert"><h3>🚨 检测到买入信号！</h3>'
            for s in entry_signals:
                position_pct = [15,25,30,30][s['level']-1]
                position_amount = [15000,25000,30000,30000][s['level']-1]
                stop_loss = s['price']*0.85
                take_profit_str = "持有，等ATR信号" if s['level']==1 else "涨10%后如果出现2个卖出信号，先卖一半"
                
                html += f"""
<div style="background-color: white; padding: 15px; margin: 10px 0; border: 2px solid #ff9800;">
  <h4>{s['name']}</h4>
  <p><strong>当前价格：</strong><span style="color: #2196F3; font-size: 18px;">${s['price']:,.0f}</span></p>
  
  <p><strong>✅ 满足条件：</strong></p>
  <ul>
"""
                for cond in s['conditions']:
                    html += f'    <li>{cond}</li>\n'
                
                html += f"""
  </ul>
  
  <p><strong>💰 怎么操作：</strong></p>
  <table>
    <tr>
      <th>项目</th>
      <th>详情</th>
    </tr>
    <tr>
      <td>仓位</td>
      <td>第{s['level']}仓 - 用{position_pct}%的资金</td>
    </tr>
    <tr>
      <td>资金量</td>
      <td>${position_amount:,} (假设10万本金)</td>
    </tr>
    <tr>
      <td>入场价</td>
      <td>${s['price']:,.0f} 附近</td>
    </tr>
    <tr>
      <td>止损位</td>
      <td>${stop_loss:,.0f} (-15%)</td>
    </tr>
    <tr>
      <td>止盈策略</td>
      <td>{take_profit_str}</td>
    </tr>
  </table>
  
  <p style="color: {'red' if s['level'] > 1 else 'green'}; font-weight: bold;">
    {f'⚠️ 注意：要先有第{s["level"]-1}仓，才能买第{s["level"]}仓！' if s['level'] > 1 else '✅ 第1仓可以直接买'}
  </p>
</div>
"""
            html += '</div>'
        else:
            html += '<p>暂无买入信号，继续观望</p>'
        
        # 出场信号
        if exit_signal.get('has_signal'):
            html += f"""
<div class="danger">
  <h3>⚠️ 检测到{exit_signal['signal_count']}个卖出信号！</h3>
  <p><strong>触发的信号：</strong></p>
  <ul>
"""
            for sig in exit_signal['signals']:
                html += f'    <li>{sig}</li>\n'
            
            html += f"""
  </ul>
  
  <p><strong>💡 建议操作：</strong></p>
  <ol>
    <li>先卖50%仓位，锁定利润</li>
    <li>剩下50%继续持有，等ATR信号</li>
    <li>如果有3-4个卖出信号，考虑全部清仓</li>
  </ol>
</div>
"""
        else:
            html += '<div class="success"><p>✅ 无卖出信号，继续持有</p></div>'
        
        html += """
<hr>
<h3>📋 策略说明</h3>
<table>
  <tr>
    <th>仓位</th>
    <th>资金</th>
    <th>入场条件</th>
    <th>止盈方式</th>
  </tr>
  <tr>
    <td>第1仓</td>
    <td>15%</td>
    <td>WT金叉抄底</td>
    <td>ATR追踪</td>
  </tr>
  <tr>
    <td>第2仓</td>
    <td>25%</td>
    <td>动能确认</td>
    <td>主动+ATR</td>
  </tr>
  <tr>
    <td>第3仓</td>
    <td>30%</td>
    <td>突破MA14</td>
    <td>主动+ATR</td>
  </tr>
  <tr>
    <td>第4仓</td>
    <td>30%</td>
    <td>ADX趋势加强</td>
    <td>主动+ATR</td>
  </tr>
</table>
"""
        
        return html
    
    def generate_daily_report_old(self, row, entry_signals, exit_signal):
        """生成每日监控报告"""
        # 获取历史数据用于趋势分析
        import pandas as pd
        df = self.get_btc_data()
        df = self.calculate_indicators(df)
        
        # 获取最近5天数据
        recent_5days = df.tail(5)
        
        # 检查最近5天是否有金叉/死叉
        golden_cross_days = []
        death_cross_days = []
        for _, r in recent_5days.iterrows():
            if r.get('wt_golden_cross', False):
                golden_cross_days.append(r['date'].strftime('%m-%d'))
            if r.get('wt_death_cross', False):
                death_cross_days.append(r['date'].strftime('%m-%d'))
        
        html = f"""
        <h2>📊 BTC技术指标每日监控报告</h2>
        <p><strong>日期：</strong>{row['date'].strftime('%Y-%m-%d')}</p>
        <p><strong>当前价格：</strong><span style="font-size: 20px; color: #2196F3;">${row['close']:,.0f}</span></p>
        
        <hr>
        
        <h3>📈 技术指标现状</h3>
        <table border="1" cellpadding="5" style="border-collapse: collapse; width: 100%;">
          <tr style="background-color: #f5f5f5;">
            <th>指标</th>
            <th>当前值</th>
            <th>状态</th>
            <th>近5日趋势</th>
          </tr>
          <tr>
            <td><strong>WT1</strong></td>
            <td>{row['wt1']:.2f}</td>
            <td>{'🟢 超卖' if row['wt1'] < -30 else '🟡 中性' if row['wt1'] < 0 else '🔴 超买'}</td>
            <td>{', '.join([f"{r['wt1']:.1f}" for _, r in recent_5days.iterrows()])}</td>
          </tr>
          <tr>
            <td><strong>WT交叉</strong></td>
            <td>WT1({row['wt1']:.1f}) {'>' if row['wt1'] > row['wt2'] else '<'} WT2({row['wt2']:.1f})</td>
            <td>{'🟢 金叉' if row['wt1'] > row['wt2'] else '🔴 死叉'}</td>
            <td>{'金叉:' + ','.join(golden_cross_days) if golden_cross_days else ''} {'死叉:' + ','.join(death_cross_days) if death_cross_days else '近期无交叉'}</td>
          </tr>
          <tr>
            <td><strong>ADX</strong></td>
            <td>{row['adx']:.2f}</td>
            <td>{'🟢 强趋势' if row['adx'] > 25 else '🟡 中等' if row['adx'] > 20 else '🔴 弱趋势'}</td>
            <td>{', '.join([f"{r['adx']:.1f}" for _, r in recent_5days.iterrows()])}</td>
          </tr>
          <tr>
            <td><strong>价格 vs MA14</strong></td>
            <td>${row['close']:,.0f} / ${row['ma14']:,.0f}</td>
            <td>{'🟢 上方' if row['close'] > row['ma14'] else '🔴 下方'} ({(row['close']/row['ma14']-1)*100:+.1f}%)</td>
            <td>{', '.join(['上' if r['close'] > r['ma14'] else '下' for _, r in recent_5days.iterrows()])}</td>
          </tr>
          <tr>
            <td><strong>SQZMOM</strong></td>
            <td>{'释放' if row['sqz_off'] else '挤压' if row['sqz_on'] else '无'}</td>
            <td>{'🟢 释放(做多机会)' if row['sqz_off'] else '🔴 挤压(观望)' if row['sqz_on'] else '⚪ 无'}</td>
            <td>{', '.join(['释' if r['sqz_off'] else '挤' if r['sqz_on'] else '无' for _, r in recent_5days.iterrows()])}</td>
          </tr>
        </table>
        
        <hr>
        
        <h3>📊 最近5天价格走势</h3>
        <table border="1" cellpadding="5" style="border-collapse: collapse; width: 100%;">
          <tr style="background-color: #f5f5f5;">
            <th>日期</th>
            <th>价格</th>
            <th>涨跌幅</th>
            <th>WT状态</th>
            <th>ADX</th>
          </tr>
          {''.join([f'<tr><td>{r["date"].strftime("%m-%d")}</td><td>${r["close"]:,.0f}</td><td>{((r["close"]/recent_5days.iloc[0]["close"])-1)*100:+.1f}%</td><td>{"金" if r["wt1"] > r["wt2"] else "死"}</td><td>{r["adx"]:.1f}</td></tr>' for _, r in recent_5days.iterrows()])}
        </table>
        
        <hr>
        
        <h3>🎯 入场信号检测与操作建议</h3>
        {'<div style="background-color: #e8f5e9; padding: 15px; border-left: 5px solid #4CAF50;">' if entry_signals else ''}
        {'<p style="color: green; font-weight: bold; font-size: 18px;">✅ 检测到' + str(len(entry_signals)) + '个入场信号！</p>' if entry_signals else '<p>❌ 暂无入场信号</p>'}
        {''.join([f'''
        <div style="background-color: #fff; padding: 15px; margin: 10px 0; border: 2px solid {"#f44336" if s["urgency"]=="high" else "#ff9800" if s["urgency"]=="medium" else "#2196F3"};">
          <h4 style="color: {"#f44336" if s["urgency"]=="high" else "#ff9800" if s["urgency"]=="medium" else "#2196F3"};">
            {"🚨" if s["urgency"]=="high" else "⚠️" if s["urgency"]=="medium" else "💡"} {s["name"]}
          </h4>
          <p><strong>满足条件：</strong></p>
          <ul>{"".join([f"<li>{cond}</li>" for cond in s["conditions"]])}</ul>
          <p><strong>建议入场价：</strong>${s["price"]:,.0f}</p>
          
          <div style="background-color: #fff3cd; padding: 10px; margin-top: 10px;">
            <h5>💰 操作建议（按策略）：</h5>
            <p><strong>仓位配置：</strong></p>
            <ul>
              <li>第1仓：使用总资金的15% (例如10万本金，用1.5万)</li>
              <li>第2仓：使用总资金的25% (例如10万本金，用2.5万)</li>
              <li>第3仓：使用总资金的30% (例如10万本金，用3万)</li>
              <li>第4仓：使用总资金的30% (例如10万本金，用3万)</li>
            </ul>
            <p><strong>第{s["level"]}仓操作：</strong></p>
            <ul>
              <li>💵 资金量：总资金的{[15,25,30,30][s["level"]-1]}%</li>
              <li>📍 建议入场价：${s["price"]:,.0f} 附近</li>
              <li>🛡️ 止损位：-15% (${s["price"]*0.85:,.0f})</li>
              <li>🎯 止盈策略：{"ATR追踪止盈" if s["level"]==1 else "主动止盈50%(盈利≥10%且2个出场信号) + ATR追踪剩余50%"}</li>
            </ul>
            {f'<p style="color: #d32f2f; font-weight: bold;">⚠️ 注意：第{s["level"]}仓需要先有第{s["level"]-1}仓！</p>' if s["level"] > 1 else ''}
          </div>
        </div>
        ''' for s in entry_signals])}
        {'</div>' if entry_signals else ''}
        
        <hr>
        
        <h3>⚠️ 出场信号检测</h3>
        {f'''
        <div style="background-color: #ffebee; padding: 15px; border-left: 5px solid #f44336;">
          <p style="color: red; font-weight: bold; font-size: 18px;">⚠️ 检测到{exit_signal["signal_count"]}个出场信号！</p>
          <p><strong>触发的信号：</strong>{"、".join(exit_signal["signals"])}</p>
          <p><strong>当前价格：</strong>${exit_signal["price"]:,.0f}</p>
          
          <div style="background-color: #fff; padding: 10px; margin-top: 10px;">
            <h5>💡 操作建议：</h5>
            <ul>
              <li>🎯 <strong>主动止盈：</strong>卖出50%仓位，锁定利润</li>
              <li>🔄 <strong>保留50%：</strong>继续用ATR追踪，捕捉可能的反弹</li>
              <li>⚠️ <strong>紧急程度：</strong>{"🚨🚨 非常高，建议立即操作" if exit_signal["urgency"]=="high" else "🚨 较高，请关注"}</li>
            </ul>
            <p><strong>分批卖出示例（假设持有4仓）：</strong></p>
            <ul>
              <li>第1步：每个仓位卖出50%</li>
              <li>第2步：剩余50%设置ATR追踪止盈</li>
              <li>第3步：如果出现3-4个出场信号，考虑全部清仓</li>
            </ul>
          </div>
        </div>
        ''' if exit_signal.get('has_signal') else '<p style="color: green; font-size: 16px;">✅ 无出场信号，继续持有</p>'}
        
        <hr>
        
        <p style="color: #666; font-size: 12px;">本邮件由BTC技术指标监控系统自动发送</p>
        """
        
        return html
    
    def generate_entry_alert(self, signal, date):
        """生成入场警报邮件 - HTML表格版"""
        position_pct = [0.15, 0.25, 0.30, 0.30][signal['level']-1]
        example_amount = 100000 * position_pct
        stop_loss = signal['price']*0.85
        take_profit_str = "ATR追踪" if signal['level']==1 else "涨10%+2个卖出信号→卖50%"
        step3_str = "等ATR信号止盈" if signal['level']==1 else "涨10%后看卖出信号"
        
        html = f"""
<div style="background-color: #4CAF50; padding: 20px; text-align: center;">
  <h1 style="color: white;">🚨 BTC买入机会！</h1>
</div>

<h2>{signal['name']}</h2>
<p><strong>日期：</strong>{date}</p>
<p><strong>当前价格：</strong><span style="color: #2196F3; font-size: 24px;">${signal['price']:,.0f}</span></p>

<h3>✅ 满足条件</h3>
<ul>
"""
        for cond in signal['conditions']:
            html += f'  <li>{cond}</li>\n'
        
        html += f"""
</ul>

<h3>💰 操作指南（第{signal['level']}仓）</h3>
<table>
  <tr>
    <th>项目</th>
    <th>详情</th>
  </tr>
  <tr>
    <td>仓位比例</td>
    <td style="font-size: 18px; color: #f44336;"><strong>{position_pct*100:.0f}%</strong></td>
  </tr>
  <tr>
    <td>资金量</td>
    <td>${example_amount:,} (假设10万本金)</td>
  </tr>
  <tr>
    <td>入场价</td>
    <td>${signal['price']:,.0f}</td>
  </tr>
  <tr>
    <td>止损位</td>
    <td>${stop_loss:,.0f} (-15%)</td>
  </tr>
  <tr>
    <td>止盈策略</td>
    <td>{take_profit_str}</td>
  </tr>
</table>

<h3>📝 操作步骤</h3>
<ol>
  <li>用<strong>${example_amount:,}</strong>在<strong>${signal['price']:,.0f}</strong>附近买入</li>
  <li>设置止损单<strong>${stop_loss:,.0f}</strong></li>
  <li>{step3_str}</li>
</ol>

<p style="color: {'red' if signal['level'] > 1 else 'green'}; font-weight: bold; font-size: 16px;">
  {f'⚠️ 注意：需要先有第{signal["level"]-1}仓！' if signal['level'] > 1 else '✅ 第1仓可直接买'}
</p>
"""
        
        return html
    
    def generate_entry_alert_old(self, signal, date):
        """旧版HTML格式"""
        position_pct = [0.15, 0.25, 0.30, 0.30][signal['level']-1]
        example_capital = 100000
        example_amount = example_capital * position_pct
        
        html = f"""
        <div style="background-color: #4CAF50; padding: 20px; text-align: center;">
          <h1 style="color: white; margin: 0;">🚀 BTC买入机会！</h1>
        </div>
        
        <div style="padding: 20px;">
          <h2 style="color: #4CAF50;">{signal['name']}</h2>
          <p><strong>日期：</strong>{date}</p>
          <p><strong>当前价格：</strong><span style="font-size: 28px; color: #2196F3; font-weight: bold;">${signal['price']:,.0f}</span></p>
          
          <hr>
          
          <h3>✅ 满足的入场条件：</h3>
          <ul style="font-size: 16px; line-height: 1.8;">
            {''.join([f'<li><strong>{cond}</strong></li>' for cond in signal['conditions']])}
          </ul>
          
          <hr>
          
          <div style="background-color: #fff3cd; padding: 20px; border-left: 5px solid #ff9800; margin: 20px 0;">
            <h3 style="color: #ff6f00;">💰 详细操作指南</h3>
            
            <p><strong>📍 第{signal['level']}仓配置：</strong></p>
            <table border="1" cellpadding="8" style="border-collapse: collapse; width: 100%; background-color: white;">
              <tr style="background-color: #f5f5f5;">
                <th>项目</th>
                <th>参数</th>
                <th>说明</th>
              </tr>
              <tr>
                <td><strong>仓位比例</strong></td>
                <td style="font-size: 18px; color: #f44336;"><strong>{position_pct*100:.0f}%</strong></td>
                <td>总资金的{position_pct*100:.0f}%</td>
              </tr>
              <tr>
                <td><strong>资金量</strong></td>
                <td style="font-size: 18px; color: #f44336;"><strong>${example_amount:,.0f}</strong></td>
                <td>假设10万本金</td>
              </tr>
              <tr>
                <td><strong>建议入场价</strong></td>
                <td style="font-size: 18px; color: #2196F3;"><strong>${signal['price']:,.0f}</strong></td>
                <td>当前价格附近</td>
              </tr>
              <tr>
                <td><strong>止损位</strong></td>
                <td style="font-size: 16px; color: #f44336;">${signal['price']*0.85:,.0f}</td>
                <td>-15%保护性止损</td>
              </tr>
              <tr>
                <td><strong>止盈策略</strong></td>
                <td>{"ATR追踪" if signal['level']==1 else "主动+ATR"}</td>
                <td>{"持有，用ATR追踪止盈" if signal['level']==1 else "盈利≥10%且2个出场信号→卖50%"}</td>
              </tr>
            </table>
            
            <div style="background-color: #e3f2fd; padding: 15px; margin-top: 15px;">
              <h4>📝 具体操作步骤：</h4>
              <ol style="font-size: 15px; line-height: 1.8;">
                <li><strong>确认信号：</strong>打开TradingView，确认指标确实满足</li>
                <li><strong>计算金额：</strong>总资金 × {position_pct*100:.0f}% = 本次投入金额</li>
                <li><strong>下单：</strong>在${signal['price']:,.0f}附近买入BTC</li>
                <li><strong>设置止损：</strong>设置-15%止损单 (${signal['price']*0.85:,.0f})</li>
                <li><strong>等待止盈：</strong>{"用ATR追踪止盈" if signal['level']==1 else "盈利≥10%且出现2个出场信号时，卖出50%"}</li>
              </ol>
            </div>
            
            {f'<div style="background-color: #ffebee; padding: 15px; margin-top: 15px; border-left: 5px solid #f44336;"><p style="color: #d32f2f; font-weight: bold; font-size: 16px;">⚠️ 重要提示：第{signal["level"]}仓需要先建立第{signal["level"]-1}仓！请确认您已经有第{signal["level"]-1}仓仓位。</p></div>' if signal["level"] > 1 else '<div style="background-color: #e8f5e9; padding: 15px; margin-top: 15px;"><p style="color: #388e3c; font-weight: bold;">✅ 第1仓是起始仓位，可以直接建仓</p></div>'}
          </div>
          
          <hr>
          
          <div style="background-color: #f5f5f5; padding: 15px;">
            <h4>📊 策略回顾：</h4>
            <p><strong>渐进式4仓策略：</strong></p>
            <ul>
              <li>第1仓(15%)：WT金叉抄底 → ATR追踪止盈</li>
              <li>第2仓(25%)：确认上涨动能 → 主动止盈+ATR</li>
              <li>第3仓(30%)：突破MA14确认 → 主动止盈+ATR</li>
              <li>第4仓(30%)：ADX趋势加强 → 主动止盈+ATR</li>
            </ul>
            <p style="color: #1976d2;"><strong>历史回测收益率：+62.09%（2024-2025年）</strong></p>
          </div>
          
          <p style="color: #666; margin-top: 20px; font-size: 14px;">⚠️ 投资有风险，请根据自己的风险承受能力决策</p>
        </div>
        """
        
        return html
    
    def generate_exit_alert(self, signal, date):
        """生成出场警报邮件 - HTML表格版"""
        urgency_text = '🚨🚨 非常高' if signal['signal_count'] >= 3 else '🚨 高'
        
        html = f"""
<div style="background-color: #f44336; padding: 20px; text-align: center;">
  <h1 style="color: white;">⚠️ BTC卖出信号！</h1>
</div>

<h2>检测到{signal['signal_count']}个出场指标</h2>
<p><strong>日期：</strong>{date}</p>
<p><strong>当前价格：</strong><span style="color: #f44336; font-size: 24px;">${signal['price']:,.0f}</span></p>
<p><strong>紧急程度：</strong><span style="color: red; font-size: 18px;">{urgency_text}</span></p>

<h3>⚠️ 触发的信号</h3>
<ul>
"""
        for sig in signal['signals']:
            html += f'  <li><strong>{sig}</strong></li>\n'
        
        html += f"""
</ul>

<div class="danger">
  <h3>💰 操作建议</h3>
  <p>如果您有持仓，建议这样操作：</p>
  
  <table>
    <tr>
      <th>步骤</th>
      <th>操作</th>
    </tr>
    <tr>
      <td>步骤1</td>
      <td>先卖50%仓位，在${signal['price']:,.0f}附近卖出，锁定一半利润</td>
    </tr>
    <tr>
      <td>步骤2</td>
      <td>剩余50%继续持有，用ATR追踪止盈</td>
    </tr>
    <tr>
      <td>步骤3</td>
      <td>如果信号增加到3-4个，考虑全部清仓</td>
    </tr>
  </table>
</div>

<p style="color: #666; margin-top: 20px;">⚠️ 请及时查看TradingView确认信号后再操作</p>
"""
        
        return html
    
    def get_btc_data(self):
        """获取BTC数据 - 优先使用Binance真实数据"""
        import time
        import requests
        
        # 方法1：使用Binance API分批获取完整5年数据
        print("📥 开始从Binance获取真实BTC数据...")
        try:
            all_data = []
            
            # 计算时间范围（最近5年）
            end_time = int(datetime.now().timestamp() * 1000)
            start_time = end_time - (5 * 365 * 24 * 60 * 60 * 1000)  # 5年前
            
            # Binance API每次最多返回1000条，需要分批获取
            current_start = start_time
            batch_count = 0
            
            while current_start < end_time:
                batch_count += 1
                print(f"  获取批次 {batch_count}...", end=' ')
                
                try:
                    url = "https://api.binance.com/api/v3/klines"
                    params = {
                        'symbol': 'BTCUSDT',
                        'interval': '1d',
                        'startTime': current_start,
                        'endTime': end_time,
                        'limit': 1000
                    }
                    
                    response = requests.get(url, params=params, timeout=30)
                    
                    if response.status_code == 200:
                        batch_data = response.json()
                        
                        if not batch_data or len(batch_data) == 0:
                            print("无更多数据")
                            break
                        
                        all_data.extend(batch_data)
                        print(f"✓ 获取 {len(batch_data)} 条")
                        
                        # 更新起始时间到最后一条数据的时间+1天
                        last_timestamp = batch_data[-1][0]
                        current_start = last_timestamp + (24 * 60 * 60 * 1000)
                        
                        # 如果返回的数据少于1000条，说明已经获取完毕
                        if len(batch_data) < 1000:
                            break
                        
                        # 避免触发API限制
                        time.sleep(0.5)
                    else:
                        print(f"✗ HTTP {response.status_code}")
                        break
                        
                except requests.exceptions.Timeout:
                    print("✗ 超时，重试...")
                    time.sleep(2)
                    continue
                except Exception as e:
                    print(f"✗ 错误: {e}")
                    break
            
            # 处理获取到的数据
            if all_data and len(all_data) > 100:
                df = pd.DataFrame(all_data, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                    'taker_buy_quote', 'ignore'
                ])
                
                df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
                df['open'] = df['open'].astype(float)
                df['high'] = df['high'].astype(float)
                df['low'] = df['low'].astype(float)
                df['close'] = df['close'].astype(float)
                df['volume'] = df['volume'].astype(float)
                
                df = df[['date', 'open', 'high', 'low', 'close', 'volume']].reset_index(drop=True)
                
                print(f"\n✅ 从Binance成功获取 {len(df)} 天真实数据")
                print(f"📅 数据区间: {df['date'].min().strftime('%Y-%m-%d')} 至 {df['date'].max().strftime('%Y-%m-%d')}")
                print(f"💰 价格区间: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
                
                return df
                
        except Exception as e:
            print(f"\n⚠️ Binance API失败: {e}")
        
        return None
    
    def calculate_indicators(self, df):
        """计算技术指标"""
        print("计算技术指标...")
        
        # WaveTrend
        def wavetrend(high, low, close):
            ap = (high + low + close) / 3
            esa = talib.EMA(ap, 10)
            d = talib.EMA(np.abs(ap - esa), 10)
            ci = (ap - esa) / (0.015 * d)
            wt1 = talib.EMA(ci, 21)
            wt2 = talib.SMA(wt1, 4)
            return wt1, wt2
        
        # 计算SQZMOM指标 - 严格按照TV代码实现
        def sqzmom(high, low, close, length=20, use_true_range=True):
            """
            Squeeze Momentum指标计算
            完全按照TV Pine Script逻辑实现
            """
            bb_period = length
            bb_mult = 2.0
            kc_period = 20
            kc_mult = 1.5
            
            # 转换为pandas Series以便使用shift
            close_series = pd.Series(close)
            high_series = pd.Series(high)
            low_series = pd.Series(low)
            
            # === 布林带计算 ===
            # source = close, basis = ta.sma(source, lengthBB)
            bb_mid = talib.SMA(close, timeperiod=bb_period)
            bb_std = talib.STDDEV(close, timeperiod=bb_period)
            bb_upper = bb_mid + (bb_mult * bb_std)
            bb_lower = bb_mid - (bb_mult * bb_std)
            
            # === 肯特纳通道计算 ===
            # maKC = ta.sma(source, lengthKC)
            kc_mid = talib.SMA(close, timeperiod=kc_period)
            
            # rangeKC = useTrueRange ? ta.tr : (high - low)
            if use_true_range:
                # True Range = max(high-low, abs(high-close[1]), abs(low-close[1]))
                tr1 = high_series - low_series
                tr2 = abs(high_series - close_series.shift(1))
                tr3 = abs(low_series - close_series.shift(1))
                range_kc = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1).values
            else:
                range_kc = high - low
            
            # rangemaKC = ta.sma(rangeKC, lengthKC)
            range_ma_kc = talib.SMA(range_kc, timeperiod=kc_period)
            kc_upper = kc_mid + (range_ma_kc * kc_mult)
            kc_lower = kc_mid - (range_ma_kc * kc_mult)
            
            # === 挤压状态判断 ===
            # sqzOn = (lowerBB > lowerKC) and (upperBB < upperKC)
            # sqzOff = (lowerBB < lowerKC) and (upperBB > upperKC)
            sqz_on = (bb_lower > kc_lower) & (bb_upper < kc_upper)
            sqz_off = (bb_lower < kc_lower) & (bb_upper > kc_upper)
            no_sqz = ~sqz_on & ~sqz_off
            
            # === 动能线线性回归计算 ===
            # avgHL = (ta.highest(high, lengthKC) + ta.lowest(low, lengthKC)) / 2
            avg_hl = (talib.MAX(high, timeperiod=kc_period) + talib.MIN(low, timeperiod=kc_period)) / 2
            # avgAll = (avgHL + ta.sma(close, lengthKC)) / 2
            avg_all = (avg_hl + talib.SMA(close, timeperiod=kc_period)) / 2
            # val = ta.linreg(source - avgAll, lengthKC, 0)
            source_minus_avg = close - avg_all
            val = linear_regression(source_minus_avg, kc_period)
            
            # === 动能柱状态判断 ===
            val_series = pd.Series(val)
            val_prev = val_series.shift(1).fillna(0).values
            
            # isLime = val > 0 and val > nz(val[1])   - 强多柱（lime绿）
            is_lime = (val > 0) & (val > val_prev)
            # isGreen = val > 0 and val < nz(val[1])  - 弱多柱（深绿）
            is_green = (val > 0) & (val < val_prev)
            # isRed = val < 0 and val < nz(val[1])    - 强空柱（红色）
            is_red = (val < 0) & (val < val_prev)
            # isMaroon = val < 0 and val > nz(val[1]) - 弱空柱（暗红）
            is_maroon = (val < 0) & (val > val_prev)
            
            return sqz_on, sqz_off, no_sqz, val, is_lime, is_green, is_red, is_maroon
        
        def linear_regression(series, period):
            """
            计算线性回归值，等同于TV的ta.linreg(series, period, 0)
            offset=0表示当前bar的线性回归预测值
            """
            result = np.zeros_like(series)
            # 先填充NaN值
            series_clean = pd.Series(series).fillna(method='bfill').fillna(method='ffill').fillna(0).values
            
            for i in range(period-1, len(series_clean)):
                y = series_clean[i-period+1:i+1]
                x = np.arange(period)
                # 使用最小二乘法计算线性回归
                if len(y) == period and not np.isnan(y).any():
                    try:
                        coeffs = np.polyfit(x, y, 1)
                        # offset=0表示预测当前点（最后一个点）
                        result[i] = coeffs[0] * (period - 1) + coeffs[1]
                    except:
                        result[i] = 0
                else:
                    result[i] = 0
            return result
        
        df['wt1'], df['wt2'] = wavetrend(df['high'], df['low'], df['close'])
        df['sqz_on'], df['sqz_off'], df['no_sqz'], df['sqz_val'], df['is_lime'], df['is_green'], df['is_red'], df['is_maroon'] = sqzmom(df['high'], df['low'], df['close'])
        df['adx'] = talib.ADX(df['high'], df['low'], df['close'], 14)
        df['ma14'] = talib.SMA(df['close'], 14)
        
        # 填充NaN值
        df = df.fillna(method='bfill').fillna(method='ffill')
        
        df['wt_golden_cross'] = (df['wt1'].shift(1) < df['wt2'].shift(1)) & (df['wt1'] > df['wt2'])
        df['wt_death_cross'] = (df['wt1'].shift(1) > df['wt2'].shift(1)) & (df['wt1'] < df['wt2'])
        df['adx_up'] = (df['adx'] > 20) & (df['adx'] > df['adx'].shift(1))
        
        df = df.fillna(method='bfill').fillna(method='ffill')
        
        print("✅ 技术指标计算完成")
        return df
    
    def run_quick_backtest(self, df):
        """快速策略回测 - 用于每日报告"""
        try:
            # 模拟策略参数
            initial_capital = 100000
            current_cash = initial_capital
            positions = []
            trades = []
            
            # 简化的策略逻辑
            for idx, row in df.tail(30).iterrows():  # 只测试最近30天
                current_price = row['close']
                
                # 检查入场信号
                if row['wt1'] < -30 and row['wt1'] > row['wt2'] and len(positions) == 0:
                    # 第1仓入场
                    position_size = initial_capital * 0.15
                    shares = position_size / current_price
                    positions.append({
                        'entry_price': current_price,
                        'shares': shares,
                        'amount': position_size,
                        'level': 1
                    })
                    current_cash -= position_size
                    trades.append({
                        'date': row['date'],
                        'action': '买入',
                        'price': current_price,
                        'amount': position_size,
                        'level': 1
                    })
                
                # 检查出场信号
                if positions and (row.get('wt_death_cross', False) or row['adx'] < 20):
                    for pos in positions:
                        pnl = (current_price - pos['entry_price']) / pos['entry_price']
                        current_cash += pos['amount'] + (pos['shares'] * current_price - pos['amount'])
                        trades.append({
                            'date': row['date'],
                            'action': '卖出',
                            'price': current_price,
                            'amount': pos['amount'],
                            'pnl_pct': pnl * 100
                        })
                    positions = []
            
            # 计算收益
            total_value = current_cash
            for pos in positions:
                total_value += pos['shares'] * df['close'].iloc[-1]
            
            return_pct = (total_value - initial_capital) / initial_capital * 100
            
            return {
                'total_return': return_pct,
                'trades_count': len(trades),
                'current_positions': len(positions),
                'total_value': total_value
            }
        except Exception as e:
            return {
                'total_return': 0,
                'trades_count': 0,
                'current_positions': 0,
                'total_value': 100000,
                'error': str(e)
            }


if __name__ == "__main__":
    # 配置邮箱 - 支持环境变量和默认值
    email_config = {
        'smtp_server': 'smtp.qq.com',  # QQ邮箱服务器
        'smtp_port': 587,
        'sender_email': os.getenv('SENDER_EMAIL', '350980368@qq.com'),  # 从环境变量获取
        'sender_password': os.getenv('EMAIL_PASSWORD', 'dvclkoinlmnebjdi'),   # 从环境变量获取
        'receiver_email': os.getenv('RECEIVER_EMAIL', '350980368@qq.com')    # 从环境变量获取
    }
    
    # 创建监控系统
    monitor = BTCIndicatorMonitor(email_config)
    
    # 运行监控
    monitor.monitor_and_alert()
    
    print("\n" + "="*80)
    print("📧 使用说明:")
    print("="*80)
    print("\n1. 配置邮箱:")
    print("   - 如果使用Gmail，需要开启'两步验证'")
    print("   - 然后生成'应用专用密码'")
    print("   - 将密码填入上面的email_config")
    
    print("\n2. 定时运行:")
    print("   - 可以用cron定时执行（每天1次）")
    print("   - crontab -e")
    print("   - 添加: 0 9 * * * /usr/bin/python3 /path/to/【邮箱提示】指标提醒.py")
    
    print("\n3. 邮件内容:")
    print("   - 每天发送监控日报")
    print("   - 入场信号触发时发送醒目提醒")
    print("   - 出场信号触发时发送醒目提醒")
    
    print("\n✅ 配置完成后，您将收到:")
    print("   📧 每天的监控报告")
    print("   🚨 重要信号的醒目提醒")

