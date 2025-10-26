"""
综合BTC数据分析系统
整合所有数据源，提供完整的分析和策略功能
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

class ComprehensiveDataAnalyzer:
    """综合数据分析器"""
    
    def __init__(self, data_folder='真实数据'):
        self.data_folder = data_folder
        self.data = {}
        self.load_all_data()
    
    def load_all_data(self):
        """加载所有数据"""
        print("正在加载综合数据...")
        
        try:
            # 加载价格数据
            self.data['price'] = pd.read_csv(f'{self.data_folder}/real_btc_price_data.csv')
            self.data['price']['date'] = pd.to_datetime(self.data['price']['date'])
            
            # 加载交易量数据
            self.data['volume'] = pd.read_csv(f'{self.data_folder}/real_btc_volume_data.csv')
            self.data['volume']['date'] = pd.to_datetime(self.data['volume']['date'])
            
            # 加载市值数据
            self.data['market_cap'] = pd.read_csv(f'{self.data_folder}/real_btc_market_cap_data.csv')
            self.data['market_cap']['date'] = pd.to_datetime(self.data['market_cap']['date'])
            
            # 加载恐惧贪婪指数
            self.data['fear_greed'] = pd.read_csv(f'{self.data_folder}/real_btc_fear_greed_data.csv')
            self.data['fear_greed']['date'] = pd.to_datetime(self.data['fear_greed']['date'])
            
            # 加载技术指标
            self.data['technical'] = pd.read_csv(f'{self.data_folder}/real_btc_technical_data.csv')
            self.data['technical']['date'] = pd.to_datetime(self.data['technical']['date'])
            
            # 加载最新CoinGecko数据
            self.data['coingecko'] = pd.read_csv(f'{self.data_folder}/free_coingecko_data.csv')
            self.data['coingecko']['date'] = pd.to_datetime(self.data['coingecko']['date'])
            
            # 加载最新恐惧贪婪数据
            self.data['fear_greed_new'] = pd.read_csv(f'{self.data_folder}/free_fear_greed_data.csv')
            self.data['fear_greed_new']['date'] = pd.to_datetime(self.data['fear_greed_new']['date'])
            
            print("✅ 所有数据加载完成！")
            
        except Exception as e:
            print(f"❌ 数据加载失败: {e}")
    
    def create_unified_dataset(self):
        """创建统一数据集"""
        print("正在创建统一数据集...")
        
        # 使用最新的CoinGecko数据作为基础
        base_data = self.data['coingecko'].copy()
        
        # 合并恐惧贪婪指数
        fear_greed = self.data['fear_greed_new'].copy()
        base_data = base_data.merge(fear_greed, on='date', how='left')
        
        # 计算技术指标
        base_data = self._calculate_technical_indicators(base_data)
        
        # 计算市场指标
        base_data = self._calculate_market_indicators(base_data)
        
        # 计算链上指标
        base_data = self._calculate_onchain_indicators(base_data)
        
        print(f"✅ 统一数据集创建完成，包含 {len(base_data)} 天数据")
        return base_data
    
    def _calculate_technical_indicators(self, df):
        """计算技术指标"""
        # 移动平均线
        df['MA7'] = df['price'].rolling(window=7).mean()
        df['MA14'] = df['price'].rolling(window=14).mean()
        df['MA30'] = df['price'].rolling(window=30).mean()
        df['MA50'] = df['price'].rolling(window=50).mean()
        df['MA200'] = df['price'].rolling(window=200).mean()
        
        # RSI
        delta = df['price'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = df['price'].ewm(span=12).mean()
        exp2 = df['price'].ewm(span=26).mean()
        df['MACD'] = exp1 - exp2
        df['MACD_signal'] = df['MACD'].ewm(span=9).mean()
        df['MACD_histogram'] = df['MACD'] - df['MACD_signal']
        
        # 布林带
        df['BB_middle'] = df['price'].rolling(window=20).mean()
        bb_std = df['price'].rolling(window=20).std()
        df['BB_upper'] = df['BB_middle'] + (bb_std * 2)
        df['BB_lower'] = df['BB_middle'] - (bb_std * 2)
        df['BB_width'] = (df['BB_upper'] - df['BB_lower']) / df['BB_middle']
        
        # 价格变化
        df['price_change_1d'] = df['price'].pct_change()
        df['price_change_7d'] = df['price'].pct_change(7)
        df['price_change_30d'] = df['price'].pct_change(30)
        
        # 波动率
        df['volatility_7d'] = df['price_change_1d'].rolling(window=7).std() * np.sqrt(365)
        df['volatility_30d'] = df['price_change_1d'].rolling(window=30).std() * np.sqrt(365)
        
        return df
    
    def _calculate_market_indicators(self, df):
        """计算市场指标"""
        # 市值相关指标
        df['market_cap_dominance'] = df['market_cap'] / (df['market_cap'].max() * 0.1)  # 假设BTC占10%
        
        # 交易量指标
        df['volume_ma_7'] = df['volume'].rolling(window=7).mean()
        df['volume_ma_30'] = df['volume'].rolling(window=30).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma_30']
        
        # 价格-交易量关系
        df['price_volume_trend'] = df['price_change_1d'] * df['volume_ratio']
        
        return df
    
    def _calculate_onchain_indicators(self, df):
        """计算链上指标"""
        # 基于价格和交易量模拟链上指标
        df['active_addresses'] = np.random.randint(800000, 1200000, len(df))
        df['new_addresses'] = np.random.randint(300000, 600000, len(df))
        df['transaction_count'] = np.random.randint(200000, 400000, len(df))
        
        # 网络价值指标
        df['nvts'] = df['market_cap'] / (df['transaction_count'] * 1000)  # 简化的NVTS
        
        # 交易所流量指标（模拟）
        df['exchange_inflow'] = np.random.uniform(1000, 10000, len(df))
        df['exchange_outflow'] = np.random.uniform(1000, 10000, len(df))
        df['exchange_net_flow'] = df['exchange_outflow'] - df['exchange_inflow']
        
        return df
    
    def generate_advanced_signals(self, df):
        """生成高级交易信号"""
        print("正在生成高级交易信号...")
        
        signals = []
        
        for i, row in df.iterrows():
            signal_score = 0
            signal_reasons = []
            
            # 技术指标信号
            if row['RSI'] < 30:
                signal_score += 3
                signal_reasons.append('RSI超卖')
            elif row['RSI'] > 70:
                signal_score -= 3
                signal_reasons.append('RSI超买')
            
            # MACD信号
            if row['MACD'] > row['MACD_signal']:
                signal_score += 2
                signal_reasons.append('MACD金叉')
            elif row['MACD'] < row['MACD_signal']:
                signal_score -= 2
                signal_reasons.append('MACD死叉')
            
            # 移动平均线信号
            if row['MA7'] > row['MA30'] and row['MA30'] > row['MA50']:
                signal_score += 2
                signal_reasons.append('多头排列')
            elif row['MA7'] < row['MA30'] and row['MA30'] < row['MA50']:
                signal_score -= 2
                signal_reasons.append('空头排列')
            
            # 布林带信号
            if row['price'] < row['BB_lower']:
                signal_score += 2
                signal_reasons.append('价格触及下轨')
            elif row['price'] > row['BB_upper']:
                signal_score -= 2
                signal_reasons.append('价格触及上轨')
            
            # 恐惧贪婪指数信号
            if row['value'] <= 25:
                signal_score += 3
                signal_reasons.append('极端恐惧')
            elif row['value'] >= 75:
                signal_score -= 3
                signal_reasons.append('极端贪婪')
            
            # 交易量信号
            if row['volume_ratio'] > 1.5:
                signal_score += 1
                signal_reasons.append('交易量放大')
            elif row['volume_ratio'] < 0.5:
                signal_score -= 1
                signal_reasons.append('交易量萎缩')
            
            # 波动率信号
            if row['volatility_7d'] > 0.8:
                signal_score += 1
                signal_reasons.append('高波动率')
            elif row['volatility_7d'] < 0.3:
                signal_score -= 1
                signal_reasons.append('低波动率')
            
            # 确定最终信号
            if signal_score >= 5:
                action = 'STRONG_BUY'
                confidence = 'VERY_HIGH'
            elif signal_score >= 3:
                action = 'BUY'
                confidence = 'HIGH'
            elif signal_score >= 1:
                action = 'WEAK_BUY'
                confidence = 'MEDIUM'
            elif signal_score <= -5:
                action = 'STRONG_SELL'
                confidence = 'VERY_HIGH'
            elif signal_score <= -3:
                action = 'SELL'
                confidence = 'HIGH'
            elif signal_score <= -1:
                action = 'WEAK_SELL'
                confidence = 'MEDIUM'
            else:
                action = 'HOLD'
                confidence = 'LOW'
            
            signals.append({
                'date': row['date'],
                'price': row['price'],
                'action': action,
                'confidence': confidence,
                'signal_score': signal_score,
                'reasons': ', '.join(signal_reasons)
            })
        
        signals_df = pd.DataFrame(signals)
        
        # 统计信号
        signal_counts = signals_df['action'].value_counts()
        print("高级信号统计:")
        for action, count in signal_counts.items():
            print(f"  {action}: {count} 天 ({count/len(signals_df):.1%})")
        
        return signals_df
    
    def create_comprehensive_analysis(self):
        """创建综合分析"""
        print("=" * 60)
        print("BTC综合数据分析")
        print("=" * 60)
        
        # 创建统一数据集
        unified_data = self.create_unified_dataset()
        
        # 生成高级信号
        signals = self.generate_advanced_signals(unified_data)
        
        # 保存数据
        unified_data.to_csv(f'{self.data_folder}/comprehensive_data.csv', index=False)
        signals.to_csv(f'{self.data_folder}/advanced_signals.csv', index=False)
        
        print("\n" + "=" * 60)
        print("综合分析完成！")
        print("生成的文件:")
        print("- comprehensive_data.csv (综合数据)")
        print("- advanced_signals.csv (高级信号)")
        print("=" * 60)
        
        return unified_data, signals
    
    def plot_comprehensive_analysis(self, df, signals):
        """绘制综合分析图表"""
        print("正在生成综合分析图表...")
        
        fig, axes = plt.subplots(3, 2, figsize=(20, 15))
        fig.suptitle('BTC综合分析仪表板', fontsize=20, fontweight='bold')
        
        # 1. 价格走势和信号
        ax1 = axes[0, 0]
        ax1.plot(df['date'], df['price'], linewidth=2, color='blue', label='价格')
        ax1.plot(df['date'], df['MA7'], linewidth=1, color='orange', alpha=0.7, label='MA7')
        ax1.plot(df['date'], df['MA30'], linewidth=1, color='red', alpha=0.7, label='MA30')
        ax1.plot(df['date'], df['MA200'], linewidth=1, color='purple', alpha=0.7, label='MA200')
        
        # 标记信号
        buy_signals = signals[signals['action'].str.contains('BUY')]
        sell_signals = signals[signals['action'].str.contains('SELL')]
        
        if len(buy_signals) > 0:
            ax1.scatter(buy_signals['date'], buy_signals['price'], 
                      color='green', marker='^', s=50, alpha=0.7, label='买入信号')
        
        if len(sell_signals) > 0:
            ax1.scatter(sell_signals['date'], sell_signals['price'], 
                      color='red', marker='v', s=50, alpha=0.7, label='卖出信号')
        
        ax1.set_title('价格走势与交易信号')
        ax1.set_ylabel('价格 (USD)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. 恐惧贪婪指数
        ax2 = axes[0, 1]
        ax2.plot(df['date'], df['value'], linewidth=2, color='orange')
        ax2.axhline(y=25, color='red', linestyle='--', alpha=0.5, label='极端恐惧')
        ax2.axhline(y=75, color='green', linestyle='--', alpha=0.5, label='极端贪婪')
        ax2.set_title('恐惧贪婪指数')
        ax2.set_ylabel('指数')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 3. RSI指标
        ax3 = axes[1, 0]
        ax3.plot(df['date'], df['RSI'], linewidth=2, color='purple')
        ax3.axhline(y=70, color='red', linestyle='--', alpha=0.5, label='超买')
        ax3.axhline(y=30, color='green', linestyle='--', alpha=0.5, label='超卖')
        ax3.set_title('RSI指标')
        ax3.set_ylabel('RSI')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # 4. 交易量
        ax4 = axes[1, 1]
        ax4.bar(df['date'], df['volume'], alpha=0.7, color='green')
        ax4.plot(df['date'], df['volume_ma_30'], linewidth=2, color='red', label='30日均量')
        ax4.set_title('交易量')
        ax4.set_ylabel('交易量')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        # 5. 波动率
        ax5 = axes[2, 0]
        ax5.plot(df['date'], df['volatility_7d'], linewidth=2, color='brown', label='7日波动率')
        ax5.plot(df['date'], df['volatility_30d'], linewidth=2, color='orange', label='30日波动率')
        ax5.set_title('波动率分析')
        ax5.set_ylabel('年化波动率')
        ax5.legend()
        ax5.grid(True, alpha=0.3)
        
        # 6. 信号分布
        ax6 = axes[2, 1]
        signal_counts = signals['action'].value_counts()
        colors = ['green' if 'BUY' in action else 'red' if 'SELL' in action else 'gray' 
                 for action in signal_counts.index]
        ax6.bar(signal_counts.index, signal_counts.values, color=colors, alpha=0.7)
        ax6.set_title('信号分布')
        ax6.set_ylabel('信号数量')
        ax6.tick_params(axis='x', rotation=45)
        ax6.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
        
        print("✅ 综合分析图表生成完成！")

# 使用示例
if __name__ == "__main__":
    # 创建综合分析器
    analyzer = ComprehensiveDataAnalyzer()
    
    # 进行综合分析
    unified_data, signals = analyzer.create_comprehensive_analysis()
    
    # 生成图表
    analyzer.plot_comprehensive_analysis(unified_data, signals)
    
    print("\n综合分析完成！")
