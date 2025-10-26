#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BTC趋势交易策略 - 主运行脚本
使用整合后的核心模块
"""

import sys
import pandas as pd
from pathlib import Path

sys.path.append(str(Path(__file__).parent / '模块'))

from 核心策略模块 import ScoringModule, TrendTradingStrategy
from 核心回测模块 import TrendBacktestEngine
from 数据模块 import DataModule

def main():
    print("=" * 100)
    print("🎯 BTC趋势交易策略 - 完整系统")
    print("=" * 100)
    print()
    
    # 1. 加载数据
    print("【步骤1】加载数据...")
    print("-" * 100)
    data_module = DataModule()
    
    # 获取价格数据
    price_data = data_module.get_price_data()
    if price_data is None:
        print("❌ 无法获取价格数据")
        return
    print(f"✓ 价格数据: {len(price_data)}条记录")
    
    # 加载链上数据
    chart_data = data_module.digitize_chart_data()
    if chart_data is None:
        print("❌ 无法获取链上数据")
        return
    
    # 合并数据
    chart_data['date'] = pd.to_datetime(chart_data['date'])
    full_data = price_data.merge(chart_data, on='date', how='left')
    full_data = full_data.ffill().bfill()
    print(f"✓ 合并后数据: {len(full_data)}条记录")
    print()
    
    # 2. 加载正确的评分数据
    print("【步骤2】加载正确的评分数据...")
    print("-" * 100)
    try:
        # 优先使用已有的正确评分数据
        score_df = pd.read_csv('数字化数据/正确评分数据.csv')
        score_df['date'] = pd.to_datetime(score_df['date'])
        
        # 合并评分到full_data
        scored_data = full_data.merge(
            score_df[['date', 'total_score', 'mvrv_score', 'whale_score', 'lth_score']], 
            on='date', how='left'
        )
        scored_data = scored_data.ffill().bfill()
        print(f"✓ 已加载正确评分数据")
        
        # 显示评分分布
        score_dist = scored_data['total_score'].value_counts().sort_index()
        print(f"\n评分分布:")
        for score, count in score_dist.items():
            pct = count / len(scored_data) * 100
            if score >= 5:
                label = "抄底区"
            elif score >= 3:
                label = "定投区"
            elif score >= 1:
                label = "持有区"
            else:
                label = "观望区"
            print(f"  {score}分 ({label}): {count}天 ({pct:.1f}%)")
        
        target_days = ((scored_data['total_score'] >= 3) & (scored_data['total_score'] <= 6)).sum()
        print(f"\n✅ 3-6分区间: {target_days}天 ({target_days/len(scored_data)*100:.1f}%)")
        
    except Exception as e:
        print(f"⚠️  无法加载正确评分数据，使用计算的评分: {e}")
        scoring = ScoringModule()
        scored_data = scoring.calculate_period_scores(full_data)
    print()
    
    # 3. 运行策略
    print("【步骤3】运行趋势交易策略...")
    print("-" * 100)
    strategy = TrendTradingStrategy()
    strategy_results = strategy.run_strategy(scored_data)
    print()
    
    # 4. 运行回测
    print("【步骤4】运行回测...")
    print("-" * 100)
    backtest = TrendBacktestEngine(initial_capital=10000, max_loss_per_trade=0.10)
    portfolio_df, trades_df = backtest.run_backtest(strategy_results)
    
    # 5. 保存结果
    print("【步骤5】保存结果...")
    print("-" * 100)
    backtest.save_results(portfolio_df, trades_df)
    
    # 6. 对比买入持有
    print("【步骤6】对比买入持有...")
    print("-" * 100)
    start_price = scored_data.iloc[0]['close']
    end_price = scored_data.iloc[-1]['close']
    hold_return = (end_price / start_price - 1) * 100
    strategy_return = (portfolio_df['total_value'].iloc[-1] / 10000 - 1) * 100
    
    print(f"\n📊 最终对比:")
    print(f"  买入持有: {hold_return:.2f}%")
    print(f"  趋势策略: {strategy_return:.2f}%")
    print(f"  差距: {(strategy_return - hold_return):.2f}%")
    
    if strategy_return > hold_return:
        print(f"\n✅ 策略跑赢买入持有！")
    else:
        print(f"\n⚠️  在超级牛市中跑输买入持有（正常现象）")
        print(f"    策略优势：最大回撤{portfolio_df['drawdown'].min():.2f}% vs 买入持有约-81%")
    
    print()
    print("=" * 100)
    print("✅ 完成！")
    print("=" * 100)
    print()
    print("📂 查看结果:")
    print("  • 数字化数据/final_backtest_portfolio.csv")
    print("  • 数字化数据/final_backtest_trades.csv")
    print()


if __name__ == "__main__":
    main()

