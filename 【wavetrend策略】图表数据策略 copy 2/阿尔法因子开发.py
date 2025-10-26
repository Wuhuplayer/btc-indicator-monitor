#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BTC阿尔法因子开发与测试
开发多个因子，评估其预测能力和收益表现
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from scipy import stats

sys.path.append(str(Path(__file__).parent / '模块'))
from 数据模块 import DataModule


class AlphaFactorLibrary:
    """阿尔法因子库"""
    
    def __init__(self):
        pass
    
    # ========== 技术因子 ==========
    
    def factor_rsi_reversal(self, df, period=14):
        """
        因子1: RSI反转因子
        假设：极度超卖后会反弹
        """
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # 因子值：RSI越低，因子值越高（看涨信号）
        factor = (30 - rsi) / 30
        factor = factor.clip(lower=-1, upper=1)  # 标准化到[-1, 1]
        return factor
    
    def factor_momentum(self, df, lookback=20):
        """
        因子2: 动量因子
        假设：过去涨得好的会继续涨
        """
        returns = df['close'].pct_change(lookback)
        # 标准化
        factor = (returns - returns.mean()) / returns.std()
        return factor
    
    def factor_volatility(self, df, window=20):
        """
        因子3: 波动率因子
        假设：低波动率后会有大行情
        """
        returns = df['close'].pct_change()
        volatility = returns.rolling(window=window).std()
        
        # 因子值：波动率越低，因子值越高（预期大行情）
        factor = -volatility
        factor = (factor - factor.mean()) / factor.std()
        return factor
    
    def factor_wavetrend_deep_oversold(self, df):
        """
        因子4: WaveTrend深度超卖因子
        假设：wt1<-60的深度超卖会强力反弹
        """
        # 计算WaveTrend
        n1, n2 = 10, 21
        hlc3 = (df['high'] + df['low'] + df['close']) / 3
        esa = hlc3.ewm(span=n1, adjust=False).mean()
        d = (hlc3 - esa).abs().ewm(span=n1, adjust=False).mean()
        ci = (hlc3 - esa) / (0.015 * d)
        wt1 = ci.ewm(span=n2, adjust=False).mean()  # EMA - TradingView标准
        
        # 因子值：wt1越低（越超卖），因子值越高
        factor = (-wt1 - 40) / 40  # -40以下才有值
        factor = factor.clip(lower=0, upper=2)
        return factor
    
    def factor_mean_reversion(self, df, window=200):
        """
        因子5: 均值回归因子
        假设：价格偏离长期均线太多会回归
        """
        ma = df['close'].rolling(window=window).mean()
        deviation = (df['close'] - ma) / ma
        
        # 因子值：负偏离越大（越便宜），因子值越高
        factor = -deviation
        factor = (factor - factor.mean()) / factor.std()
        return factor
    
    # ========== 链上数据因子 ==========
    
    def factor_mvrv_value(self, df):
        """
        因子6: MVRV价值因子
        假设：MVRV<1是低估，会上涨
        """
        if 'sth_mvrv' not in df.columns:
            return pd.Series(0, index=df.index)
        
        mvrv = df['sth_mvrv']
        # 因子值：MVRV越低，因子值越高
        factor = (1 - mvrv).clip(lower=-2, upper=2)
        return factor
    
    def factor_whale_accumulation(self, df):
        """
        因子7: 鲸鱼增持因子
        假设：大户买入是看涨信号
        """
        if 'whale_holdings_change' not in df.columns:
            return pd.Series(0, index=df.index)
        
        # 标准化
        factor = df['whale_holdings_change']
        factor = (factor - factor.mean()) / factor.std()
        return factor
    
    def factor_lth_hodl(self, df):
        """
        因子8: LTH囤币因子
        假设：长期持有者增持是强看涨信号
        """
        if 'lth_net_change_30d' not in df.columns:
            return pd.Series(0, index=df.index)
        
        lth = df['lth_net_change_30d']
        # 标准化
        factor = (lth - lth.mean()) / lth.std()
        return factor
    
    # ========== 趋势因子 ==========
    
    def factor_trend_strength(self, df, period=14):
        """
        因子9: 趋势强度因子
        使用ADX衡量趋势强度
        """
        high_diff = df['high'].diff()
        low_diff = -df['low'].diff()
        
        plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
        minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)
        
        tr1 = df['high'] - df['low']
        tr2 = abs(df['high'] - df['close'].shift())
        tr3 = abs(df['low'] - df['close'].shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        atr = tr.rolling(window=period).mean()
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()
        
        # 因子值：趋势越强（ADX越高），因子值越高
        factor = (adx - 20) / 20
        factor = factor.clip(lower=-1, upper=2)
        return factor
    
    def factor_ma_cross(self, df, fast=50, slow=200):
        """
        因子10: 移动平均线交叉因子
        假设：金叉看涨，死叉看跌
        """
        ma_fast = df['close'].rolling(window=fast).mean()
        ma_slow = df['close'].rolling(window=slow).mean()
        
        # 因子值：快线在慢线上方为正，下方为负
        factor = (ma_fast - ma_slow) / ma_slow
        factor = factor.clip(lower=-0.2, upper=0.2) * 5  # 放大到合理范围
        return factor


class FactorAnalyzer:
    """因子分析器"""
    
    def __init__(self):
        self.factor_lib = AlphaFactorLibrary()
    
    def calculate_all_factors(self, df):
        """计算所有因子"""
        print("📊 计算所有阿尔法因子...")
        
        df = df.copy()
        
        # 技术因子
        df['factor_rsi_reversal'] = self.factor_lib.factor_rsi_reversal(df)
        df['factor_momentum'] = self.factor_lib.factor_momentum(df)
        df['factor_volatility'] = self.factor_lib.factor_volatility(df)
        df['factor_wt_oversold'] = self.factor_lib.factor_wavetrend_deep_oversold(df)
        df['factor_mean_reversion'] = self.factor_lib.factor_mean_reversion(df)
        
        # 链上因子
        df['factor_mvrv'] = self.factor_lib.factor_mvrv_value(df)
        df['factor_whale'] = self.factor_lib.factor_whale_accumulation(df)
        df['factor_lth'] = self.factor_lib.factor_lth_hodl(df)
        
        # 趋势因子
        df['factor_trend'] = self.factor_lib.factor_trend_strength(df)
        df['factor_ma_cross'] = self.factor_lib.factor_ma_cross(df)
        
        # 计算未来收益（用于评估因子）
        df['future_return_5d'] = df['close'].pct_change(5).shift(-5)
        df['future_return_20d'] = df['close'].pct_change(20).shift(-20)
        df['future_return_60d'] = df['close'].pct_change(60).shift(-60)
        
        print("✅ 因子计算完成")
        return df
    
    def calculate_ic(self, factor_values, future_returns):
        """
        计算IC值 (Information Coefficient)
        衡量因子预测能力
        """
        # 删除NaN值
        valid_data = pd.DataFrame({
            'factor': factor_values,
            'return': future_returns
        }).dropna()
        
        if len(valid_data) < 30:
            return np.nan, np.nan
        
        # 计算Spearman相关系数
        ic, p_value = stats.spearmanr(valid_data['factor'], valid_data['return'])
        return ic, p_value
    
    def evaluate_factors(self, df):
        """评估所有因子的表现"""
        print()
        print("=" * 100)
        print("📊 因子评估报告")
        print("=" * 100)
        print()
        
        factor_cols = [col for col in df.columns if col.startswith('factor_')]
        
        results = []
        
        for factor_name in factor_cols:
            factor_display_name = factor_name.replace('factor_', '').replace('_', ' ').title()
            
            # 计算不同周期的IC值
            ic_5d, p_5d = self.calculate_ic(df[factor_name], df['future_return_5d'])
            ic_20d, p_20d = self.calculate_ic(df[factor_name], df['future_return_20d'])
            ic_60d, p_60d = self.calculate_ic(df[factor_name], df['future_return_60d'])
            
            # 计算因子的均值和标准差
            factor_mean = df[factor_name].mean()
            factor_std = df[factor_name].std()
            
            results.append({
                'factor': factor_display_name,
                'ic_5d': ic_5d,
                'p_5d': p_5d,
                'ic_20d': ic_20d,
                'p_20d': p_20d,
                'ic_60d': ic_60d,
                'p_60d': p_60d,
                'mean': factor_mean,
                'std': factor_std
            })
        
        results_df = pd.DataFrame(results)
        
        # 显示结果
        print("IC值评估（IC越高，预测能力越强，>0.05为有效因子）:")
        print()
        print(f"{'因子名称':<25} {'IC(5日)':<12} {'IC(20日)':<12} {'IC(60日)':<12} {'评级':<10}")
        print("-" * 100)
        
        for _, row in results_df.iterrows():
            # 评级
            max_ic = max(abs(row['ic_5d']) if not pd.isna(row['ic_5d']) else 0,
                        abs(row['ic_20d']) if not pd.isna(row['ic_20d']) else 0,
                        abs(row['ic_60d']) if not pd.isna(row['ic_60d']) else 0)
            
            if max_ic > 0.10:
                rating = "⭐⭐⭐"
            elif max_ic > 0.05:
                rating = "⭐⭐"
            elif max_ic > 0.02:
                rating = "⭐"
            else:
                rating = "❌"
            
            ic_5d_str = f"{row['ic_5d']:+.4f}" if not pd.isna(row['ic_5d']) else "N/A"
            ic_20d_str = f"{row['ic_20d']:+.4f}" if not pd.isna(row['ic_20d']) else "N/A"
            ic_60d_str = f"{row['ic_60d']:+.4f}" if not pd.isna(row['ic_60d']) else "N/A"
            
            print(f"{row['factor']:<25} {ic_5d_str:<12} {ic_20d_str:<12} {ic_60d_str:<12} {rating:<10}")
        
        print()
        print("=" * 100)
        
        return results_df
    
    def test_factor_strategy(self, df, factor_name, threshold=0.5):
        """
        测试单个因子的交易策略
        策略：因子值>threshold时买入，<-threshold时卖出
        """
        print()
        print(f"🔍 测试因子策略: {factor_name.replace('factor_', '').replace('_', ' ').title()}")
        print("-" * 80)
        
        df = df.copy()
        df = df.dropna(subset=[factor_name, 'close'])
        
        initial_capital = 10000
        cash = initial_capital
        btc_holdings = 0
        
        trades = []
        portfolio_values = []
        
        for i in range(len(df)):
            row = df.iloc[i]
            price = row['close']
            factor_value = row[factor_name]
            
            # 买入信号
            if factor_value > threshold and btc_holdings == 0 and cash > 0:
                btc_holdings = (cash * 0.95) / price
                cash = cash * 0.05
                trades.append({'date': row['date'], 'action': 'BUY', 'price': price})
            
            # 卖出信号
            elif factor_value < -threshold and btc_holdings > 0:
                cash += btc_holdings * price
                btc_holdings = 0
                trades.append({'date': row['date'], 'action': 'SELL', 'price': price})
            
            total_value = cash + btc_holdings * price
            portfolio_values.append(total_value)
        
        final_value = portfolio_values[-1]
        total_return = (final_value - initial_capital) / initial_capital * 100
        
        # 计算最大回撤
        peak = initial_capital
        max_dd = 0
        for value in portfolio_values:
            if value > peak:
                peak = value
            dd = (peak - value) / peak * 100
            if dd > max_dd:
                max_dd = dd
        
        print(f"  交易次数: {len(trades)}")
        print(f"  最终收益: {total_return:+.2f}%")
        print(f"  最大回撤: -{max_dd:.2f}%")
        
        return total_return, max_dd, len(trades)


def main():
    print("=" * 100)
    print("🎯 BTC阿尔法因子开发与测试")
    print("=" * 100)
    print()
    
    # 1. 加载数据
    print("【步骤1】加载数据...")
    data_module = DataModule()
    price_data = data_module.get_price_data()
    
    # 加载链上数据
    try:
        chart_data = data_module.digitize_chart_data()
        chart_data['date'] = pd.to_datetime(chart_data['date'])
        full_data = price_data.merge(chart_data, on='date', how='left')
        full_data = full_data.ffill().bfill()
        print(f"✅ 已加载价格数据和链上数据")
    except:
        full_data = price_data
        print(f"⚠️  仅加载价格数据")
    print()
    
    # 2. 计算因子
    print("【步骤2】计算阿尔法因子...")
    analyzer = FactorAnalyzer()
    df_with_factors = analyzer.calculate_all_factors(full_data)
    print()
    
    # 3. 评估因子
    print("【步骤3】评估因子有效性...")
    results = analyzer.evaluate_factors(df_with_factors)
    print()
    
    # 4. 测试最佳因子的策略
    print("【步骤4】测试因子策略...")
    print()
    
    # 选择IC值最高的几个因子测试
    factor_cols = [col for col in df_with_factors.columns if col.startswith('factor_')]
    
    strategy_results = []
    for factor_col in factor_cols[:5]:  # 测试前5个因子
        ret, dd, trades = analyzer.test_factor_strategy(df_with_factors, factor_col, threshold=0.3)
        strategy_results.append({
            'factor': factor_col.replace('factor_', '').replace('_', ' ').title(),
            'return': ret,
            'max_dd': dd,
            'trades': trades
        })
    
    print()
    print("=" * 100)
    print("📊 因子策略表现对比")
    print("=" * 100)
    print()
    
    # 对比买入持有
    start_price = full_data.iloc[0]['close']
    end_price = full_data.iloc[-1]['close']
    hold_return = (end_price / start_price - 1) * 100
    
    print(f"{'策略':<25} {'收益率':<15} {'最大回撤':<15} {'交易次数':<10}")
    print("-" * 100)
    print(f"{'买入持有':<25} {hold_return:+.2f}%         {'-81.00%':<15} {0:<10}")
    
    for result in strategy_results:
        print(f"{result['factor']:<25} {result['return']:+.2f}%         {-result['max_dd']:.2f}%         {result['trades']:<10}")
    
    print()
    print("=" * 100)
    
    # 保存结果
    results.to_csv('数字化数据/factor_evaluation.csv', index=False, encoding='utf-8-sig')
    print()
    print("✅ 因子评估结果已保存: 数字化数据/factor_evaluation.csv")
    print()


if __name__ == "__main__":
    main()

