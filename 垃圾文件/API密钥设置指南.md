# 全球链上数据API密钥设置指南

## 🌍 支持的链上数据API

### 1. Glassnode（推荐）
- **网站**: https://glassnode.com/
- **免费额度**: 每月10,000次请求
- **数据质量**: ⭐⭐⭐⭐⭐ 最高
- **包含指标**: MVRV、UTXO、鲸鱼数据、LTH数据等

#### 获取免费API密钥：
1. 访问 https://glassnode.com/
2. 点击 "Sign Up" 注册账号
3. 验证邮箱
4. 登录后进入 "API" 页面
5. 创建新的API密钥
6. 复制API密钥

### 2. CryptoQuant
- **网站**: https://cryptoquant.com/
- **免费额度**: 有限
- **数据质量**: ⭐⭐⭐⭐⭐ 最高
- **包含指标**: 交易所数据、矿工数据、链上指标

#### 获取免费API密钥：
1. 访问 https://cryptoquant.com/
2. 注册账号
3. 进入API设置页面
4. 创建API密钥

### 3. 免费API（无需密钥）
- **Blockchain.info**: 基础区块数据
- **Blockstream**: 区块和交易数据
- **Mempool.space**: 网络状态数据
- **Alternative.me**: 恐惧贪婪指数

## 🔧 使用方法

### 方法1：在代码中设置API密钥

```python
from BTC策略分析系统 import BTCStrategyAnalyzer

# 创建分析器
analyzer = BTCStrategyAnalyzer()

# 设置API密钥
glassnode_key = "YOUR_GLASSNODE_API_KEY"
analyzer.set_api_keys(glassnode_key=glassnode_key)

# 运行分析（使用真实链上数据）
results, latest = analyzer.run_complete_analysis(use_real_onchain=True, days=365)
```

### 方法2：使用环境变量

```bash
# 设置环境变量
export GLASSNODE_API_KEY="YOUR_GLASSNODE_API_KEY"
export CRYPTOQUANT_API_KEY="YOUR_CRYPTOQUANT_API_KEY"
```

```python
import os
from BTC策略分析系统 import BTCStrategyAnalyzer

# 创建分析器
analyzer = BTCStrategyAnalyzer()

# 从环境变量读取API密钥
glassnode_key = os.getenv('GLASSNODE_API_KEY')
cryptoquant_key = os.getenv('CRYPTOQUANT_API_KEY')

if glassnode_key:
    analyzer.set_api_keys(glassnode_key=glassnode_key)
if cryptoquant_key:
    analyzer.set_api_keys(cryptoquant_key=cryptoquant_key)

# 运行分析
results, latest = analyzer.run_complete_analysis(use_real_onchain=True)
```

## 📊 数据质量对比

| 数据源 | 真实性 | 完整性 | 更新频率 | 成本 |
|--------|--------|--------|----------|------|
| Glassnode | ✅ 真实 | ✅ 完整 | 实时 | 免费版有限制 |
| CryptoQuant | ✅ 真实 | ✅ 完整 | 实时 | 免费版有限制 |
| 免费API | ✅ 真实 | ⚠️ 有限 | 实时 | 免费 |
| 估算数据 | ❌ 估算 | ✅ 完整 | 实时 | 免费 |

## 🚀 推荐配置

### 初学者（免费）
```python
# 使用免费API和估算数据
analyzer = BTCStrategyAnalyzer()
results, latest = analyzer.run_complete_analysis(use_real_onchain=False)
```

### 进阶用户（免费API密钥）
```python
# 使用Glassnode免费API密钥
analyzer = BTCStrategyAnalyzer()
analyzer.set_api_keys(glassnode_key="YOUR_FREE_GLASSNODE_KEY")
results, latest = analyzer.run_complete_analysis(use_real_onchain=True)
```

### 专业用户（付费API）
```python
# 使用多个付费API
analyzer = BTCStrategyAnalyzer()
analyzer.set_api_keys(
    glassnode_key="YOUR_PAID_GLASSNODE_KEY",
    cryptoquant_key="YOUR_PAID_CRYPTOQUANT_KEY"
)
results, latest = analyzer.run_complete_analysis(use_real_onchain=True)
```

## ⚠️ 重要提醒

1. **API密钥安全**：
   - 不要将API密钥提交到代码仓库
   - 使用环境变量或配置文件
   - 定期轮换API密钥

2. **请求限制**：
   - 免费API通常有请求频率限制
   - 建议设置请求间隔避免超限

3. **数据准确性**：
   - 真实链上数据 > 估算数据
   - 多个数据源交叉验证更可靠

4. **成本控制**：
   - 免费额度通常足够个人使用
   - 付费版本适合高频交易或商业用途

## 🔗 相关链接

- [Glassnode API文档](https://docs.glassnode.com/)
- [CryptoQuant API文档](https://cryptoquant.com/api)
- [Blockchain.info API](https://blockchain.info/api)
- [Blockstream API](https://blockstream.info/api/)
- [Mempool.space API](https://mempool.space/api/)

## 📞 技术支持

如果遇到API集成问题：
1. 检查API密钥是否正确
2. 确认网络连接正常
3. 查看API文档了解参数要求
4. 联系我获取技术支持

---

**建议**：对于你的BTC策略项目，建议先使用免费API密钥获取真实的链上数据，这样能显著提高策略分析的准确性。
